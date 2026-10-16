"""Synthetic source-faithfulness cases, not medical gold-standard assertions."""
import copy
import json
import pytest
from medicine_agent.analysis.quality import analysis_violations, quality_view, layout_candidate, UNCOVERED
from medicine_agent.domain.models import EvidenceRecord, SkillInvocation
from medicine_agent.domain.tcm_knowledge import TCMKnowledgeGraph, validate_graph_evidence
from medicine_agent.bootstrap import create_facade


def record(eid='e1', text='自制原话：以此为人之生命的根本。'):
    return {'evidence_id':eid,'source_id':'source','fragment_id':'f'+eid,'raw_text':text,'location':{}}


def payload(records):
    q=[{'evidence_id':r['evidence_id'],'text':r['raw_text']} for r in records]
    return {'semantic_version':'0.3.2','nodes':[{'node_id':'local','source_id':'source',
        'title':'自制命题','statement':'仅为软件自制样例','categories':['tcm_foundation'],'quotes':q,
        'groups':[{'group_id':'main','kind':'theory','facts':[{'field_id':'tcm.theory_proposition_text',
            'value':''.join(r['raw_text'] for r in records),'quotes':q}]}]}]}


@pytest.mark.parametrize('replacement',['自制原话：以此为之生命的根本。','概括后的答案','自制原话:以此为人之生命的根本。'])
def test_raw_proposition_cannot_lose_letters_paraphrase_or_change_punctuation(replacement):
    records=[record()];p=payload(records)
    p['nodes'][0]['groups'][0]['facts'][0]['value']=replacement
    assert analysis_violations(TCMKnowledgeGraph.model_validate(p).model_dump(mode='json'),records)
    # Historical packages retain their old fields/identity; stricter generation
    # checks must not quarantine or rewrite them on read.
    validate_graph_evidence(TCMKnowledgeGraph.model_validate(p),[EvidenceRecord.model_validate(records[0])])


def test_literal_cross_line_join_keeps_reading_order_and_all_source_characters():
    records=[record('e1','自制原话：以此为人'),record('e2','之生命的根本。')]
    p=payload(records);graph=TCMKnowledgeGraph.model_validate(p).model_dump(mode='json')
    assert not analysis_violations(graph,records)
    f=graph['nodes'][0]['groups'][0]['facts'][0]
    f['value']='之生命的根本。自制原话：以此为人'
    assert analysis_violations(graph,records)


def test_cited_work_is_separate_from_school_and_does_not_become_another_source():
    records=[record(text='自制材料引用《示例篇》，观点归于甲。')];p=payload(records)
    facts=p['nodes'][0]['groups'][0]['facts']
    facts.append({'field_id':'tcm.theory_school','value':['《示例篇》'],'state':'stated','quotes':facts[0]['quotes']})
    assert analysis_violations(TCMKnowledgeGraph.model_validate(p).model_dump(mode='json'),records)
    facts[-1]['field_id']='tcm.theory_cited_work'
    g=TCMKnowledgeGraph.model_validate(p).model_dump(mode='json')
    assert not analysis_violations(g,records)
    assert {n['source_id'] for n in g['nodes']}=={'source'}
    facts[-1]['value']='《未读文献》'
    assert analysis_violations(TCMKnowledgeGraph.model_validate(p).model_dump(mode='json'),records)


def test_independent_propositions_are_not_hidden_in_a_large_node():
    records=[record()];p=payload(records)
    g=copy.deepcopy(p['nodes'][0]['groups'][0]);g['group_id']='second'
    p['nodes'][0]['groups'].append(g)
    assert analysis_violations(TCMKnowledgeGraph.model_validate(p).model_dump(mode='json'),records)
    # Supporting material can remain with its owning proposition, without
    # inventing an arbitrary node-count or text-length limit.
    g['about_group_id']='main';g['facts'][0]['field_id']='tcm.theory_source_explanation'
    assert not analysis_violations(TCMKnowledgeGraph.model_validate(p).model_dump(mode='json'),records)


def test_repeated_source_occurrences_are_preserved_instead_of_silently_deduplicated():
    records=[record()];p=payload(records)
    facts=p['nodes'][0]['groups'][0]['facts']
    facts.append(copy.deepcopy(facts[0]))
    graph=TCMKnowledgeGraph.model_validate(p).model_dump(mode='json')
    assert not analysis_violations(graph,records)
    assert len(graph['nodes'][0]['groups'][0]['facts'])==2
    facts[-1]['value']='以此为人之生命的根本。'
    assert analysis_violations(TCMKnowledgeGraph.model_validate(p).model_dump(mode='json'),records)


class SourceModel:
    provider='synthetic';model='source-fixture'
    def __init__(self, fix=True):self.calls=0;self.fix=fix
    def generate_json(self,**kwargs):
        self.calls+=1;r=json.loads(kwargs['user']);r=r['evidence'] if isinstance(r,dict) else r
        p=payload(r[-1:])
        if self.calls==1 or not self.fix:p['nodes'][0]['groups'][0]['facts'][0]['value']='遗漏原话'
        return p


def test_source_faithfulness_repair_is_bounded_and_never_silently_changes_values():
    for fix,status in [(True,'success'),(False,'success')]:
        model=SourceModel(fix)
        result=create_facade(model).invoke_skill(SkillInvocation(task_id='qa',skill_id='tcm-knowledge-analysis',
            input_data={'evidence':[record()]}))
        assert result.status==status and model.calls==2
        fact=result.output['graph']['nodes'][0]['groups'][0]['facts'][0]
        if fix:assert fact['value']==record()['raw_text']
        else:
            assert fact['value'] is None and fact['state']=='ambiguous'
            assert '遗漏原话' in fact['reason']
            assert fact['quotes'][0]['text']==record()['raw_text']
            assert result.output['graph']['nodes'][0]['gaps']


def test_false_source_quotes_cannot_use_the_ambiguous_draft_retention_path():
    class BadSource(SourceModel):
        def generate_json(self,**kwargs):
            p=payload([record()]);p['nodes'][0]['quotes'][0]['text']='不存在的引文'
            return p
    result=create_facade(BadSource()).invoke_skill(SkillInvocation(task_id='invalid-source',skill_id='tcm-knowledge-analysis',
        input_data={'evidence':[record()]}))
    assert result.status=='failure'


def test_context_is_not_repeatedly_reported_as_current_uncovered_evidence():
    class Model(SourceModel):
        def generate_json(self,**kwargs):return payload(json.loads(kwargs['user'])[-1:])
    records=[record('old','旧页原文'),record('current','新页原文')]
    result=create_facade(Model()).invoke_skill(SkillInvocation(task_id='focus',skill_id='tcm-knowledge-analysis',
        input_data={'evidence':records,'focus_evidence_ids':['current']}))
    assert result.status=='success' and not result.output['graph']['gaps']
    invalid=create_facade(Model()).invoke_skill(SkillInvocation(task_id='invalid',skill_id='tcm-knowledge-analysis',
        input_data={'evidence':records,'focus_evidence_ids':['absent']}))
    assert invalid.status=='failure'


def test_quality_view_keeps_every_original_gap_and_distinguishes_layout_and_references():
    records=[record('old','已在其他结果中引用'),record('new','尚未引用正文'),record('header','16 自制教材')]
    records[-1]['location']={'region':[1,1,80,10],'page_size':[100,200],'render_scale':1,'origin':'top-left'}
    p=payload(records[:1]);p['gaps']=[{'reason':UNCOVERED,'quotes':[{'evidence_id':r['evidence_id'],'text':r['raw_text']}]} for r in records]
    graph=TCMKnowledgeGraph.model_validate(p).model_dump(mode='json');before=copy.deepcopy(graph)
    view=quality_view(graph,records,'自制教材')
    assert view['counts']=={'layout_candidate':1,'referenced_elsewhere':1,'uncovered_evidence':1,'model_reported':0}
    assert graph==before
    assert [e['original_gap'] for e in view['entries']]==graph['gaps']
    assert layout_candidate(records[-1],'自制教材')
    assert not layout_candidate(records[1],'自制教材')


def test_owned_legacy_graph_uses_its_recorded_semantic_version_not_new_defaults(tmp_path):
    from medicine_agent.analysis.service import DataAnalysisAgent
    from medicine_agent.domain.owned_analysis import OwnedAnalysisRequest
    from medicine_agent.packages.owned import read_owned_cache, attach_owned_cache
    from medicine_agent.packages.tcm import read_graph, attach_graph
    from medicine_agent.packages.io import validate_package_path
    from test_tcm_knowledge import FixtureModel, TEXT
    source=tmp_path/'source.txt';source.write_text(TEXT,encoding='utf-8')
    agent=DataAnalysisAgent(tmp_path/'work',tmp_path/'packages',FixtureModel())
    task=agent.submit(OwnedAnalysisRequest(paths=[str(source)],owner_id='synthetic',allowed_use='test'))
    done=agent.run(task['task_id']);assert done['status']=='completed'
    package=agent.catalog._path(done['children'][0]['package_path'])
    cache=json.loads((package/'ownership.json').read_text(encoding='utf-8'))
    graph=read_graph(package);before=[n.node_id for n in graph.nodes]
    graph.semantic_version='0.3.0'
    for unit in cache['units']:unit['analysis']['tcm_graph']['semantic_version']='0.3.0'
    attach_graph(package,graph);attach_owned_cache(package,cache)
    assert validate_package_path(package).valid
    assert read_owned_cache(package).units[0].analysis.tcm_graph.semantic_version=='0.3.0'
    assert [n.node_id for n in read_graph(package).nodes]==before


def test_lock_initialization_contention_can_retry_without_leaking_a_raw_error(tmp_path,monkeypatch):
    from pathlib import Path
    from medicine_agent.analysis.library import cache_lock
    original=Path.open;failed=[]
    class ContendedStream:
        def __init__(self,stream):self.stream=stream
        def __enter__(self):return self
        def __exit__(self,*args):self.stream.close()
        def __getattr__(self,name):return getattr(self.stream,name)
        def write(self,value):
            failed.append(True)
            raise PermissionError('simulated concurrent byte lock initialization')
    lock=tmp_path/'shared.lock'
    def open_file(path,*args,**kwargs):
        stream=original(path,*args,**kwargs)
        return ContendedStream(stream) if path==lock and not failed else stream
    monkeypatch.setattr(Path,'open',open_file)
    with cache_lock(lock):assert failed
