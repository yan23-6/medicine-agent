import base64
import csv
import hashlib
import io
import json
import platform
import subprocess
import sys
import zipfile

import pytest

from medicine_agent import wheelhouse as wh


def snapshot(pins=None):
    pins = pins or {'medicine-agent':'1.0', 'dependency':'2.0'}
    return dict(contract='environment-preflight', version='0.1.0', status='passed',
                python=platform.python_version(), os=platform.system(), architecture=platform.machine(),
                project={'version':pins['medicine-agent']},
                distributions=[dict(name=n,version=v,python_status='passed') for n,v in sorted(pins.items())],
                version_snapshot=[f'{n}=={v}' for n,v in sorted(pins.items())])


def wheel(root, name, version, requires=(), tag='py3-none-any', extra=None, corrupt_record=False,
          md_name=None, wheel_tag=None, python='>=3.13,<3.14', duplicate=False):
    normalized = name.replace('-', '_')
    path = root / f'{normalized}-{version}-{tag}.whl'
    prefix = f'{normalized}-{version}.dist-info/'
    md = f'Metadata-Version: 2.3\nName: {md_name or name}\nVersion: {version}\nRequires-Python: {python}\n'
    md += ''.join(f'Requires-Dist: {r}\n' for r in requires)
    files = {prefix+'METADATA':md.encode(), prefix+'WHEEL':f'Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: {wheel_tag or tag}\n'.encode(), normalized+'/__init__.py':b'raise RuntimeError("must never execute")\n'}
    files.update(extra or {})
    output = io.StringIO(newline='')
    writer = csv.writer(output)
    for key,data in files.items():
        digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b'=').decode()
        writer.writerow([key, 'sha256='+('wrong' if corrupt_record else digest), len(data)])
    writer.writerow([prefix+'RECORD','',''])
    files[prefix+'RECORD'] = output.getvalue().encode()
    with zipfile.ZipFile(path,'w') as z:
        for key, data in files.items():
            # On Windows ZipInfo's constructor normalizes backslashes. Retain
            # the actual malicious member spelling to exercise the ZIP guard.
            info = zipfile.ZipInfo(key)
            info.filename = info.orig_filename = key
            z.writestr(info,data)
        if duplicate:
            with pytest.warns(UserWarning):
                z.writestr(prefix+'METADATA',md)
    return path


def complete(root):
    wheel(root,'medicine-agent','1.0',['dependency>=2,<3'])
    wheel(root,'dependency','2.0')


def test_complete_read_only_has_verified_hashes_not_installation(tmp_path):
    complete(tmp_path)
    before = {p.name:p.read_bytes() for p in tmp_path.iterdir()}
    result = wh.inspect_wheelhouse(tmp_path,snapshot())
    assert result['status'] == 'passed'
    assert result['metadata_resolution'] == 'passed'
    assert result['installation'] == result['native_runtime'] == result['model_resources'] == 'not_evaluated'
    assert result['supply_chain_trust'] == 'not_evaluated'
    for row in result['wheels']:
        assert row['sha256'] == hashlib.sha256(before[row['filename']]).hexdigest()
    assert before == {p.name:p.read_bytes() for p in tmp_path.iterdir()}


@pytest.mark.parametrize('kind', ['empty','missing','wrong_version','wrong_platform'])
def test_missing_materials(tmp_path,kind):
    if kind != 'empty':
        wheel(tmp_path,'medicine-agent','1.0',['dependency>=2'])
    if kind == 'wrong_version':
        wheel(tmp_path,'dependency','1.0')
    if kind == 'wrong_platform':
        wheel(tmp_path,'dependency','2.0',tag='cp39-cp39-win32')
    result = wh.inspect_wheelhouse(tmp_path,snapshot())
    assert result['status'] == 'blocked'
    assert 'dependency' in result['missing']
    assert result['diagnostic_codes'] == ['WHEEL_MISSING_OR_INCOMPATIBLE']


@pytest.mark.parametrize('kwargs,code', [
    ({'extra':{'../outside.py':b'bad'}}, 'WHEEL_CONTENT_INVALID'),
    ({'extra':{'C:/outside.py':b'bad'}}, 'WHEEL_CONTENT_INVALID'),
    ({'extra':{'a\\outside.py':b'bad'}}, 'WHEEL_CONTENT_INVALID'),
    ({'duplicate':True}, 'WHEEL_CONTENT_INVALID'),
    ({'corrupt_record':True}, 'WHEEL_RECORD_INVALID'),
    ({'md_name':'other'}, 'WHEEL_METADATA_INVALID'),
    ({'wheel_tag':'cp39-cp39-win32'}, 'WHEEL_TAG_MISMATCH'),
])
def test_invalid_wheel(tmp_path,kwargs,code):
    wheel(tmp_path,'medicine-agent','1.0',**kwargs)
    result = wh.inspect_wheelhouse(tmp_path,snapshot({'medicine-agent':'1.0'}))
    assert result['status'] == 'blocked'
    assert result['diagnostic_codes'] == [code]


@pytest.mark.parametrize('requires,python,pins', [
    (['dependency>=3'],'>=3.13',{'medicine-agent':'1.0','dependency':'2.0'}),
    (['unknown>=1'],'>=3.13',{'medicine-agent':'1.0','dependency':'2.0'}),
    ([], '>=4', {'medicine-agent':'1.0'}),
    ([], '>=3.13', {'medicine-agent':'1.0','dependency':'2.0'}),
])
def test_frozen_closure_must_be_exact(tmp_path,requires,python,pins):
    wheel(tmp_path,'medicine-agent','1.0',requires,python=python)
    if 'dependency' in pins:
        wheel(tmp_path,'dependency','2.0')
    result = wh.inspect_wheelhouse(tmp_path,snapshot(pins))
    assert result['status'] == 'blocked'
    assert result['diagnostic_codes'] == ['FROZEN_DEPENDENCY_CLOSURE_INVALID']


def test_extra_marker_closure(tmp_path):
    wheel(tmp_path,'medicine-agent','1.0',['dependency[chosen]>=2'])
    wheel(tmp_path,'dependency','2.0',['leaf; extra == "chosen"'])
    wheel(tmp_path,'leaf','1.0')
    result = wh.inspect_wheelhouse(tmp_path,snapshot({'medicine-agent':'1.0','dependency':'2.0','leaf':'1.0'}))
    assert result['status'] == 'passed'


def test_corrupt_zip_returns_diagnostic(tmp_path):
    (tmp_path/'medicine_agent-1.0-py3-none-any.whl').write_bytes(b'not a zip')
    result = wh.inspect_wheelhouse(tmp_path,snapshot({'medicine-agent':'1.0'}))
    assert result['status'] == 'blocked'


def test_missing_record_rejected(tmp_path):
    path = wheel(tmp_path,'medicine-agent','1.0')
    with zipfile.ZipFile(path) as z:
        files = {n:z.read(n) for n in z.namelist() if not n.endswith('/RECORD')}
    with zipfile.ZipFile(path,'w') as z:
        for n,data in files.items(): z.writestr(n,data)
    result = wh.inspect_wheelhouse(tmp_path,snapshot({'medicine-agent':'1.0'}))
    assert result['diagnostic_codes'] == ['WHEEL_METADATA_INVALID']


@pytest.mark.parametrize('change', ['version','platform','duplicate','pins','unhealthy','type'])
def test_bad_snapshot(tmp_path,change):
    value = snapshot()
    if change == 'version': value['version']='9'
    if change == 'platform': value['os']='other'
    if change == 'duplicate': value['distributions'] *= 2
    if change == 'pins': value['version_snapshot'] = []
    if change == 'unhealthy': value['status']='blocked'
    if change == 'type': value['project'] = []
    result = wh.inspect_wheelhouse(tmp_path,value)
    assert result['status'] == 'blocked'


def test_ambiguity_rejected(tmp_path):
    complete(tmp_path)
    wheel(tmp_path,'dependency','2.0',tag='py313-none-any')
    result = wh.inspect_wheelhouse(tmp_path,snapshot())
    assert result['diagnostic_codes'] == ['WHEEL_SELECTION_AMBIGUOUS']


@pytest.mark.parametrize('limit', ['MAX_WHEELS','MAX_FILE','MAX_EXPANDED','MAX_MEMBERS','MAX_METADATA'])
def test_limits_fail_closed(tmp_path,monkeypatch,limit):
    complete(tmp_path)
    monkeypatch.setattr(wh,limit,1)
    result = wh.inspect_wheelhouse(tmp_path,snapshot())
    assert result['status'] == 'blocked'


def test_parser_missing(tmp_path,monkeypatch):
    monkeypatch.setattr(wh,'_parser',lambda:None)
    result = wh.inspect_wheelhouse(tmp_path,snapshot())
    assert result['status'] == 'not_evaluated'


def test_reparse_guard(tmp_path,monkeypatch):
    from types import SimpleNamespace
    class Path:
        def lstat(self): return SimpleNamespace(st_file_attributes=0x400, st_mode=0o100644)
    with pytest.raises(wh.InvalidMaterials,match='MATERIAL_LINK_REJECTED'):
        wh._regular(Path())


def test_cli_success_and_duplicate_key_rejection(tmp_path):
    root = tmp_path/'wheels'
    root.mkdir()
    complete(root)
    request = tmp_path/'snapshot.json'
    request.write_text(json.dumps(snapshot()),encoding='utf-8')
    command = [sys.executable,'-m','medicine_agent.wheelhouse','--wheel-dir',str(root),'--snapshot',str(request)]
    result = subprocess.run(command,capture_output=True,text=True)
    assert result.returncode == 0, result.stdout+result.stderr
    assert json.loads(result.stdout) == wh.inspect_wheelhouse(root,snapshot())
    request.write_text('{"contract":"first","contract":"second"}',encoding='utf-8')
    result = subprocess.run(command,capture_output=True,text=True)
    assert result.returncode == 1
    assert json.loads(result.stdout)['diagnostic_codes'] == ['SNAPSHOT_INVALID']
