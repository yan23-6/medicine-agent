"""Single-file product delivery and the user's three-source 气/热 example."""
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from medicine_agent.analysis.orchestrator import OrchestratorAgent
from medicine_agent.analysis.file_learning import FileLearningService
from medicine_agent.analysis.library import PackageLibrary, default_knowledge_root
from medicine_agent.domain.ids import file_sha256
from medicine_agent.packages.archive import unpack_archive
from medicine_agent.packages.tcm import read_graph
from medicine_agent.contracts import export_schemas
from medicine_agent.bootstrap import create_facade


class ConceptModel:
    provider='synthetic-software-check'
    model='concept-schema-fixture'
    def __init__(self):self.calls=0
    def generate_json(self,*,system,user,schema):
        self.calls+=1
        evidence=json.loads(user)[-1]
        title=evidence['raw_text'].split('|')[0]
        quote={'evidence_id':evidence['evidence_id'],'text':evidence['raw_text']}
        return {'nodes':[{'node_id':'local','source_id':evidence['source_id'],
            'title':title,'statement':evidence['raw_text'],'categories':['tcm_foundation'],
            'quotes':[quote],'groups':[{'group_id':'g1','kind':'theory','facts':[{
                'field_id':'tcm.theory_proposition_text','value':evidence['raw_text'],'quotes':[quote]}]}]}]}


def learn(tmp_path,public,name,text,contributor,*,bases=()):
    source=tmp_path/(name+'.txt');source.write_text(text,encoding='utf-8')
    model=ConceptModel()
    agent=OrchestratorAgent(tmp_path/('work-'+name),public,model)
    task=agent.receive('analyze_files',{'paths':[str(source)],'owner_id':contributor,
        'base_packages':list(bases),'allowed_use':'synthetic-software-test'})
    result=agent.execute(task['task_id'])
    assert result['status']=='completed',result
    file=public/result['package_path']
    assert file.is_file() and file.suffix=='.medpkg'
    return agent,file,task,model


def nodes(library,file):
    root,bundle=library.load(file)
    return {(c.package_id,n.node_id):n.model_dump(mode='json') for c in bundle.components
            for n in (read_graph(root/c.path).nodes if read_graph(root/c.path) else [])}


def test_three_source_concept_new_heat_and_untouched_knowledge_in_one_file(tmp_path,monkeypatch):
    public=tmp_path/'knowledge'
    first,p1,_,_=learn(tmp_path,public,'book1','气|来源一的气解释。\n阴阳|来源一独有旧知识。','user-1')
    second,p2,_,_=learn(tmp_path,public,'book2','气|来源二的气解释。\n津液|来源二独有旧知识。','user-2')
    library=first.files.library
    before={p.name:p.read_bytes() for p in (p1,p2)}
    original={**nodes(library,p1),**nodes(library,p2)}
    combined=second.receive('query_knowledge',{'text':'气'})
    assert any(len(g['members'])==2 for g in combined['concept_groups'])
    source=tmp_path/'A.txt';source.write_text('气|新书A自己的解释。\n热|新书A新增知识。',encoding='utf-8')
    model=ConceptModel();work=tmp_path/'work-third'
    third=OrchestratorAgent(work,public,model)
    job=third.receive('analyze_files',{'paths':[str(source)],'owner_id':'user-3',
        'base_packages':[p1.name,p2.name],'allowed_use':'synthetic-software-test'})
    assert third.execute(job['task_id'],max_units=1)['status']=='paused'
    assert model.calls==1
    # Original base files disappear after submission; the task owns verified snapshots.
    holding=tmp_path/'holding';holding.mkdir()
    for p in (p1,p2):shutil.move(str(p),holding/p.name)
    source.unlink()
    resumed=OrchestratorAgent(work,model_client=model)
    result=resumed.execute(job['task_id']);assert result['status']=='completed',result
    assert model.calls==2  # A's 气 was read, even though two bases already contained it.
    p3=public/result['package_path']
    representation,bundle=resumed.files.library.load(p3)
    history={p.stem for p in (representation/'history').glob('*.json')}
    assert set(bundle.base_package_ids)<=history
    assert all((holding/name).read_bytes()==value for name,value in before.items())
    complete=nodes(resumed.files.library,p3)
    assert all(complete[key]==value for key,value in original.items())
    assert len(complete)==6
    migrated=tmp_path/'another-computer'/'knowledge';migrated.mkdir(parents=True)
    shutil.copyfile(p3,migrated/p3.name)  # Only a single package file is migrated.
    blocked=[tmp_path/'work-book1',tmp_path/'work-book2',work,holding]
    read_text,read_bytes=Path.read_text,Path.read_bytes
    def guard(path):
        assert not any(path.resolve().is_relative_to(p.resolve()) for p in blocked),'Read an original workspace'
    def text(path,*a,**kw):guard(path);return read_text(path,*a,**kw)
    def binary(path,*a,**kw):guard(path);return read_bytes(path,*a,**kw)
    monkeypatch.setattr(Path,'read_text',text);monkeypatch.setattr(Path,'read_bytes',binary)
    fresh=OrchestratorAgent(tmp_path/'another-computer'/'work',migrated)
    query=fresh.receive('query_knowledge',{'text':'气'})
    gas=[n for p in query['packages'] for n in p['medical_nodes'] if n['title']=='气']
    assert len(gas)==3
    assert {n['groups'][0]['facts'][0]['value'] for n in gas}=={
        '气|来源一的气解释。','气|来源二的气解释。','气|新书A自己的解释。'}
    assert any(len(g['members'])==3 for g in query['concept_groups'])
    assert len(query['associations'])>=2
    assert fresh.receive('query_knowledge',{'text':'热'})['packages']
    for term in ('阴阳','津液'):
        assert any(p['medical_nodes'] for p in fresh.receive('query_knowledge',{'text':term})['packages'])
    (migrated/p3.name).unlink()
    assert fresh.receive('query_knowledge',{'text':'气'})['packages']==[]


def test_default_fixed_path_ignores_working_directory(tmp_path,monkeypatch):
    monkeypatch.setattr(Path,'home',staticmethod(lambda:tmp_path/'profile'))
    public=default_knowledge_root();assert public==tmp_path/'profile/MedicineAgent/knowledge'
    agent,file,_,_=learn(tmp_path,public,'fixed','气|默认目录自制说明。','user')
    assert agent.receive('capabilities',{})['package_folder']==str(public.resolve())
    assert (public/'数据包说明书.md').is_file() and (public/'package-spec.json').is_file()
    monkeypatch.chdir(tmp_path/'profile')
    fresh=OrchestratorAgent(tmp_path/'new-work')
    assert any(p['medical_nodes'] for p in fresh.receive('query_knowledge',{'text':'气'})['packages'])


def test_failed_final_commit_is_retryable_without_reanalysis(tmp_path,monkeypatch):
    public=tmp_path/'knowledge';source=tmp_path/'source.txt';source.write_text('气|故障检查。',encoding='utf-8')
    model=ConceptModel();agent=OrchestratorAgent(tmp_path/'work',public,model)
    task=agent.receive('analyze_files',{'paths':[str(source)],'allowed_use':'synthetic-software-test'})
    rename=Path.rename
    def fail(path,target):
        if path.name.startswith('.pending-package-'):raise OSError('synthetic final commit failure')
        return rename(path,target)
    monkeypatch.setattr(Path,'rename',fail)
    failed=agent.execute(task['task_id'])
    assert failed['status']=='failed' and failed['errors']
    assert not list(public.glob('*.medpkg')) and not list(public.glob('.pending-package-*'))
    assert model.calls==1
    monkeypatch.setattr(Path,'rename',rename)
    resumed=OrchestratorAgent(tmp_path/'work',model_client=model)
    result=resumed.execute(task['task_id'])
    assert result['status']=='completed',result
    assert model.calls==1
    before=(public/result['package_path']).read_bytes()
    assert resumed.execute(task['task_id'])['package_path']==result['package_path']
    assert (public/result['package_path']).read_bytes()==before


def test_corrupt_or_removed_file_does_not_reappear_from_cache(tmp_path):
    public=tmp_path/'knowledge'
    agent,file,_,_=learn(tmp_path,public,'source','气|完整性检查。','user')
    assert agent.receive('query_knowledge',{'text':'气'})['packages']
    (public/'corrupt.medpkg').write_bytes(b'broken archive')
    query=agent.receive('query_knowledge',{'text':'气'})
    assert any(i['state']=='quarantined' for i in query['package_files'])
    assert query['packages']
    file.unlink()
    assert agent.receive('query_knowledge',{'text':'气'})['packages']==[]


@pytest.mark.parametrize('name',['../escape.txt','C:/escape.txt','a\\escape.txt'])
def test_archive_paths_are_rejected_and_partial_extract_removed(tmp_path,name):
    file=tmp_path/'unsafe.medpkg'
    with zipfile.ZipFile(file,'w') as archive:archive.writestr(name,'bad')
    destination=tmp_path/'extraction'
    with pytest.raises(ValueError):unpack_archive(file,destination)
    assert not destination.exists() and not (tmp_path/'escape.txt').exists()


def test_archive_undeclared_data_is_rejected(tmp_path):
    agent,file,_,_=learn(tmp_path,tmp_path/'knowledge','source','气|自制归档检查。','user')
    malicious=tmp_path/'extra.medpkg';shutil.copyfile(file,malicious)
    with zipfile.ZipFile(malicious,'a') as archive:archive.writestr('unlisted.txt','not declared')
    with pytest.raises(ValueError):unpack_archive(malicious,tmp_path/'extraction')
    assert not (tmp_path/'extraction').exists()


def test_cli_cross_process_pause_resume_and_learning_schema(tmp_path):
    source=tmp_path/'source.txt';source.write_text('原文一\n原文二\n原文三',encoding='utf-8')
    public,work=tmp_path/'knowledge',tmp_path/'work'
    def cli(*args):
        result=subprocess.run([sys.executable,'-m','medicine_agent.cli','analyze',*map(str,args)],capture_output=True,text=True,encoding='utf-8')
        assert result.returncode==0,result.stdout+result.stderr
        return json.loads(result.stdout)
    task=cli('submit',source,'--workspace',work,'--packages',public,'--mode','extractive','--allowed-use','synthetic-software-test')
    assert cli('run',task['task_id'],'--workspace',work,'--max-units',1)['status']=='paused'
    finished=cli('run',task['task_id'],'--workspace',work)
    assert finished['status']=='completed' and (public/finished['package_path']).is_file()
    assert cli('query','--workspace',work,'--packages',public,'--text','原文')['packages']
    out=tmp_path/'schema';export_schemas(create_facade(),out,contract_set='learning')
    expected=Path(__file__).parents[1]/'schemas/learning'
    assert {p.relative_to(out).as_posix():p.read_bytes() for p in out.rglob('*.json')}=={
        p.relative_to(expected).as_posix():p.read_bytes() for p in expected.rglob('*.json')}


def test_foreign_corrected_package_is_a_live_learning_base(tmp_path):
    public=tmp_path/'knowledge'
    agent,file,_,_=learn(tmp_path,public,'original','气|自制原始解释。','user-1')
    item=agent.files.review_queue('fact')['items'][0]
    reviewed=agent.receive('record_review',{'target':item['target'],'decision':'needs_revision',
        'reviewer':'synthetic-reviewer','reason':'自制更正软件检查','proposed_value':'保留的自制更正值',
        'expected_previous_id':None})
    revised=agent.receive('revise_candidate',{'parent_path':reviewed['package_path'],
        'review_ids':[reviewed['record']['review_id']]})
    new_source=tmp_path/'new-book.txt';new_source.write_text('热|第三人新资料原文。',encoding='utf-8')
    third=OrchestratorAgent(tmp_path/'third-work',public,ConceptModel())
    task=third.receive('analyze_files',{'paths':[str(new_source)],'owner_id':'user-3',
        'parent_package':revised['package_path'],'allowed_use':'synthetic-software-test'})
    done=third.execute(task['task_id']);assert done['status']=='completed',done
    only=tmp_path/'only';only.mkdir();shutil.copyfile(public/done['package_path'],only/done['package_path'])
    fresh=OrchestratorAgent(tmp_path/'fresh',only)
    result=fresh.receive('query_knowledge',{'text':'保留的自制更正值'})
    assert any(p['medical_nodes'] for p in result['packages'])
    assert any(p['correction_provenance'] for p in result['packages'])
    assert fresh.receive('query_knowledge',{'text':'热'})['packages']


def test_failed_review_publication_does_not_change_the_readable_history(tmp_path,monkeypatch):
    agent,file,_,_=learn(tmp_path,tmp_path/'knowledge','original','气|复核事务检查。','user')
    item=agent.files.review_queue('fact')['items'][0]
    request={'target':item['target'],'decision':'confirmed','reviewer':'synthetic',
        'reason':'自制软件检查','expected_previous_id':None}
    def fail(*args,**kwargs):raise OSError('synthetic publication failure')
    monkeypatch.setattr(agent.files.library,'publish',fail)
    with pytest.raises(OSError):agent.receive('record_review',request)
    assert agent.files.review_queue('fact')['items'][0]['user_review_state']=='unreviewed'


def test_changed_basis_fails_before_model_call_and_leaves_old_file_usable(tmp_path):
    public=tmp_path/'knowledge'
    _,file,_,_=learn(tmp_path,public,'base','气|基础原文。','user-1')
    source=tmp_path/'A.txt';source.write_text('热|新资料原文。',encoding='utf-8')
    model=ConceptModel();agent=OrchestratorAgent(tmp_path/'work-A',public,model)
    task=agent.receive('analyze_files',{'paths':[str(source)],'base_packages':[file.name],
        'owner_id':'user-3','allowed_use':'synthetic-software-test'})
    directory=agent.files.task_dir(task['task_id'])
    (directory/'basis'/'bundle.json').write_text('{}',encoding='utf-8')
    result=agent.execute(task['task_id'])
    assert result['status']=='failed' and result['errors']
    assert model.calls==0 and len(list(public.glob('*.medpkg')))==1
    assert agent.receive('query_knowledge',{'text':'气'})['packages']


def test_failed_correction_publication_keeps_shared_view_clean_and_can_retry(tmp_path,monkeypatch):
    agent,file,_,_=learn(tmp_path,tmp_path/'knowledge','original','气|更正事务检查。','user')
    item=agent.files.review_queue('fact')['items'][0]
    reviewed=agent.receive('record_review',{'target':item['target'],'decision':'needs_revision',
        'reviewer':'synthetic','reason':'自制事务检查','proposed_value':'更正后自制值',
        'expected_previous_id':None})
    request={'parent_path':reviewed['package_path'],'review_ids':[reviewed['record']['review_id']]}
    catalog,_=agent.files.library.view()
    before={p.relative_to(catalog.root).as_posix() for p in catalog.root.rglob('manifest.json')}
    publish=agent.files.library.publish
    def fail(*args,**kwargs):raise OSError('synthetic correction publication failure')
    monkeypatch.setattr(agent.files.library,'publish',fail)
    with pytest.raises(OSError):agent.receive('revise_candidate',request)
    assert before=={p.relative_to(catalog.root).as_posix() for p in catalog.root.rglob('manifest.json')}
    monkeypatch.setattr(agent.files.library,'publish',publish)
    revised=agent.receive('revise_candidate',request)
    assert (agent.files.library.root/revised['package_path']).is_file()
    assert any(p['medical_nodes'] for p in agent.receive('query_knowledge',{'text':'更正后自制值'})['packages'])


def test_concurrent_first_queries_share_a_complete_private_cache(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    public=tmp_path/'knowledge'
    learn(tmp_path,public,'base','气|并发只读自制检查。','user')
    reader=OrchestratorAgent(tmp_path/'cold-reader',public)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:reader.receive('query_knowledge',{'text':'气'}),range(2)))
    assert all(any(p['medical_nodes'] for p in r['packages']) for r in results)
    assert all(all(p['state']!='quarantined' for p in r['package_files']) for r in results)
