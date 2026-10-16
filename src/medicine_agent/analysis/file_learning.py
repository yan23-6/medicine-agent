"""Product file delivery over the existing analysis agent; no author permission gate."""
import json
import re
from pathlib import Path
from uuid import uuid4

from medicine_agent.analysis.library import PackageLibrary, default_knowledge_root
from medicine_agent.analysis.composition import compose
from medicine_agent.analysis.models import AnalysisError
from medicine_agent.analysis.service import DataAnalysisAgent
from medicine_agent.analysis.catalog import PackageCatalog
from medicine_agent.analysis.store import atomic_json, digest, process_lock
from medicine_agent.domain.learning import LearningRequest
from medicine_agent.domain.owned_analysis import OwnedAnalysisRequest
from medicine_agent.bootstrap import create_facade
from medicine_agent.packages.bundle import read_bundle


class FileLearningService:
    def __init__(self, workspace, package_root=None, model_client=None):
        self.workspace=Path(workspace).resolve()
        self.workspace.mkdir(parents=True,exist_ok=True)
        settings=self.workspace/'knowledge-settings.json'
        if package_root is not None:
            atomic_json(settings,{'package_root':str(Path(package_root).resolve())})
        root=json.loads(settings.read_text('utf-8'))['package_root'] if settings.exists() else default_knowledge_root()
        self.library=PackageLibrary(root,self.workspace/'library-cache')
        self.model_client=model_client

    def task_dir(self, task):
        if not re.fullmatch(r'learning_[a-f0-9]{32}',task):
            raise AnalysisError('TASK_ID_INVALID','Invalid learning task identity')
        path=self.workspace/'learning'/task
        if path.resolve()!=self.workspace/'learning'/task:
            raise AnalysisError('PACKAGE_PATH_INVALID','Learning workspace was redirected')
        return path

    def submit(self,payload):
        request=LearningRequest.model_validate(payload)
        task='learning_'+uuid4().hex
        directory=self.task_dir(task);directory.mkdir(parents=True)
        bases=list(request.base_packages)
        if request.parent_package:
            bases.append(request.parent_package)
        inputs=[];ids=[]
        for name in dict.fromkeys(bases):
            path=Path(name)
            if not path.is_absolute():path=self.library.root/path
            if path.suffix.lower()=='.medpkg':
                source,bundle=self.library.load(path);inputs.append(source);ids.append(bundle.bundle_id)
            elif path.is_dir():
                # Import legacy experiments once; all delivered outputs are files.
                inputs.append(path)
                ids.append(json.loads((path/'manifest.json').read_text('utf-8'))['package_id'])
            else:raise AnalysisError('BASE_PACKAGE_INVALID','A base must be an existing complete data package')
        if inputs:
            view,_=self.library.view()
            roots=[view.root] if (view.root/'bundle.json').exists() else []
            compose(inputs,directory/'basis',base_ids=ids,contributor_id=request.owner_id,sidecar_roots=roots)
        agent=DataAnalysisAgent(directory/'analysis',directory/'sources',self.model_client,branch_id=task)
        inner=OwnedAnalysisRequest.model_validate({**request.model_dump(mode='json',exclude={'base_packages'}),
            'parent_package':None,'owner_id':request.owner_id or 'anonymous-contributor'})
        submitted=agent.submit(inner)
        atomic_json(directory/'task.json',{'task_id':task,'inner_task_id':submitted['task_id'],
            'basis_id':read_bundle(directory/'basis').bundle_id if inputs else None,
            'contributor_id':request.owner_id,'status':'queued','package_path':None,'errors':[]})
        return self.status(task)

    def status(self,task):
        directory=self.task_dir(task)
        try:data=json.loads((directory/'task.json').read_text('utf-8'))
        except (OSError,ValueError) as exc:raise AnalysisError('TASK_NOT_FOUND','Learning task is missing or corrupt') from exc
        agent=DataAnalysisAgent(directory/'analysis',model_client=self.model_client)
        inner=agent.status(data['inner_task_id'])
        return {**data,'role':'orchestrator','children':inner['children']}

    def run(self,task,**limits):
        directory=self.task_dir(task)
        with process_lock(directory/'delivery.lock'):
            data=json.loads((directory/'task.json').read_text('utf-8'))
            if data['status']=='completed':
                target=self.library.root/data['package_path']
                if not target.exists():self.library.publish(directory/'delivery')
                self.library.load(target)
                return self.status(task)
            data.update(status='running',errors=[]);atomic_json(directory/'task.json',data)
            agent=DataAnalysisAgent(directory/'analysis',model_client=self.model_client)
            try:
                if data.get('basis_id') and read_bundle(directory/'basis').bundle_id!=data['basis_id']:
                    raise AnalysisError('BASE_SNAPSHOT_CHANGED','Verified base snapshot changed before learning')
                result=agent.run(data['inner_task_id'],**limits)
                if result['status']!='completed':
                    data['status']=result['status']
                    data['errors']=[error for child in result['children'] for error in child['errors']]
                else:
                    sources=[agent.catalog._path(c['package_path']) for c in result['children']]
                    inputs=([directory/'basis'] if (directory/'basis').exists() else [])+sources
                    ids=read_bundle(directory/'basis').base_package_ids if (directory/'basis').exists() else []
                    representation=compose(inputs,directory/'delivery',contributor_id=data['contributor_id'],base_ids=ids)
                    file=self.library.publish(representation)
                    data.update(status='completed',package_path=file.name,errors=[])
            except (OSError,ValueError,KeyError,TypeError,AnalysisError) as exc:
                data.update(status='failed',errors=[{'code':getattr(exc,'code','PACKAGE_DELIVERY_FAILED'),
                    'message':str(exc) if isinstance(exc,AnalysisError) else 'File learning or package delivery failed'}])
            atomic_json(directory/'task.json',data)
        return self.status(task)

    def pause(self,task):
        directory=self.task_dir(task);data=json.loads((directory/'task.json').read_text('utf-8'))
        if data['status']!='completed':
            DataAnalysisAgent(directory/'analysis',model_client=self.model_client).pause(data['inner_task_id'])
            data['status']='paused';atomic_json(directory/'task.json',data)
        return self.status(task)

    def query(self,**filters):
        return self.library.query(create_facade(),**filters)

    def review_queue(self,scope='node'):
        catalog,_=self.library.view()
        return catalog.review_queue(scope)

    def record_review(self,request):
        catalog,_=self.library.view()
        # Work on a separate snapshot: publication failure must not expose half a review.
        scratch=self.workspace/'review-work'/uuid4().hex
        compose([catalog.root],scratch,base_ids=[read_bundle(catalog.root).bundle_id])
        catalog=PackageCatalog(scratch)
        record=catalog.record_review(request)
        destination=self.workspace/'review-deliveries'/record['review_id']
        representation=compose([catalog.root],destination,base_ids=[read_bundle(catalog.root).bundle_id])
        file=self.library.publish(representation)
        return {'record':record,'package_path':file.name}

    def revise(self,request):
        catalog,_=self.library.view()
        # A failed file publication must not leave a revised source in the
        # shared readable view. Keep the entire operation in a private snapshot.
        basis_id=read_bundle(catalog.root).bundle_id
        operation=digest({'basis_id':basis_id,'request':request})
        scratch=self.workspace/'correction-work'/operation
        # Reuse the checked private operation on retry, including its original
        # creation metadata. Never rebuild the same correction with new timestamps.
        with process_lock(self.workspace/('.correction-'+operation+'.lock')):
            compose([catalog.root],scratch,base_ids=[basis_id])
        catalog=PackageCatalog(scratch)
        if str(request.get('parent_path','')).lower().endswith('.medpkg'):
            _,bundle=self.library.load(request['parent_path'])
            allowed={c.package_id for c in bundle.components}
            records={r['review_id']:r for r in catalog.reviews()['records']}
            targets={records[rid]['request']['target']['address']['package_id']
                     for rid in request['review_ids'] if rid in records}
            if len(targets)!=1 or not targets<=allowed:
                raise AnalysisError('CORRECTION_TARGET_SCOPE','Select reviews addressing one source within the chosen file')
            parent=next((p['path'] for p in catalog.scan() if p.get('package_id') in targets and p['state']!='quarantined'),None)
            if parent is None:raise AnalysisError('REVIEW_TARGET_UNAVAILABLE','Reviewed source is unavailable')
            request={**request,'parent_path':parent}
        result=catalog.revise_candidate(request)
        representation=compose([catalog.root,catalog._path(result['package_path'])],
            self.workspace/'correction-deliveries'/operation,
            base_ids=[read_bundle(catalog.root).bundle_id])
        file=self.library.publish(representation)
        return {**result,'package_path':file.name,'activation':'available_in_fixed_folder'}

    def associate(self,request):
        from medicine_agent.analysis.catalog import PackageCatalog
        catalog,_=self.library.view()
        scratch=self.workspace/'link-work'/uuid4().hex
        compose([catalog.root],scratch,base_ids=[read_bundle(catalog.root).bundle_id])
        working=PackageCatalog(scratch)
        record=working.associate(**request)
        representation=compose([scratch],self.workspace/'link-deliveries'/record['association_id'],
            base_ids=[read_bundle(scratch).bundle_id])
        file=self.library.publish(representation)
        return {'record':record,'package_path':file.name}
