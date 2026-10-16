"""Source-faithfulness checks and a derived view; never rewrites source data."""
import re

UNCOVERED = '该证据未形成结构化知识，需继续分析'
LAYOUT = '版面文字候选，原文保留；不作为医学知识未覆盖计数'


def compact(text):
    return ''.join(text.split())


def only_work_titles(value):
    """Reject a bibliography used as a school; allow names with cited works."""
    if isinstance(value, list):
        return bool(value) and all(only_work_titles(v) for v in value)
    if not isinstance(value, str) or '《' not in value:
        return False
    remaining = re.sub(r'《[^》]*》', '', value)
    return not remaining.strip(' \t\n，,；;、。:：/（）()“”\"')


def analysis_violations(graph, records):
    """Strict checks apply to new generation, not historical package identities."""
    order = {r['evidence_id']: i for i, r in enumerate(records)}
    raw = {r['evidence_id']: r['raw_text'] for r in records}
    issues = []
    for ni, node in enumerate(graph['nodes']):
        roots = []
        for gi, group in enumerate(node['groups']):
            propositions = []
            main = False
            for fi, fact in enumerate(group['facts']):
                if fact['state'] not in {'stated', 'inferred'}:
                    continue
                field, value = fact['field_id'], fact['value']
                location = ['nodes', ni, 'groups', gi, 'facts', fi]
                if field == 'tcm.theory_school' and only_work_titles(value):
                    issues.append({'location': location, 'message':
                        '文献名不能替代流派/医家；请保留在tcm.theory_cited_work并附原引文，不删除出处。'})
                if field in {'tcm.theory_proposition_text', 'tcm.theory_concept_definition'}:
                    main = True
                if field == 'tcm.theory_proposition_text':
                    # Repeated occurrences of the same literal must survive;
                    # only distinct statements require separate proposition groups.
                    propositions.append(compact(value) if isinstance(value, str) else repr(value))
                    quotes = sorted(fact['quotes'], key=lambda q: (
                        order.get(q['evidence_id'], -1), raw.get(q['evidence_id'], '').find(q['text'])))
                    literal = ''.join(q['text'] for q in quotes)
                    if not isinstance(value, str) or not compact(value) or compact(value) not in compact(literal):
                        issues.append({'location': location, 'code': 'raw_literal_mismatch',
                            'quoted_original': literal, 'observed_value': value, 'message':
                            '理论命题原话值必须逐字来自按原顺序排列的引文，只忽略排版空白；解释请另存，不得漏字或改标点。'})
                if field == 'tcm.theory_cited_work':
                    texts = value if isinstance(value, list) else [value]
                    literal = ''.join(q['text'] for q in fact['quotes'])
                    if any(not isinstance(t, str) or not compact(t) or compact(t) not in compact(literal) for t in texts):
                        issues.append({'location': location, 'message':
                            '转引文献/篇名保留材料中的原字，不能补出未核验书目或新建一手来源。'})
            if len(set(propositions)) > 1:
                issues.append({'location': ['nodes', ni, 'groups', gi], 'message':
                    '同一理论分组有多个独立原话命题；分别成节点，保留每条原话和证据。'})
            if group['kind'] == 'theory' and main and not group.get('about_group_id'):
                roots.append(gi)
        if len(roots) > 1:
            issues.append({'location': ['nodes', ni], 'message':
                '一个节点存在多个独立理论主命题。请分节点；共同论证/出处等辅助组用about_group_id归属，不要合并无关命题。'})
    return issues


class FaithfulnessError(ValueError):
    def __init__(self, issues):
        self.issues = issues
        super().__init__('New analysis has source-faithfulness issues')


def retain_ambiguous_drafts(graph, issues):
    """Do not turn an unfaithful proposal into a fabricated corrected fact."""
    import json
    import copy
    from medicine_agent.domain.tcm_knowledge import TCMKnowledgeGraph
    data = copy.deepcopy(graph.model_dump(mode='json'))
    if not issues or any(i.get('code') != 'raw_literal_mismatch' for i in issues):
        raise FaithfulnessError(issues)
    for issue in issues:
        _, ni, _, gi, _, fi = issue['location']
        node = data['nodes'][ni]
        fact = node['groups'][gi]['facts'][fi]
        # Preserve the entire rejected value explicitly as an unaccepted draft,
        # not as a source assertion. Quotes and complete source evidence stay intact.
        reason = '模型草稿未与引文逐字吻合，不采信为确定原话；未采信原值：' + json.dumps(fact['value'], ensure_ascii=False)
        if fact.get('reason'):
            reason += '；原理由：' + fact['reason']
        fact.update(value=None, state='ambiguous', reason=reason)
        node['gaps'].append({'reason':reason, 'quotes':copy.deepcopy(fact['quotes'])})
    return TCMKnowledgeGraph.model_validate(data)


def layout_candidate(record, title):
    """Conservative header/footer hint; text is always retained."""
    loc = record.get('location', {})
    box, size = loc.get('region'), loc.get('page_size')
    if not box or not size:
        return False
    scale = loc.get('render_scale', 1) if loc.get('coordinate_unit') == 'rendered-pixel' else 1
    height = size[1] * scale
    at_edge = box[1] < height * .12 or box[3] > height * .88
    if not at_edge:
        return False
    text = compact(record['raw_text'])
    book_header = title and re.sub(r'[0-9０-９]', '', text) == compact(title)
    chapter_header = re.fullmatch(r'第[一二三四五六七八九十百0-9]+章[^。；]+[0-9]+', text)
    return bool(book_header or chapter_header)


def quality_view(graph, records, title=None):
    """Preserve every warning, but distinguish warnings from missing knowledge."""
    covered = {q['evidence_id'] for n in graph['nodes'] for q in n['quotes']}
    covered.update(q['evidence_id'] for n in graph['nodes'] for g in n['groups'] for f in g['facts'] for q in f['quotes'])
    layout = {r['evidence_id'] for r in records if layout_candidate(r, title)}
    gaps = [*graph['gaps'], *(g for n in graph['nodes'] for g in n['gaps'])]
    entries = []
    for gap in gaps:
        refs = {q['evidence_id'] for q in gap['quotes']}
        if gap['reason'] == LAYOUT or refs and refs <= layout:
            kind = 'layout_candidate'
        elif gap['reason'] == UNCOVERED and refs and refs <= covered:
            kind = 'referenced_elsewhere'
        elif gap['reason'] == UNCOVERED:
            kind = 'uncovered_evidence'
        else:
            kind = 'model_reported'
        entries.append({'kind': kind, 'original_gap': gap})
    kinds = ('layout_candidate', 'referenced_elsewhere', 'uncovered_evidence', 'model_reported')
    return {'scope': 'whole_source_package', 'raw_gap_records': len(entries),
        'counts': {k: sum(e['kind'] == k for e in entries) for k in kinds},
        'entries': entries, 'generation_issues': analysis_violations(graph, records),
        'notice': '提示条数不是遗漏知识点数；引用存在不代表已经充分理解。原始提示和原文均保留。'}
