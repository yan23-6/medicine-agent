"""Synthetic snapshot admission tests; never real materials or model services."""
import json
import os
import pathlib
import shutil
import stat
import traceback
from types import SimpleNamespace

import pytest

from medicine_agent.analysis.models import AnalysisError
from medicine_agent.analysis.review_preparation import ReviewPreparationService
from medicine_agent.analysis.review_snapshot import load_preparation_snapshot
from medicine_agent.domain.ids import file_sha256, stable_id
from test_review_preparation import material, snapshot


@pytest.fixture
def exported(material, tmp_path):
    _, package = material
    target = tmp_path / 'snapshot'
    ReviewPreparationService(package.parent, tmp_path / 'export-cache').export(target)
    return target, package.parent, tmp_path / 'read-cache'


def load(exported):
    target, packages, workspace = exported
    return load_preparation_snapshot(target, packages=packages, workspace=workspace)


def rewrite_report(target, mutate):
    """Simulate self-consistent tampering, including IDs and manifest hashes."""
    report_path = target / 'preparation.json'
    report = json.loads(report_path.read_text('utf-8'))
    mutate(report)
    report['preparation_id'] = stable_id('preparation',
        {k: v for k, v in report.items() if k != 'preparation_id'})
    report_path.write_text(json.dumps(report, ensure_ascii=False), encoding='utf-8')
    manifest_path = target / 'manifest.json'
    manifest = json.loads(manifest_path.read_text('utf-8'))
    manifest['preparation_id'] = report['preparation_id']
    manifest['status'] = report['status']
    manifest['files']['preparation.json'] = file_sha256(report_path.read_bytes())
    manifest_path.write_text(json.dumps(manifest), encoding='utf-8')


def test_complete_snapshot_rebinds_without_changing_inputs(exported):
    target, packages, _ = exported
    before = snapshot(target), snapshot(packages)
    result = load(exported)
    assert result.report.status == 'complete'
    assert result.snapshot_id.startswith('snapshot_')
    assert result.manifest_sha256 == file_sha256((target / 'manifest.json').read_bytes())
    assert result.report.medical_review == 'unreviewed' and not result.report.release_allowed
    assert (snapshot(target), snapshot(packages)) == before
    assert load(exported).snapshot_id == result.snapshot_id


@pytest.mark.parametrize('change', ['fingerprint', 'source', 'count'])
def test_self_consistent_tampering_cannot_pass_source_binding(exported, change):
    def mutate(report):
        if change == 'fingerprint':
            report['candidates'][0]['target']['fingerprint'] = 'a' * 64
        elif change == 'source':
            report['sources'][0]['source']['sha256'] = 'a' * 64
        else:
            report['counts']['nodes'] += 1

    rewrite_report(exported[0], mutate)
    with pytest.raises(AnalysisError) as exc:
        load(exported)
    assert exc.value.code == 'SNAPSHOT_SOURCE_MISMATCH'


def test_invalid_manifest_path_rejected_before_opening_declared_resource(exported, monkeypatch):
    from medicine_agent.analysis import review_snapshot as module

    manifest_path = exported[0] / 'manifest.json'
    manifest = json.loads(manifest_path.read_text('utf-8'))
    manifest['files']['../outside.txt'] = 'a' * 64
    manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
    original = module._read_file
    reads = []

    def observed(path, **kwargs):
        reads.append(path.name)
        return original(path, **kwargs)

    monkeypatch.setattr(module, '_read_file', observed)
    with pytest.raises(AnalysisError) as exc:
        load(exported)
    assert exc.value.code == 'SNAPSHOT_RESOURCES_INVALID'
    assert 'outside.txt' not in reads


# --- D02 fixed synthetic matrix (appended 2026-10-24; tests above unchanged) ---
# Every case starts from an independent healthy export of synthetic fixture material.

def manifest_of(target):
    return json.loads((target / 'manifest.json').read_text('utf-8'))


def put_manifest(target, manifest):
    (target / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')


def report_of(target):
    return json.loads((target / 'preparation.json').read_text('utf-8'))


def reseal(target, report):
    """Forge a self-consistent report: recompute stable id and rebind manifest hashes."""
    report['preparation_id'] = stable_id('preparation',
        {k: v for k, v in report.items() if k != 'preparation_id'})
    (target / 'preparation.json').write_text(json.dumps(report, ensure_ascii=False), encoding='utf-8')
    manifest = manifest_of(target)
    manifest['preparation_id'] = report['preparation_id']
    manifest['status'] = report['status']
    manifest['files']['preparation.json'] = file_sha256((target / 'preparation.json').read_bytes())
    put_manifest(target, manifest)
    return report


def rehash(target, name):
    manifest = manifest_of(target)
    manifest['files'][name] = file_sha256((target / name).read_bytes())
    put_manifest(target, manifest)


def expect(exported, code):
    with pytest.raises(AnalysisError) as exc:
        load(exported)
    assert exc.value.code == code
    return exc.value


def addresses_of(report):
    return [r['address'] for r in report['coverage']['records'] if r.get('address')]


# Row 1: resource set and shape.
@pytest.mark.parametrize('damage', ['missing_body', 'extra_file', 'body_is_directory'])
def test_resource_shape_invalid(exported, damage):
    target, _, _ = exported
    if damage == 'extra_file':
        (target / 'synthetic-extra.md').write_text('synthetic extra', encoding='utf-8')
    else:
        (target / 'README.md').unlink()
        if damage == 'body_is_directory':
            (target / 'README.md').mkdir()
    expect(exported, 'SNAPSHOT_RESOURCES_INVALID')


# Row 2: three paths must be disjoint; workspace must be a creatable directory.
@pytest.mark.parametrize('case', ['snapshot_is_packages', 'workspace_in_snapshot',
                                  'workspace_in_packages', 'workspace_is_file'])
def test_paths_must_be_disjoint(exported, case, tmp_path):
    target, packages, workspace = exported
    if case == 'snapshot_is_packages':
        root, source, cache = target, target, workspace
    elif case == 'workspace_in_snapshot':
        root, source, cache = target, packages, target / 'private-cache'
    elif case == 'workspace_in_packages':
        root, source, cache = target, packages, packages / 'private-cache'
    else:
        blocker = tmp_path / 'workspace-file'
        blocker.write_text('synthetic file, not a directory', encoding='utf-8')
        root, source, cache = target, packages, blocker
    before = snapshot(target), snapshot(packages)
    with pytest.raises(AnalysisError) as exc:
        load_preparation_snapshot(root, packages=source, workspace=cache)
    assert exc.value.code == 'SNAPSHOT_PATH_INVALID'
    assert not (target / 'private-cache').exists()
    assert not (packages / 'private-cache').exists()
    assert (snapshot(target), snapshot(packages)) == before


# Row 3: body bytes changed but manifest not updated.
def test_body_byte_change_without_manifest(exported):
    target, _, _ = exported
    path = target / 'candidates.md'
    path.write_bytes(path.read_bytes() + b' ')
    expect(exported, 'SNAPSHOT_HASH_MISMATCH')


# Row 4: declared resource paths must never be opened.
@pytest.mark.parametrize('kind', ['parent', 'absolute', 'backslash'])
def test_declared_path_never_opened(exported, monkeypatch, tmp_path, kind):
    from medicine_agent.analysis import review_snapshot as module

    target, _, _ = exported
    outside = tmp_path / 'outside.txt'
    outside.write_text('synthetic outside file', encoding='utf-8')
    manifest = manifest_of(target)
    del manifest['files']['README.md']
    manifest['files'][{'parent': '../outside.txt', 'absolute': str(outside),
                       'backslash': '..\\outside.txt'}[kind]] = file_sha256(outside.read_bytes())
    put_manifest(target, manifest)
    reads = []
    original = module._read_file

    def observed(path, **kwargs):
        reads.append(str(path))
        return original(path, **kwargs)

    monkeypatch.setattr(module, '_read_file', observed)
    expect(exported, 'SNAPSHOT_RESOURCES_INVALID')
    # The seven known snapshot files are read before the manifest key set is
    # rejected; the declared external path itself must never be opened.
    root = os.path.normcase(str(target))
    assert len(reads) == 7
    assert all(os.path.normcase(path).startswith(root + os.sep) for path in reads)
    assert not any(os.path.basename(path) == 'outside.txt' for path in reads)


# Row 5: malformed JSON in manifest and report respectively.
@pytest.mark.parametrize('name', ['manifest.json', 'preparation.json'])
def test_duplicate_json_keys_rejected(exported, name):
    target, _, _ = exported
    path = target / name
    text = path.read_text('utf-8').strip()
    assert text.endswith('}')
    path.write_text(text[:-1] + ', "synthetic": 1, "synthetic": 2}', encoding='utf-8')
    expect(exported, 'SNAPSHOT_JSON_INVALID')


@pytest.mark.parametrize('name', ['manifest.json', 'preparation.json'])
def test_invalid_utf8_rejected(exported, name):
    (exported[0] / name).write_bytes(b'\xff\xfe{"version": "0.1.0"}')
    expect(exported, 'SNAPSHOT_JSON_INVALID')


@pytest.mark.parametrize('name', ['manifest.json', 'preparation.json'])
def test_non_object_top_level_rejected(exported, name):
    (exported[0] / name).write_text('[]', encoding='utf-8')
    expect(exported, 'SNAPSHOT_JSON_INVALID')


# Row 6: non-finite numbers rejected during parsing.
@pytest.mark.parametrize('literal', ['NaN', 'Infinity', '1e999'])
def test_non_finite_number_rejected(exported, literal):
    path = exported[0] / 'manifest.json'
    text = path.read_text('utf-8').strip()
    assert text.endswith('}')
    path.write_text(text[:-1] + ', "synthetic_extra": ' + literal + '}', encoding='utf-8')
    expect(exported, 'SNAPSHOT_JSON_INVALID')


# Row 7: explicit 0.1.0 version required for manifest and report.
@pytest.mark.parametrize('change', ['unsupported', 'missing'])
@pytest.mark.parametrize('name', ['manifest', 'report'])
def test_version_must_be_supported(exported, name, change):
    target, _, _ = exported
    if name == 'manifest':
        manifest = manifest_of(target)
        if change == 'unsupported':
            manifest['version'] = '0.2.0'
        else:
            manifest.pop('version', None)
        put_manifest(target, manifest)
    else:
        report = report_of(target)
        if change == 'unsupported':
            report['version'] = '0.2.0'
        else:
            report.pop('version', None)
        (target / 'preparation.json').write_text(json.dumps(report, ensure_ascii=False), encoding='utf-8')
        rehash(target, 'preparation.json')
    expect(exported, 'SNAPSHOT_VERSION_UNSUPPORTED')


# Row 8: forged id that was never recomputed from report content.
def test_report_id_not_recomputed(exported):
    target, _, _ = exported
    report = report_of(target)
    report['preparation_id'] = 'preparation_' + '0' * 24
    (target / 'preparation.json').write_text(json.dumps(report, ensure_ascii=False), encoding='utf-8')
    manifest = manifest_of(target)
    manifest['preparation_id'] = report['preparation_id']
    manifest['files']['preparation.json'] = file_sha256((target / 'preparation.json').read_bytes())
    put_manifest(target, manifest)
    expect(exported, 'SNAPSHOT_ID_MISMATCH')


# Row 9: partial/empty exports are recognised but unsupported.
@pytest.mark.parametrize('status', ['partial', 'empty'])
def test_non_complete_status_rejected(exported, status):
    report = report_of(exported[0])
    report['status'] = status
    reseal(exported[0], report)
    expect(exported, 'SNAPSHOT_STATUS_UNSUPPORTED')


# Row 10: any non-empty worksheet field on any material kind.
@pytest.mark.parametrize('field', ['reviewer', 'decision', 'reason'])
@pytest.mark.parametrize('kind', ['sources', 'candidates', 'anomalies'])
def test_non_empty_worksheet_rejected(exported, kind, field):
    report = report_of(exported[0])
    report[kind][0]['worksheet'][field] = {
        'reviewer': 'synthetic-reviewer-id', 'decision': 'accept', 'reason': 'synthetic reason'}[field]
    reseal(exported[0], report)
    expect(exported, 'SNAPSHOT_WORKSHEET_NOT_EMPTY')


# Row 11: selected package missing, or the whole packages directory missing.
def test_selected_package_missing(exported):
    _, packages, _ = exported
    for path in packages.glob('*.medpkg'):
        path.unlink()
    expect(exported, 'SNAPSHOT_SOURCE_UNAVAILABLE')


def test_packages_directory_missing(exported, tmp_path):
    target, _, workspace = exported
    expect((target, tmp_path / 'absent-packages', workspace), 'SNAPSHOT_SOURCE_UNAVAILABLE')


# Row 12: source bytes differ from the snapshot's binding.
def test_source_bytes_changed_after_export(exported):
    _, packages, _ = exported
    package = next(packages.glob('*.medpkg'))
    package.write_bytes(package.read_bytes() + b'x')
    expect(exported, 'SNAPSHOT_SOURCE_MISMATCH')


def test_coverage_archive_hash_tampered(exported):
    report = report_of(exported[0])
    addresses = addresses_of(report)
    assert addresses
    addresses[0]['archive_sha256'] = 'b' * 64
    reseal(exported[0], report)
    expect(exported, 'SNAPSHOT_SOURCE_MISMATCH')


# Row 13: self-consistent tampering outside archive identity still fails rebuild.
@pytest.mark.parametrize('field', ['candidate_item_id', 'evidence_text', 'anomaly_reason',
                                   'coverage_manifest_sha'])
def test_self_consistent_tampering_fails_rebuild(exported, field):
    report = report_of(exported[0])
    if field == 'candidate_item_id':
        report['candidates'][0]['item_id'] = 'reviewitem_' + '0' * 24
    elif field == 'evidence_text':
        report['sources'][0]['evidence']['raw_text'] = 'synthetic tampered text'
    elif field == 'anomaly_reason':
        item = next(a for a in report['anomalies'] if a.get('gap'))
        item['gap']['reason'] = 'synthetic tampered reason'
    else:
        addresses = addresses_of(report)
        assert addresses
        addresses[0]['manifest_sha256'] = 'c' * 64
    reseal(exported[0], report)
    expect(exported, 'SNAPSHOT_SOURCE_MISMATCH')


# Row 14: presentation markdown rewritten with a fresh manifest hash.
def test_presentation_markdown_tampered(exported):
    target, _, _ = exported
    path = target / 'quality-gates.md'
    path.write_text(path.read_text('utf-8') + '\nSynthetic extra line.\n', encoding='utf-8')
    rehash(target, 'quality-gates.md')
    expect(exported, 'SNAPSHOT_PRESENTATION_MISMATCH')


# Row 15: source package grows while the rebuild runs.
def test_source_append_during_rebuild_detected(exported, monkeypatch):
    _, packages, _ = exported
    package = next(packages.glob('*.medpkg'))
    original = ReviewPreparationService.prepare

    def patched(self, request=None):
        report = original(self, request)
        package.write_bytes(package.read_bytes() + b'append')
        return report

    monkeypatch.setattr(ReviewPreparationService, 'prepare', patched)
    expect(exported, 'SNAPSHOT_CHANGED')


# Row 16: snapshot markdown changes after the rebuild but before return.
def test_snapshot_change_after_rebuild_detected(exported, monkeypatch):
    target, _, _ = exported
    markdown = target / 'README.md'
    original = ReviewPreparationService.prepare

    def patched(self, request=None):
        report = original(self, request)
        markdown.write_bytes(markdown.read_bytes() + b'changed')
        return report

    monkeypatch.setattr(ReviewPreparationService, 'prepare', patched)
    expect(exported, 'SNAPSHOT_CHANGED')


# Row 17: size limits, per file and in total, without creating large files.
def test_single_file_limit(exported, monkeypatch):
    from medicine_agent.analysis import review_snapshot as module
    monkeypatch.setattr(module, 'MAX_FILE_BYTES', 1)
    expect(exported, 'SNAPSHOT_LIMIT_EXCEEDED')


def test_snapshot_total_limit(exported, monkeypatch):
    from medicine_agent.analysis import review_snapshot as module
    monkeypatch.setattr(module, 'MAX_SNAPSHOT_BYTES', 1)
    expect(exported, 'SNAPSHOT_LIMIT_EXCEEDED')


# Row 18: links/reparse points. A real link is used when the host allows it;
# the reparse branch is also covered by a controlled lstat stub, not claimed as a real link.
def test_real_symlink_rejected_or_skipped(exported, tmp_path):
    target, _, _ = exported
    original = (target / 'README.md').read_bytes()
    outside = tmp_path / 'outside-readme.md'
    outside.write_bytes(original)
    (target / 'README.md').unlink()
    try:
        os.symlink(outside, target / 'README.md')
    except (OSError, NotImplementedError) as exc:
        (target / 'README.md').write_bytes(original)
        pytest.skip('link creation unavailable in this environment: ' + type(exc).__name__)
    expect(exported, 'SNAPSHOT_PATH_INVALID')


def test_reparse_branch_via_lstat_stub(exported, monkeypatch):
    target, _, _ = exported
    victim = os.path.normcase(str((target / 'README.md').absolute()))
    real = pathlib.Path.lstat

    def fake(self):
        if os.path.normcase(str(self)) == victim:
            # A regular file with the Windows reparse attribute exercises the
            # second predicate, independently of the symlink mode predicate.
            return SimpleNamespace(st_mode=stat.S_IFREG | 0o644, st_file_attributes=0x400)
        return real(self)

    monkeypatch.setattr(pathlib.Path, 'lstat', fake)
    expect(exported, 'SNAPSHOT_PATH_INVALID')


# Row 19: copy of snapshot and same-byte package at a new location keeps identity.
def test_moved_snapshot_and_package_keep_identity(exported, tmp_path):
    target, packages, _ = exported
    before = snapshot(target), snapshot(packages)
    moved = tmp_path / 'moved'
    shutil.copytree(target, moved / 'snapshot')
    shutil.copytree(packages, moved / 'packages')
    result = load_preparation_snapshot(moved / 'snapshot', packages=moved / 'packages',
                                       workspace=moved / 'private-cache')
    assert result.report.status == 'complete'
    assert result.snapshot_id == load(exported).snapshot_id
    assert result.report.medical_review == 'unreviewed' and not result.report.release_allowed
    assert (snapshot(target), snapshot(packages)) == before
    assert snapshot(moved / 'snapshot') == before[0]


# Row 20: schema failure must not echo injected content into the message or traceback.
def test_schema_failure_does_not_leak_injected_content(exported):
    target, _, _ = exported
    marker = 'SENTINEL_SHOULD_NOT_LEAK_7f3a'
    report = report_of(target)
    report.pop('sources')
    report['release_allowed'] = marker
    reseal(target, report)
    error = expect(exported, 'SNAPSHOT_SCHEMA_INVALID')
    traced = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
    assert marker not in str(error)
    assert marker not in traced
