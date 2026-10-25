"""Read complete preparation snapshots and rebind them to verified source packages.

Internal management API. No model calls, review writes, or medical confirmation.
"""
from dataclasses import dataclass
import json
import math
from pathlib import Path
import re
import stat

from pydantic import ValidationError

from medicine_agent.analysis.models import AnalysisError
from medicine_agent.analysis.review_preparation import ReviewPreparationService, render_preparation
from medicine_agent.domain.ids import file_sha256, stable_id
from medicine_agent.domain.review_preparation import (
    ReviewPreparationExport, ReviewPreparationReport, ReviewPreparationRequest,
)


BODY_FILES = frozenset({'preparation.json', 'README.md', 'source-annotations.md',
    'candidates.md', 'anomalies.md', 'quality-gates.md'})
SNAPSHOT_FILES = BODY_FILES | {'manifest.json'}
MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_SNAPSHOT_BYTES = 128 * 1024 * 1024


@dataclass(frozen=True)
class ValidatedPreparationSnapshot:
    """Validation result, not an authorization token; contained models are mutable."""
    snapshot_id: str
    manifest_sha256: str
    export: ReviewPreparationExport
    report: ReviewPreparationReport


def _fail(code):
    raise AnalysisError(code, 'Preparation snapshot validation failed: ' + code) from None


def _safe_path(value):
    # Inspect before resolving: resolve() alone would hide junctions and symlinks.
    path = Path(value).absolute()
    for item in (path, *path.parents):
        if not item.exists() and not item.is_symlink():
            continue
        info = item.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            _fail('SNAPSHOT_PATH_INVALID')
    return path.resolve()


def _signature(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _read_file(path, *, limit=None):
    _safe_path(path)
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode):
        _fail('SNAPSHOT_RESOURCES_INVALID')
    if limit is not None and before.st_size > limit:
        _fail('SNAPSHOT_LIMIT_EXCEEDED')
    with path.open('rb') as stream:
        data = stream.read() if limit is None else stream.read(limit + 1)
    if limit is not None and len(data) > limit:
        _fail('SNAPSHOT_LIMIT_EXCEEDED')
    _safe_path(path)
    if _signature(before) != _signature(path.lstat()) or len(data) != before.st_size:
        _fail('SNAPSHOT_CHANGED')
    return data


def _read_snapshot(root):
    _safe_path(root)
    if not root.is_dir():
        _fail('SNAPSHOT_PATH_INVALID')
    entries = list(root.iterdir())
    if {p.name for p in entries} != SNAPSHOT_FILES:
        _fail('SNAPSHOT_RESOURCES_INVALID')
    # Check every entry before opening any body or manifest.
    for entry in entries:
        _safe_path(entry)
        if not stat.S_ISREG(entry.lstat().st_mode):
            _fail('SNAPSHOT_RESOURCES_INVALID')
    if sum(p.stat().st_size for p in entries) > MAX_SNAPSHOT_BYTES:
        _fail('SNAPSHOT_LIMIT_EXCEEDED')
    result = {p.name: _read_file(p, limit=MAX_FILE_BYTES) for p in entries}
    if sum(map(len, result.values())) > MAX_SNAPSHOT_BYTES:
        _fail('SNAPSHOT_LIMIT_EXCEEDED')
    return result


def _json_object(data):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate key')
            result[key] = value
        return result

    def invalid_constant(value):
        raise ValueError('Non-finite JSON number')

    def finite_float(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError('Non-finite JSON number')
        return number

    try:
        value = json.loads(data.decode('utf-8'), object_pairs_hook=pairs,
            parse_constant=invalid_constant, parse_float=finite_float)
        if not isinstance(value, dict):
            raise ValueError('Object required')
        return value
    except (ValueError, UnicodeError, RecursionError):
        _fail('SNAPSHOT_JSON_INVALID')


def load_preparation_snapshot(snapshot_dir, *, packages, workspace):
    """Validate one complete blank snapshot against original, available packages.

    Only the disjoint private workspace may be written by package validation.
    Partial and empty exports are recognized but unsupported for session creation.
    """
    try:
        return _load(snapshot_dir, packages=packages, workspace=workspace)
    except AnalysisError:
        raise
    except (OSError, ValueError, TypeError, KeyError, AttributeError, RecursionError):
        # Do not leak source text or low-level exception details.
        _fail('SNAPSHOT_SCHEMA_INVALID')


def _load(snapshot_dir, *, packages, workspace):
    root, source, cache = map(_safe_path, (snapshot_dir, packages, workspace))
    paths = (root, source, cache)
    if any(a.is_relative_to(b) or b.is_relative_to(a)
            for i, a in enumerate(paths) for b in paths[i + 1:]):
        _fail('SNAPSHOT_PATH_INVALID')
    if cache.exists() and not cache.is_dir():
        _fail('SNAPSHOT_PATH_INVALID')
    if not source.is_dir():
        _fail('SNAPSHOT_SOURCE_UNAVAILABLE')
    original = _read_snapshot(root)
    manifest, raw_report = (_json_object(original[name])
        for name in ('manifest.json', 'preparation.json'))
    if any(data.get('version') != '0.1.0' for data in (manifest, raw_report)):
        _fail('SNAPSHOT_VERSION_UNSUPPORTED')
    files = manifest.get('files')
    if not isinstance(files, dict) or set(files) != BODY_FILES:
        _fail('SNAPSHOT_RESOURCES_INVALID')
    if any(not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value)
            for value in files.values()):
        _fail('SNAPSHOT_SCHEMA_INVALID')
    if any(file_sha256(original[name]) != expected for name, expected in files.items()):
        _fail('SNAPSHOT_HASH_MISMATCH')
    try:
        export = ReviewPreparationExport.model_validate(manifest)
        report = ReviewPreparationReport.model_validate(raw_report)
    except ValidationError:
        _fail('SNAPSHOT_SCHEMA_INVALID')
    if report.preparation_id != export.preparation_id or report.preparation_id != stable_id(
            'preparation', report.model_dump(mode='json', exclude={'preparation_id'})):
        _fail('SNAPSHOT_ID_MISMATCH')
    if report.status != export.status:
        _fail('SNAPSHOT_SCHEMA_INVALID')
    if report.status != 'complete':
        _fail('SNAPSHOT_STATUS_UNSUPPORTED')
    for item in (*report.sources, *report.candidates, *report.anomalies):
        if item.worksheet.model_dump() != dict(reviewer=None, decision=None, reason=None, submitted=False):
            _fail('SNAPSHOT_WORKSHEET_NOT_EMPTY')

    addresses = [r.address for r in report.coverage.records if r.address is not None]
    names = sorted({a.archive for a in addresses})
    if not names:
        _fail('SNAPSHOT_SOURCE_UNAVAILABLE')
    try:
        request = ReviewPreparationRequest(archives=names)
    except ValidationError:
        _fail('SNAPSHOT_PATH_INVALID')
    package_hashes = {}
    for name in names:
        path = source / name
        _safe_path(path)
        if not path.is_file():
            _fail('SNAPSHOT_SOURCE_UNAVAILABLE')
        package_hashes[name] = file_sha256(_read_file(path))
    if any(package_hashes[a.archive] != a.archive_sha256 for a in addresses):
        _fail('SNAPSHOT_SOURCE_MISMATCH')
    try:
        rebuilt = ReviewPreparationService(source, cache).prepare(request)
    except (AnalysisError, OSError, ValueError, TypeError, KeyError, AttributeError):
        _fail('SNAPSHOT_SOURCE_MISMATCH')
    if rebuilt.model_dump(mode='json') != report.model_dump(mode='json'):
        _fail('SNAPSHOT_SOURCE_MISMATCH')
    for name, content in render_preparation(report).items():
        if original[name] != content.encode('utf-8'):
            _fail('SNAPSHOT_PRESENTATION_MISMATCH')
    if any(file_sha256(_read_file(source / name)) != expected
            for name, expected in package_hashes.items()):
        _fail('SNAPSHOT_CHANGED')
    if _read_snapshot(root) != original:
        _fail('SNAPSHOT_CHANGED')
    manifest_sha256 = file_sha256(original['manifest.json'])
    return ValidatedPreparationSnapshot(
        snapshot_id=stable_id('snapshot', {'manifest_sha256': manifest_sha256,
            'preparation_id': report.preparation_id}),
        manifest_sha256=manifest_sha256, export=export, report=report)
