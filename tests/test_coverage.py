"""Synthetic software fixtures; no real PDF/OCR/model calls or medical review."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from medicine_agent.analysis.coverage import CoverageService
from medicine_agent.analysis.file_learning import FileLearningService
from medicine_agent.analysis.models import AnalysisError, DocumentUnit, DocumentBlock, DocumentPosition
from medicine_agent.bootstrap import create_facade
from medicine_agent.contracts import export_schemas
from medicine_agent.domain.coverage import CoverageRequest, CoverageHistory
from medicine_agent.domain.ids import file_sha256, stable_id
from medicine_agent.packages.archive import pack_archive, unpack_archive
from medicine_agent.analysis.store import atomic_json


class SyntheticModel:
    provider = 'synthetic-software-check'
    model = 'coverage-fixture'

    def generate_json(self, *, system, user, schema):
        payload = json.loads(user)
        e = (payload['evidence'] if isinstance(payload, dict) else payload)[-1]
        quote = {'evidence_id': e['evidence_id'], 'text': e['raw_text']}
        return {'nodes': [{'node_id': 'local', 'source_id': e['source_id'],
            'title': 'Self-authored unit', 'statement': e['raw_text'], 'categories': ['tcm_foundation'],
            'quotes': [quote], 'groups': [{'group_id': 'g', 'kind': 'theory', 'facts': [{
                'field_id': 'tcm.theory_proposition_text', 'value': e['raw_text'], 'quotes': [quote]}]}]}]}


@pytest.fixture
def factory(tmp_path, monkeypatch):
    # Simulate the adapter boundary, not the validators. No PDF fixture is created.
    kind = ['physical_page']
    monkeypatch.setattr('medicine_agent.analysis.service.inspect_document', lambda p: ('pdf' if kind[0] == 'physical_page' else 'txt', 5))

    def extract(path, unit, force_ocr, timeout):
        return DocumentUnit(index=unit, method='synthetic-adapter', blocks=[DocumentBlock(
            text=f'Self-authored test source unit {unit}.',
            position=DocumentPosition(unit=unit, page=unit if kind[0] == 'physical_page' else None))])

    monkeypatch.setattr('medicine_agent.skills.document_extraction.handler.extract_unit', extract)
    source = tmp_path / 'synthetic-adapter-input.txt'
    source.write_text('Synthetic bytes, not a PDF or medical source.', encoding='utf-8')
    sha = file_sha256(source.read_bytes())
    sequence = []

    def make(*, units=(1, 2), mode='model', public=None, unit_kind='physical_page'):
        kind[0] = unit_kind
        index = len(sequence)
        sequence.append(index)
        public = public or tmp_path / 'packages'
        service = FileLearningService(tmp_path / f'work-{index}', public, SyntheticModel() if mode == 'model' else None)
        task = service.submit({'paths': [str(source)], 'allowed_use': 'synthetic-software-only',
            'mode': mode, 'units': list(units), 'owner_id': f'fixture-{index}'})
        result = service.run(task['task_id'])
        assert result['status'] == 'completed', result
        return public / result['package_path']

    return make, sha


def request(sha, **kwargs):
    return CoverageRequest(source_sha256=sha, unit_kind='physical_page', document_unit_count=5,
                           units=[1, 2, 3, 4, 5], **kwargs)


def service(tmp_path, root=None):
    return CoverageService(root or tmp_path / 'packages', tmp_path / 'coverage-cache')


def mutate(file, tmp_path, change, bundle_change=None):
    """Re-sign synthetic metadata so tests reach semantic validation, not only ZIP hashes."""
    root = tmp_path / ('mutation-' + file.stem)
    bundle = unpack_archive(file, root)
    for component in bundle.components:
        path = root / component.path
        change(path)
        manifest = json.loads((path / 'manifest.json').read_text('utf-8'))
        manifest['files'] = {name: file_sha256((path / name).read_bytes()) for name in manifest['files'] if (path / name).exists()}
        atomic_json(path / 'manifest.json', manifest)
        atomic_json(path / 'checksums.json', manifest['files'])
        component.manifest_sha256 = file_sha256((path / 'manifest.json').read_bytes())
    if bundle_change:
        bundle_change(bundle)
    bundle.bundle_id = stable_id('bundle', bundle.model_dump(mode='json', exclude={'bundle_id'}))
    atomic_json(root / 'bundle.json', bundle.model_dump(mode='json'))
    target = file.parent / ('modified-' + file.name)
    pack_archive(root, target)
    file.unlink()  # Only a temporary synthetic fixture, not any user package.
    return target


def without_cache(path):
    (path / 'ownership.json').unlink()


def test_real_validation_and_minimal_plan_read_only(factory, tmp_path):
    make, sha = factory
    file = make()
    before = {p.name: p.read_bytes() for p in file.parent.iterdir() if p.is_file()}
    s = service(tmp_path)
    plan = s.plan(request(sha))
    assert not plan.inventory.issues
    assert [(d.unit, d.action, d.stage) for d in plan.decisions] == [
        (1, 'covered', None), (2, 'covered', None), (3, 'proposed', 'extraction'),
        (4, 'proposed', 'extraction'), (5, 'proposed', 'extraction')]
    assert all(r.state == 'verified' and r.address.resources for r in plan.inventory.records)
    assert all(r.adapter_versions and r.extraction_methods for r in plan.inventory.records if r.stage == 'extraction')
    assert before == {p.name: p.read_bytes() for p in file.parent.iterdir() if p.is_file()}
    assert s.plan(request(sha)).model_dump() == plan.model_dump()


def test_extract_only_does_not_claim_semantics(factory, tmp_path):
    make, sha = factory
    make(mode='extractive')
    plan = service(tmp_path).plan(request(sha))
    assert [(d.action, d.stage) for d in plan.decisions[:2]] == [('proposed', 'semantic_candidate')] * 2
    assert not any(r.stage == 'semantic_candidate' and r.state == 'verified' for r in plan.inventory.records)


def test_unsorted_overlapping_duplicate_files_and_history_are_deterministic(factory, tmp_path):
    make, sha = factory
    a = make(units=(3, 1, 2))
    make(units=(4, 2))
    shutil.copyfile(a, a.parent / 'duplicate.medpkg')
    history = [{'source_sha256': sha, 'unit_kind': 'physical_page', 'units': [5, 5],
                'stage': 'semantic_candidate', 'reference': 'old-report'}]
    s = service(tmp_path)
    plan = s.plan(request(sha, history=history + history))
    assert [d.action for d in plan.decisions] == ['covered'] * 4 + ['held']
    assert s.plan(request(sha, history=list(reversed(history + history)))).model_dump() == plan.model_dump()


def test_legacy_revision_and_scope_missing_are_unknown(factory, tmp_path):
    make, sha = factory
    file = make()

    def change(path):
        without_cache(path)
        (path / 'revision.json').unlink()

    mutate(file, tmp_path, change)
    plan = service(tmp_path).plan(request(sha))
    assert not plan.inventory.issues
    assert all(r.reason == 'REVISION_MISSING' for r in plan.inventory.records)
    assert all(d.action == 'needs_check' for d in plan.decisions)


@pytest.mark.parametrize('field', ['processing_scope', 'runtime'])
def test_optional_metadata_missing_does_not_crash(factory, tmp_path, field):
    make, sha = factory
    file = make()

    def change(path):
        without_cache(path)
        revision = json.loads((path / 'revision.json').read_text('utf-8'))
        revision.pop(field)
        atomic_json(path / 'revision.json', revision)

    mutate(file, tmp_path, change)
    plan = service(tmp_path).plan(request(sha))
    assert not plan.inventory.issues
    assert all(d.action == 'needs_check' for d in plan.decisions[:2])


def test_history_only_known_and_unbound_sources(factory, tmp_path):
    _, sha = factory
    (tmp_path / 'packages').mkdir()
    history = [dict(source_sha256=sha, unit_kind='physical_page', units=[2, 1],
                    stage='semantic_candidate', reference='historical-declaration'),
               dict(stage='extraction', reference='book-name-without-fingerprint')]
    plan = service(tmp_path).plan(request(sha, history=history))
    assert [d.action for d in plan.decisions] == ['held', 'held', 'proposed', 'proposed', 'proposed']
    assert plan.unresolved_record_indexes
    other = service(tmp_path).plan(request('a' * 64, history=history))
    assert all(d.action == 'proposed' for d in other.decisions)
    assert not any(r.state == 'verified' for r in plan.inventory.records)


@pytest.mark.parametrize('damage', ['revision_sha', 'source_identity', 'out_of_bounds', 'page_confusion'])
def test_semantically_bad_metadata_is_quarantined_with_healthy_package(factory, tmp_path, damage):
    make, sha = factory
    file = make()
    healthy = make(units=(3,))

    def change(path):
        without_cache(path)
        revision = json.loads((path / 'revision.json').read_text('utf-8'))
        if damage == 'revision_sha':
            revision['source_sha256'] = 'a' * 64
        elif damage == 'source_identity':
            rows = (path / 'sources.jsonl').read_text('utf-8')
            (path / 'sources.jsonl').write_text(rows.replace(sha, 'a' * 64), encoding='utf-8')
        elif damage == 'out_of_bounds':
            revision['units'] = [6]
            revision['processing_scope']['selected_units'] = [6]
        else:
            rows = [json.loads(line) for line in (path / 'evidence.jsonl').read_text('utf-8').splitlines()]
            rows[0]['location']['page'] = 5
            (path / 'evidence.jsonl').write_text('\n'.join(json.dumps(row) for row in rows) + '\n', encoding='utf-8')
        atomic_json(path / 'revision.json', revision)

    mutate(file, tmp_path, change)
    plan = service(tmp_path).plan(request(sha))
    assert len(plan.inventory.issues) == 1
    assert all(r.address.archive == healthy.name for r in plan.inventory.records)
    assert plan.decisions[2].action == 'covered'
    assert plan.decisions[0].action == 'needs_check'


def test_corrupt_zip_isolated_and_source_directory_not_repaired(factory, tmp_path):
    make, sha = factory
    make()
    bad = tmp_path / 'packages' / 'broken.medpkg'
    bad.write_bytes(b'invalid archive')
    plan = service(tmp_path).plan(request(sha))
    assert len(plan.inventory.issues) == 1 and plan.decisions[0].action == 'covered'
    assert plan.decisions[2].action == 'needs_check'
    assert bad.read_bytes() == b'invalid archive'


def test_policy_mismatch_keeps_extraction_and_requires_check(factory, tmp_path):
    make, sha = factory
    make()
    plan = service(tmp_path).plan(request(sha, policy={'analysis_policy': 'future-policy'}))
    assert all(d.reason == 'INCOMPATIBLE_POLICY' and d.stage == 'semantic_candidate' for d in plan.decisions[:2])
    assert {plan.inventory.records[i].stage for i in plan.decisions[0].record_indexes} == {'extraction', 'semantic_candidate'}


def test_verified_commit_missing_policy_version_requires_check(factory, tmp_path):
    make, sha = factory
    file = make()

    def change(path):
        for name in ('revision.json', 'ownership.json'):
            data = json.loads((path / name).read_text('utf-8'))
            data['runtime'].pop('analysis_policy')
            atomic_json(path / name, data)

    mutate(file, tmp_path, change)
    plan = service(tmp_path).plan(request(sha))
    assert not plan.inventory.issues
    assert all(d.reason == 'POLICY_UNKNOWN' for d in plan.decisions[:2])


def test_unowned_extractive_legacy_preserves_minimal_semantic_plan(factory, tmp_path):
    make, sha = factory
    file = make(mode='extractive')
    mutate(file, tmp_path, without_cache)
    plan = service(tmp_path).plan(request(sha))
    assert not plan.inventory.issues
    assert [(d.action, d.stage) for d in plan.decisions[:2]] == [('proposed', 'semantic_candidate')] * 2


def test_legacy_missing_position_stays_unknown_not_false_or_crash(factory, tmp_path):
    make, sha = factory
    file = make()

    def change(path):
        without_cache(path)
        rows = [json.loads(line) for line in (path / 'evidence.jsonl').read_text('utf-8').splitlines()]
        rows[0]['location'].pop('unit')
        (path / 'evidence.jsonl').write_text('\n'.join(json.dumps(row) for row in rows) + '\n', encoding='utf-8')

    mutate(file, tmp_path, change)
    plan = service(tmp_path).plan(request(sha))
    assert not plan.inventory.issues
    assert all(d.action == 'needs_check' for d in plan.decisions[:2])


def test_missing_page_only_marks_affected_unit_unknown(factory, tmp_path):
    make, sha = factory
    file = make(mode='extractive')

    def change(path):
        without_cache(path)
        rows = [json.loads(line) for line in (path / 'evidence.jsonl').read_text('utf-8').splitlines()]
        rows[0]['location'].pop('page')
        (path / 'evidence.jsonl').write_text('\n'.join(json.dumps(row) for row in rows) + '\n', encoding='utf-8')

    mutate(file, tmp_path, change)
    plan = service(tmp_path).plan(request(sha))
    assert not plan.inventory.issues
    assert plan.decisions[0].action == 'needs_check'
    assert (plan.decisions[1].action, plan.decisions[1].stage) == ('proposed', 'semantic_candidate')


def test_unit_kind_and_document_count_conflicts_not_truncated(factory, tmp_path):
    make, sha = factory
    make()
    r = request(sha).model_dump()
    for update in ({'unit_kind': 'text_line'}, {'document_unit_count': 4, 'units': [1, 2, 3, 4]}):
        plan = service(tmp_path).plan({**r, **update})
        assert all(d.reason == 'UNIT_KIND_OR_DOCUMENT_SIZE_CONFLICT' for d in plan.decisions)


def test_wrong_target_fingerprint_does_not_match_book_name(factory, tmp_path):
    make, _ = factory
    make()
    assert all(d.action == 'proposed' for d in service(tmp_path).plan(request('a' * 64)).decisions)


def test_nonphysical_units_retained_without_fabricated_pages(factory, tmp_path):
    make, sha = factory
    make(unit_kind='text_line')
    s = service(tmp_path)
    assert {r.unit_kind for r in s.inventory().records} == {'text_line'}
    assert all(d.action == 'needs_check' for d in s.plan(request(sha)).decisions)
    r = request(sha).model_dump()
    r['unit_kind'] = 'text_line'
    assert [d.action for d in s.plan(r).decisions[:2]] == ['covered', 'covered']


def test_inactive_components_only_hold_not_cover(factory, tmp_path):
    make, sha = factory
    file = make()

    def deactivate(bundle):
        for component in bundle.components:
            component.active = False
        bundle.concept_groups = []

    mutate(file, tmp_path, lambda p: None, deactivate)
    plan = service(tmp_path).plan(request(sha))
    assert not plan.inventory.issues
    assert [d.action for d in plan.decisions[:2]] == ['held', 'held']


def test_same_lane_active_revision_conflict_requires_selection(factory, tmp_path):
    make, sha = factory
    make()
    s = service(tmp_path)
    family = s.inventory().records[0].address.family
    second = make()

    def change(path):
        without_cache(path)
        revision = json.loads((path / 'revision.json').read_text('utf-8'))
        revision['family'] = family
        atomic_json(path / 'revision.json', revision)

    mutate(second, tmp_path, change)
    plan = s.plan(request(sha))
    assert not plan.inventory.issues
    assert all(d.reason == 'ACTIVE_REVISION_CONFLICT' for d in plan.decisions[:2])


def test_changed_archive_during_scan_does_not_commit_partial_coverage(factory, tmp_path, monkeypatch):
    make, _ = factory
    file = make()
    s = service(tmp_path)
    load = s.library.load

    def racing_load(path):
        result = load(path)
        with file.open('ab') as stream:
            stream.write(b'synthetic-race')
        return result

    monkeypatch.setattr(s.library, 'load', racing_load)
    inventory = s.inventory()
    assert inventory.issues and not inventory.records


def test_cache_and_source_must_be_non_nested(tmp_path):
    with pytest.raises(AnalysisError, match='non-nested'):
        CoverageService(tmp_path / 'workspace' / 'archives', tmp_path / 'workspace')
    with pytest.raises(AnalysisError):
        CoverageService(tmp_path / 'packages', tmp_path / 'packages' / 'cache')


def test_missing_root_not_created_and_not_assumed_empty(tmp_path):
    root = tmp_path / 'missing'
    plan = service(tmp_path, root).plan(request('a' * 64))
    assert not root.exists() and plan.inventory.issues
    assert all(d.action == 'needs_check' for d in plan.decisions)


@pytest.mark.parametrize('units', [[0], [6], ['1'], [True], [1.0], []])
def test_request_invalid_ranges_rejected(units):
    with pytest.raises(ValidationError):
        CoverageRequest(source_sha256='a' * 64, unit_kind='physical_page', document_unit_count=5, units=units)


def test_history_rejects_bad_fields_and_normalizes_ranges():
    assert CoverageHistory(stage='extraction', reference='old', units=[3, 1, 3]).units == [1, 3]
    with pytest.raises(ValidationError):
        CoverageHistory(stage='extraction', reference='old', units=[True])


def test_cli_and_exported_contracts(factory, tmp_path):
    make, sha = factory
    make()
    input_file = tmp_path / 'request.json'
    input_file.write_text(request(sha).model_dump_json(), encoding='utf-8')
    command = [sys.executable, '-m', 'medicine_agent.cli', 'analyze', 'coverage',
        '--packages', str(tmp_path / 'packages'), '--workspace', str(tmp_path / 'cli-cache'), '--input-file', str(input_file)]
    result = subprocess.run(command, capture_output=True, encoding='utf-8', timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)['decisions'][0]['action'] == 'covered'
    input_file.write_text('{"invalid":true}', encoding='utf-8')
    invalid = subprocess.run(command, capture_output=True, encoding='utf-8', timeout=30)
    assert invalid.returncode == 1 and json.loads(invalid.stdout)['error']['code'] == 'COVERAGE_REQUEST_INVALID'
    root = tmp_path / 'schemas'
    index = export_schemas(create_facade(), root, contract_set='coverage')
    assert index['contract_version'] == '0.1.0' and len(index['files']) == 9
    for name, sha in index['files'].items():
        assert file_sha256((root / name).read_bytes()) == sha
        assert (root / name).read_bytes() == (Path('schemas/coverage') / name).read_bytes()
