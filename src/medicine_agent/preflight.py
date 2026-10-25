"""Read-only dependency metadata diagnostic; runnable without medical dependencies."""
from __future__ import annotations

import importlib.metadata as metadata
import json
import platform
import re
import sys
from collections import deque


def _name(value):
    return re.sub(r'[-_.]+', '-', value).lower()


def _parser():
    try:
        from packaging.requirements import Requirement
        from packaging.specifiers import SpecifierSet
        return Requirement, SpecifierSet
    except ImportError:
        return None


def _source(dist):
    try:
        raw = dist.read_text('direct_url.json')
        if not raw:
            return 'installed_metadata'
        value = json.loads(raw)
        if value.get('dir_info', {}).get('editable') is True:
            return 'editable'
        if 'dir_info' in value:
            return 'local_directory'
        if 'archive_info' in value:
            return 'archive'
        return 'other_direct_source'
    except (OSError, ValueError, TypeError, AttributeError):
        return 'unknown'


def _inspect(distribution, python_version, parsers):
    diagnostics = set()
    rows, resolved, extras, processed = {}, {}, {'medicine-agent': set()}, {}
    pending = deque(['medicine-agent'])
    requirement_count = 0
    project = {'name': 'medicine-agent', 'version': None, 'source': 'unknown'}
    while pending:
        name = pending.popleft()
        signature = tuple(sorted(extras[name]))
        if processed.get(name) == signature:
            continue
        processed[name] = signature
        if len(processed) > 500:
            diagnostics.add('DEPENDENCY_LIMIT_EXCEEDED')
            break
        try:
            dist = distribution(name)
            version = dist.version
            if not isinstance(version, str) or not version or '\n' in version:
                raise ValueError()
            requires_python = dist.metadata.get('Requires-Python')
            requirements = dist.requires or []
            if not isinstance(requirements, list) or not all(isinstance(r, str) for r in requirements):
                raise ValueError()
        except metadata.PackageNotFoundError:
            diagnostics.add('DEPENDENCY_MISSING')
            resolved[name] = {'name': name, 'version': None, 'python_status': 'not_evaluated'}
            continue
        except (OSError, ValueError, TypeError, AttributeError):
            diagnostics.add('METADATA_INVALID')
            continue
        python_status = 'not_evaluated'
        if parsers:
            try:
                if requires_python is not None and not isinstance(requires_python, str):
                    raise ValueError()
                # Installed metadata is not necessarily a valid PEP440 version.
                if not parsers[1]('==' + version).contains(version, prereleases=True):
                    raise ValueError()
                python_status = 'passed' if not requires_python or parsers[1](requires_python).contains(python_version, prereleases=True) else 'incompatible'
            except (ValueError, TypeError):
                diagnostics.add('REQUIREMENT_INVALID')
        if python_status == 'incompatible':
            diagnostics.add('PYTHON_INCOMPATIBLE')
        resolved[name] = {'name': name, 'version': version, 'python_status': python_status}
        if name == 'medicine-agent':
            project.update(version=version, source=_source(dist))
        if not parsers:
            diagnostics.add('REQUIREMENT_PARSER_UNAVAILABLE')
            continue
        for raw in requirements:
            requirement_count += 1
            if requirement_count > 5000:
                diagnostics.add('DEPENDENCY_LIMIT_EXCEEDED')
                pending.clear()
                break
            try:
                req = parsers[0](raw)
                child = _name(req.name)
                # Evaluate an extra marker in each selected extra context, plus base.
                marker_environment = {'python_version': '.'.join(python_version.split('.')[:2]),
                                      'python_full_version': python_version}
                active = not req.marker or any(req.marker.evaluate(dict(marker_environment, extra=extra)) for extra in ('', *signature))
                status = 'pending' if active else 'not_applicable'
                if req.url:
                    # Do not print potentially credential-bearing direct URLs.
                    status = 'not_evaluated' if active else status
                    if active:
                        diagnostics.add('DIRECT_REQUIREMENT_NOT_EVALUATED')
                row = {'parent': name, 'name': child, 'requirement': child + str(req.specifier),
                       'extras': sorted(req.extras), 'status': status, 'installed_version': None}
                rows[(name, raw)] = row
                if active:
                    new = child not in extras
                    known = extras.setdefault(child, set())
                    before = set(known)
                    known.update(req.extras)
                    if new or before != known:
                        pending.append(child)
            except (ValueError, TypeError, KeyError):
                diagnostics.add('REQUIREMENT_INVALID')
    for (parent, raw), row in rows.items():
        if row['status'] != 'pending':
            continue
        installed = resolved.get(row['name'], {}).get('version')
        row['installed_version'] = installed
        if installed is None:
            row['status'] = 'missing'
            diagnostics.add('DEPENDENCY_MISSING')
        else:
            try:
                row['status'] = 'passed' if parsers[0](raw).specifier.contains(installed, prereleases=True) else 'incompatible'
                if row['status'] == 'incompatible':
                    diagnostics.add('DEPENDENCY_INCOMPATIBLE')
            except ValueError:
                row['status'] = 'not_evaluated'
                diagnostics.add('METADATA_INVALID')
    blockers = diagnostics - {'REQUIREMENT_PARSER_UNAVAILABLE', 'DIRECT_REQUIREMENT_NOT_EVALUATED'}
    status = 'blocked' if blockers else ('not_evaluated' if diagnostics else 'passed')
    return {
        'version': '0.1.0', 'contract': 'environment-preflight', 'status': status,
        'python': python_version, 'implementation': platform.python_implementation(),
        'os': platform.system(), 'architecture': platform.machine(), 'project': project,
        'distributions': sorted(resolved.values(), key=lambda r: r['name']),
        'requirements': [rows[k] for k in sorted(rows)], 'diagnostic_codes': sorted(diagnostics),
        'version_snapshot': [f"{r['name']}=={r['version']}" for r in sorted(resolved.values(), key=lambda r: r['name']) if r['version']],
        'offline_cache': 'not_evaluated', 'runtime_imports': 'not_evaluated',
        'model_resources': 'not_evaluated', 'reproducible_lock': False,
    }


def inspect_environment():
    """Inspect installed metadata only; no imports of runtime/OCR/model clients."""
    return _inspect(metadata.distribution, platform.python_version(), _parser())


def main():
    report = inspect_environment()
    print(json.dumps(report, ensure_ascii=True, indent=2))
    raise SystemExit(0 if report['status'] == 'passed' else 1)


if __name__ == '__main__':
    main()
