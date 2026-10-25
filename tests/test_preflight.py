import importlib.metadata as metadata
import json
import subprocess
import sys

import pytest

from medicine_agent.preflight import _inspect, _parser, inspect_environment


class Dist:
    def __init__(self, version='1.0', requirements=None, python='>=3.13,<3.14', source=None):
        self.version = version
        self.requires = requirements or []
        self.metadata = {'Requires-Python': python}
        self.source = source

    def read_text(self, name):
        assert name == 'direct_url.json'
        return self.source


def inspect(dists, version='3.13.15', parsers=True):
    def read(name):
        if name not in dists:
            raise metadata.PackageNotFoundError(name)
        return dists[name]
    return _inspect(read, version, _parser() if parsers else None)


def test_dependency_closure_markers_extras_cycles():
    result = inspect({'medicine-agent': Dist(requirements=['a[feature]>=1', 'ignored; python_version < "3"']),
                      'a': Dist(requirements=['b; extra == "feature"']),
                      'b': Dist(requirements=['a>=1'])})
    assert result['status'] == 'passed'
    assert result['version_snapshot'] == ['a==1.0', 'b==1.0', 'medicine-agent==1.0']
    assert [r['status'] for r in result['requirements'] if r['name'] == 'ignored'] == ['not_applicable']
    assert result['offline_cache'] == result['runtime_imports'] == result['model_resources'] == 'not_evaluated'
    assert result['reproducible_lock'] is False


@pytest.mark.parametrize('dists,code', [
    ({}, 'DEPENDENCY_MISSING'),
    ({'medicine-agent': Dist(requirements=['missing>=1'])}, 'DEPENDENCY_MISSING'),
    ({'medicine-agent': Dist(requirements=['a>=2']), 'a': Dist()}, 'DEPENDENCY_INCOMPATIBLE'),
    ({'medicine-agent': Dist(python='>=4')}, 'PYTHON_INCOMPATIBLE'),
    ({'medicine-agent': Dist(requirements=['not a requirement !!!'])}, 'REQUIREMENT_INVALID'),
    ({'medicine-agent': Dist(version='nonsense')}, 'REQUIREMENT_INVALID'),
    ({'medicine-agent': Dist(python=['invalid'])}, 'REQUIREMENT_INVALID'),
    ({'medicine-agent': Dist(version='broken\n')}, 'METADATA_INVALID'),
])
def test_blocks_invalid(dists, code):
    result = inspect(dists)
    assert result['status'] == 'blocked'
    assert code in result['diagnostic_codes']


def test_parser_missing_does_not_guess():
    result = inspect({'medicine-agent': Dist(requirements=['a>=2'])}, parsers=False)
    assert result['status'] == 'not_evaluated'
    assert result['diagnostic_codes'] == ['REQUIREMENT_PARSER_UNAVAILABLE']


def test_late_extra_revisits_previously_inactive_requirement():
    result = inspect({'medicine-agent': Dist(requirements=['a', 'b']),
                      'a': Dist(requirements=['c; extra == "late"']),
                      'b': Dist(requirements=['a[late]']), 'c': Dist()})
    assert result['status'] == 'passed'
    assert any(r['name'] == 'c' and r['status'] == 'passed' for r in result['requirements'])


def test_marker_uses_reported_python():
    result = inspect({'medicine-agent': Dist(requirements=['missing; python_version < "3.12"'])}, version='3.11.1')
    assert result['status'] == 'blocked'
    assert 'DEPENDENCY_MISSING' in result['diagnostic_codes']


def test_metadata_limits_fail_closed():
    result = inspect({'medicine-agent': Dist(requirements=['a'] * 5001), 'a': Dist()})
    assert result['status'] == 'blocked'
    assert 'DEPENDENCY_LIMIT_EXCEEDED' in result['diagnostic_codes']


def test_late_extra_revisits_previously_inactive_requirement():
    result = inspect({'medicine-agent': Dist(requirements=['a', 'b']),
                      'a': Dist(requirements=['c; extra == "late"']),
                      'b': Dist(requirements=['a[late]']), 'c': Dist()})
    assert result['status'] == 'passed'
    assert any(r['name'] == 'c' and r['status'] == 'passed' for r in result['requirements'])


def test_marker_uses_reported_python():
    result = inspect({'medicine-agent': Dist(requirements=['missing; python_version < "3.12"'])}, version='3.11.1')
    assert result['status'] == 'blocked'
    assert 'DEPENDENCY_MISSING' in result['diagnostic_codes']


def test_metadata_limits_fail_closed():
    result = inspect({'medicine-agent': Dist(requirements=['a'] * 5001), 'a': Dist()})
    assert result['status'] == 'blocked'
    assert 'DEPENDENCY_LIMIT_EXCEEDED' in result['diagnostic_codes']


@pytest.mark.parametrize('source,kind', [
    (None, 'installed_metadata'),
    ('{"dir_info":{"editable":true},"url":"file:///private/secret"}', 'editable'),
    ('{"archive_info":{},"url":"https://user:password@private/a.whl"}', 'archive'),
    ('bad-json', 'unknown'),
])
def test_source_no_path_or_secret(source, kind):
    result = inspect({'medicine-agent': Dist(source=source)})
    assert result['project']['source'] == kind
    assert 'private' not in json.dumps(result)
    assert 'password' not in json.dumps(result)


def test_direct_requirement_never_echoes_url_or_claims_pin():
    result = inspect({'medicine-agent': Dist(requirements=['a @ https://token:secret@private/a.whl']), 'a': Dist()})
    assert result['status'] == 'not_evaluated'
    assert 'secret' not in json.dumps(result)


def test_current_metadata_is_read_only():
    result = inspect_environment()
    assert result['project']['version'] == metadata.version('medicine-agent')
    assert result['status'] == 'passed'
    assert len(result['version_snapshot']) >= 8


def test_starts_with_standard_library_only():
    # -S removes site-packages, including Pydantic and packaging. PYTHONPATH is
    # used only to expose this source module; no runtime dependency is imported.
    from pathlib import Path
    code = "import sys; sys.path.insert(0, 'src'); from medicine_agent.preflight import inspect_environment; import json; print(json.dumps(inspect_environment())); assert 'pydantic' not in sys.modules; assert 'httpx' not in sys.modules"
    result = subprocess.run([sys.executable, '-S', '-c', code], cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report['status'] == 'blocked'
    assert 'DEPENDENCY_MISSING' in report['diagnostic_codes']
