"""Source-preserving portable analysis cache with a declared construction owner."""
import json
from pathlib import Path

from medicine_agent.analysis.models import DocumentUnit
from medicine_agent.analysis.store import atomic_json, digest
from medicine_agent.domain.ids import stable_id, file_sha256
from medicine_agent.domain.models import DocumentFragment, EvidenceRecord
from medicine_agent.domain.owned_analysis import OwnedAnalysisCache
from medicine_agent.domain.tcm_knowledge import TCMKnowledgeGraph, validate_graph_evidence
from medicine_agent.packages.io import read_jsonl


def owned_identity(cache):
    # Content may be byte-identical across users; their revision lanes remain separate.
    return stable_id('pkg', {'content_package_id': cache.content_package_id, 'owner_id': cache.owner_id,
                            **({'derivation_id':cache.derivation_id} if cache.derivation_id else {})})


def analysis_options(request):
    return digest({k: request[k] for k in ('mode', 'force_ocr', 'metadata', 'allowed_use')})


def unit_records(data, extraction):
    evidence, fragments = [], []
    unit = DocumentUnit.model_validate(extraction)
    for i, block in enumerate(unit.blocks):
        if not block.text.strip():
            continue
        fid = stable_id('frag', {'source': data['source_id'], 'unit': unit.index,
            'block': i, 'text': block.text, 'position': block.position.model_dump()})
        fragment = DocumentFragment(fragment_id=fid, source_id=data['source_id'],
            ordinal=unit.index * 100000 + i, text=block.text, start_line=unit.index, end_line=unit.index)
        location = block.position.model_dump(mode='json')
        location.update({'source_sha256': data['sha256'], 'method': unit.method,
                        'confidence': block.confidence, 'adapter_versions': data['runtime']['adapters']})
        record = EvidenceRecord(evidence_id=stable_id('ev', {'fragment': fid}),
            source_id=data['source_id'], fragment_id=fid, raw_text=block.text, location=location)
        fragments.append(fragment.model_dump(mode='json'))
        evidence.append(record.model_dump(mode='json'))
    return evidence, fragments


def read_owned_cache(path: Path):
    manifest = json.loads((path/'manifest.json').read_text('utf-8'))
    file = path/'ownership.json'
    if not file.exists() and 'ownership.json' not in manifest['files']:
        return None
    if 'ownership.json' not in manifest['files']:
        raise ValueError('Unprotected ownership/cache metadata')
    cache = OwnedAnalysisCache.model_validate_json(file.read_text('utf-8'))
    package_id = manifest['package_id']
    corrected = (path/'corrections.json').exists()
    if corrected:
        from medicine_agent.packages.corrections import read_corrections
        audit = read_corrections(path)
        package_id = audit.history[0].parent_package_id
    if owned_identity(cache) != package_id:
        raise ValueError('Owned package identity mismatch')
    if cache.source_id != stable_id('src', {'sha256': cache.source_sha256}):
        raise ValueError('Owned source identity mismatch')
    revision = json.loads((path/'revision.json').read_text('utf-8'))
    if (revision['units'] != [u.ordinal for u in cache.units] or
        revision['source_sha256'] != cache.source_sha256 or revision['runtime'] != cache.runtime):
        raise ValueError('Cache differs from revision metadata')
    expected_family = stable_id('family', {'source_id':cache.source_id, 'owner_id':cache.owner_id,
        **({'derivation_id':cache.derivation_id} if cache.derivation_id else {})})
    if revision['family'] != expected_family:
        raise ValueError('Owned revision lane mismatch')
    sources = read_jsonl(path/'sources.jsonl')
    if len(sources)!=1 or sources[0]['source_id']!=cache.source_id or sources[0]['sha256']!=cache.source_sha256:
        raise ValueError('Cache belongs to another source')
    all_evidence, all_fragments, knowledge, relations, nodes, gaps = {}, {}, {}, {}, {}, []
    previous = []
    for unit in cache.units:
        payload = unit.analysis.model_dump(mode='json')
        current, fragments = unit_records({'source_id':cache.source_id,'sha256':cache.source_sha256,
                                           'runtime':cache.runtime}, unit.extraction.model_dump(mode='json'))
        if current != payload['current_evidence'] or fragments != payload['fragments']:
            raise ValueError('Cache does not preserve extracted original text and position')
        context = previous + current if unit.predecessor_unit is not None else current
        refs = {e['evidence_id'] for e in context}
        for item in payload['knowledge'] + payload['relations']:
            if not item['evidence_refs'] or not set(item['evidence_refs']) <= refs:
                raise ValueError('Cached assertion has invalid context evidence')
        if unit.analysis.tcm_graph is not None:
            graph = unit.analysis.tcm_graph
            validate_graph_evidence(graph,[EvidenceRecord.model_validate(e) for e in context])
            for node in graph.nodes:
                if node.node_id != stable_id('tcm',node.model_dump(mode='json',exclude={'node_id'})):
                    raise ValueError('Cached node identity mismatch')
                nodes[node.node_id]=node.model_dump(mode='json')
            gaps += [g.model_dump(mode='json') for g in graph.gaps]
        for name, key, destination in (('current_evidence','evidence_id',all_evidence),
            ('fragments','fragment_id',all_fragments),('knowledge','knowledge_id',knowledge),('relations','relation_id',relations)):
            destination.update({item[key]:item for item in payload[name]})
        previous = current
    if list(all_evidence.values()) != read_jsonl(path/'evidence.jsonl') or list(all_fragments.values()) != read_jsonl(path/'fragments.jsonl'):
        raise ValueError('Cache original records differ from packaged sources')
    identity = {'source':sources[0], 'fragments':list(all_fragments.values()),
        'evidence':list(all_evidence.values()), 'knowledge':list(knowledge.values()),
        'relations':list(relations.values()), 'raw_fields':read_jsonl(path/'raw_fields.jsonl')}
    if cache.content_package_id != stable_id('pkg',identity):
        raise ValueError('Cached content identity differs from committed analysis')
    if cache.runtime['model'] is None and any(u.analysis.tcm_graph is not None for u in cache.units):
        raise ValueError('Extractive cache cannot claim model analysis')
    if cache.runtime['model'] is not None:
        versions = {u.analysis.tcm_graph.semantic_version for u in cache.units if u.analysis.tcm_graph is not None}
        if len(versions) != 1:
            raise ValueError('Cached graph semantic versions differ')
        # Reconstruct with the recorded version, never today's default. Reading
        # an old archive must not silently migrate its metadata or invalidate it.
        expected = TCMKnowledgeGraph(semantic_version=next(iter(versions)), nodes=list(nodes.values()), gaps=gaps)
        actual = audit.history[0].parent_graph if corrected else TCMKnowledgeGraph.model_validate_json((path/'tcm.json').read_text('utf-8'))
        if expected != actual:
            raise ValueError('Packaged graph differs from committed analysis')
    if not corrected:
        if list(knowledge.values())!=read_jsonl(path/'knowledge.jsonl') or list(relations.values())!=read_jsonl(path/'relations.jsonl'):
            raise ValueError('Packaged query records differ from committed analysis')
    return cache


def attach_owned_cache(path, cache):
    cache = OwnedAnalysisCache.model_validate(cache)
    atomic_json(path/'ownership.json',cache.model_dump(mode='json'))
    manifest = json.loads((path/'manifest.json').read_text('utf-8'))
    manifest['package_id'] = owned_identity(cache)
    manifest['files']['ownership.json'] = file_sha256((path/'ownership.json').read_bytes())
    atomic_json(path/'manifest.json',manifest)
    atomic_json(path/'checksums.json',manifest['files'])
