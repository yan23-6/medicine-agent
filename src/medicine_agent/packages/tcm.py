"""Checksummed optional extension; legacy packages remain readable."""
import json
from pathlib import Path
from medicine_agent.domain.models import EvidenceRecord
from medicine_agent.domain.ids import file_sha256, stable_id
from medicine_agent.domain.tcm_knowledge import TCMKnowledgeGraph, validate_graph_evidence
from medicine_agent.analysis.store import atomic_json

CURRENT_EXTENSIONS = {'tcm-knowledge': '0.2.0'}
SUPPORTED_EXTENSIONS = ({'tcm-knowledge': '0.1.0'}, CURRENT_EXTENSIONS)


def read_graph(path: Path) -> TCMKnowledgeGraph | None:
    extension = path / 'extensions.json'
    graph_path = path / 'tcm.json'
    if not extension.exists() and not graph_path.exists():
        return None
    manifest = json.loads((path / 'manifest.json').read_text('utf-8'))
    if not {'extensions.json', 'tcm.json'} <= manifest['files'].keys():
        raise ValueError('Unprotected medical extension')
    if json.loads(extension.read_text('utf-8')) not in SUPPORTED_EXTENSIONS:
        raise ValueError('Unsupported medical extension version')
    graph = TCMKnowledgeGraph.model_validate_json(graph_path.read_text('utf-8'))
    records = [EvidenceRecord.model_validate_json(line) for line in
        (path / 'evidence.jsonl').read_text('utf-8').splitlines() if line.strip()]
    validate_graph_evidence(graph, records)
    projections = {json.loads(line)['knowledge_id'] for line in
        (path / 'knowledge.jsonl').read_text('utf-8').splitlines() if line.strip()}
    for n in graph.nodes:
        if n.node_id != stable_id('tcm', n.model_dump(mode='json', exclude={'node_id'})):
            raise ValueError('Medical node identity differs from its content')
        if n.node_id not in projections:
            raise ValueError('Medical node is absent from query projection')
    return graph


def attach_graph(path: Path, graph: TCMKnowledgeGraph):
    atomic_json(path / 'extensions.json', CURRENT_EXTENSIONS)
    atomic_json(path / 'tcm.json', graph.model_dump(mode='json'))
    manifest = json.loads((path / 'manifest.json').read_text('utf-8'))
    for name in ('extensions.json', 'tcm.json'):
        manifest['files'][name] = file_sha256((path / name).read_bytes())
    atomic_json(path / 'manifest.json', manifest)
    atomic_json(path / 'checksums.json', manifest['files'])
    read_graph(path)
