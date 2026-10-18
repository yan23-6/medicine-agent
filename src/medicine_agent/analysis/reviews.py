"""Portable append-only reviews and deterministic evidence-backed review queues."""
from collections import Counter, defaultdict
from datetime import datetime, UTC
import json
from pathlib import Path

from medicine_agent.analysis.associations import node_index, address_key
from medicine_agent.analysis.models import AnalysisError
from medicine_agent.analysis.store import atomic_json, digest, process_lock
from medicine_agent.domain.ids import stable_id
from medicine_agent.domain.reviews import ReviewTarget, ReviewRequest, ReviewRecord


def target_value(target, index):
    node = index.get(address_key(target.address))
    if node is None:
        raise AnalysisError('REVIEW_TARGET_UNAVAILABLE', 'The source package or node is unavailable')
    value = node['node']
    if target.scope == 'fact':
        groups = [g for g in value['groups'] if g['group_id'] == target.group_id]
        if not groups or target.fact_index >= len(groups[0]['facts']):
            raise AnalysisError('REVIEW_TARGET_INVALID', 'Field occurrence does not exist')
        value = groups[0]['facts'][target.fact_index]
    if digest(value) != target.fingerprint:
        raise AnalysisError('REVIEW_TARGET_CHANGED', 'Review target fingerprint differs')
    return value


def read_reviews(catalog, index=None):
    index = node_index(catalog) if index is None else index
    records, errors = [], []
    for path in sorted((catalog.root / 'reviews').glob('*.json')):
        try:
            if not path.resolve().is_relative_to(catalog.root):
                raise ValueError('Review file escapes root')
            data = json.loads(path.read_text('utf-8'))
            if set(data) != {'record', 'sha256'} or digest(data['record']) != data['sha256']:
                raise ValueError('Review checksum mismatch')
            record = ReviewRecord.model_validate(data['record'])
            if record.review_id != stable_id('review', record.model_dump(mode='json', exclude={'review_id'})):
                raise ValueError('Review identity mismatch')
            if path.stem != record.review_id:
                raise ValueError('Review filename does not match identity')
            records.append(record.model_dump(mode='json'))
        except (OSError, ValueError, KeyError, TypeError):
            errors.append({'file': path.name, 'code': 'REVIEW_RECORD_INVALID'})
    groups = defaultdict(list)
    for record in records:
        groups[digest(record['request']['target'])].append(record)
    states = {}
    for key, values in groups.items():
        ids = {v['review_id'] for v in values}
        previous = [v['request']['expected_previous_id'] for v in values]
        roots = [v for v in values if v['request']['expected_previous_id'] is None]
        heads = [v for v in values if v['review_id'] not in previous]
        duplicate_parent = any(n > 1 for n in Counter(previous).values())
        broken = (len(ids) != len(values) or len(roots) != 1 or len(heads) != 1 or duplicate_parent
            or any(p is not None and p not in ids for p in previous))
        if not broken:
            by_id = {v['review_id']: v for v in values}
            seen, current = set(), heads[0]['review_id']
            while current is not None and current not in seen:
                seen.add(current)
                current = by_id[current]['request']['expected_previous_id']
            broken = current is not None or len(seen) != len(values)
        resolution = 'resolved'
        try:
            target_value(ReviewTarget.model_validate(values[0]['request']['target']), index)
        except AnalysisError as exc:
            resolution = exc.code
        states[key] = {'target': values[0]['request']['target'], 'resolution': resolution,
            'user_review_state': 'history_invalid' if broken or errors else heads[0]['request']['decision'],
            'latest_review_id': None if broken or errors else heads[0]['review_id'],
            'history_ids': sorted(ids)}
    return {'records': records, 'states': states, 'errors': errors,
            'medical_review': 'unreviewed', 'reviewer_identity': 'self_declared'}


def record_review(catalog, request):
    request = ReviewRequest.model_validate(request)
    with process_lock(catalog.root / '.review-write.lock'):
        index = node_index(catalog)
        target_value(request.target, index)
        history = read_reviews(catalog, index)
        if history['errors']:
            raise AnalysisError('REVIEW_HISTORY_INVALID', 'Review storage contains invalid records')
        current = history['states'].get(digest(request.target.model_dump(mode='json')))
        if current and current['user_review_state'] == 'history_invalid':
            raise AnalysisError('REVIEW_HISTORY_INVALID', 'Target has conflicting or incomplete review history')
        latest = current['latest_review_id'] if current else None
        if latest != request.expected_previous_id:
            raise AnalysisError('REVIEW_STALE_WRITE', 'Review history changed; refresh before submitting')
        payload = {'version': '0.1.0', 'created_at': datetime.now(UTC), 'request': request}
        provisional = ReviewRecord(review_id='pending', **payload)
        rid = stable_id('review', provisional.model_dump(mode='json', exclude={'review_id'}))
        record = ReviewRecord(review_id=rid, **payload).model_dump(mode='json')
        path = catalog._path('reviews/' + rid + '.json')
        if path.exists():
            raise AnalysisError('REVIEW_ID_CONFLICT', 'Review identity is already present')
        atomic_json(path, {'record': record, 'sha256': digest(record)})
        return record


def review_queue(catalog, scope='node'):
    if scope not in {'node', 'fact', 'all'}:
        raise AnalysisError('REVIEW_SCOPE_INVALID', 'Use node, fact or all')
    index = node_index(catalog)
    history = read_reviews(catalog, index)
    selected = {p['package_id'] for p in catalog.selected()}
    return build_review_queue(index, history, selected, scope)


def build_review_queue(index, history, selected, scope='all'):
    """Pure internal projection shared by catalogs and read-only preparation."""
    if scope not in {'node', 'fact', 'all'}:
        raise AnalysisError('REVIEW_SCOPE_INVALID', 'Use node, fact or all')
    items = []
    for (pid, nid), record in index.items():
        if pid not in selected:
            continue
        node = record['node']
        evidence = {e['evidence_id']: e for e in record['evidence']}
        entries = [('node', None, None, node)] if scope in {'node', 'all'} else []
        if scope in {'fact', 'all'}:
            entries += [('fact', g['group_id'], i, f) for g in node['groups'] for i, f in enumerate(g['facts'])]
        for kind, gid, occurrence, value in entries:
            target = ReviewTarget(address=record['address'], scope=kind, group_id=gid,
                fact_index=occurrence, fingerprint=digest(value)).model_dump(mode='json')
            references = value['quotes']
            quotes = [{'evidence_id': q['evidence_id'], 'text': q['text'],
                'source_id': evidence[q['evidence_id']]['source_id'],
                'location': evidence[q['evidence_id']]['location']} for q in references]
            flags = []
            if kind == 'fact' and value['state'] != 'stated':
                flags.append('field_' + value['state'])
            if kind == 'node':
                if node['gaps']:
                    flags.append('node_gaps')
                if any(f['state'] != 'stated' for g in node['groups'] for f in g['facts']):
                    flags.append('inference_or_ambiguity')
                if any(len({f['field_id'] for f in g['facts']}) < len(g['facts']) for g in node['groups']):
                    flags.append('repeated_fields_in_group')
            if len({q['location'].get('page') for q in quotes if q['location'].get('page')}) > 1:
                flags.append('cross_page')
            if any(q['location'].get('confidence') is not None and q['location']['confidence'] < .9 for q in quotes):
                flags.append('low_ocr_confidence')
            state = history['states'].get(digest(target))
            invalid = bool(history['errors']) or bool(state and state['resolution'] != 'resolved')
            items.append({'target': target, 'title': node['title'], 'categories': node['categories'],
                'field_id': value.get('field_id'), 'value': value.get('value', node['statement']),
                'fact_state': value.get('state'), 'reason': value.get('reason'),
                'quotes': quotes, 'flags': flags, 'user_review_state':
                    ('history_invalid' if invalid else state['user_review_state'] if state else 'unreviewed'),
                'expected_previous_id': state['latest_review_id'] if state and not invalid else None})
    items.sort(key=lambda i: (-len(i['flags']), i['target']['address']['package_id'],
                             i['target']['address']['node_id'], i['target']['scope'],
                             i['target']['group_id'] or '', i['target']['fact_index'] or 0))
    return {'items': items, 'errors': history['errors'], 'medical_review': 'unreviewed',
            'counts': dict(Counter(i['user_review_state'] for i in items))}


def render_review_markdown(queue, limit=10):
    """A derived view; the JSON targets and source records remain authoritative."""
    from medicine_agent.semantics import load_semantic_registry
    fields = {f.field_id: f.label_zh for f in load_semantic_registry().fields}
    flags = {'node_gaps': '有未理解/截断片段', 'inference_or_ambiguity': '含推断或歧义',
        'repeated_fields_in_group': '同组多次出现同名字段，检查是否需拆分',
        'cross_page': '跨页引文', 'low_ocr_confidence': 'OCR置信度偏低',
        'field_inferred': '模型推断', 'field_ambiguous': '含义有歧义',
        'field_missing': '资料缺失', 'field_not_applicable': '标为不适用'}
    states = {'unreviewed': '待核对', 'confirmed': '用户认可', 'needs_revision': '需修改',
              'rejected': '用户否定', 'history_invalid': '复核历史异常'}
    lines = ['# 中医候选：逐条核对清单', '',
        '以下候选尚待核对。用户意见单独保存，不覆盖原文，也不等于专家医学审核。', '',
        '先独立标注来源原文，再对照候选；保存意见须使用完整稳定目标、目标指纹和前序记录，不能只靠显示序号。', '',
        f"当前共 {len(queue['items'])} 个复核目标；下面展示前 {min(limit,len(queue['items']))} 个，完整定位和引文保存在同批 JSON 清单中。", '']
    if queue['errors']:
        lines += ['复核记录存在异常，暂不展示最终确认结论。', '']
    for i, item in enumerate(queue['items'][:limit], 1):
        page = sorted({q['location']['page'] for q in item['quotes'] if q['location'].get('page')})
        value = item['value'] if isinstance(item['value'], str) else json.dumps(item['value'], ensure_ascii=False)
        lines += [f"## {i}. {item['title']}", '',
            f"- 状态：{states.get(item['user_review_state'],item['user_review_state'])}；范围：{'节点' if item['target']['scope']=='node' else '字段'}。",
            f"- PDF 物理页：{', '.join(map(str,page)) or '来源未提供物理页'}。",
            '- 核对重点：'+('；'.join(flags.get(f,f) for f in item['flags']) or '原话与解释是否一致')+'。',
            f"- 稳定目标：`{digest(item['target'])[:16]}`。"]
        if item['field_id']:
            lines += ['- 字段：'+fields.get(item['field_id'],item['field_id'])+'。']
        lines += ['', '**当前解释或字段值**', '', value, '', '**原文摘录**', '']
        for quote in item['quotes'][:4]:
            text = quote['text'][:500].replace('\n','\n> ')
            lines += ['> '+text, '']
        if len(item['quotes']) > 4:
            lines += ['（此处展示部分引文，完整引文与位置见 JSON 清单。）', '']
        if item['reason']:
            lines += ['**已有理由**：'+item['reason'], '']
    lines += ['## 如何保存意见', '',
        '当前没有替你填写任何条目的确认意见。review-record接收明确填写的ReviewRequest；准备表或无法判断项不可直接当作确认意见提交。',
        '保存意见后，原数据仍可回查。更正候选不会自动替换源字段；新修订也不自动继承旧确认。', '']
    return '\n'.join(lines)
