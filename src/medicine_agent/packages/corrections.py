"""Deterministic correction application and portable, self-contained provenance."""
import copy
import json
from pathlib import Path

from medicine_agent.analysis.store import digest
from medicine_agent.domain.ids import stable_id, file_sha256
from medicine_agent.domain.corrections import CorrectionBundle
from medicine_agent.domain.tcm_knowledge import TCMKnowledgeGraph


def apply_reviews(graph, package_id, reviews):
    """Quotes, source identities, grouping and gaps are never editable here."""
    before = graph.model_dump(mode='json')
    result = copy.deepcopy(before)
    nodes = {n['node_id']: n for n in result['nodes']}
    occupied = {}
    for record in sorted(reviews, key=lambda r: r.review_id):
        request = record.request
        target = request.target
        if target.address.package_id != package_id or target.address.node_id not in nodes:
            raise ValueError('Review does not address the parent package')
        nid = target.address.node_id
        slots = occupied.setdefault(nid, set())
        slot = (target.group_id, target.fact_index) if target.scope == 'fact' else 'node'
        if slot in slots or slot == 'node' and slots or 'node' in slots:
            raise ValueError('Overlapping correction targets require separate revisions')
        slots.add(slot)
        original = next(n for n in before['nodes'] if n['node_id'] == nid)
        value = original
        destination = nodes[nid]
        if target.scope == 'fact':
            groups = [g for g in original['groups'] if g['group_id'] == target.group_id]
            if not groups or target.fact_index >= len(groups[0]['facts']):
                raise ValueError('Review field occurrence is absent')
            value = groups[0]['facts'][target.fact_index]
            destination = next(g for g in nodes[nid]['groups'] if g['group_id'] == target.group_id)['facts'][target.fact_index]
        if digest(value) != target.fingerprint:
            raise ValueError('Correction target fingerprint differs')
        if request.decision != 'needs_revision' or request.proposed_value is None:
            raise ValueError('A correction requires an explicit needs_revision proposal')
        proposal = request.proposed_value
        if target.scope == 'node':
            if isinstance(proposal, str):
                updates = {'statement': proposal}
            elif isinstance(proposal, dict) and proposal and set(proposal) <= {'title', 'statement', 'aliases', 'topics', 'categories'}:
                updates = proposal
            else:
                raise ValueError('Node proposal must be a statement or an allowed metadata patch')
            destination.update(copy.deepcopy(updates))
        else:
            # Explicit wrapper distinguishes a structured fact patch from JSON-valued facts.
            if isinstance(proposal, dict) and set(proposal) == {'fact_patch'}:
                updates = proposal['fact_patch']
                if not isinstance(updates, dict) or not updates or not set(updates) <= {'value', 'state', 'reason'}:
                    raise ValueError('Fact patch may only change value, state and reason')
                destination.update(copy.deepcopy(updates))
            else:
                destination['value'] = copy.deepcopy(proposal)
        if destination == value:
            raise ValueError('Correction has no effect')
    mapping = {}
    for node in result['nodes']:
        old = node['node_id']
        node['node_id'] = stable_id('tcm', {k: v for k, v in node.items() if k != 'node_id'})
        mapping[old] = node['node_id']
    return TCMKnowledgeGraph.model_validate(result), mapping


def correction_identity(parent_id, reviews):
    return stable_id('pkg', {'correction_version': '0.1.0', 'parent_package_id': parent_id,
                            'review_ids': sorted(r.review_id for r in reviews)})


def revised_metadata(previous, package_id, graph):
    result = copy.deepcopy(previous)
    result.update(task_id=stable_id('correction', package_id), parent=previous['task_id'],
                  sequence=previous['sequence'] + 1, changes={'added_units': [], 'removed_units': []})
    result['classification']['knowledge_categories'] = sorted(
        set(previous['classification']['knowledge_categories']) | {c for n in graph.nodes for c in n.categories})
    return result


def read_corrections(path: Path):
    manifest = json.loads((path / 'manifest.json').read_text('utf-8'))
    resource = path / 'corrections.json'
    if not resource.exists() and 'corrections.json' not in manifest['files']:
        return None
    if 'corrections.json' not in manifest['files']:
        raise ValueError('Unprotected correction provenance')
    bundle = CorrectionBundle.model_validate_json(resource.read_text('utf-8'))
    prior = None
    prior_revision = None
    prior_resources = None
    for event in bundle.history:
        if event.package_id != correction_identity(event.parent_package_id, event.reviews):
            raise ValueError('Correction identity mismatch')
        history = {r.review_id: r for r in event.review_history}
        if len(history) != len(event.review_history):
            raise ValueError('Duplicate correction review history')
        used = set()
        for selected in event.reviews:
            current = selected.review_id
            chain = set()
            while current is not None:
                if current in chain or current not in history:
                    raise ValueError('Incomplete or cyclic correction review history')
                chain.add(current)
                record = history[current]
                if record.request.target != selected.request.target:
                    raise ValueError('Correction history switches review target')
                current = record.request.expected_previous_id
            if history[selected.review_id] != selected:
                raise ValueError('Applied review differs from saved history')
            used.update(chain)
        if used != set(history):
            raise ValueError('Unexpected review records in correction history')
        for record in event.review_history:
            if record.review_id != stable_id('review', record.model_dump(mode='json', exclude={'review_id'})):
                raise ValueError('Correction review identity mismatch')
        from medicine_agent.domain.models import EvidenceRecord
        from medicine_agent.domain.tcm_knowledge import validate_graph_evidence
        evidence = [EvidenceRecord.model_validate_json(line) for line in
                    (path / 'evidence.jsonl').read_text('utf-8').splitlines() if line.strip()]
        validate_graph_evidence(event.parent_graph, evidence)
        if any(n.node_id != stable_id('tcm', n.model_dump(mode='json', exclude={'node_id'})) for n in event.parent_graph.nodes):
            raise ValueError('Parent medical node identity differs')
        graph, mapping = apply_reviews(event.parent_graph, event.parent_package_id, event.reviews)
        if mapping != event.node_mapping:
            raise ValueError('Correction node mapping differs')
        if prior and (event.parent_package_id != prior[0] or event.parent_graph != prior[1]):
            raise ValueError('Correction history is disconnected')
        if prior_revision is not None and event.parent_revision.model_dump(mode='json') != prior_revision:
            raise ValueError('Correction version history is disconnected')
        if prior_resources is not None and event.preserved_files != prior_resources:
            raise ValueError('Correction history changes inherited source resources')
        prior = event.package_id, graph
        prior_revision = revised_metadata(event.parent_revision.model_dump(mode='json'), event.package_id, graph)
        prior_resources = event.preserved_files
    last = bundle.history[-1]
    if last.package_id != manifest['package_id']:
        raise ValueError('Correction package identity differs')
    actual = TCMKnowledgeGraph.model_validate_json((path / 'tcm.json').read_text('utf-8'))
    if actual != prior[1]:
        raise ValueError('Corrected content differs from the explicit proposals')
    for name, expected in last.preserved_files.items():
        resource = path / name
        if not resource.resolve().is_relative_to(path.resolve()) or file_sha256(resource.read_bytes()) != expected:
            raise ValueError('Correction changed inherited source resources')
        if manifest['files'].get(name) != expected:
            raise ValueError('Unprotected inherited correction resource')
    required = {'sources.jsonl', 'fragments.jsonl', 'evidence.jsonl', 'raw_fields.jsonl', 'runs.jsonl', 'extensions.json'}
    if not required <= last.preserved_files.keys():
        raise ValueError('Correction provenance omits source preservation checks')
    revision = json.loads((path / 'revision.json').read_text('utf-8'))
    previous = last.parent_revision.model_dump(mode='json')
    expected = revised_metadata(previous, last.package_id, actual)
    if revision != expected or 'revision.json' not in manifest['files']:
        raise ValueError('Correction revision metadata differs')
    # The legacy query projection must describe the new graph, not old summaries.
    projected = {json.loads(line)['knowledge_id']: json.loads(line) for line in
                 (path / 'knowledge.jsonl').read_text('utf-8').splitlines() if line.strip()}
    for node in actual.nodes:
        item = projected[node.node_id]
        if item['statement'] != node.statement or item['label'] != node.title:
            raise ValueError('Correction query projection is stale')
    return bundle
