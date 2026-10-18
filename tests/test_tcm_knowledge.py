"""Synthetic software fixtures; these tests do not validate medical truth."""
import json
import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError

from medicine_agent.analysis.models import AnalysisError, AnalysisRequest, PackageClassification
from medicine_agent.analysis.service import DataAnalysisAgent
from medicine_agent.analysis.catalog import PackageCatalog
from medicine_agent.bootstrap import create_facade
from medicine_agent.domain.models import EvidenceRecord, SkillInvocation
from medicine_agent.domain.tcm_knowledge import GroundedFact, TCMKnowledgeGraph, validate_graph_evidence
from medicine_agent.packages.io import validate_package_path
from medicine_agent.analysis.store import atomic_json
from medicine_agent.domain.ids import file_sha256


TEXT = '自制结构测试：甘能缓急。保留原文；这不是医学金标准。'


def graph_payload(records, category='tcm_foundation', kind='theory', field='tcm.theory_proposition_text'):
    record = records[-1]
    quote = {'evidence_id': record['evidence_id'], 'text': record['raw_text']}
    return {'version': '0.1.0', 'semantic_version': '0.3.0', 'nodes': [{
        'node_id': 'local', 'source_id': record['source_id'], 'title': '甘能缓急',
        'statement': record['raw_text'], 'categories': [category], 'quotes': [quote],
        'groups': [{'group_id': 'g1', 'kind': kind, 'facts': [
            {'field_id': field, 'value': record['raw_text'], 'quotes': [quote]}]}]}]}


class FixtureModel:
    provider = 'synthetic-test-only'
    model = 'schema-fixture'

    def generate_json(self, *, system, user, schema):
        assert '唯一语义字典' in system and 'tcm.theory_proposition_text' in system
        assert schema['$defs']['GroundedFact']
        records = json.loads(user)
        return graph_payload(records['evidence'] if isinstance(records, dict) else records)


def create_medical_package(tmp_path, name, text=TEXT, material='textbook'):
    source = tmp_path / (name + '.txt')
    source.write_text(text, encoding='utf-8')
    agent = DataAnalysisAgent(tmp_path / ('work-' + name), tmp_path / 'packages', FixtureModel())
    task = agent.submit(AnalysisRequest(paths=[str(source)], allowed_use='synthetic-software-test',
        classification=PackageClassification(material_types=[material])))
    result = agent.run(task['task_id'])
    assert result['status'] == 'completed', result
    relative = result['children'][0]['package_path']
    return agent.catalog, agent.catalog._path(relative)


@pytest.mark.parametrize('category,kind,field', [
    ('tcm_foundation', 'theory', 'tcm.theory_proposition_text'),
    ('chinese_materia_medica', 'herb', 'tcm.herb_origin_species'),
    ('tcm_pattern_differentiation', 'differentiation', 'tcm.pathomechanism'),
    ('tcm_formula', 'formula', 'tcm.formula_original_composition'),
    ('tcm_clinical_case', 'case', 'tcm.case_history'),
])
def test_all_five_categories_and_theory_without_symptoms(category, kind, field):
    evidence = EvidenceRecord(evidence_id='e1', source_id='s1', fragment_id='f1', raw_text=TEXT, location={'page': 1})
    graph = TCMKnowledgeGraph.model_validate(graph_payload([evidence.model_dump()], category, kind, field))
    validate_graph_evidence(graph, [evidence])
    assert graph.nodes[0].groups[0].facts[0].value == TEXT


def test_multicategory_theory_and_herb_keep_conditional_proposition():
    evidence = EvidenceRecord(evidence_id='e1', source_id='s1', fragment_id='f1', raw_text=TEXT, location={'page': 1})
    payload = graph_payload([evidence.model_dump()])
    payload['nodes'][0]['categories'].append('chinese_materia_medica')
    payload['nodes'][0]['groups'].append({'group_id': 'g2', 'kind': 'herb', 'facts': [
        {'field_id': 'tcm.herb_flavor', 'value': '甘', 'quotes': [{'evidence_id': 'e1', 'text': '甘能缓急'}]}]})
    graph = TCMKnowledgeGraph.model_validate(payload)
    validate_graph_evidence(graph, [evidence])
    assert len(graph.nodes[0].categories) == 2


def test_unknown_missing_inference_and_false_quotes_are_rejected():
    with pytest.raises(ValidationError):
        GroundedFact(field_id='tcm.invented', value='x')
    with pytest.raises(ValidationError):
        GroundedFact(field_id='tcm.herb_toxicity', state='missing', value='无毒', reason='原文未提')
    with pytest.raises(ValidationError):
        GroundedFact(field_id='tcm.herb_toxicity', state='inferred', value='无毒', quotes=[{'evidence_id': 'e1', 'text': TEXT}])
    evidence = EvidenceRecord(evidence_id='e1', source_id='s1', fragment_id='f1', raw_text=TEXT, location={'page': 1})
    payload = graph_payload([evidence.model_dump()])
    payload['nodes'][0]['groups'][0]['facts'][0]['quotes'][0]['text'] = '伪造原文'
    graph = TCMKnowledgeGraph.model_validate(payload)
    with pytest.raises(ValueError, match='original evidence'):
        validate_graph_evidence(graph, [evidence])
    payload = graph_payload([evidence.model_dump()])
    payload['nodes'][0]['source_id'] = 'other-source'
    with pytest.raises(ValueError, match='another source'):
        validate_graph_evidence(TCMKnowledgeGraph.model_validate(payload), [evidence])


def test_dose_conversion_and_outcome_context_are_required():
    from medicine_agent.domain.tcm_knowledge import MedicalRecordGroup
    quote = [{'evidence_id': 'e1', 'text': TEXT}]
    with pytest.raises(ValidationError, match='conversion basis'):
        MedicalRecordGroup(group_id='d1', kind='dose', facts=[
            GroundedFact(field_id='tcm.dose_normalized_amount', value=3, quotes=quote)])
    with pytest.raises(ValidationError, match='evidence context'):
        MedicalRecordGroup(group_id='o1', kind='outcome', facts=[
            GroundedFact(field_id='tcm.outcome_endpoint', value='改善', quotes=quote)])
    group = MedicalRecordGroup(group_id='o1', kind='outcome', facts=[
        GroundedFact(field_id='tcm.outcome_outcome_kind', value='source_claim', quotes=quote),
        GroundedFact(field_id='tcm.outcome_evidence_context', value='single_case', quotes=quote),
        GroundedFact(field_id='tcm.outcome_denominator', state='missing', reason='未提供')])
    assert group.facts[-1].value is None


def test_model_skill_rejects_bad_output_and_preserves_unanalysed_evidence():
    class BadModel(FixtureModel):
        def generate_json(self, **kwargs):
            payload = super().generate_json(**kwargs)
            payload['nodes'][0]['quotes'][0]['text'] = '不存在'
            return payload
    e = EvidenceRecord(evidence_id='e1', source_id='s1', fragment_id='f1', raw_text=TEXT, location={'page': 1})
    result = create_facade(BadModel()).invoke_skill(SkillInvocation(task_id='bad-model',
        skill_id='tcm-knowledge-analysis', input_data={'evidence': [e.model_dump()]}))
    assert result.status == 'failure' and result.issues[0].code == 'OUTPUT_SCHEMA_INVALID'
    second = e.model_copy(update={'evidence_id': 'e2'})
    result = create_facade(FixtureModel()).invoke_skill(SkillInvocation(task_id='coverage',
        skill_id='tcm-knowledge-analysis', input_data={'evidence': [e.model_dump(), second.model_dump()]}))
    assert result.status == 'success'
    assert result.output['graph']['gaps'][0]['quotes'][0]['evidence_id'] == 'e1'


def test_source_nodes_links_unplug_restore_and_move_without_workspace(tmp_path):
    catalog, first = create_medical_package(tmp_path, 'book')
    _, second = create_medical_package(tmp_path, 'paper', TEXT + '论文样本。', 'paper')
    response = catalog.query(create_facade(), text='甘能缓急', knowledge_category='tcm_foundation')
    assert len(response['packages']) == 2
    a, b = response['packages']
    source = {'package_id': a['package']['package_id'], 'node_id': a['medical_nodes'][0]['node_id']}
    target = {'package_id': b['package']['package_id'], 'node_id': b['medical_nodes'][0]['node_id']}
    before = {p: {f.name: f.read_bytes() for f in p.iterdir() if f.is_file()} for p in (first, second)}
    edge = catalog.associate(source, target, 'same_definition', '自制测试：仅建立候选对应，分别保留原文')
    assert edge['status'] == 'candidate'
    for p in (first, second):
        assert before[p] == {f.name: f.read_bytes() for f in p.iterdir() if f.is_file()}
    result = catalog.query(create_facade(), knowledge_id=source['node_id'])
    assert len(result['related_nodes']) == 1
    assert result['related_nodes'][0]['evidence'][0]['raw_text']
    assert result['material_type_union'] == ['paper', 'textbook']
    holding = tmp_path / 'unplugged'
    shutil.move(str(second), holding)
    assert catalog.associations()['associations'][0]['resolution'] == 'target_unavailable'
    assert len(catalog.scan()) == 1
    shutil.move(str(holding), second)
    assert catalog.associations()['associations'][0]['resolution'] == 'resolved'
    destination = tmp_path / 'another-computer'
    shutil.copytree(catalog.root, destination)
    # All product inputs and task workspaces can disappear; only the package root remains.
    moved = PackageCatalog(destination)
    result = moved.query(create_facade(), knowledge_id=source['node_id'])
    assert result['associations'][0]['resolution'] == 'resolved'
    assert len(result['related_nodes']) == 1
    assert result['related_nodes'][0]['address'] == target
    assert all(validate_package_path(moved._path(item['path'])).valid for item in moved.scan())


def test_unknown_extension_or_ungrounded_fact_quarantines_package(tmp_path):
    catalog, path = create_medical_package(tmp_path, 'book')
    extensions = path / 'extensions.json'
    atomic_json(extensions, {'tcm-knowledge': '99.0.0'})
    manifest = json.loads((path / 'manifest.json').read_text('utf-8'))
    manifest['files']['extensions.json'] = file_sha256(extensions.read_bytes())
    atomic_json(path / 'manifest.json', manifest)
    assert not validate_package_path(path).valid
    assert catalog.scan()[0]['state'] == 'quarantined'


def test_legacy_tcm_extension_remains_readable_without_reextracting_source(tmp_path):
    catalog,path=create_medical_package(tmp_path,'legacy')
    graph=json.loads((path/'tcm.json').read_text('utf-8'))
    graph.pop('rejected_candidates',None)
    atomic_json(path/'tcm.json',graph)
    atomic_json(path/'extensions.json',{'tcm-knowledge':'0.1.0'})
    manifest=json.loads((path/'manifest.json').read_text('utf-8'))
    for name in ('tcm.json','extensions.json'):
        manifest['files'][name]=file_sha256((path/name).read_bytes())
    atomic_json(path/'manifest.json',manifest)
    atomic_json(path/'checksums.json',manifest['files'])
    assert validate_package_path(path).valid
    assert catalog.query(create_facade(),text='甘能缓急')['packages']


def test_corrupt_link_is_reported_and_does_not_damage_source_packages(tmp_path):
    catalog, first = create_medical_package(tmp_path, 'book')
    (catalog.root / 'links').mkdir()
    (catalog.root / 'links' / 'broken.json').write_text('{broken', encoding='utf-8')
    assert catalog.associations()['errors'][0]['code'] == 'ASSOCIATION_INVALID'
    assert validate_package_path(first).valid


def test_exported_guide_and_schemas_match_the_only_registry(tmp_path):
    from medicine_agent.semantics.guide import export_tcm_field_guide
    from medicine_agent.contracts import export_schemas
    from medicine_agent.semantics import load_semantic_registry
    guide = tmp_path / 'guide.md'
    result = export_tcm_field_guide(guide)
    assert result['group_fields'] == 111
    assert guide.read_bytes() == (Path(__file__).parents[1] / 'md' / '中医字段说明书.generated.md').read_bytes()
    text = guide.read_text('utf-8')
    for field in load_semantic_registry().fields:
        if any(x.startswith('tcm_group:') for x in field.allowed_on):
            assert field.field_id in text and field.label_zh in text
    out = tmp_path / 'schemas'
    export_schemas(create_facade(), out, contract_set='tcm')
    expected = Path(__file__).parents[1] / 'schemas' / 'tcm'
    assert {p.relative_to(out).as_posix(): p.read_bytes() for p in out.rglob('*.json')} == {
        p.relative_to(expected).as_posix(): p.read_bytes() for p in expected.rglob('*.json')}


def test_cyclic_group_ownership_is_rejected():
    evidence = EvidenceRecord(evidence_id='e1', source_id='s1', fragment_id='f1', raw_text=TEXT, location={})
    payload = graph_payload([evidence.model_dump()])
    payload['nodes'][0]['groups'][0]['about_group_id'] = 'g1'
    with pytest.raises(ValidationError, match='Cyclic'):
        TCMKnowledgeGraph.model_validate(payload)


def test_schema_repair_is_bounded_and_preserves_missing_semantics():
    class RepairModel(FixtureModel):
        calls = 0
        def generate_json(self, **kwargs):
            self.calls += 1
            payload = super().generate_json(**kwargs)
            if self.calls == 1:
                fact = payload['nodes'][0]['groups'][0]['facts'][0]
                fact.update(state='ambiguous', reason='跨页截断，首次错误地保留了值')
            else:
                assert json.loads(kwargs['user'])['validation_errors']
            return payload
    e=EvidenceRecord(evidence_id='e1',source_id='s1',fragment_id='f1',raw_text=TEXT,location={})
    model=RepairModel()
    result=create_facade(model).invoke_skill(SkillInvocation(task_id='repair',skill_id='tcm-knowledge-analysis',
        input_data={'evidence':[e.model_dump()]}))
    assert result.status=='success' and model.calls==2


def test_explicit_analysis_upgrade_reuses_only_unanalyzed_verified_extraction(tmp_path):
    source=tmp_path/'text.txt'
    source.write_text(TEXT,encoding='utf-8')
    agent=DataAnalysisAgent(tmp_path/'work',tmp_path/'packages',FixtureModel())
    task=agent.submit(AnalysisRequest(paths=[str(source)],allowed_use='synthetic-software-test'))
    child=task['children'][0]['task_id']
    agent.run(task['task_id'],stop_after_extraction=True)
    before=agent.store.rows(child)[0]['extraction_hash']
    data=json.loads(agent.store.get(child)['request'])
    data['runtime'].pop('analysis_policy')
    agent.store.update(child,request=json.dumps(data))
    assert agent.upgrade_unanalyzed_task(child)['extracted']==1
    assert agent.store.rows(child)[0]['extraction_hash']==before
    assert agent.run(task['task_id'])['status']=='completed'
    assert len([c for c in agent.store.calls(child) if c.get('skill_id')=='document-extraction'])==1
    with pytest.raises(AnalysisError,match='unanalyzed'):
        agent.upgrade_unanalyzed_task(child)


def test_field_level_quotes_count_as_coverage_without_removing_model_gaps():
    class FieldCoverageModel(FixtureModel):
        def generate_json(self, **kwargs):
            records=json.loads(kwargs['user'])
            payload=graph_payload(records)
            payload['nodes'][0]['quotes']=[{'evidence_id':records[0]['evidence_id'],'text':records[0]['raw_text']}]
            return payload
    e=EvidenceRecord(evidence_id='e1',source_id='s1',fragment_id='f1',raw_text=TEXT,location={})
    second=e.model_copy(update={'evidence_id':'e2'})
    result=create_facade(FieldCoverageModel()).invoke_skill(SkillInvocation(task_id='field-coverage',
        skill_id='tcm-knowledge-analysis',input_data={'evidence':[e.model_dump(),second.model_dump()]}))
    assert result.status=='success' and result.output['graph']['gaps']==[]


def test_one_invalid_field_is_quarantined_without_losing_valid_siblings():
    class MixedFieldModel(FixtureModel):
        def generate_json(self, **kwargs):
            payload=super().generate_json(**kwargs)
            quote=payload['nodes'][0]['quotes'][0]
            payload['nodes'][0]['groups'][0]['facts'].append({
                'field_id':'tcm.unknown_from_model','value':'不应进入事实层','quotes':[quote]})
            return payload
    e=EvidenceRecord(evidence_id='e1',source_id='s1',fragment_id='f1',raw_text=TEXT,location={})
    result=create_facade(MixedFieldModel()).invoke_skill(SkillInvocation(task_id='partial-field',
        skill_id='tcm-knowledge-analysis',input_data={'evidence':[e.model_dump()]}))
    assert result.status=='success'
    graph=result.output['graph']
    assert graph['nodes'][0]['groups'][0]['facts'][0]['field_id']=='tcm.theory_proposition_text'
    assert all(f['field_id']!='tcm.unknown_from_model' for g in graph['nodes'][0]['groups'] for f in g['facts'])
    rejected=graph['rejected_candidates']
    assert rejected[0]['code']=='FIELD_REJECTED'
    assert rejected[0]['path']=='nodes.0.groups.0.facts.1'
    assert rejected[0]['raw_candidate']['value']=='不应进入事实层'
    assert rejected[0]['evidence_ids']==['e1']


def test_rejected_candidates_are_preserved_in_final_package(tmp_path):
    class MixedFieldModel(FixtureModel):
        def generate_json(self, **kwargs):
            payload=super().generate_json(**kwargs)
            quote=payload['nodes'][0]['quotes'][0]
            payload['nodes'][0]['groups'][0]['facts'].append({
                'field_id':'tcm.unknown_from_model','value':'隔离审计值','quotes':[quote]})
            return payload
    source=tmp_path/'mixed.txt'
    source.write_text(TEXT,encoding='utf-8')
    agent=DataAnalysisAgent(tmp_path/'work-mixed',tmp_path/'packages',MixedFieldModel())
    task=agent.submit(AnalysisRequest(paths=[str(source)],allowed_use='synthetic-software-test'))
    result=agent.run(task['task_id'])
    assert result['status']=='completed',result
    package=agent.catalog._path(result['children'][0]['package_path'])
    graph=json.loads((package/'tcm.json').read_text('utf-8'))
    assert graph['rejected_candidates'][0]['raw_candidate']['value']=='隔离审计值'
    assert validate_package_path(package).valid


def test_multidimensional_facets_and_bounded_local_graph_are_derived_from_old_shape(tmp_path):
    catalog, first=create_medical_package(tmp_path,'book',material='textbook')
    _, second=create_medical_package(tmp_path,'paper',TEXT+' 第二来源。',material='paper')
    initial=catalog.query(create_facade(),text='甘能缓急',knowledge_type='theory',evidence_state='stated')
    assert len(initial['packages'])==2
    for package in initial['packages']:
        facets=package['medical_nodes'][0]['retrieval_facets']
        assert 'theory' in facets['knowledge_types']
        assert 'stated' in facets['evidence_states']
        assert facets['source_types'] in (['textbook'],['paper'])
    addresses=[{'package_id':p['package']['package_id'],'node_id':p['medical_nodes'][0]['node_id']}
               for p in initial['packages']]
    catalog.associate(addresses[0],addresses[1],'related','自制局部图边界检查')
    stopped=catalog.query(create_facade(),seed_addresses=[addresses[0]],max_hops=0,max_nodes=10)
    assert len(stopped['local_graph']['nodes'])==1
    assert stopped['local_graph']['audit']['truncated'] is True
    expanded=catalog.query(create_facade(),seed_addresses=[addresses[0]],max_hops=1,max_nodes=10)
    assert len(expanded['local_graph']['nodes'])==2
    assert len(expanded['local_graph']['edges'])==1
    assert expanded['local_graph']['audit']['requested_max_hops']==1
    bounded=catalog.query(create_facade(),seed_addresses=addresses,max_hops=1,max_nodes=1)
    assert len(bounded['local_graph']['nodes'])==1
    assert bounded['local_graph']['audit']['truncated'] is True
    missing=catalog.query(create_facade(),seed_addresses=[{'package_id':'missing','node_id':'missing'}])
    assert missing['local_graph']['nodes']==[]
    assert missing['local_graph']['audit']['missing_seed_addresses'][0]['package_id']=='missing'
    no_match=catalog.query(create_facade(),text='甘能缓急',knowledge_type='formula')
    assert no_match['packages']==[] and no_match['local_graph']['nodes']==[]


def test_lexical_concept_candidate_is_auditable_and_never_auto_merged(tmp_path):
    class NamedModel(FixtureModel):
        def __init__(self,title,topics):self.title,self.topics=title,topics
        def generate_json(self,**kwargs):
            payload=super().generate_json(**kwargs)
            payload['nodes'][0]['title']=self.title
            payload['nodes'][0]['topics']=self.topics
            return payload
    def make(name,title,text,topics):
        source=tmp_path/(name+'.txt');source.write_text(text,encoding='utf-8')
        agent=DataAnalysisAgent(tmp_path/('work-'+name),tmp_path/'packages',NamedModel(title,topics))
        task=agent.submit(AnalysisRequest(paths=[str(source)],allowed_use='synthetic-software-test'))
        assert agent.run(task['task_id'])['status']=='completed'
        return agent.catalog
    catalog=make('a','气的运动变化',TEXT,['气化'])
    make('b','气的运动与变化',TEXT+' 第二来源。',['气化'])
    make('c','气温升高',TEXT+' 无关反例。',['天气'])
    result=catalog.query(create_facade(),text='气的运动变化')
    assert result['associations']==[]
    candidates=result['concept_link_candidates']
    assert len(candidates)==1
    assert candidates[0]['candidate_type'] in {'topic_and_lexical','lexical_overlap'}
    assert candidates[0]['status']=='candidate' and '不能' in candidates[0]['rationale']
