"""Contract checks for the explicit JSON Schema keyword subset used here.

This is not a general-purpose JSON Schema validator or a draft conformance test.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

import pytest

from medicine_agent.runtime_readiness_schemas import schemas, export_runtime_schemas
from medicine_agent.preflight import inspect_environment
from medicine_agent.wheelhouse import inspect_wheelhouse
from medicine_agent.ocr_resources import inspect_ocr_resources


def check(value,schema):
    supported={'$schema','$id','title','type','additionalProperties','properties','required','items',
               'enum','const','minimum','maximum','minLength','pattern','minItems','maxItems','uniqueItems','if','then'}
    assert set(schema)<=supported
    if 'const' in schema: assert type(value) is type(schema['const']) and value==schema['const']
    if 'enum' in schema: assert value in schema['enum']
    types=schema.get('type',[])
    if isinstance(types,str): types=[types]
    matches={'object':isinstance(value,dict),'array':isinstance(value,list),'string':isinstance(value,str),
             'integer':type(value) is int,'null':value is None,'boolean':type(value) is bool}
    if types: assert any(matches[t] for t in types)
    if isinstance(value,dict):
        assert set(schema.get('required',[]))<=set(value)
        if schema.get('additionalProperties') is False: assert set(value)<=set(schema['properties'])
        for key,child in schema.get('properties',{}).items():
            if key in value: check(value[key],child)
        if 'if' in schema:
            try: check(value,schema['if'])
            except AssertionError: pass
            else: check(value,schema['then'])
    if isinstance(value,list):
        assert schema.get('minItems',0)<=len(value)<=schema.get('maxItems',float('inf'))
        if schema.get('uniqueItems'): assert len(value)==len({json.dumps(v,sort_keys=True) for v in value})
        for child in value: check(child,schema['items'])
    if isinstance(value,str):
        assert len(value)>=schema.get('minLength',0)
        if 'pattern' in schema: assert re.search(schema['pattern'],value)
    if type(value) is int:
        assert schema.get('minimum',float('-inf'))<=value<=schema.get('maximum',float('inf'))


@pytest.fixture
def reports(tmp_path):
    return {'EnvironmentPreflightReport':inspect_environment(),
            'WheelhouseReadinessReport':inspect_wheelhouse(tmp_path,{}),
            'OCRResourceReport':inspect_ocr_resources(),
            'OCRResourceDescription':json.loads((Path(__file__).resolve().parents[1]/'src/medicine_agent/resources/ocr/rapidocr-3.10.0.json').read_text('utf-8'))}


def test_current_outputs_and_resource_description_match_contracts(reports,tmp_path):
    for name,report in reports.items(): check(report,schemas()[name])
    check(inspect_ocr_resources(tmp_path),schemas()['OCRResourceReport'])


@pytest.mark.parametrize('name', ['EnvironmentPreflightReport','WheelhouseReadinessReport','OCRResourceReport','OCRResourceDescription'])
@pytest.mark.parametrize('change', ['unknown','missing','version'])
def test_unknown_missing_or_wrong_version_rejected(reports,name,change):
    value=deepcopy(reports[name])
    if change=='unknown': value['unexpected']=True
    if change=='missing': del value['contract']
    if change=='version': value['version']='2'
    with pytest.raises(AssertionError): check(value,schemas()[name])


def test_resource_hash_is_required_for_passed_row_and_no_offline_overclaim(reports):
    report=deepcopy(reports['OCRResourceReport'])
    del report['models'][0]['sha256']
    with pytest.raises(AssertionError): check(report,schemas()['OCRResourceReport'])
    report=deepcopy(reports['EnvironmentPreflightReport'])
    report['offline_cache']='passed'
    with pytest.raises(AssertionError): check(report,schemas()['EnvironmentPreflightReport'])


def test_export_snapshot_hashes_and_both_cli_entries(tmp_path):
    from medicine_agent.contracts import export_schemas
    standalone=export_runtime_schemas(tmp_path/'stdlib')
    assert export_schemas(None,tmp_path/'dispatch',contract_set='runtime-readiness')==standalone
    checked=Path(__file__).resolve().parents[1]/'schemas/runtime-readiness'
    for name,sha in standalone['files'].items():
        assert hashlib.sha256((tmp_path/'stdlib'/name).read_bytes()).hexdigest()==sha
        assert (checked/name).read_bytes()==(tmp_path/'stdlib'/name).read_bytes()==(tmp_path/'dispatch'/name).read_bytes()
    assert (checked/'schema-index.json').read_bytes()==(tmp_path/'stdlib/schema-index.json').read_bytes()
    result=subprocess.run([sys.executable,'-m','medicine_agent.cli','export-schemas','--contract-set','runtime-readiness','--output-dir',str(tmp_path/'cli')],capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
    assert json.loads(result.stdout)['files']==standalone['files']
    # No optional dependencies are needed for the independent schema exporter.
    code="import sys; sys.path.insert(0,'src'); from medicine_agent.runtime_readiness_schemas import export_runtime_schemas; export_runtime_schemas(sys.argv[1]); assert 'pydantic' not in sys.modules"
    result=subprocess.run([sys.executable,'-S','-c',code,str(tmp_path/'no-site')],cwd=checked.parents[1],capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr


def test_schema_calls_are_independent():
    value=schemas()
    value['EnvironmentPreflightReport']['properties'].clear()
    assert schemas()['EnvironmentPreflightReport']['properties']
