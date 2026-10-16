"""Review storage software checks; no medical approvals are generated for real data."""
import copy
import json
import shutil
from datetime import datetime, UTC, timedelta
from pathlib import Path
import subprocess
import sys

import pytest

from medicine_agent.analysis.catalog import PackageCatalog
from medicine_agent.analysis.models import AnalysisError
from medicine_agent.analysis.models import AnalysisRequest
from medicine_agent.analysis.service import DataAnalysisAgent
from medicine_agent.analysis.store import atomic_json, digest
from medicine_agent.bootstrap import create_facade
from medicine_agent.contracts import export_schemas
from medicine_agent.domain.ids import stable_id
from medicine_agent.domain.reviews import ReviewRecord
from medicine_agent.packages.io import validate_package_path
from test_tcm_knowledge import create_medical_package, FixtureModel, TEXT


def request(item, decision='confirmed', **changes):
    return {'target': item['target'], 'reviewer': 'synthetic-user', 'decision': decision,
            'reason': '自制软件测试意见，非医学审核', 'expected_previous_id': item['expected_previous_id'], **changes}


def test_review_queue_has_precise_occurrences_and_original_evidence(tmp_path):
    catalog, _ = create_medical_package(tmp_path, 'book')
    queue = catalog.review_queue('all')
    assert len(queue['items']) == 2
    assert {i['target']['scope'] for i in queue['items']} == {'node', 'fact'}
    assert all(i['quotes'][0]['location']['unit']==1 for i in queue['items'])
    assert all(i['user_review_state']=='unreviewed' for i in queue['items'])
    assert not (catalog.root/'reviews').exists()


def test_correction_is_append_only_and_does_not_change_source_or_medical_status(tmp_path):
    catalog, path = create_medical_package(tmp_path, 'book')
    before = {p.name: p.read_bytes() for p in path.iterdir() if p.is_file()}
    field = catalog.review_queue('fact')['items'][0]
    record = catalog.record_review(request(field, 'needs_revision', proposed_value='自制更正候选'))
    assert catalog.review_queue('fact')['items'][0]['user_review_state']=='needs_revision'
    assert catalog.review_queue('fact')['items'][0]['value']==field['value']
    assert catalog.review_queue('node')['items'][0]['user_review_state']=='unreviewed'
    assert record['request']['proposed_value']=='自制更正候选'
    assert before=={p.name: p.read_bytes() for p in path.iterdir() if p.is_file()}
    assert catalog.reviews()['medical_review']=='unreviewed'
    queried = catalog.query(create_facade(), knowledge_id=field['target']['address']['node_id'])
    assert queried['medical_review']=='unreviewed'
    assert queried['user_reviews'][0]['request']['proposed_value']=='自制更正候选'


def test_compare_and_append_history_preserves_old_decisions(tmp_path):
    catalog, _ = create_medical_package(tmp_path, 'book')
    original = catalog.review_queue()['items'][0]
    first = catalog.record_review(request(original))
    with pytest.raises(AnalysisError, match='history changed'):
        catalog.record_review(request(original, 'rejected'))
    refreshed = catalog.review_queue()['items'][0]
    second = catalog.record_review(request(refreshed, 'needs_revision'))
    assert second['request']['expected_previous_id']==first['review_id']
    assert len(catalog.reviews()['records'])==2
    assert catalog.review_queue()['items'][0]['user_review_state']=='needs_revision'


def test_node_confirmation_does_not_confirm_fields(tmp_path):
    catalog, _ = create_medical_package(tmp_path, 'book')
    catalog.record_review(request(catalog.review_queue()['items'][0]))
    assert catalog.review_queue()['items'][0]['user_review_state']=='confirmed'
    assert catalog.review_queue('fact')['items'][0]['user_review_state']=='unreviewed'


def test_review_migration_unplug_and_restore(tmp_path):
    catalog, path = create_medical_package(tmp_path, 'book')
    catalog.record_review(request(catalog.review_queue()['items'][0], 'needs_revision'))
    moved = tmp_path/'moved'
    shutil.copytree(catalog.root, moved)
    copy_catalog = PackageCatalog(moved)
    assert copy_catalog.review_queue()['items'][0]['user_review_state']=='needs_revision'
    relative = path.relative_to(catalog.root)
    holding = tmp_path/'holding'
    shutil.move(str(moved/relative), holding)
    state = next(iter(copy_catalog.reviews()['states'].values()))
    assert state['resolution']=='REVIEW_TARGET_UNAVAILABLE'
    assert len(copy_catalog.reviews()['records'])==1
    shutil.move(str(holding), moved/relative)
    assert next(iter(copy_catalog.reviews()['states'].values()))['resolution']=='resolved'


def test_invalid_fingerprint_is_rejected_without_creating_review(tmp_path):
    catalog, _ = create_medical_package(tmp_path, 'book')
    item = catalog.review_queue()['items'][0]
    item['target']['fingerprint']='0'*64
    with pytest.raises(AnalysisError, match='fingerprint'):
        catalog.record_review(request(item))
    assert not (catalog.root/'reviews').exists()


def test_tampered_review_is_not_a_final_confirmation_and_source_remains_valid(tmp_path):
    catalog, path = create_medical_package(tmp_path, 'book')
    catalog.record_review(request(catalog.review_queue()['items'][0]))
    record = next((catalog.root/'reviews').glob('*.json'))
    payload = json.loads(record.read_text('utf-8'))
    payload['record']['request']['decision']='rejected'
    atomic_json(record, payload)
    assert catalog.reviews()['errors']
    assert catalog.review_queue()['items'][0]['user_review_state']=='history_invalid'
    assert validate_package_path(path).valid


def test_branching_or_incomplete_history_requires_resolution(tmp_path):
    catalog, _ = create_medical_package(tmp_path, 'book')
    first = catalog.record_review(request(catalog.review_queue()['items'][0]))
    duplicate = ReviewRecord.model_validate(first)
    duplicate.created_at += timedelta(seconds=1)
    duplicate.request.reason='另一分支的自制意见'
    duplicate.review_id=stable_id('review',duplicate.model_dump(mode='json',exclude={'review_id'}))
    value=duplicate.model_dump(mode='json')
    atomic_json(catalog.root/'reviews'/(duplicate.review_id+'.json'),{'record':value,'sha256':digest(value)})
    assert catalog.review_queue()['items'][0]['user_review_state']=='history_invalid'
    with pytest.raises(AnalysisError,match='conflicting'):
        catalog.record_review(request(catalog.review_queue()['items'][0]))


def test_missing_previous_record_does_not_silently_accept_new_head(tmp_path):
    catalog, _ = create_medical_package(tmp_path, 'book')
    first = catalog.record_review(request(catalog.review_queue()['items'][0]))
    catalog.record_review(request(catalog.review_queue()['items'][0], 'needs_revision'))
    shutil.move(str(catalog.root/'reviews'/(first['review_id']+'.json')), tmp_path/'saved-first.json')
    assert catalog.review_queue()['items'][0]['user_review_state']=='history_invalid'


def test_review_schema_snapshot_matches(tmp_path):
    out=tmp_path/'schema'
    export_schemas(create_facade(),out,contract_set='review')
    expected=Path(__file__).parents[1]/'schemas'/'review'
    assert {p.relative_to(out).as_posix():p.read_bytes() for p in out.rglob('*.json')}=={
        p.relative_to(expected).as_posix():p.read_bytes() for p in expected.rglob('*.json')}


def test_cli_export_cannot_overwrite_source_package(tmp_path):
    catalog, path = create_medical_package(tmp_path, 'book')
    before=(path/'tcm.json').read_bytes()
    result=subprocess.run([sys.executable,'-m','medicine_agent.cli','analyze','review-queue',
        '--packages',str(catalog.root),'--output-file',str(path/'tcm.json')],capture_output=True,text=True,encoding='utf-8')
    assert result.returncode==1 and json.loads(result.stdout)['error']['code']=='REVIEW_EXPORT_PATH_INVALID'
    assert (path/'tcm.json').read_bytes()==before


def test_changed_revision_does_not_inherit_old_review(tmp_path):
    catalog, path = create_medical_package(tmp_path, 'book')
    catalog.record_review(request(catalog.review_queue()['items'][0]))
    class RevisedModel(FixtureModel):
        def generate_json(self, **kwargs):
            payload=super().generate_json(**kwargs)
            payload['nodes'][0]['aliases']=['自制新修订的别名']
            return payload
    agent=DataAnalysisAgent(tmp_path/'new-work',catalog.root,RevisedModel())
    task=agent.submit(AnalysisRequest(paths=[str(tmp_path/'book.txt')],allowed_use='synthetic-test',
        parent_package=path.relative_to(catalog.root).as_posix()))
    assert agent.run(task['task_id'])['status']=='completed'
    assert catalog.review_queue()['items'][0]['user_review_state']=='unreviewed'
    assert len(catalog.reviews()['records'])==1


def test_repeated_field_ids_still_have_distinct_review_occurrences(tmp_path):
    class RepeatedModel(FixtureModel):
        def generate_json(self, **kwargs):
            payload=super().generate_json(**kwargs)
            facts=payload['nodes'][0]['groups'][0]['facts']
            facts.append(copy.deepcopy(facts[0]))
            return payload
    source=tmp_path/'same-fields.txt'; source.write_text(TEXT,encoding='utf-8')
    agent=DataAnalysisAgent(tmp_path/'work',tmp_path/'packages',RepeatedModel())
    task=agent.submit(AnalysisRequest(paths=[str(source)],allowed_use='synthetic-test'))
    assert agent.run(task['task_id'])['status']=='completed'
    fields=agent.catalog.review_queue('fact')['items']
    assert len(fields)==2 and fields[0]['target']['fact_index']!=fields[1]['target']['fact_index']
    agent.catalog.record_review(request(fields[0]))
    assert [i['user_review_state'] for i in agent.catalog.review_queue('fact')['items']]==['confirmed','unreviewed']
    assert 'repeated_fields_in_group' in agent.catalog.review_queue()['items'][0]['flags']
