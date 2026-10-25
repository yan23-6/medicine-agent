import hashlib
from importlib import metadata
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from medicine_agent import ocr_resources as ocr
from medicine_agent.analysis import documents
from medicine_agent.analysis.models import AnalysisError


def synthetic(root):
    package=root/'backend'
    package.mkdir()
    models=package/'models'
    models.mkdir()
    files={}
    for name in ('config.yaml','default_models.yaml'):
        content=(name+': synthetic').encode()
        (package/name).write_bytes(content)
        files[name]=hashlib.sha256(content).hexdigest()
    rows=[]
    for role in ('det','cls','rec'):
        content=('synthetic model '+role).encode()
        filename=role+'.onnx'
        (models/filename).write_bytes(content)
        rows.append(dict(role=role,filename=filename,bytes=len(content),sha256=hashlib.sha256(content).hexdigest()))
    description=dict(contract='ocr-resource-description',version='0.1.0',backend='rapidocr',backend_version='test',files=files,models=rows)
    return package,models,description


def hashes(root):
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}


def test_verified_files_read_only_not_inference_or_license(tmp_path):
    package,models,description=synthetic(tmp_path)
    before=hashes(tmp_path)
    report,paths=ocr._verify(package,models,'test',description)
    assert report['status']=='passed' and set(paths)=={'det','cls','rec'}
    assert report['native_runtime']==report['inference']==report['license']=='not_evaluated'
    assert str(tmp_path) not in json.dumps(report)
    assert before==hashes(tmp_path)


@pytest.mark.parametrize('kind,code',[
    ('missing','OCR_RESOURCE_MISSING'), ('changed','OCR_RESOURCE_HASH_INVALID'),
    ('size','OCR_RESOURCE_SIZE_INVALID'), ('config','OCR_DEFAULT_CONFIG_CHANGED'),
    ('version','OCR_RESOURCE_DESCRIPTION_INVALID'), ('traversal','OCR_RESOURCE_DESCRIPTION_INVALID'),
    ('duplicate','OCR_RESOURCE_DESCRIPTION_INVALID'), ('sha','OCR_RESOURCE_DESCRIPTION_INVALID'),
    ('bool_size','OCR_RESOURCE_DESCRIPTION_INVALID'), ('roles','OCR_RESOURCE_DESCRIPTION_INVALID'),
])
def test_bad_local_resources_fail_closed(tmp_path,kind,code):
    package,models,description=synthetic(tmp_path)
    if kind=='missing': (models/'det.onnx').unlink()
    if kind=='changed': (models/'det.onnx').write_bytes(b'x'*(models/'det.onnx').stat().st_size)
    if kind=='size': (models/'det.onnx').write_bytes(b'x')
    if kind=='config': (package/'config.yaml').write_text('changed')
    if kind=='version': description['backend_version']='other'
    if kind=='traversal': description['models'][0]['filename']='../det.onnx'
    if kind=='duplicate': description['models'][1]['filename']='det.onnx'
    if kind=='sha': description['models'][0]['sha256']='x'
    if kind=='bool_size': description['models'][0]['bytes']=True
    if kind=='roles': description['models'][1]['role']='det'
    report,paths=ocr._verify(package,models,'test',description)
    assert report['status']=='blocked' and paths=={}
    assert code in report['diagnostic_codes']


def test_model_total_limit(tmp_path,monkeypatch):
    package,models,description=synthetic(tmp_path)
    monkeypatch.setattr(ocr,'MAX_TOTAL_BYTES',1)
    report,paths=ocr._verify(package,models,'test',description)
    assert report['diagnostic_codes']==['OCR_RESOURCE_SIZE_INVALID'] and not paths


def test_reparse_link_guard():
    class Path:
        def lstat(self): return SimpleNamespace(st_file_attributes=0x400,st_mode=0o100644)
    with pytest.raises(ocr.ResourceInvalid,match='OCR_RESOURCE_LINK_REJECTED'):
        ocr._regular(Path())


@pytest.mark.parametrize('kind', ['missing','unknown'])
def test_backend_missing_or_unrecognised(monkeypatch,kind):
    def read(name):
        if kind=='missing': raise metadata.PackageNotFoundError(name)
        return SimpleNamespace(version='999.0')
    monkeypatch.setattr(ocr.metadata,'distribution',read)
    result=ocr.inspect_ocr_resources()
    assert result['status']==('blocked' if kind=='missing' else 'not_evaluated')


def test_missing_resource_blocks_before_import_or_engine_construction(monkeypatch):
    called=[]
    def fail(): raise ocr.ResourceInvalid('not ready')
    monkeypatch.setattr(ocr,'validated_model_paths',fail)
    monkeypatch.setitem(sys.modules,'rapidocr',SimpleNamespace(RapidOCR=lambda **kwargs:called.append(kwargs)))
    with pytest.raises(AnalysisError) as exc:
        documents._ocr(None)
    assert exc.value.code=='OCR_RESOURCES_UNAVAILABLE' and not called


def test_runtime_passes_all_verified_paths_explicitly(monkeypatch):
    import numpy as np
    paths={role:Path(role+'.onnx') for role in ('det','cls','rec')}
    monkeypatch.setattr(ocr,'validated_model_paths',lambda:paths)
    called=[]
    class Engine:
        def __init__(self,params): called.append(params)
        def __call__(self,image): return SimpleNamespace(boxes=[],txts=None,scores=[])
    monkeypatch.setitem(sys.modules,'rapidocr',SimpleNamespace(RapidOCR=Engine))
    from PIL import Image
    assert documents._ocr(Image.new('RGB',(10,10))) == ([],['NO_TEXT_DETECTED'])
    assert called==[{'Global.log_level':'error','Det.model_path':'det.onnx','Cls.model_path':'cls.onnx','Rec.model_path':'rec.onnx'}]


def test_capabilities_do_not_confuse_metadata_and_resources(monkeypatch):
    monkeypatch.setattr(documents,'adapter_versions',lambda:{'rapidocr':'test'})
    monkeypatch.setattr(ocr,'inspect_ocr_resources',lambda:{'status':'blocked'})
    result=documents.capabilities()
    assert result['available'] is False
    assert {'txt','md'}.issubset(result['formats'])
    assert result['native_text_inputs']==['txt','md']
    assert result['native_runtime']=='not_evaluated'


def test_current_resources_and_cli_explicit_empty_root(tmp_path):
    report=ocr.inspect_ocr_resources()
    assert report['status']=='passed' and len(report['models'])==3
    result=subprocess.run([sys.executable,'-m','medicine_agent.ocr_resources','--model-root',str(tmp_path)],capture_output=True,text=True)
    assert result.returncode==1
    value=json.loads(result.stdout)
    assert value['diagnostic_codes']==['OCR_RESOURCE_MISSING']
    assert not list(tmp_path.iterdir())


def test_real_local_ocr_on_self_authored_fixture_never_calls_downloader(monkeypatch):
    from rapidocr.utils.download_file import DownloadFile
    def forbidden(*args,**kwargs): raise AssertionError('implicit download branch must never run')
    monkeypatch.setattr(DownloadFile,'run',forbidden)
    fixture=Path(__file__).parent/'fixtures/t02p/scan.png'
    # Run the same worker core in this process so the download guard actually
    # covers backend execution; extract_unit launches a separate subprocess.
    unit=documents._extract(fixture,1,False)
    assert unit.method=='ocr'
    assert '保留原文和来源' in ''.join(b.text for b in unit.blocks)
