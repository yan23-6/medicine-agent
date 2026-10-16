"""A fixed public directory of package files, with private rebuildable views."""
import json
import shutil
import zipfile
import zlib
import time
import contextlib
import tempfile
import os
from pathlib import Path

from medicine_agent.analysis.models import AnalysisError
from medicine_agent.analysis.store import atomic_json, digest, process_lock
from medicine_agent.runtime.files import replace_path
from medicine_agent.analysis.composition import compose
from medicine_agent.analysis.catalog import PackageCatalog
from medicine_agent.domain.ids import file_sha256
from medicine_agent.packages.archive import unpack_archive, pack_archive
from medicine_agent.packages.bundle import read_bundle


def default_knowledge_root():
    return Path.home()/'MedicineAgent'/'knowledge'


@contextlib.contextmanager
def cache_lock(path):
    deadline=time.monotonic()+60
    while True:
        lock=process_lock(path)
        try:lock.__enter__();break
        except AnalysisError as exc:
            if exc.code!='TASK_BUSY' or time.monotonic()>=deadline:raise
            time.sleep(.05)
    try:yield
    finally:lock.__exit__(None,None,None)


class PackageLibrary:
    def __init__(self, root, workspace):
        self.root=Path(root).resolve()
        self.workspace=Path(workspace).resolve()
        if self.workspace.is_relative_to(self.root):
            raise AnalysisError('WORKSPACE_LOCATION_INVALID','Keep analysis/cache workspace outside the public package folder')
        self.workspace.mkdir(parents=True,exist_ok=True)

    def prepare(self):
        self.root.mkdir(parents=True,exist_ok=True)
        from medicine_agent.semantics import load_semantic_registry
        from medicine_agent.semantics.guide import export_tcm_field_guide
        from medicine_agent.domain.learning import DerivedBundle
        from medicine_agent.domain.tcm_knowledge import TCMKnowledgeGraph
        from medicine_agent.domain.reviews import ReviewRecord
        from medicine_agent.domain.corrections import CorrectionBundle
        specification={'file_format':'medpkg-0.1.0',
            'semantics':load_semantic_registry().model_dump(mode='json'),
            'container_schema':DerivedBundle.model_json_schema(),
            'data_schemas':{m.__name__:m.model_json_schema() for m in (TCMKnowledgeGraph,ReviewRecord,CorrectionBundle)}}
        target=self.root/'package-spec.json'
        try:current=json.loads(target.read_text('utf-8'))
        except (OSError,ValueError):current=None
        if current!=specification:atomic_json(target,specification)
        fd,name=tempfile.mkstemp(prefix='.guide-',suffix='.tmp',dir=self.root);os.close(fd)
        temp=Path(name)
        try:
            export_tcm_field_guide(temp)
            guide=self.root/'数据包说明书.md'
            if not guide.exists() or guide.read_bytes()!=temp.read_bytes():replace_path(temp,guide)
        finally:temp.unlink(missing_ok=True)

    def load(self,file):
        with cache_lock(self.workspace/'.archive-cache.lock'):
            return self._load(file)

    def _load(self,file):
        file=Path(file)
        if not file.is_absolute():file=self.root/file
        if file.suffix.lower()!='.medpkg' or not file.is_file():
            raise AnalysisError('PACKAGE_FILE_INVALID','Select a complete .medpkg package file')
        sha=file_sha256(file.read_bytes())
        cache=self.workspace/'archives'/sha
        if cache.exists():
            try:
                bundle=read_bundle(cache)
                from medicine_agent.domain.learning import DerivedBundle
                with zipfile.ZipFile(file) as archive:
                    expected=DerivedBundle.model_validate_json(archive.read('bundle.json'))
                if bundle!=expected:raise ValueError('Cached content differs from package file')
                return cache,bundle
            except (OSError,ValueError,KeyError,TypeError):
                if cache.resolve().parent!=(self.workspace/'archives').resolve() or cache.is_symlink():
                    raise AnalysisError('PACKAGE_PATH_INVALID','Cache path was redirected')
                shutil.rmtree(cache)
        cache.parent.mkdir(parents=True,exist_ok=True)
        try:
            bundle=unpack_archive(file,cache)
            return cache,bundle
        except (OSError,ValueError,KeyError,TypeError,zipfile.BadZipFile,RuntimeError,EOFError,zlib.error) as exc:
            raise AnalysisError('PACKAGE_FILE_INVALID','Package archive failed structure, integrity or source validation') from exc

    def scan(self):
        self.prepare()
        result=[]
        for file in sorted(self.root.iterdir()):
            if file.suffix.lower()!='.medpkg' or file.name.startswith('.'):continue
            try:
                if not file.resolve().is_relative_to(self.root):raise ValueError('External package link')
                _,bundle=self.load(file)
                result.append({'file':file.name,'package_id':bundle.bundle_id,'state':'research_candidate',
                    'contributor_id':bundle.contributor_id,'components':len(bundle.components)})
            except (AnalysisError,OSError,ValueError) as exc:
                result.append({'file':file.name,'state':'quarantined','error':getattr(exc,'code','PACKAGE_FILE_INVALID')})
        return result

    def view(self):
        with cache_lock(self.workspace/'.view-cache.lock'):
            return self._view()

    def _view(self):
        report=self.scan()
        files=[self.root/i['file'] for i in report if i['state']!='quarantined']
        if not files:
            return PackageCatalog(self.workspace/'empty'),report
        inputs=[self.load(f)[0] for f in files]
        key=digest([(f.name,file_sha256(f.read_bytes())) for f in files])
        target=self.workspace/'views'/key
        if target.exists():
            try:read_bundle(target)
            except (OSError,ValueError,KeyError,TypeError):
                if target.resolve().parent!=(self.workspace/'views').resolve() or target.is_symlink():
                    raise AnalysisError('PACKAGE_PATH_INVALID','View cache path was redirected')
                shutil.rmtree(target)
        if not target.exists():
            compose(inputs,target,base_ids=[self.load(f)[1].bundle_id for f in files])
        bundle=read_bundle(target)
        pins={}
        for c in bundle.components:
            if c.active:
                revision=target/c.path/'revision.json'
                family=json.loads(revision.read_text('utf-8'))['family'] if revision.exists() else c.package_id
                pins[family]=c.path
        atomic_json(target/'.selected.json',pins)
        selection=self.workspace/'selection.json'
        if selection.exists():
            overrides=json.loads(selection.read_text('utf-8'))
            catalog=PackageCatalog(target)
            items=catalog.scan()
            for family,pid in overrides.items():
                choices=[p for p in items if p.get('family')==family and p.get('package_id')==pid and p['state']!='quarantined']
                if not choices:raise AnalysisError('PIN_UNAVAILABLE','Selected source version is no longer available')
                pins[family]=choices[0]['path']
            atomic_json(target/'.selected.json',pins)
        return PackageCatalog(target),report

    def select(self,relative):
        catalog,_=self.view();item=catalog.select(relative)
        path=self.workspace/'selection.json'
        pins=json.loads(path.read_text('utf-8')) if path.exists() else {}
        pins[item['family']]=item['package_id'];atomic_json(path,pins)
        return item

    def query(self,facade,**filters):
        catalog,report=self.view()
        result=catalog.query(facade,**filters)
        result['package_files']=report
        return result

    def publish(self,representation):
        self.prepare()
        bundle=read_bundle(Path(representation))
        target=self.root/(bundle.bundle_id+'.medpkg')
        pack_archive(Path(representation),target)
        return target
