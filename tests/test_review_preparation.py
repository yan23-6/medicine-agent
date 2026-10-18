"""Preparation software fixtures only; no actual OCR, external model or experts."""
import json
import shutil
import subprocess
import sys
from datetime import timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from medicine_agent.analysis.file_learning import FileLearningService
from medicine_agent.analysis.models import AnalysisError, DocumentBlock, DocumentPosition, DocumentUnit
from medicine_agent.analysis.review_preparation import ReviewPreparationService
from medicine_agent.analysis.store import atomic_json
from medicine_agent.bootstrap import create_facade
from medicine_agent.contracts import export_schemas
from medicine_agent.domain.ids import file_sha256, stable_id
from medicine_agent.domain.review_preparation import ReviewPreparationReport, ReviewPreparationRequest
from medicine_agent.domain.reviews import ReviewRecord
from test_coverage import mutate, without_cache


class PreparationModel:
    provider = 'synthetic-software-only'
    model = 'preparation-fixture'

    def generate_json(self, *, system, user, schema):
        data = json.loads(user)
        records = data['evidence'] if isinstance(data, dict) else data
        e = records[-1]
        quote = {'evidence_id': e['evidence_id'], 'text': e['raw_text']}
        fact = {'field_id': 'tcm.theory_proposition_text', 'value': e['raw_text'], 'quotes': [quote]}
        inferred = {**fact, 'state': 'inferred', 'reason': 'Synthetic rationale, not a medical finding'}
        if len(records) > 4:
            inferred['quotes'] = [quote, {'evidence_id': records[3]['evidence_id'], 'text': records[3]['raw_text']}]
        gap = {'reason': 'Synthetic unread meaning', 'quotes': [{'evidence_id': records[-3]['evidence_id'], 'text': records[-3]['raw_text']}]}
        return {'nodes': [{'node_id': 'local', 'title': 'Synthetic source', 'source_id': e['source_id'],
            'statement': e['raw_text'], 'categories': ['tcm_foundation'], 'quotes': [quote], 'gaps': [gap],
            'groups': [{'group_id': 'g', 'kind': 'theory', 'facts': [fact, inferred,
                {**fact, 'field_id': 'tcm.synthetic_unregistered'}]}]}], 'gaps': [gap]}


@pytest.fixture
def material(tmp_path, monkeypatch):
    monkeypatch.setattr('medicine_agent.analysis.service.inspect_document', lambda p: ('pdf', 5))

    def extract(path, unit, force_ocr, timeout):
        return DocumentUnit(index=unit, method='synthetic-adapter', blocks=[DocumentBlock(
            text=f'Self authored {label} unit {unit}.', position=DocumentPosition(unit=unit, page=unit), confidence=.85)
            for label in ('unreferenced', 'gap', 'context', 'statement')])

    monkeypatch.setattr('medicine_agent.skills.document_extraction.handler.extract_unit', extract)
    source = tmp_path / 'source.txt'
    source.write_text('Self authored adapter bytes, not a PDF.', encoding='utf-8')
    public = tmp_path / 'packages'
    learning = FileLearningService(tmp_path / 'learning', public, PreparationModel())
    task = learning.submit({'paths': [str(source)], 'units': [1, 2], 'allowed_use': 'synthetic-software-test'})
    result = learning.run(task['task_id'])
    assert result['status'] == 'completed', result
    return learning, public / result['package_path']


def service(tmp_path, root=None):
    return ReviewPreparationService(root or tmp_path / 'packages', tmp_path / 'prep-cache')


def snapshot(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}


def test_complete_independent_sources_candidates_anomalies_and_blank_templates(material, tmp_path):
    _, file = material
    before = snapshot(file.parent)
    report = service(tmp_path).prepare()
    assert report.status == 'complete', report.issues
    assert report.counts == dict(source_evidence=8, candidate_targets=6, nodes=2, facts=4,
        gaps=8, rejected_candidates=2, issues=0, facts_inferred=2, facts_stated=2)
    assert sum('unreferenced' in s.evidence.raw_text for s in report.sources) == 2
    assert not any('unreferenced' in q.text for c in report.candidates for q in c.quotes)
    assert any('cross_page' in c.flags for c in report.candidates)
    assert any('low_ocr_confidence' in c.flags for c in report.candidates)
    assert {a.kind for a in report.anomalies} == {'graph_gap', 'node_gap', 'rejected_candidate'}
    for item in [*report.sources, *report.candidates, *report.anomalies]:
        assert item.worksheet.model_dump() == dict(reviewer=None, decision=None, reason=None, submitted=False)
        assert item.origins and all(o.archive_sha256 == file_sha256(file.read_bytes()) for o in item.origins)
    gates = {g.name: g.status for g in report.gates}
    assert gates['engineering'] == 'passed' and gates['source'] == 'passed'
    assert gates['medical'] == gates['training'] == gates['case_baseline'] == 'blocked'
    assert gates['performance'] == gates['license'] == gates['cross_source'] == 'not_evaluated'
    assert not report.release_allowed and report.medical_review == 'unreviewed' and not report.review_records
    assert snapshot(file.parent) == before


def test_input_order_duplicates_and_repeat_are_deterministic(material, tmp_path):
    _, file = material
    copy = file.parent / 'copy.medpkg'
    shutil.copyfile(file, copy)
    s = service(tmp_path)
    a = s.prepare({'archives': [file.name, copy.name, file.name]})
    b = s.prepare({'archives': [copy.name, file.name]})
    assert a == b == s.prepare()
    assert a.counts['source_evidence'] == 8 and a.counts['candidate_targets'] == 6
    assert all(len(i.origins) == 2 for i in a.sources + a.candidates + a.anomalies)


def test_bad_package_isolated_not_false_complete_and_selected_files_filter(material, tmp_path):
    _, file = material
    (file.parent / 'bad.medpkg').write_bytes(b'not an archive')
    report = service(tmp_path).prepare()
    assert report.status == 'partial' and report.counts['source_evidence'] == 8
    assert any(i.code == 'PACKAGE_QUARANTINED' for i in report.issues)
    assert next(g.status for g in report.gates if g.name == 'engineering') == 'blocked'
    selected = service(tmp_path).prepare({'archives': [file.name]})
    assert selected.status == 'complete' and not selected.issues


def test_missing_requested_archive_and_missing_root_are_explicit(tmp_path):
    report = service(tmp_path).prepare({'archives': ['missing.medpkg']})
    assert report.status == 'empty' and report.issues and not (tmp_path / 'packages').exists()
    assert all(g.status != 'passed' for g in report.gates)


def test_old_no_revision_preserves_materials_unknown_coverage(material, tmp_path):
    _, file = material

    def legacy(path):
        without_cache(path)
        (path / 'revision.json').unlink()

    mutate(file, tmp_path, legacy)
    report = service(tmp_path).prepare()
    assert report.counts['source_evidence'] == 8 and report.counts['candidate_targets'] == 6
    assert all(r.state == 'unknown' for r in report.coverage.records)
    assert next(g.status for g in report.gates if g.name == 'source') == 'not_evaluated'


def test_optional_page_missing_is_retained_without_fabricated_location(material, tmp_path):
    _, file = material

    def missing(path):
        without_cache(path)
        records = [json.loads(l) for l in (path / 'evidence.jsonl').read_text('utf-8').splitlines()]
        records[0]['location'].pop('page')
        (path / 'evidence.jsonl').write_text('\n'.join(json.dumps(e) for e in records) + '\n', encoding='utf-8')

    mutate(file, tmp_path, missing)
    report = service(tmp_path).prepare()
    item = next(s for s in report.sources if 'source_location_incomplete' in s.flags)
    assert 'page' not in item.evidence.location and report.counts['source_evidence'] == 8
    assert next(g.status for g in report.gates if g.name == 'source') == 'not_evaluated'


def test_review_opinion_is_separate_and_portable_ancestor_not_conflict(material, tmp_path):
    learning, _ = material
    target = learning.review_queue('fact')['items'][0]
    first = learning.record_review({'target': target['target'], 'decision': 'needs_revision',
        'reviewer': 'synthetic-user', 'reason': 'Synthetic software check', 'proposed_value': 'not medical truth'})
    report = service(tmp_path).prepare()
    assert report.status == 'complete', report.issues
    current = next(c for c in report.candidates if c.target.model_dump(mode='json') == target['target'])
    assert current.user_review_state == 'needs_revision'
    assert current.expected_previous_id == first['record']['review_id']
    assert current.worksheet.decision is None and report.medical_review == 'unreviewed'
    assert len(report.review_records) == 1


def test_export_complete_self_contained_hashed_new_directory(material, tmp_path):
    _, file = material
    before = snapshot(file.parent)
    out = tmp_path / 'export'
    exported = service(tmp_path).export(out)
    assert exported.status == 'complete'
    assert set(p.name for p in out.iterdir()) == {*exported.files, 'manifest.json'}
    for name, sha in exported.files.items():
        assert file_sha256((out / name).read_bytes()) == sha
    report = ReviewPreparationReport.model_validate_json((out / 'preparation.json').read_text('utf-8'))
    assert report.preparation_id == exported.preparation_id
    text = (out / 'source-annotations.md').read_text('utf-8')
    assert text.count('## annotation_') == 8 and 'unreferenced' in text
    candidates = (out / 'candidates.md').read_text('utf-8')
    assert '已获暂时认可' not in candidates and candidates.count('稳定目标') >= 6
    assert '不是可写ReviewTarget' in (out / 'anomalies.md').read_text('utf-8')
    assert snapshot(file.parent) == before
    with pytest.raises(AnalysisError):
        service(tmp_path).export(out)


@pytest.mark.parametrize('location', ['packages/out', 'packages', 'prep-cache/archives/out', 'out.json', 'out.md'])
def test_export_rejects_unsafe_or_file_paths(material, tmp_path, location):
    with pytest.raises(AnalysisError, match='new directory'):
        service(tmp_path).export(tmp_path / location)


def test_export_failure_does_not_publish_or_leave_pending_material(material, tmp_path, monkeypatch):
    def broken(report):
        raise OSError('synthetic write failure')
    monkeypatch.setattr('medicine_agent.analysis.review_preparation.render_preparation', broken)
    out = tmp_path / 'export'
    with pytest.raises(OSError):
        service(tmp_path).export(out)
    assert not out.exists() and not list(tmp_path.glob('.pending-review-preparation-*'))


def test_export_race_does_not_replace_another_output(material, tmp_path, monkeypatch):
    import medicine_agent.analysis.review_preparation as module
    render = module.render_preparation
    out = tmp_path / 'racing-output'

    def race(report):
        out.mkdir()
        (out / 'other.txt').write_text('Existing user output', encoding='utf-8')
        return render(report)

    monkeypatch.setattr(module, 'render_preparation', race)
    with pytest.raises(AnalysisError):
        service(tmp_path).export(out)
    assert (out / 'other.txt').read_text('utf-8') == 'Existing user output'
    assert not list(tmp_path.glob('.pending-review-preparation-*'))


def test_partially_failed_export_cannot_look_complete(material, tmp_path):
    _, file = material
    (file.parent / 'bad.medpkg').write_bytes(b'bad')
    out = tmp_path / 'partial'
    result = service(tmp_path).export(out)
    assert result.status == 'partial'
    assert 'partial' in (out / 'README.md').read_text('utf-8')
    assert json.loads((out / 'preparation.json').read_text('utf-8'))['status'] == 'partial'


@pytest.mark.parametrize('archive', ['../x.medpkg', 'C:/x.medpkg', 'x.json', 'folder\\x.medpkg'])
def test_invalid_input_file_paths_rejected(archive):
    with pytest.raises(ValidationError):
        ReviewPreparationRequest(archives=[archive])


def opinion(material):
    learning, _ = material
    target = learning.review_queue('fact')['items'][0]
    result = learning.record_review({'target': target['target'], 'decision': 'confirmed',
        'reviewer': 'synthetic-user', 'reason': 'Synthetic opinion; not medical confirmation'})
    return learning.library.root / result['package_path']


@pytest.mark.parametrize('damage', ['fingerprint', 'branch', 'invalid_record'])
def test_history_anomalies_do_not_become_final_confirmation(material, tmp_path, damage):
    file = opinion(material)
    root = tmp_path / ('mutation-' + file.stem)

    def edit_bundle(bundle):
        relative = next(name for name in bundle.files if name.startswith('reviews/'))
        payload = json.loads((root / relative).read_text('utf-8'))
        if damage == 'invalid_record':
            atomic_json(root / relative, {'invalid': 'synthetic record'})
            bundle.files[relative] = file_sha256((root / relative).read_bytes())
            return
        record = ReviewRecord.model_validate(payload['record'])
        if damage == 'fingerprint':
            record.request.target.fingerprint = '0' * 64
            bundle.files.pop(relative)
            (root / relative).unlink()
        else:
            record.created_at += timedelta(seconds=1)
            record.request.reason = 'Synthetic competing root opinion'
        record.review_id = stable_id('review', record.model_dump(mode='json', exclude={'review_id'}))
        value = record.model_dump(mode='json')
        from medicine_agent.analysis.store import digest
        destination = 'reviews/' + record.review_id + '.json'
        atomic_json(root / destination, {'record': value, 'sha256': digest(value)})
        bundle.files[destination] = file_sha256((root / destination).read_bytes())

    modified = mutate(file, tmp_path, lambda p: None, edit_bundle)
    report = service(tmp_path).prepare({'archives': [modified.name]})
    assert report.status == 'partial'
    assert any(i.code == 'REVIEW_HISTORY_INVALID' for i in report.issues)
    assert not any(c.user_review_state == 'confirmed' for c in report.candidates)
    assert all(c.expected_previous_id is None for c in report.candidates)
    assert report.medical_review == 'unreviewed'


def test_archive_changes_after_inventory_leave_no_partial_file_material(material, tmp_path, monkeypatch):
    _, file = material
    s = service(tmp_path)
    original = s.coverage.inventory

    def changed():
        inventory = original()
        with file.open('ab') as stream:
            stream.write(b'synthetic-race')
        return inventory

    monkeypatch.setattr(s.coverage, 'inventory', changed)
    report = s.prepare()
    assert report.status == 'empty' and not report.sources and not report.candidates
    assert not report.coverage.records
    assert any(i.code == 'PREPARATION_ARCHIVE_QUARANTINED' for i in report.issues)


def test_cli_and_schema_snapshot(material, tmp_path):
    _, file = material
    out = tmp_path / 'cli-output'
    command = [sys.executable, '-m', 'medicine_agent.cli', 'analyze', 'review-prepare',
        '--packages', str(file.parent), '--workspace', str(tmp_path / 'cli-cache'), '--output-dir', str(out)]
    result = subprocess.run(command, capture_output=True, encoding='utf-8', timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)['status'] == 'complete'
    invalid = tmp_path / 'request.json'
    invalid.write_text('{"archives":["../wrong.medpkg"]}', encoding='utf-8')
    result = subprocess.run(command[:-2] + ['--input-file', str(invalid)], capture_output=True, encoding='utf-8', timeout=30)
    assert result.returncode == 1 and 'PREPARATION_REQUEST_INVALID' in result.stdout
    root = tmp_path / 'schemas'
    index = export_schemas(create_facade(), root, contract_set='review-preparation')
    assert len(index['files']) == 10 and index['contract_version'] == '0.1.0'
    for name, sha in index['files'].items():
        assert file_sha256((root / name).read_bytes()) == sha
        assert (root / name).read_bytes() == (Path('schemas/review-preparation') / name).read_bytes()
