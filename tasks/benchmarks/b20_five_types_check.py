"""Internal five-type minimal software loop; never a clinical gold standard."""
import argparse
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
import runpy
import sys

ROOT=Path(__file__).resolve().parents[2]
PRIOR=ROOT/'tasks/benchmarks/b19_library_check.py'
assert hashlib.sha256(PRIOR.read_bytes()).hexdigest()=='0cd549f6b9a775216ff95d22d16c4ce99138125b6a03adde795669cd96c3f092'
COMMON=runpy.run_path(str(PRIOR))
CASES=(('tcm_foundation','theory','tcm.theory_proposition_text'),
       ('chinese_materia_medica','herb','tcm.herb_origin_species'),
       ('tcm_pattern_differentiation','differentiation','tcm.pathomechanism'),
       ('tcm_formula','formula','tcm.formula_original_composition'),
       ('tcm_clinical_case','case','tcm.case_history'))
TOKEN='FIVETYPE_SOFTWARE_ONLY'


class FiveModel(COMMON['SyntheticModel']):
    model='b20-frozen-five-types'
    def __init__(self,case):
        super().__init__(); self.case=case
    def generate_json(self,**kwargs):
        payload=super().generate_json(**kwargs)
        category,kind,field=self.case
        node=payload['nodes'][0]
        node['categories']=[category]
        node['groups'][0]['kind']=kind
        node['groups'][0]['facts'][0]['field_id']=field
        return payload


def run(output,smoke):
    from medicine_agent.domain.models import EvidenceRecord
    from medicine_agent.domain.tcm_knowledge import TCMKnowledgeGraph,validate_graph_evidence
    from medicine_agent.analysis.file_learning import FileLearningService
    from medicine_agent.analysis.library import PackageLibrary
    from medicine_agent.analysis.review_preparation import ReviewPreparationService
    from medicine_agent.analysis.review_sessions import ReviewSessionService
    from medicine_agent.analysis.review_progress import ReviewProgressService
    from medicine_agent.packages.tcm import read_graph
    from medicine_agent.domain.ids import content_hash
    from medicine_agent.bootstrap import create_facade
    def no_network(event,args):
        if event in ('socket.connect','socket.getaddrinfo'): raise RuntimeError('NETWORK_FORBIDDEN')
    sys.addaudithook(no_network)
    base=(ROOT/'artifacts/b20-d01').resolve(); output=output.resolve()
    assert base.is_relative_to(ROOT) and output.is_relative_to(base) and output!=base
    output.mkdir(parents=True,exist_ok=False)
    save=lambda name,value:(output/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    sha=COMMON['sha']; protected=COMMON['PROTECTED']
    before=protected(); save('protected-before.json',before)
    save('environment.json',dict(python=sys.version,os=platform.platform(),pydantic=version('pydantic'),
        source_sha256=sha(Path(__file__)),scope='minimal one-field software samples, not medical correctness'))
    records=[]; contracts=[]; checks=[]; failure=None
    selected=(CASES[0],CASES[-1]) if smoke else CASES
    try:
        # Reuse the current registry-backed type validators; no new dictionary.
        for case in CASES:
            evidence=EvidenceRecord(evidence_id='self-evidence',source_id='self-source',fragment_id='self-fragment',
                raw_text=TOKEN+' '+case[0],location={'unit':1})
            payload=FiveModel(case).generate_json(system='',user=json.dumps([evidence.model_dump(mode='json')]),schema={})
            graph=TCMKnowledgeGraph.model_validate(payload)
            validate_graph_evidence(graph,[evidence])
            assert graph.nodes[0].groups[0].facts[0].field_id==case[2]
            contracts.append(dict(category=case[0],group=case[1],field=case[2],status='passed'))
        save('contract-checks.json',contracts)
        (output/'inputs').mkdir()
        for i,case in enumerate(selected):
            category,kind,field=case
            source=output/'inputs'/f'{category}.txt'
            source.write_text(f'{TOKEN} {category}; self authored software data, not a medical assertion.\n',encoding='utf-8')
            model=FiveModel(case)
            learning=FileLearningService(output/'generation'/category,output/'knowledge',model)
            task=learning.submit(dict(paths=[str(source)],owner_id='synthetic-author',allowed_use='self-authored-software-test',
                classification=dict(knowledge_categories=[category])))
            result=learning.run(task['task_id'])
            assert result['status']=='completed' and model.calls==1
            archive=output/'knowledge'/result['package_path']
            representation,bundle=learning.library.load(archive)
            assert len(bundle.components)==1
            component=bundle.components[0]; graph=read_graph(representation/component.path)
            assert len(graph.nodes)==1
            node=graph.nodes[0]
            assert node.categories==[category] and len(node.groups)==1 and node.groups[0].kind==kind
            assert len(node.groups[0].facts)==1 and node.groups[0].facts[0].field_id==field
            assert node.groups[0].facts[0].state=='stated' and node.statement==source.read_text('utf-8').strip()
            source_records=[json.loads(line) for line in (representation/component.path/'sources.jsonl').read_text('utf-8').splitlines()]
            assert len(source_records)==1 and source_records[0]['sha256']==sha(source)
            assert node.source_id==source_records[0]['source_id'] and node.review_status=='unreviewed'
            records.append(dict(index=i,category=category,group=kind,field=field,filename=archive.name,
                archive_sha256=sha(archive),bundle_id=bundle.bundle_id,component_id=component.package_id,
                node_id=node.node_id,node_sha256=content_hash(node.model_dump(mode='json')),
                source_id=node.source_id,source_sha256=sha(source),owner_id='synthetic-author'))
        save('corpus.json',records)
        size=len(selected)
        assert len({r['source_sha256'] for r in records})==size
        library=PackageLibrary(output/'knowledge',output/'query-cache')
        facade=create_facade()
        joint=COMMON['validate_query'](library,facade,records,set(range(size)),text=TOKEN)
        checks.append(dict(check='joint-query',status='passed',matched_nodes=joint['matched_nodes']))
        public_before=COMMON['files'](output/'knowledge')
        for record in records:
            response=library.query(facade,text=TOKEN,knowledge_category=record['category'],max_hops=0,max_nodes=50)
            matches=[(p['package']['package_id'],n) for p in response['packages'] for n in p['medical_nodes']]
            assert len(matches)==1
            pid,node=matches[0]
            assert (pid,node['node_id'])==(record['component_id'],record['node_id'])
            assert node['categories']==[record['category']] and node['groups'][0]['kind']==record['group']
            assert node['groups'][0]['facts'][0]['field_id']==record['field']
            assert content_hash({k:v for k,v in node.items() if k!='retrieval_facets'})==record['node_sha256']
            assert response['medical_review']=='unreviewed' and not response['consultation_available']
            checks.append(dict(check='category-query',category=record['category'],matched_nodes=1,status='passed'))
        preparation=ReviewPreparationService(output/'knowledge',output/'prepare-cache')
        report=preparation.prepare()
        assert report.status=='complete' and not report.issues and not report.review_records
        assert (report.counts['source_evidence'],report.counts['nodes'],report.counts['facts'],report.counts['candidate_targets'],
                report.counts['gaps'],report.counts['rejected_candidates'])==(size,size,size,2*size,0,0)
        assert report.medical_review=='unreviewed' and not report.release_allowed
        assert all(item.worksheet.model_dump()==dict(reviewer=None,decision=None,reason=None,submitted=False)
                   for item in (*report.sources,*report.candidates,*report.anomalies))
        candidate_keys={(item.target.address.package_id,item.target.address.node_id,item.target.scope) for item in report.candidates}
        assert candidate_keys=={(r['component_id'],r['node_id'],scope) for r in records for scope in ('node','fact')}
        save('preparation-summary.json',dict(counts=report.counts,preparation_id=report.preparation_id,
            medical_review=report.medical_review,release_allowed=report.release_allowed,review_records=0))
        checks.append(dict(check='blank-review-preparation',status='passed',targets=3*size))
        preparation.export(output/'preparation')
        ReviewSessionService(output/'knowledge',output/'session-cache').create(output/'preparation',output/'session')
        progress=ReviewProgressService(output/'knowledge',output/'progress-cache').report(output/'session')
        assert progress.target_count==3*size and progress.reviewer_count==0 and not progress.event_ids
        assert {r.scope:r.total for r in progress.coverage}==dict(source_annotation=size,candidate_node=size,candidate_fact=size,anomaly=0)
        assert all(r.pending==r.total for r in progress.coverage)
        assert not progress.release_allowed and not progress.training_allowed and progress.medical_gate=='blocked'
        save('blank-progress.json',progress.model_dump(mode='json'))
        checks.append(dict(check='verified-blank-session',status='passed',targets=3*size,opinions=0))
        assert COMMON['files'](output/'knowledge')==public_before
        assert all(sha(output/'knowledge'/r['filename'])==r['archive_sha256'] for r in records)
        save('checks.json',checks)
    except Exception as exc:
        failure=dict(exception_type=type(exc).__name__,code=getattr(exc,'code','FIVE_TYPE_CHECK_FAILED'))
        save('partial-checks.json',checks)
    after=protected(); save('protected-after.json',after)
    success=not failure and before==after
    save('summary.json',dict(status='executed_pending_review' if success else 'failed',smoke=smoke,
        contract_rows=len(contracts),produced_categories=[r['category'] for r in records],completed_checks=len(checks),
        failure=failure,protected_unchanged=before==after,
        not_checked=['medical truth','CanonicalCase/visit timeline','formula efficacy/dose/safety',
                     'herb identification/clinical use','real material coverage','license','cross-platform']))
    print(json.dumps(dict(output=str(output),failure=failure,contract_rows=len(contracts),produced_types=len(records),
                         completed_checks=len(checks),protected_unchanged=before==after)))
    return 0 if success else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True); parser.add_argument('--smoke',action='store_true')
    args=parser.parse_args()
    raise SystemExit(run(args.output,args.smoke))


if __name__=='__main__': main()
