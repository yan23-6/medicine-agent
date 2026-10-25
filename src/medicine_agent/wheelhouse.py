"""Bounded, read-only validation of an explicit frozen offline wheel set."""
from __future__ import annotations

import argparse
import base64
import csv
from email.parser import BytesParser
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import stat
import zipfile
import zlib

from medicine_agent.preflight import _inspect, _name, _parser

MAX_WHEELS = 500
MAX_FILE = 512 * 1024 * 1024
MAX_EXPANDED = 2 * 1024 * 1024 * 1024
MAX_MEMBERS = 20000
MAX_METADATA = 4 * 1024 * 1024


class InvalidMaterials(ValueError):
    """Fixed diagnostic code only, never exception text from input files."""


def _regular(path, directory=False):
    info = path.lstat()
    if getattr(info, 'st_file_attributes', 0) & 0x400:
        raise InvalidMaterials('MATERIAL_LINK_REJECTED')
    if not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)):
        raise InvalidMaterials('MATERIAL_LINK_REJECTED')
    return info


def _unique_json(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise InvalidMaterials('SNAPSHOT_INVALID')
        value[key] = item
    return value


def _snapshot(value):
    from packaging.version import Version
    if not isinstance(value, dict) or value.get('contract') != 'environment-preflight' or value.get('version') != '0.1.0' or value.get('status') != 'passed':
        raise InvalidMaterials('SNAPSHOT_INVALID')
    if any(value.get(k) != actual for k, actual in [('python', platform.python_version()), ('os', platform.system()), ('architecture', platform.machine())]):
        raise InvalidMaterials('SNAPSHOT_PLATFORM_MISMATCH')
    rows = value.get('distributions')
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_WHEELS:
        raise InvalidMaterials('SNAPSHOT_INVALID')
    pins = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != {'name', 'version', 'python_status'}:
            raise InvalidMaterials('SNAPSHOT_INVALID')
        name, version = row['name'], row['version']
        if not isinstance(name, str) or not name or _name(name) != name or name in pins or row['python_status'] != 'passed':
            raise InvalidMaterials('SNAPSHOT_INVALID')
        if not isinstance(version, str):
            raise InvalidMaterials('SNAPSHOT_INVALID')
        Version(version)
        pins[name] = version
    if 'medicine-agent' not in pins or value.get('project', {}).get('version') != pins['medicine-agent']:
        raise InvalidMaterials('SNAPSHOT_INVALID')
    if value.get('version_snapshot') != [f'{n}=={v}' for n,v in sorted(pins.items())]:
        raise InvalidMaterials('SNAPSHOT_INVALID')
    return pins


class WheelDistribution:
    def __init__(self, metadata):
        self.metadata = metadata
        self.version = metadata['Version']
        self.requires = metadata.get_all('Requires-Dist') or []

    def read_text(self, name):
        return None


def _wheel(path, remaining=MAX_EXPANDED):
    from packaging.tags import parse_tag
    from packaging.utils import parse_wheel_filename
    from packaging.version import Version

    before = _regular(path)
    if before.st_size > MAX_FILE:
        raise InvalidMaterials('MATERIAL_LIMIT_EXCEEDED')
    name, version, _, filename_tags = parse_wheel_filename(path.name)
    with path.open('rb') as stream:
        opened = os.fstat(stream.fileno())
        if not stat.S_ISREG(opened.st_mode) or (opened.st_size, opened.st_mtime_ns, opened.st_ino) != (before.st_size, before.st_mtime_ns, before.st_ino):
            raise InvalidMaterials('MATERIAL_CHANGED')
        hasher, read_bytes = hashlib.sha256(), 0
        while chunk := stream.read(min(1024 * 1024, MAX_FILE - read_bytes + 1)):
            read_bytes += len(chunk)
            if read_bytes > MAX_FILE:
                raise InvalidMaterials('MATERIAL_LIMIT_EXCEEDED')
            hasher.update(chunk)
        if read_bytes != opened.st_size:
            raise InvalidMaterials('MATERIAL_CHANGED')
        digest = hasher.hexdigest()
        stream.seek(0)
        with zipfile.ZipFile(stream) as archive:
            members = archive.infolist()
            expanded = sum(m.file_size for m in members)
            if len(members) > MAX_MEMBERS or expanded > remaining:
                raise InvalidMaterials('MATERIAL_LIMIT_EXCEEDED')
            names = [m.filename for m in members]
            if len(names) != len(set(names)):
                raise InvalidMaterials('WHEEL_CONTENT_INVALID')
            for m in members:
                p = PurePosixPath(m.filename)
                if not m.filename or m.orig_filename != m.filename or p.is_absolute() or '..' in p.parts or '\\' in m.filename or ':' in m.filename or p.as_posix() != m.filename.rstrip('/') or stat.S_ISLNK(m.external_attr >> 16):
                    raise InvalidMaterials('WHEEL_CONTENT_INVALID')
            metadata_names = [n for n in names if n.endswith('.dist-info/METADATA')]
            if len(metadata_names) != 1:
                raise InvalidMaterials('WHEEL_METADATA_INVALID')
            metaname = metadata_names[0]
            prefix = metaname[:-len('METADATA')]
            for member in (metaname, prefix+'WHEEL', prefix+'RECORD'):
                if member not in names or archive.getinfo(member).file_size > MAX_METADATA:
                    raise InvalidMaterials('WHEEL_METADATA_INVALID')
            md = BytesParser().parsebytes(archive.read(metaname))
            wm = BytesParser().parsebytes(archive.read(prefix+'WHEEL'))
            if any(len(md.get_all(k, [])) != 1 for k in ('Name', 'Version')) or len(wm.get_all('Wheel-Version', [])) != 1 or len(md.get_all('Requires-Python', [])) > 1:
                raise InvalidMaterials('WHEEL_METADATA_INVALID')
            if _name(md['Name']) != str(name) or Version(md['Version']) != version or wm['Wheel-Version'] != '1.0':
                raise InvalidMaterials('WHEEL_METADATA_INVALID')
            expected = f'{str(name).replace("-", "_")}-{version}.dist-info/'
            if prefix != expected:
                raise InvalidMaterials('WHEEL_METADATA_INVALID')
            wheel_tags = set()
            for tag in wm.get_all('Tag', []):
                wheel_tags.update(parse_tag(tag))
            if wheel_tags != set(filename_tags):
                raise InvalidMaterials('WHEEL_TAG_MISMATCH')
            records = {}
            for row in csv.reader(io.StringIO(archive.read(prefix+'RECORD').decode('utf-8'))):
                if len(row) != 3 or row[0] in records:
                    raise InvalidMaterials('WHEEL_RECORD_INVALID')
                records[row[0]] = row[1:]
            files = {m.filename for m in members if not m.is_dir()}
            if set(records) != files:
                raise InvalidMaterials('WHEEL_RECORD_INVALID')
            for member in sorted(files):
                hashed, size = records[member]
                if member == prefix+'RECORD':
                    if hashed or size:
                        raise InvalidMaterials('WHEEL_RECORD_INVALID')
                    continue
                with archive.open(member) as content:
                    actual = base64.urlsafe_b64encode(hashlib.file_digest(content,'sha256').digest()).rstrip(b'=').decode('ascii')
                if hashed != 'sha256='+actual or size != str(archive.getinfo(member).file_size):
                    raise InvalidMaterials('WHEEL_RECORD_INVALID')
        after = os.fstat(stream.fileno())
        if (opened.st_size, opened.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise InvalidMaterials('MATERIAL_CHANGED')
    return str(name), str(version), filename_tags, WheelDistribution(md), expanded, dict(
        filename=path.name, bytes=before.st_size, sha256=digest)


def _empty_report():
    return dict(contract='wheelhouse-readiness', version='0.1.0', status='blocked',
                  metadata_resolution='not_evaluated', wheels=[], missing=[], diagnostic_codes=[],
                  installation='not_evaluated', native_runtime='not_evaluated',
                  model_resources='not_evaluated', supply_chain_trust='not_evaluated')


def inspect_wheelhouse(directory, snapshot):
    """Validate frozen materials for this interpreter; never install or execute."""
    result = _empty_report()
    try:
        if not _parser():
            result.update(status='not_evaluated', diagnostic_codes=['REQUIREMENT_PARSER_UNAVAILABLE'])
            return result
        from packaging.tags import sys_tags
        from packaging.version import Version
        pins = _snapshot(snapshot)
        directory = Path(directory)
        _regular(directory, directory=True)
        paths = []
        # Stop during enumeration rather than first allocating an arbitrary list.
        for path in directory.iterdir():
            if path.suffix.lower() == '.whl':
                paths.append(path)
                if len(paths) > MAX_WHEELS:
                    raise InvalidMaterials('MATERIAL_LIMIT_EXCEEDED')
        available = {}
        compatible = set(sys_tags())
        remaining = MAX_EXPANDED
        total_bytes = 0
        for path in sorted(paths):
            total_bytes += path.lstat().st_size
            if total_bytes > MAX_EXPANDED:
                raise InvalidMaterials('MATERIAL_LIMIT_EXCEEDED')
            name, version, tags, dist, expanded, record = _wheel(path, remaining)
            remaining -= expanded
            if name in pins and Version(version) == Version(pins[name]) and tags & compatible:
                if name in available:
                    raise InvalidMaterials('WHEEL_SELECTION_AMBIGUOUS')
                available[name] = (dist, record)
        result['missing'] = sorted(set(pins) - set(available))
        result['wheels'] = [dict(name=n, version=available[n][0].version, **available[n][1]) for n in sorted(available)]
        if result['missing']:
            result['diagnostic_codes'] = ['WHEEL_MISSING_OR_INCOMPATIBLE']
            return result
        def lookup(name):
            if name not in available:
                raise importlib.metadata.PackageNotFoundError(name)
            return available[name][0]
        closure = _inspect(lookup, platform.python_version(), _parser())
        if closure['status'] != 'passed' or {r['name'] for r in closure['distributions']} != set(pins):
            result['diagnostic_codes'] = ['FROZEN_DEPENDENCY_CLOSURE_INVALID']
            return result
        result.update(status='passed', metadata_resolution='passed')
    except InvalidMaterials as exc:
        result['diagnostic_codes'] = [str(exc)]
    except (OSError, ValueError, TypeError, KeyError, AttributeError, RuntimeError, EOFError):
        result['diagnostic_codes'] = ['MATERIALS_INVALID']
    except (zipfile.BadZipFile, zlib.error):
        result['diagnostic_codes'] = ['WHEEL_CONTENT_INVALID']
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wheel-dir', type=Path, required=True)
    parser.add_argument('--snapshot', type=Path, required=True)
    args = parser.parse_args()
    try:
        info = _regular(args.snapshot)
        if info.st_size > MAX_METADATA:
            raise InvalidMaterials('SNAPSHOT_INVALID')
        with args.snapshot.open('rb') as stream:
            content = stream.read(MAX_METADATA+1)
        if len(content) > MAX_METADATA:
            raise InvalidMaterials('SNAPSHOT_INVALID')
        snapshot = json.loads(content, object_pairs_hook=_unique_json)
        result = inspect_wheelhouse(args.wheel_dir, snapshot)
    except (OSError, ValueError, TypeError):
        result = _empty_report()
        result['diagnostic_codes'] = ['SNAPSHOT_INVALID']
    print(json.dumps(result, ensure_ascii=True, indent=2))
    raise SystemExit(0 if result['status'] == 'passed' else 1)


if __name__ == '__main__':
    main()
