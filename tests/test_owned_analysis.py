"""Declared-builder update isolation and shared consumption of synthetic packages."""
import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from medicine_agent.analysis.catalog import PackageCatalog
from medicine_agent.analysis.models import AnalysisError, AnalysisRequest
from medicine_agent.analysis.service import DataAnalysisAgent
from medicine_agent.analysis.store import atomic_json
from medicine_agent.bootstrap import create_facade
from medicine_agent.contracts import export_schemas
from medicine_agent.domain.ids import file_sha256
from medicine_agent.domain.owned_analysis import OwnedAnalysisRequest
from medicine_agent.packages.io import validate_package_path, read_jsonl
from medicine_agent.packages.owned import read_owned_cache
from test_reviews import request as review_request
from test_tcm_knowledge import FixtureModel


TEXT='自制第一页：甘能缓急。\n自制第二页：各保留原文。\n自制第三页：不代表医学结论。'


class CountingModel(FixtureModel):
    def __init__(self): self.calls=0
    def generate_json(self, **kwargs):
        self.calls+=1
        return super().generate_json(**kwargs)


def prepare(tmp_path, owner='user-a', name='source', text=TEXT, units=None):
    source=tmp_path/(name+'.txt')
    source.write_text(text,encoding='utf-8')
    model=CountingModel()
    agent=DataAnalysisAgent(tmp_path/('work-'+name+'-'+owner),tmp_path/'packages',model)
    job=agent.submit(OwnedAnalysisRequest(paths=[str(source)],owner_id=owner,
        allowed_use='synthetic-software-test', units=units))
    result=agent.run(job['task_id'])
    assert result['status']=='completed',result
    return agent,source,result['children'][0]['package_path'],model


def update(agent, source, parent, units, owner='user-a', **changes):
    return agent.submit(OwnedAnalysisRequest(paths=[str(source)],parent_package=parent,
        owner_id=owner,units=units,allowed_use='synthetic-software-test',**changes))


def test_same_owner_reuses_verified_analysis_and_only_calls_for_new_unit(tmp_path):
    agent,source,parent,model=prepare(tmp_path,units=[1])
    before={p.name:p.read_bytes() for p in agent.catalog._path(parent).iterdir() if p.is_file()}
    assert model.calls==1
    job=update(agent,source,parent,[2])
    assert job['children'][0]['analyzed']==1
    outcome=agent.run(job['task_id'])
    assert outcome['status']=='completed',outcome
    assert model.calls==2
    path=agent.catalog._path(outcome['children'][0]['package_path'])
    cache=read_owned_cache(path)
    assert cache.reused_analysis_units==[1] and cache.reused_extraction_units==[1]
    assert [u.ordinal for u in cache.units]==[1,2]
    calls=agent.store.calls(job['children'][0]['task_id'])
    assert len([c for c in calls if c.get('skill_id')=='document-extraction'])==1
    assert {p.name:p.read_bytes() for p in agent.catalog._path(parent).iterdir() if p.is_file()}==before
    assert validate_package_path(path).valid
    assert len(read_jsonl(path/'runs.jsonl'))>len(read_jsonl(agent.catalog._path(parent)/'runs.jsonl'))


def test_added_predecessor_invalidates_old_analysis_but_reuses_ocr(tmp_path):
    agent,source,parent,model=prepare(tmp_path,units=[1,3])
    assert model.calls==2
    job=update(agent,source,parent,[2])
    result=agent.run(job['task_id'])
    assert result['status']=='completed',result
    assert model.calls==4
    cache=read_owned_cache(agent.catalog._path(result['children'][0]['package_path']))
    assert cache.reused_analysis_units==[1]
    assert cache.reused_extraction_units==[1,3]
    assert cache.invalidated_context_units==[3]


@pytest.mark.parametrize('owner', ['user-b', None])
def test_contributor_is_not_permission_to_continue_same_source(tmp_path, owner):
    agent,source,parent,_=prepare(tmp_path,units=[1])
    before=(agent.catalog._path(parent)/'tcm.json').read_bytes()
    result=agent.run(update(agent,source,parent,[2],owner=owner)['task_id'])
    assert result['status']=='completed',result
    assert (agent.catalog._path(parent)/'tcm.json').read_bytes()==before


def test_legacy_package_can_be_continued_without_an_author_gate(tmp_path):
    source=tmp_path/'legacy.txt';source.write_text(TEXT,encoding='utf-8')
    agent=DataAnalysisAgent(tmp_path/'work',tmp_path/'packages',CountingModel())
    job=agent.submit(AnalysisRequest(paths=[str(source)],units=[1],allowed_use='synthetic-software-test'))
    result=agent.run(job['task_id']);parent=result['children'][0]['package_path']
    assert agent.catalog.query(create_facade(),text='甘能缓急')['packages']
    result=agent.run(update(agent,source,parent,[2])['task_id'])
    assert result['status']=='completed',result
    assert read_owned_cache(agent.catalog._path(result['children'][0]['package_path'])).reused_analysis_units==[]


def test_different_source_and_configuration_do_not_reuse_old_originals(tmp_path):
    agent,source,parent,_=prepare(tmp_path,units=[1])
    other=tmp_path/'other.txt';other.write_text('第二资料独有原话。',encoding='utf-8')
    with pytest.raises(AnalysisError) as exc: update(agent,other,parent,[1])
    assert exc.value.code=='PARENT_SOURCE_CONFLICT'
    with pytest.raises(AnalysisError) as exc: update(agent,source,parent,[2],force_ocr=True)
    assert exc.value.code=='INCREMENTAL_CONFIG_CONFLICT'
    job=agent.submit(OwnedAnalysisRequest(paths=[str(other)],owner_id='user-a',allowed_use='synthetic-software-test'))
    result=agent.run(job['task_id']);assert result['status']=='completed'
    path=agent.catalog._path(result['children'][0]['package_path'])
    assert [e['raw_text'] for e in read_jsonl(path/'evidence.jsonl')]==['第二资料独有原话。']
    assert read_owned_cache(path).reused_analysis_units==[]
    combined=agent.catalog.query(create_facade(),text='资料')
    assert len(combined['packages'])==2
    assert len({p['package']['family'] for p in combined['packages']})==2


def test_two_users_same_file_have_independent_packages_and_can_query_together(tmp_path):
    agent,source,first,_=prepare(tmp_path,units=[1])
    job=agent.submit(OwnedAnalysisRequest(paths=[str(source)],owner_id='user-b',units=[1],allowed_use='synthetic-software-test'))
    result=agent.run(job['task_id']);assert result['status']=='completed',result
    selected=agent.catalog.selected()
    assert len(selected)==2
    assert len({p['package_id'] for p in selected})==2
    assert {p['owner_id'] for p in selected}=={'user-a','user-b'}
    query=agent.catalog.query(create_facade(),text='甘能缓急')
    assert len(query['packages'])==2
    assert all(p['medical_nodes'] and p['medical_evidence'] for p in query['packages'])


def test_portable_cache_updates_without_old_workspace_and_survives_restart(tmp_path):
    agent,source,parent,_=prepare(tmp_path,units=[1])
    moved=tmp_path/'moved';shutil.copytree(agent.catalog.root,moved)
    model=CountingModel()
    second=DataAnalysisAgent(tmp_path/'new-work',moved,model)
    job=update(second,source,parent,[2,3])
    assert second.run(job['task_id'],max_units=1)['status']=='paused'
    resumed=DataAnalysisAgent(tmp_path/'new-work',model_client=model)
    result=resumed.run(job['task_id'])
    assert result['status']=='completed',result
    assert model.calls==2
    source.unlink()
    assert resumed.catalog.query(create_facade(),text='自制')['packages'][0]['medical_evidence']


def test_corrected_parent_is_never_reverted_by_old_model_cache(tmp_path):
    agent,source,parent,_=prepare(tmp_path,units=[1])
    item=agent.catalog.review_queue('fact')['items'][0]
    record=agent.catalog.record_review(review_request(item,'needs_revision',proposed_value='自制明确更正'))
    revision=agent.catalog.revise_candidate({'parent_path':parent,'review_ids':[record['review_id']]})
    path=agent.catalog._path(revision['package_path'])
    assert validate_package_path(path).valid
    agent.catalog.select(revision['package_path'])
    with pytest.raises(AnalysisError) as exc: update(agent,source,revision['package_path'],[2])
    assert exc.value.code=='INCREMENTAL_CORRECTED_PARENT_UNSUPPORTED'
    assert agent.catalog.query(create_facade(),text='自制明确更正')['packages'][0]['medical_nodes']


def test_cache_tampering_is_quarantined_even_when_checksum_is_replaced(tmp_path):
    agent,_,parent,_=prepare(tmp_path,units=[1])
    path=agent.catalog._path(parent)
    cache=json.loads((path/'ownership.json').read_text('utf-8'))
    cache['units'][0]['extraction']['blocks'][0]['text']='伪造原文'
    atomic_json(path/'ownership.json',cache)
    manifest=json.loads((path/'manifest.json').read_text('utf-8'))
    manifest['files']['ownership.json']=file_sha256((path/'ownership.json').read_bytes())
    atomic_json(path/'manifest.json',manifest)
    assert not validate_package_path(path).valid
    assert agent.catalog.scan()[0]['state']=='quarantined'


def test_product_input_cli_and_owned_schema(tmp_path):
    from medicine_agent.analysis.orchestrator import OrchestratorAgent
    source=tmp_path/'source.txt';source.write_text('自制新资料原话。',encoding='utf-8')
    agent=OrchestratorAgent(tmp_path/'work',tmp_path/'packages',CountingModel())
    job=agent.receive('analyze_files',{'paths':[str(source)],'owner_id':'user-a','allowed_use':'synthetic-software-test'})
    assert agent.execute(job['task_id'])['status']=='completed'
    help_result=subprocess.run([sys.executable,'-m','medicine_agent.cli','analyze','submit','--help'],capture_output=True,text=True,encoding='utf-8')
    assert '--owner-id' in help_result.stdout
    out=tmp_path/'schema';export_schemas(create_facade(),out,contract_set='owned-analysis')
    expected=Path(__file__).parents[1]/'schemas/owned-analysis'
    assert {p.relative_to(out).as_posix():p.read_bytes() for p in out.rglob('*.json')}=={
        p.relative_to(expected).as_posix():p.read_bytes() for p in expected.rglob('*.json')}
