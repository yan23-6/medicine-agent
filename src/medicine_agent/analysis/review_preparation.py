"""Deterministic, read-only material preparation; no clinical or review writes."""
from collections import Counter
import json
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace

from medicine_agent.analysis.coverage import CoverageService
from medicine_agent.analysis.models import AnalysisError
from medicine_agent.analysis.reviews import build_review_queue, read_reviews, render_review_markdown
from medicine_agent.analysis.store import atomic_json
from medicine_agent.domain.ids import file_sha256, stable_id
from medicine_agent.domain.review_preparation import (ReviewPreparationRequest, ReviewPreparationReport,
    ReviewPreparationExport, SourceAnnotation, CandidateReviewItem, PreparationAnomaly,
    PreparationIssue, PreparationQualityGate)
from medicine_agent.packages.io import read_jsonl
from medicine_agent.packages.tcm import read_graph


def canonical(value):
    if hasattr(value, 'model_dump'):
        value = value.model_dump(mode='json')
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def ordered(values):
    return [v for _, v in sorted({canonical(v): v for v in values}.items())]


def merge_materials(values, identity, history_parents=None):
    result = {}
    for item in values:
        key = getattr(item, identity)
        if key in result:
            previous = result[key]
            if previous.model_dump(exclude={'origins'}) != item.model_dump(exclude={'origins'}):
                if isinstance(item, CandidateReviewItem):
                    immutable = {'origins', 'user_review_state', 'expected_previous_id', 'flags'}
                    if previous.model_dump(exclude=immutable) != item.model_dump(exclude=immutable):
                        raise AnalysisError('PREPARATION_IDENTITY_CONFLICT', 'Conflicting target content')
                    def ancestors(head):
                        seen = {None}
                        while head is not None and head not in seen:
                            seen.add(head)
                            head = (history_parents or {}).get(head)
                        return seen
                    left, right = previous.expected_previous_id, item.expected_previous_id
                    if 'history_invalid' not in {previous.user_review_state, item.user_review_state} and left in ancestors(right):
                        previous.user_review_state = item.user_review_state
                        previous.expected_previous_id = right
                    elif 'history_invalid' not in {previous.user_review_state, item.user_review_state} and right in ancestors(left):
                        pass
                    else:
                        previous.user_review_state = 'history_invalid'
                        previous.expected_previous_id = None
                        previous.flags = sorted(set(previous.flags + ['review_history_conflict']))
                else:
                    raise AnalysisError('PREPARATION_IDENTITY_CONFLICT', 'Conflicting material identities')
            previous.origins = ordered(previous.origins + item.origins)
        else:
            result[key] = item
    return sorted(result.values(), key=lambda item: getattr(item, identity))


class ReviewPreparationService:
    """Management interface only; source files remain immutable."""

    def __init__(self, packages, workspace):
        self.coverage = CoverageService(Path(packages), Path(workspace))
        self.library = self.coverage.library

    def prepare(self, request: ReviewPreparationRequest | dict | None = None):
        request = ReviewPreparationRequest.model_validate(request or {})
        inventory = self.coverage.inventory()
        selected = set(request.archives)
        if selected:
            inventory.records = [r for r in inventory.records if r.address and r.address.archive in selected]
            inventory.issues = [i for i in inventory.issues if i.archive is None or i.archive in selected]
        issues = [PreparationIssue(code=i.code, archive=i.archive, reason=i.reason) for i in inventory.issues]
        files = {}
        for record in inventory.records:
            if record.address:
                files[record.address.archive] = record.address.archive_sha256
        for missing in sorted(selected - files.keys() - {i.archive for i in inventory.issues}):
            issues.append(PreparationIssue(code='ARCHIVE_UNAVAILABLE', archive=missing, reason='Requested file has no verified inventory'))
        sources, candidates, anomalies, reviews, families = [], [], [], [], {}
        for name, expected in sorted(files.items()):
            try:
                file = self.library.root / name
                if file_sha256(file.read_bytes()) != expected:
                    raise ValueError('Archive changed after coverage inventory')
                root, bundle = self.library.load(file)
                chunk = self._bundle(root, bundle, name, inventory)
                if file_sha256(file.read_bytes()) != expected:
                    raise ValueError('Archive changed during preparation')
                s, c, a, history, local_issues, lanes = chunk
                sources.extend(s); candidates.extend(c); anomalies.extend(a); reviews.extend(history)
                issues.extend(local_issues)
                for family, value in lanes:
                    families.setdefault(family, set()).add(value)
            except (AnalysisError, OSError, ValueError, KeyError, TypeError, AttributeError):
                issues.append(PreparationIssue(code='PREPARATION_ARCHIVE_QUARANTINED', archive=name,
                    reason='Archive changed or required material failed validation; no partial file material retained'))
                inventory.records = [r for r in inventory.records if not r.address or r.address.archive != name]
        for family, identities in sorted(families.items()):
            if len(identities) > 1:
                issues.append(PreparationIssue(code='ACTIVE_REVISION_CONFLICT',
                    reason='Multiple active versions in one source lane; keep materials separate and explicitly select files'))
        sources = merge_materials(sources, 'annotation_id')
        history_parents = {r['review_id']: r['request']['expected_previous_id'] for r in reviews}
        candidates = merge_materials(candidates, 'item_id', history_parents)
        candidates.sort(key=lambda c: (-len(c.flags), c.item_id))
        anomalies = merge_materials(anomalies, 'anomaly_id')
        if any('review_history_conflict' in c.flags for c in candidates):
            issues.append(PreparationIssue(code='REVIEW_HISTORY_CONFLICT', reason='Portable opinions disagree; no final opinion selected'))
        if not sources:
            issues.append(PreparationIssue(code='NO_ACTIVE_MATERIAL', reason='No validated active source evidence available'))
        issues = ordered(issues)
        counts = dict(Counter({'source_evidence': len(sources), 'candidate_targets': len(candidates),
            'nodes': sum(c.target.scope == 'node' for c in candidates),
            'facts': sum(c.target.scope == 'fact' for c in candidates),
            'gaps': sum(a.kind != 'rejected_candidate' for a in anomalies),
            'rejected_candidates': sum(a.kind == 'rejected_candidate' for a in anomalies),
            'issues': len(issues)}))
        counts.update({'facts_' + key: count for key, count in sorted(Counter(c.fact_state for c in candidates if c.target.scope == 'fact').items())})
        errors = any(i.severity == 'error' for i in issues)
        gates = [PreparationQualityGate(name='engineering', status='passed' if sources and not errors else 'blocked',
                    reasons=['Preparation structure and target projection checked; not product-wide or medical validation']),
            PreparationQualityGate(name='source', status='passed' if sources and not errors and all(r.state == 'verified' for r in inventory.records if r.address and r.address.active) else 'not_evaluated',
                    reasons=['Checks refer to packaged identity, hashes and evidence only; OCR correctness and semantic completeness not established'])]
        for gate, reason in (
            ('medical', 'No independent authenticated medical review or adjudication in this preparation'),
            ('license', 'Processing declarations do not establish sharing, training or publication rights'),
            ('performance', 'No scale benchmark or product SLO evaluated by this operation'),
            ('training', 'No approved gold standard, training plan or release permission'),
            ('case_baseline', 'T02-A case medical confirmation is independent and not established here'),
            ('cross_source', 'Source count or copies are not verified cross-source positive examples')):
            gates.append(PreparationQualityGate(name=gate, status='blocked' if gate in {'medical', 'training', 'case_baseline'} else 'not_evaluated', reasons=[reason]))
        report = ReviewPreparationReport(preparation_id='pending', status='empty' if not sources else 'partial' if issues else 'complete',
            coverage=inventory, sources=sources, candidates=candidates, anomalies=anomalies,
            review_records=ordered(reviews), issues=issues, gates=gates, counts=counts)
        report.preparation_id = stable_id('preparation', report.model_dump(mode='json', exclude={'preparation_id'}))
        return report

    def _bundle(self, root, bundle, name, inventory):
        sources, anomalies, index, origins, source_hashes, lanes, issues = [], [], {}, {}, {}, [], []
        for component in sorted(bundle.components, key=lambda c: c.path):
            if not component.active:
                continue
            address = next(r.address for r in inventory.records if r.address and r.address.archive == name and r.address.component == component.path)
            path = root / component.path
            manifest = json.loads((path / 'manifest.json').read_text('utf-8'))
            address = address.model_copy(update={'resources': sorted(manifest['files'])})
            if address.family:
                lanes.append((address.family, (address.package_id, address.manifest_sha256)))
            origin_id = dict(package_id=component.package_id, manifest_sha256=component.manifest_sha256)
            documents = {s['source_id']: s for s in read_jsonl(path / 'sources.jsonl')}
            evidence = {e['evidence_id']: e for e in read_jsonl(path / 'evidence.jsonl')}
            for record in evidence.values():
                source = documents[record['source_id']]
                source_hashes[source['source_id']] = source['sha256']
                flags = []
                kind = {'application/pdf': 'physical_page', 'text/plain': 'text_line', 'image/png': 'image',
                    'image/jpeg': 'image', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'structured_unit'}.get(source['media_type'], 'unknown')
                if record['location'].get('unit') is None or (kind == 'physical_page' and record['location'].get('page') is None):
                    flags.append('source_location_incomplete')
                if any(v is None for v in source['metadata'].values()):
                    flags.append('source_metadata_incomplete')
                sources.append(SourceAnnotation(annotation_id=stable_id('annotation', {**origin_id, 'evidence_id': record['evidence_id']}),
                    source=source, evidence=record, unit_kind=kind, origins=[address], flags=flags))
            graph = read_graph(path)
            if graph is None:
                issues.append(PreparationIssue(code='TCM_GRAPH_MISSING', archive=name, severity='warning',
                    reason='Source evidence retained; no TCM candidate graph available'))
                continue
            for node in graph.nodes:
                key = (component.package_id, node.node_id)
                index[key] = {'address': {'package_id': component.package_id, 'node_id': node.node_id},
                    'node': node.model_dump(mode='json'), 'evidence': list(evidence.values())}
                origins[key] = address
                for number, gap in enumerate(node.gaps):
                    anomalies.append(self._anomaly(origin_id, address, 'node_gap', number, evidence, gap=gap, node_id=node.node_id))
            for number, gap in enumerate(graph.gaps):
                anomalies.append(self._anomaly(origin_id, address, 'graph_gap', number, evidence, gap=gap))
            for number, rejected in enumerate(graph.rejected_candidates):
                anomalies.append(self._anomaly(origin_id, address, 'rejected_candidate', number, evidence, rejected=rejected))
        if any(a.unresolved_evidence_ids for a in anomalies):
            issues.append(PreparationIssue(code='ANOMALY_EVIDENCE_UNAVAILABLE', archive=name, severity='warning',
                reason='Original rejected-candidate evidence references retained but not all can be resolved'))
        history = read_reviews(SimpleNamespace(root=root), index)
        if history['errors'] or any(s['resolution'] != 'resolved' or s['user_review_state'] == 'history_invalid' for s in history['states'].values()):
            issues.append(PreparationIssue(code='REVIEW_HISTORY_INVALID', archive=name, reason='Opinions have invalid history or unavailable/changed targets; no medical confirmation inferred'))
        queue = build_review_queue(index, history, {key[0] for key in index}, 'all')
        candidates = []
        for item in queue['items']:
            key = (item['target']['address']['package_id'], item['target']['address']['node_id'])
            address = origins[key]
            for quote in item['quotes']:
                quote['source_sha256'] = source_hashes[quote['source_id']]
            candidates.append(CandidateReviewItem(**item, item_id=stable_id('reviewitem', {
                'target': item['target'], 'manifest_sha256': address.manifest_sha256}), origins=[address]))
        return sources, candidates, anomalies, history['records'], issues, lanes

    @staticmethod
    def _anomaly(origin_id, address, kind, number, evidence, *, gap=None, rejected=None, node_id=None):
        refs = [q.evidence_id for q in gap.quotes] if gap else rejected.evidence_ids
        return PreparationAnomaly(anomaly_id=stable_id('anomaly', {**origin_id, 'kind': kind,
            'node_id': node_id, 'occurrence': number}), kind=kind, package_id=address.package_id,
            node_id=node_id, occurrence=number, gap=gap, rejected=rejected,
            evidence=[evidence[e] for e in sorted(set(refs)) if e in evidence],
            unresolved_evidence_ids=sorted(set(refs) - evidence.keys()), origins=[address])

    def export(self, output_dir, request=None):
        target = Path(output_dir).resolve()
        root, workspace = self.library.root, self.library.workspace
        if (target.exists() or target.is_relative_to(root) or root.is_relative_to(target) or
            target.is_relative_to(workspace / 'archives') or target.suffix.lower() in {'.json', '.md', '.pdf', '.medpkg'}):
            raise AnalysisError('PREPARATION_EXPORT_PATH_INVALID', 'Use a new directory outside source packages and archive cache')
        report = self.prepare(request)
        target.parent.mkdir(parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix='.pending-review-preparation-', dir=target.parent))
        try:
            atomic_json(stage / 'preparation.json', report.model_dump(mode='json'))
            for name, content in render_preparation(report).items():
                (stage / name).write_text(content, encoding='utf-8', newline='\n')
            files = {p.name: file_sha256(p.read_bytes()) for p in sorted(stage.iterdir())}
            result = ReviewPreparationExport(preparation_id=report.preparation_id, status=report.status, files=files)
            atomic_json(stage / 'manifest.json', result.model_dump(mode='json'))
            # rename must not replace an existing destination, including racing exporters.
            if target.exists():
                raise AnalysisError('PREPARATION_EXPORT_PATH_INVALID', 'Export target appeared during preparation')
            stage.rename(target)
            return result
        finally:
            if stage.exists() and stage.resolve().parent == target.parent and not stage.is_symlink():
                shutil.rmtree(stage)


def render_preparation(report):
    sources = ['# 第一步：独立原文标注', '', f'准备状态：{report.status}；医学状态：unreviewed；本文件不展示模型候选。', '',
        '先逐条标注定义、条件、论据、版面、截断和未表达内容，再查看候选对照。评审者/决定/理由均未填写；无法判断保留待审。', '']
    for item in report.sources:
        e, s = item.evidence, item.source
        sources += [f'## {item.annotation_id}', '', f'来源SHA256：{s.sha256}；证据ID：{e.evidence_id}', '',
            '单位类型：' + item.unit_kind + '；原定位：' + canonical(e.location), '',
            '原文（不等于已校正文本）：', '', *['> ' + line for line in e.raw_text.splitlines()], '']
        if e.corrected_text is not None:
            sources += ['独立纠正值（原文未覆盖）：', '', *['> ' + line for line in e.corrected_text.splitlines()], '', '纠正状态：' + str(e.correction_status), '']
        sources += ['标注/评审者：____；决定：____；理由/无法判断原因：____', '']
    queue = {'items': [c.model_dump(mode='json') for c in report.candidates],
        'errors': [i.model_dump(mode='json') for i in report.issues if 'HISTORY' in i.code]}
    candidates = render_review_markdown(queue, limit=len(queue['items']))
    anomalies = ['# 缺口与隔离原候选', '', f'准备状态：{report.status}；这些材料不是可写ReviewTarget，不自动重做原页。完整原审计及证据见preparation.json。', '']
    for item in report.anomalies:
        anomalies += [f'## {item.anomaly_id} / {item.kind}', '',
            f'包：{item.package_id}；节点：{item.node_id or "无"}；出现序号：{item.occurrence}', '',
            '```json', canonical(item.gap or item.rejected), '```', '',
            '评审者：____；决定：____；理由/无法判断原因：____', '']
    gates = ['# 质量门报告', '', f'准备状态：{report.status}；医学状态：unreviewed；release_allowed=false。', '',
        '准备过程结构检查通过不等于全项目验收、OCR正确、医学正确或发布许可。', '', canonical(report.counts), '']
    for gate in report.gates:
        gates += [f'## {gate.name}: {gate.status}', '', *gate.reasons, '']
    gates += ['## 分项异常', '', *[f'- {i.code}: {i.archive or "全局"}；{i.reason}' for i in report.issues], '']
    guide = ['# 复核准备材料使用顺序', '', f'版本review-preparation/0.1.0；ID {report.preparation_id}；准备状态{report.status}。', '',
        '1. 先读source-annotations.md独立标原文，暂不查看模型候选。',
        '2. 再读candidates.md，对照全部节点/字段；显示引文可为节选，完整目标/引文/历史在preparation.json。',
        '3. 查anomalies.md和quality-gates.md；缺口/拒绝项不等于自动重做许可。',
        '4. 两名相应背景评审分别保留独立决定和理由，争议另留给指定仲裁者；当前没有替任何人填写意见。', '',
        '文件分步展示不是访问隔离，也不认证专家。准备表不是ReviewRequest；本版本不导入准备表或提交专家意见。',
        '现有user_review_state是用户声明意见，不能代替医学审核；无法判断、缺身份、未填项都保持待审。',
        '病例T02-A确认、真实跨来源正例、许可、规模和训练门独立，未由本材料补齐。',
        '所有文件可随整个目录迁移；manifest.json保存每个产物的SHA256。不得把资料许可扩展为公开分享或训练许可。', '']
    return {'source-annotations.md': '\n'.join(sources), 'candidates.md': candidates,
        'anomalies.md': '\n'.join(anomalies), 'quality-gates.md': '\n'.join(gates), 'README.md': '\n'.join(guide)}
