"""Portable, non-destructive pointers between independently owned source nodes."""
from pathlib import Path
import json
from collections import deque

from medicine_agent.analysis.models import AnalysisError
from medicine_agent.analysis.store import atomic_json, digest, process_lock
from medicine_agent.domain.ids import stable_id
from medicine_agent.domain.tcm_knowledge import KnowledgeAddress, KnowledgeAssociation
from medicine_agent.packages.tcm import read_graph


def node_index(catalog):
    result = {}
    for item in catalog.scan():
        if item['state'] == 'quarantined':
            continue
        path = catalog._path(item['path'])
        graph = read_graph(path)
        if graph:
            for node in graph.nodes:
                key = (item['package_id'], node.node_id)
                record = {'address': {'package_id': key[0], 'node_id': key[1]},
                    'node': node.model_dump(mode='json'), 'package': item,
                    'evidence': [json.loads(line) for line in
                        (path / 'evidence.jsonl').read_text('utf-8').splitlines() if line.strip()],
                    'sources': [json.loads(line) for line in
                        (path / 'sources.jsonl').read_text('utf-8').splitlines() if line.strip()]}
                # Preserve all evidence needed by fields, gaps and root statements.
                refs = {q.evidence_id for q in node.quotes}
                refs.update(q.evidence_id for g in node.groups for f in g.facts for q in f.quotes)
                refs.update(q.evidence_id for gap in node.gaps for q in gap.quotes)
                record['evidence'] = [e for e in record['evidence'] if e['evidence_id'] in refs]
                if key in result and result[key]['node'] != record['node']:
                    raise AnalysisError('NODE_IDENTITY_CONFLICT', 'Conflicting copies of a medical node')
                result[key] = record
    return result


def address_key(address):
    if isinstance(address, KnowledgeAddress):
        return address.package_id, address.node_id
    return address['package_id'], address['node_id']


def associate(catalog, source, target, relation, rationale):
    source = KnowledgeAddress.model_validate(source)
    target = KnowledgeAddress.model_validate(target)
    index = node_index(catalog)
    if address_key(source) == address_key(target):
        raise AnalysisError('LINK_SELF_REFERENCE', 'A node cannot be associated with itself')
    if address_key(source) not in index or address_key(target) not in index:
        raise AnalysisError('LINK_TARGET_UNAVAILABLE', 'Both nodes must exist when creating an association')
    payload = {'source': source.model_dump(), 'target': target.model_dump(),
               'relation': relation, 'rationale': rationale}
    edge = KnowledgeAssociation(association_id=stable_id('link', payload), **payload)
    record = edge.model_dump(mode='json')
    path = catalog._path('links/' + edge.association_id + '.json')
    with process_lock(catalog.root / '.association-write.lock'):
        if path.exists():
            existing = json.loads(path.read_text('utf-8'))
            if existing != {'record': record, 'sha256': digest(record)}:
                raise AnalysisError('LINK_IDENTITY_CONFLICT', 'Existing association has different content')
        else:
            atomic_json(path, {'record': record, 'sha256': digest(record)})
    return record


def read_associations(catalog, index=None):
    index = node_index(catalog) if index is None else index
    records, errors, seen = [], [], set()
    for path in sorted(catalog.root.rglob('links/*.json')):
        if any(part.startswith('.pending') for part in path.relative_to(catalog.root).parts):
            continue
        try:
            if not path.resolve().is_relative_to(catalog.root):
                raise ValueError('External link file')
            data = json.loads(path.read_text('utf-8'))
            if set(data) != {'record', 'sha256'} or digest(data['record']) != data['sha256']:
                raise ValueError('Link integrity error')
            edge = KnowledgeAssociation.model_validate(data['record'])
            payload = {k: getattr(edge, k) for k in ('source', 'target', 'relation', 'rationale')}
            payload['source'] = edge.source.model_dump()
            payload['target'] = edge.target.model_dump()
            if edge.association_id != stable_id('link', payload):
                raise ValueError('Link identity error')
            # A links directory embedded in an invalid package is not an import bypass.
            from medicine_agent.packages.io import validate_package_path
            for ancestor in path.parents:
                if ancestor == catalog.root:
                    break
                if (ancestor/'manifest.json').exists() and not validate_package_path(ancestor).valid:
                    raise ValueError('Association container is quarantined')
            if edge.association_id in seen:
                continue
            seen.add(edge.association_id)
            missing = [a.model_dump() for a in (edge.source, edge.target) if address_key(a) not in index]
            records.append({**edge.model_dump(mode='json'), 'resolution': 'target_unavailable' if missing else 'resolved',
                            'missing_addresses': missing})
        except (OSError, ValueError, KeyError, TypeError):
            errors.append({'file': path.name, 'code': 'ASSOCIATION_INVALID'})
    return {'associations': records, 'errors': errors}


def related(catalog, addresses, index=None):
    index = node_index(catalog) if index is None else index
    active_packages = {p['package_id'] for p in catalog.selected()}
    active = {k:v for k,v in index.items() if k[0] in active_packages}
    keys = {address_key(a) for a in addresses} & active.keys()
    report = read_associations(catalog, index)
    adjacency = {}
    for edge in report['associations']:
        for side in ('source','target'):
            adjacency.setdefault(address_key(edge[side]),[]).append(edge)
    visited, queue, used = set(keys), deque(sorted(keys)), {}
    while queue:
        current = queue.popleft()
        for edge in adjacency.get(current,[]):
            used[edge['association_id']] = edge
            for side in ('source','target'):
                neighbor = address_key(edge[side])
                if neighbor in active and neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
    edges = []
    for edge in used.values():
        inactive = [edge[side] for side in ('source','target') if address_key(edge[side]) not in active]
        edges.append({**edge, 'resolution': ('target_unavailable' if edge['missing_addresses'] else
            'target_inactive' if inactive else 'resolved'), 'inactive_addresses':inactive})
    nodes = [active[key] for key in sorted(visited-keys)]
    # An explicit non-merging view, never written back into any source package.
    selected = [index[k] for k in keys if k in index] + nodes
    names = {name.casefold() for k in keys if k in index
        for name in [index[k]['node']['title'], *index[k]['node']['aliases']]}
    candidates = [record for k, record in active.items() if k not in visited
        and names & {name.casefold() for name in [record['node']['title'], *record['node']['aliases']]}]
    return {'associations': edges, 'related_nodes': nodes,
        'association_candidates': [{'address': r['address'], 'title': r['node']['title'],
            'reason': '名称或别名相同，仅为查找线索，不代表同一定义'} for r in candidates],
        'category_union': sorted({c for item in selected for c in item['node']['categories']}),
        'topic_union': sorted({c for item in selected for c in item['node']['topics']}),
        'material_type_union': sorted({c for item in selected for c in item['package']['classification']['material_types']}),
        'association_errors': report['errors']}
