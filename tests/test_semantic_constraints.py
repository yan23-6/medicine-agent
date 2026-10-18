import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from pydantic import ValidationError

import medicine_agent.semantics.registry as registry_module
from medicine_agent.domain.tcm_knowledge import GroundedFact, MedicalRecordGroup, TCMKnowledgeGraph


FIELD_ID = 'tcm.theory_proposition_text'


def point_registry(monkeypatch, tmp_path):
    payload = registry_module.load_semantic_registry().model_dump(mode='json')
    path = tmp_path / 'registry.json'
    write_registry(path, payload)
    monkeypatch.setattr(registry_module, 'files', lambda package: tmp_path)
    registry_module._field_constraints_for_text.cache_clear()
    return path, payload


def write_registry(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding='utf-8')


def test_field_constraints_reuse_only_validated_content(monkeypatch, tmp_path):
    point_registry(monkeypatch, tmp_path)
    parser = registry_module.SemanticRegistry.model_validate_json
    calls = []

    def counted(cls, content, **kwargs):
        calls.append(content)
        return parser(content, **kwargs)

    monkeypatch.setattr(registry_module.SemanticRegistry, 'model_validate_json', classmethod(counted))
    first = registry_module.semantic_field_constraints(FIELD_ID)
    second = registry_module.semantic_field_constraints(FIELD_ID)
    assert first is second and first.owner_profile == 'tcm'
    assert 'tcm_group:theory' in first.allowed_on
    assert registry_module.semantic_field_constraints('tcm.unknown_test_field') is None
    assert len(calls) == 1


def test_field_constraints_observe_same_version_size_and_mtime_content_change(monkeypatch, tmp_path):
    path, payload = point_registry(monkeypatch, tmp_path)
    first = registry_module.semantic_field_constraints(FIELD_ID)
    previous = path.stat()
    field = next(item for item in payload['fields'] if item['field_id'] == FIELD_ID)
    field['allowed_on'] = [value.replace('tcm_group:theory', 'tcm_group:safety')
                           for value in field['allowed_on']]
    write_registry(path, payload)
    os.utime(path, ns=(previous.st_atime_ns, previous.st_mtime_ns))
    assert path.stat().st_size == previous.st_size
    assert path.stat().st_mtime_ns == previous.st_mtime_ns
    changed = registry_module.semantic_field_constraints(FIELD_ID)
    assert changed is not first and 'tcm_group:safety' in changed.allowed_on
    assert 'tcm_group:theory' in first.allowed_on
    fact = GroundedFact(field_id=FIELD_ID, value='synthetic evidence',
                       quotes=[{'evidence_id': 'e1', 'text': 'synthetic evidence'}])
    with pytest.raises(ValueError, match='wrong record group'):
        MedicalRecordGroup(group_id='g1', kind='theory', facts=[fact])


def test_field_constraints_never_fall_back_after_registry_corruption(monkeypatch, tmp_path):
    path, payload = point_registry(monkeypatch, tmp_path)
    assert registry_module.semantic_field_constraints(FIELD_ID)
    path.write_text('{invalid json', encoding='utf-8')
    for attempt in range(2):
        with pytest.raises(ValidationError):
            registry_module.semantic_field_constraints(FIELD_ID)
    with pytest.raises(ValidationError):
        registry_module.load_semantic_registry()
    write_registry(path, payload)
    assert registry_module.semantic_field_constraints(FIELD_ID)
    payload['fields'][0]['field_id'] = 'invalid_namespace'
    write_registry(path, payload)
    with pytest.raises(ValidationError):
        registry_module.semantic_field_constraints(FIELD_ID)
    path.unlink()
    with pytest.raises(FileNotFoundError):
        registry_module.semantic_field_constraints(FIELD_ID)


def test_field_constraints_cannot_be_poisoned_by_callers(monkeypatch, tmp_path):
    path, payload = point_registry(monkeypatch, tmp_path)
    constraint = registry_module.semantic_field_constraints(FIELD_ID)
    with pytest.raises(AttributeError):
        constraint.owner_profile = 'western'
    with pytest.raises(AttributeError):
        constraint.allowed_on += ('tcm_group:invalid',)
    snapshot = registry_module._field_constraints_for_text(path.read_text('utf-8'))
    with pytest.raises(TypeError):
        snapshot[FIELD_ID] = None
    public = registry_module.load_semantic_registry()
    field = next(item for item in public.fields if item.field_id == FIELD_ID)
    field.owner_profile = 'western'
    field.allowed_on.append('tcm_group:invalid')
    fresh = registry_module.load_semantic_registry()
    assert fresh is not public
    assert next(item for item in fresh.fields if item.field_id == FIELD_ID).owner_profile == 'tcm'
    assert registry_module.semantic_field_constraints(FIELD_ID) is constraint
    assert constraint.owner_profile == 'tcm' and 'tcm_group:invalid' not in constraint.allowed_on


def test_field_constraint_cache_has_bounded_capacity(monkeypatch, tmp_path):
    path, payload = point_registry(monkeypatch, tmp_path)
    for revision in range(7):
        payload['fields'][0]['definition'] = f'synthetic cache capacity revision {revision}'
        write_registry(path, payload)
        assert registry_module.semantic_field_constraints(FIELD_ID)
    info = registry_module._field_constraints_for_text.cache_info()
    assert info.maxsize == 4 and info.currsize == 4 and info.misses == 7


def graph_payload():
    quote = {'evidence_id': 'e1', 'text': 'synthetic theory'}
    return {'nodes': [{'node_id': f'node-{ordinal}', 'source_id': 'source-1',
                       'title': f'synthetic-{ordinal}', 'statement': 'synthetic theory',
                       'categories': ['tcm_foundation'], 'quotes': [quote],
                       'groups': [{'group_id': 'g1', 'kind': 'theory', 'facts': [
                           {'field_id': FIELD_ID, 'value': 'synthetic theory', 'quotes': [quote]}]}]}
                      for ordinal in range(3)]}


def test_graph_validation_reads_one_snapshot_and_refreshes_next_entry(monkeypatch, tmp_path):
    point_registry(monkeypatch, tmp_path)
    reader = registry_module._registry_text
    reads = []

    def counted():
        reads.append(True)
        return reader()

    monkeypatch.setattr(registry_module, '_registry_text', counted)
    first = TCMKnowledgeGraph.model_validate(graph_payload())
    assert len(first.nodes) == 3 and len(reads) == 1
    assert TCMKnowledgeGraph.model_validate(graph_payload()) == first
    assert len(reads) == 2
    registry_module.semantic_field_constraints(FIELD_ID)
    assert len(reads) == 3


def test_graph_validation_releases_snapshot_after_failure(monkeypatch, tmp_path):
    path, payload = point_registry(monkeypatch, tmp_path)
    graph = graph_payload()
    graph['nodes'][0]['groups'][0]['facts'][0]['field_id'] = 'tcm.unknown_test_field'
    with pytest.raises(ValidationError):
        TCMKnowledgeGraph.model_validate(graph)
    path.write_text('{invalid json', encoding='utf-8')
    with pytest.raises(ValidationError):
        registry_module.semantic_field_constraints(FIELD_ID)
    with pytest.raises(ValidationError):
        TCMKnowledgeGraph.model_validate(graph_payload())
    write_registry(path, payload)
    assert TCMKnowledgeGraph.model_validate(graph_payload()).nodes


def test_semantic_snapshot_is_consistent_only_within_its_scope(monkeypatch, tmp_path):
    path, payload = point_registry(monkeypatch, tmp_path)
    with registry_module.semantic_constraint_snapshot():
        original = registry_module.semantic_field_constraints(FIELD_ID)
        field = next(item for item in payload['fields'] if item['field_id'] == FIELD_ID)
        field['allowed_on'] = ['tcm_group:safety']
        write_registry(path, payload)
        with registry_module.semantic_constraint_snapshot():
            assert registry_module.semantic_field_constraints(FIELD_ID) is original
    current = registry_module.semantic_field_constraints(FIELD_ID)
    assert current is not original and current.allowed_on == ('tcm_group:safety',)


def test_semantic_snapshot_does_not_cross_threads(monkeypatch, tmp_path):
    path, payload = point_registry(monkeypatch, tmp_path)
    original_text = path.read_text('utf-8')
    field = next(item for item in payload['fields'] if item['field_id'] == FIELD_ID)
    field['allowed_on'] = ['tcm_group:safety']
    other_text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    owner = threading.get_ident()
    monkeypatch.setattr(registry_module, '_registry_text',
                        lambda: original_text if threading.get_ident() == owner else other_text)
    with registry_module.semantic_constraint_snapshot():
        current = registry_module.semantic_field_constraints(FIELD_ID)
        with ThreadPoolExecutor(max_workers=1) as pool:
            other = pool.submit(registry_module.semantic_field_constraints, FIELD_ID).result(timeout=5)
        assert 'tcm_group:theory' in current.allowed_on
        assert other.allowed_on == ('tcm_group:safety',)
        assert registry_module.semantic_field_constraints(FIELD_ID) is current
