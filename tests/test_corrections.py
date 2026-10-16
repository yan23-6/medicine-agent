"""Candidate amendment software checks with explicitly synthetic opinions."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from medicine_agent.analysis.catalog import PackageCatalog
from medicine_agent.analysis.models import AnalysisError
from medicine_agent.analysis.store import atomic_json
from medicine_agent.bootstrap import create_facade
from medicine_agent.contracts import export_schemas
from medicine_agent.domain.ids import file_sha256
from medicine_agent.packages.io import validate_package_path
from medicine_agent.packages.tcm import read_graph
from test_tcm_knowledge import create_medical_package
from test_reviews import request


def prepare(tmp_path, scope='fact', proposal='自制软件测试更正值'):
    catalog, path = create_medical_package(tmp_path, 'book')
    item = catalog.review_queue(scope)['items'][0]
    record = catalog.record_review(request(item, 'needs_revision', proposed_value=proposal))
    payload = {'parent_path': path.relative_to(catalog.root).as_posix(), 'review_ids': [record['review_id']]}
    return catalog, path, payload


def files(path):
    return {p.relative_to(path).as_posix(): p.read_bytes() for p in path.rglob('*') if p.is_file()}


def test_correction_changes_only_explicit_target_and_requires_selection(tmp_path):
    catalog, parent, payload = prepare(tmp_path)
    before = files(parent)
    old = read_graph(parent)
    result = catalog.revise_candidate(payload)
    path = catalog._path(result['package_path'])
    assert validate_package_path(path).valid
    assert files(parent) == before
    assert catalog.selected()[0]['path'] == payload['parent_path']
    new = read_graph(path)
    assert new.nodes[0].groups[0].facts[0].value == '自制软件测试更正值'
    assert new.nodes[0].node_id != old.nodes[0].node_id
    assert new.nodes[0].quotes == old.nodes[0].quotes
    assert new.nodes[0].groups[0].facts[0].quotes == old.nodes[0].groups[0].facts[0].quotes
    for name in ('sources.jsonl', 'fragments.jsonl', 'evidence.jsonl', 'raw_fields.jsonl', 'runs.jsonl'):
        assert (path/name).read_bytes() == before[name]
    catalog.select(result['package_path'])
    query = catalog.query(create_facade(), text='自制软件测试更正值')
    assert query['packages'][0]['medical_nodes'][0]['node_id'] == new.nodes[0].node_id
    assert query['packages'][0]['correction_provenance']['history'][0]['origin'] == 'user_entered'
    assert query['user_review_states'] == []
    assert query['medical_review'] == 'unreviewed'
    assert catalog.review_queue('fact')['items'][0]['user_review_state'] == 'unreviewed'
    catalog.select(payload['parent_path'])
    assert catalog.query(create_facade(), knowledge_id=old.nodes[0].node_id)['packages'][0]['medical_nodes']


def test_idempotency_after_selection_and_no_rewrite(tmp_path):
    catalog, _, payload = prepare(tmp_path)
    first = catalog.revise_candidate(payload)
    path = catalog._path(first['package_path'])
    before = files(path)
    catalog.select(first['package_path'])
    assert catalog.revise_candidate(payload) == first
    assert files(path) == before


@pytest.mark.parametrize('decision,proposal', [('confirmed', None), ('rejected', None), ('needs_revision', None)])
def test_noncorrection_or_missing_proposal_is_rejected(tmp_path, decision, proposal):
    catalog, parent = create_medical_package(tmp_path, 'book')
    record = catalog.record_review(request(catalog.review_queue()['items'][0], decision, proposed_value=proposal))
    with pytest.raises(AnalysisError) as exc:
        catalog.revise_candidate({'parent_path': parent.relative_to(catalog.root).as_posix(), 'review_ids':[record['review_id']]})
    assert exc.value.code == 'CORRECTION_PROPOSAL_INVALID'
    assert not (catalog.root/'revisions').exists()


def test_stale_and_duplicate_reviews_are_rejected(tmp_path):
    catalog, _, payload = prepare(tmp_path)
    with pytest.raises(AnalysisError, match='unique'):
        catalog.revise_candidate({**payload,'review_ids':payload['review_ids']*2})
    catalog.record_review(request(catalog.review_queue('fact')['items'][0], 'confirmed'))
    with pytest.raises(AnalysisError) as exc:
        catalog.revise_candidate(payload)
    assert exc.value.code == 'CORRECTION_REVIEW_STALE'


def test_parent_and_overlapping_targets_must_be_explicit(tmp_path):
    catalog, parent, payload = prepare(tmp_path)
    record = catalog.record_review(request(catalog.review_queue()['items'][0], 'needs_revision', proposed_value='自制节点更正'))
    with pytest.raises(AnalysisError, match='Overlapping'):
        catalog.revise_candidate({**payload,'review_ids': payload['review_ids']+[record['review_id']]})
    catalog2, other = create_medical_package(tmp_path, 'other', text='不同自制来源。甘能缓急。')
    with pytest.raises(AnalysisError, match='parent package'):
        catalog2.revise_candidate({**payload,'parent_path':other.relative_to(catalog.root).as_posix()})
    assert validate_package_path(parent).valid


@pytest.mark.parametrize('proposal', [
    {'fact_patch': {'state':'missing', 'value':'不能保留非空', 'reason':'自制检查'}},
    {'fact_patch': {'quotes':[]}},
    {'fact_patch': {'field_id':'tcm.invented'}},
])
def test_invalid_fact_patches_cannot_bypass_schema_or_edit_evidence(tmp_path, proposal):
    catalog, parent, payload = prepare(tmp_path, proposal=proposal)
    before = files(parent)
    with pytest.raises(AnalysisError):
        catalog.revise_candidate(payload)
    assert files(parent)==before


def test_explicit_null_and_metadata_patch_and_query_projection(tmp_path):
    catalog, parent, payload = prepare(tmp_path, proposal={'fact_patch':{'value':None,'state':'ambiguous','reason':'自制歧义说明'}})
    result = catalog.revise_candidate(payload)
    assert read_graph(catalog._path(result['package_path'])).nodes[0].groups[0].facts[0].value is None
    catalog.select(result['package_path'])
    item=catalog.review_queue()['items'][0]
    record=catalog.record_review(request(item,'needs_revision',proposed_value={'statement':'自制改写陈述','title':'自制标题'}))
    result2=catalog.revise_candidate({'parent_path':result['package_path'],'review_ids':[record['review_id']]})
    catalog.select(result2['package_path'])
    query=catalog.query(create_facade(),text='自制改写陈述')
    assert query['packages'][0]['matches'][0]['statement']=='自制改写陈述'
    assert len(query['packages'][0]['correction_provenance']['history'])==2
    assert validate_package_path(parent).valid


def test_migration_without_parent_and_replug_preserves_old_links(tmp_path):
    catalog, parent, payload = prepare(tmp_path)
    _, other = create_medical_package(tmp_path, 'paper', text='另一来源的自制资料。甘能缓急。')
    addresses=[i['target']['address'] for i in catalog.review_queue()['items']]
    catalog.associate(addresses[0], addresses[1], 'same_definition', '自制关联测试')
    result = catalog.revise_candidate(payload)
    moved=tmp_path/'moved'
    shutil.copytree(catalog.root,moved)
    migrated=PackageCatalog(moved)
    migrated.select(result['package_path'])
    holding=tmp_path/'holding'
    shutil.move(str(moved/payload['parent_path']),holding)
    assert validate_package_path(moved/result['package_path']).valid
    query=migrated.query(create_facade(),text='自制软件测试更正值')
    corrected = next(p for p in query['packages'] if p['package']['package_id']==result['package_id'])
    assert corrected['correction_provenance']['history'][0]['parent_graph']['nodes']
    assert migrated.associations()['associations']
    shutil.move(str(holding),moved/payload['parent_path'])
    assert migrated.reviews()['records']


def test_failure_does_not_commit_partial_or_change_old_selection(tmp_path, monkeypatch):
    catalog, parent, payload = prepare(tmp_path)
    before=files(parent)
    from medicine_agent.analysis import corrections
    original=corrections.atomic_json
    def fail(path,value):
        if path.name=='corrections.json':
            raise OSError('synthetic disk failure')
        return original(path,value)
    monkeypatch.setattr(corrections,'atomic_json',fail)
    with pytest.raises(OSError):
        catalog.revise_candidate(payload)
    assert files(parent)==before
    assert len(catalog.scan())==1
    assert not list(catalog.root.glob('.pending-correction-*'))
    monkeypatch.setattr(corrections,'atomic_json',original)
    assert catalog.revise_candidate(payload)['package_id']


def test_tampered_content_even_with_updated_checksums_is_rejected(tmp_path):
    catalog, _, payload = prepare(tmp_path)
    result=catalog.revise_candidate(payload)
    path=catalog._path(result['package_path'])
    bundle=json.loads((path/'corrections.json').read_text('utf-8'))
    bundle['history'][0]['node_mapping']={}
    atomic_json(path/'corrections.json',bundle)
    manifest=json.loads((path/'manifest.json').read_text('utf-8'))
    manifest['files']['corrections.json']=file_sha256((path/'corrections.json').read_bytes())
    atomic_json(path/'manifest.json',manifest)
    assert not validate_package_path(path).valid
    assert any(i['state']=='quarantined' for i in catalog.scan())


def test_cli_and_schema_contract(tmp_path):
    catalog, _, payload=prepare(tmp_path)
    input_file=tmp_path/'request.json'
    atomic_json(input_file,payload)
    result=subprocess.run([sys.executable,'-m','medicine_agent.cli','analyze','revise','--packages',str(catalog.root),
                           '--input-file',str(input_file)],capture_output=True,text=True,encoding='utf-8')
    assert result.returncode==0, result.stdout+result.stderr
    assert json.loads(result.stdout)['activation']=='explicit_selection_required'
    out=tmp_path/'schema'
    export_schemas(create_facade(),out,contract_set='correction')
    expected=Path(__file__).parents[1]/'schemas'/'correction'
    assert files(out)==files(expected)


def test_product_agent_routes_correction_without_model(tmp_path):
    from medicine_agent.analysis.orchestrator import OrchestratorAgent
    catalog, _, payload=prepare(tmp_path)
    agent=OrchestratorAgent(tmp_path/'product-work',catalog.root)
    assert 'revise_candidate' in agent.receive('capabilities',{})['goals']
    result=agent.receive('revise_candidate',payload)
    assert validate_package_path(catalog._path(result['package_path'])).valid


def test_superseded_parent_requires_explicit_selection_for_new_request(tmp_path):
    catalog, _, payload=prepare(tmp_path)
    first=catalog.revise_candidate(payload)
    item=catalog.review_queue('fact')['items'][0]
    review=catalog.record_review(request(item,'needs_revision',proposed_value='第二条自制意见'))
    catalog.select(first['package_path'])
    with pytest.raises(AnalysisError) as exc:
        catalog.revise_candidate({**payload,'review_ids':[review['review_id']]})
    assert exc.value.code=='PARENT_REVISION_CONFLICT'


def test_no_effect_unsafe_metadata_and_missing_reviews_are_rejected(tmp_path):
    catalog, parent=create_medical_package(tmp_path,'book')
    item=catalog.review_queue()['items'][0]
    for proposal in (item['value'], {'quotes':[]}, {'source_id':'other'}):
        review=catalog.record_review(request(item,'needs_revision',proposed_value=proposal))
        with pytest.raises(AnalysisError):
            catalog.revise_candidate({'parent_path':parent.relative_to(catalog.root).as_posix(),'review_ids':[review['review_id']]})
        item=catalog.review_queue()['items'][0]
    with pytest.raises(AnalysisError) as exc:
        catalog.revise_candidate({'parent_path':parent.relative_to(catalog.root).as_posix(),'review_ids':['absent']})
    assert exc.value.code=='CORRECTION_REVIEW_UNAVAILABLE'


def test_embedded_review_history_survives_without_external_records(tmp_path):
    catalog,parent=create_medical_package(tmp_path,'book')
    first=catalog.record_review(request(catalog.review_queue('fact')['items'][0],'confirmed'))
    second=catalog.record_review(request(catalog.review_queue('fact')['items'][0],'needs_revision',proposed_value='自制更正'))
    result=catalog.revise_candidate({'parent_path':parent.relative_to(catalog.root).as_posix(),'review_ids':[second['review_id']]})
    isolated=tmp_path/'standalone'
    shutil.copytree(catalog._path(result['package_path']),isolated)
    assert validate_package_path(isolated).valid
    from medicine_agent.packages.corrections import read_corrections
    audit=read_corrections(isolated)
    assert {r.review_id for r in audit.history[-1].review_history}=={first['review_id'],second['review_id']}


def test_distinct_occurrences_in_same_node_and_unrelated_node_are_preserved(tmp_path):
    import copy
    from medicine_agent.analysis.service import DataAnalysisAgent
    from medicine_agent.analysis.models import AnalysisRequest
    from test_tcm_knowledge import FixtureModel, TEXT
    class MultipleModel(FixtureModel):
        def generate_json(self, **kwargs):
            payload=super().generate_json(**kwargs)
            node=payload['nodes'][0]
            node['groups'][0]['facts'].append(copy.deepcopy(node['groups'][0]['facts'][0]))
            another=copy.deepcopy(node)
            another['node_id']='another'
            another['title']='另一个自制节点'
            payload['nodes'].append(another)
            return payload
    source=tmp_path/'source.txt'
    source.write_text(TEXT,encoding='utf-8')
    agent=DataAnalysisAgent(tmp_path/'work',tmp_path/'packages',MultipleModel())
    task=agent.submit(AnalysisRequest(paths=[str(source)],allowed_use='synthetic-software-test'))
    outcome=agent.run(task['task_id'])
    assert outcome['status']=='completed'
    parent=outcome['children'][0]['package_path']
    catalog=agent.catalog
    old=read_graph(catalog._path(parent))
    nid=old.nodes[0].node_id
    items=[i for i in catalog.review_queue('fact')['items'] if i['target']['address']['node_id']==nid]
    ids=[]
    for i,item in enumerate(items):
        ids.append(catalog.record_review(request(item,'needs_revision',proposed_value=f'自制出现序号{i}'))['review_id'])
    result=catalog.revise_candidate({'parent_path':parent,'review_ids':ids})
    new=read_graph(catalog._path(result['package_path']))
    assert len(new.nodes)==2
    assert new.nodes[1]==old.nodes[1]
    assert {f.value for f in new.nodes[0].groups[0].facts}=={'自制出现序号0','自制出现序号1'}
