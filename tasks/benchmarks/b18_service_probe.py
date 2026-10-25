"""B18-D02 internal experiment. Production APIs build and validate fixtures."""
import argparse
from collections import Counter
import hashlib
from importlib.metadata import version
import json
import math
import os
from pathlib import Path
import runpy
import platform
import shutil
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
D01 = ROOT/'tasks/benchmarks/b18_progress_probe.py'
assert hashlib.sha256(D01.read_bytes()).hexdigest() == 'baa8a61ffbc5151bb9e97bdd14fc02fef2bd88da88504383d7d96b90168e729c'
COMMON = runpy.run_path(str(D01))
CASES = {'u2-r0-h1':(2,0,1), 'u2-r2-h1':(2,2,1), 'u10-r2-h1':(10,2,1),
         'u40-r2-h1':(40,2,1), 'u10-r10-h1':(10,10,1),
         'u10-r2-h5':(10,2,5), 'u10-r10-h3':(10,10,3)}
SCOPES = ('source_annotation','candidate_node','candidate_fact','anomaly')


def save(path,value):
    path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')


def hashes(root):
    return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for folder in ('packages','session','preparation') for p in sorted((root/folder).rglob('*')) if p.is_file()}


def target_scope(target):
    return 'candidate_'+target.review_target.scope if target.kind=='candidate' else target.kind


def decision(index,reviewer):
    return ('accept' if index%5==1 else ('accept' if reviewer%2==0 else 'reject') if index%5==2
            else 'unable_to_judge' if index%5==3 else ('accept' if reviewer==0 else 'unable_to_judge'))


def build_fixture(root,case):
    import pytest
    from medicine_agent.analysis import service as analysis
    from medicine_agent.skills.document_extraction import handler
    from medicine_agent.analysis.models import DocumentUnit,DocumentBlock,DocumentPosition
    from medicine_agent.analysis.file_learning import FileLearningService
    from medicine_agent.analysis.review_preparation import ReviewPreparationService
    from medicine_agent.analysis.review_sessions import ReviewSessionService
    from medicine_agent.domain.ids import stable_id
    sys.path.insert(0,str(ROOT/'tests'))
    from test_review_preparation import PreparationModel
    units,reviewers,rounds=CASES[case]
    root.mkdir(parents=True,exist_ok=False)
    source=root/'self-authored-adapter-input.txt'
    source.write_text('Self authored fixture bytes; no real PDF or clinical source.\n',encoding='utf-8')
    started=time.perf_counter_ns()
    def extract(path,unit,force_ocr,timeout):
        return DocumentUnit(index=unit,method='synthetic-adapter',blocks=[DocumentBlock(
            text=f'Self authored {label} unit {unit}.',position=DocumentPosition(unit=unit,page=unit),confidence=.85)
            for label in ('unreferenced','gap','context','statement')])
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(analysis,'inspect_document',lambda path:('pdf',units))
        patch.setattr(handler,'extract_unit',extract)
        learning=FileLearningService(root/'build/learning',root/'packages',PreparationModel())
        request=learning.submit(dict(paths=[str(source)],units=list(range(1,units+1)),allowed_use='synthetic-software-only'))
        built=learning.run(request['task_id'])
        assert built['status']=='completed'
    # Patches are now removed. All preparation/session/source/history validators
    # and public submissions below are unmodified production implementations.
    preparation=ReviewPreparationService(root/'packages',root/'build/export-cache')
    prepared=preparation.prepare()
    assert prepared.status=='complete' and not prepared.issues
    assert (prepared.counts['source_evidence'],prepared.counts['nodes'],prepared.counts['facts'],
            prepared.counts['gaps']+prepared.counts['rejected_candidates'])==(4*units,units,2*units,5*units)
    preparation.export(root/'preparation')
    sessions=ReviewSessionService(root/'packages',root/'build/session-cache')
    manifest=sessions.create(root/'preparation',root/'session')
    view=sessions.inspect(root/'session')
    targets=sorted([row.target for row in view.targets],key=lambda t:(t.kind,t.material_id))
    assert len(targets)==12*units
    active=[(i,t) for i,t in enumerate(targets) if i%5]
    assert len(active)<=1000
    previous={}
    for round_index in range(rounds if reviewers else 0):
        for reviewer in range(reviewers):
            opinions=[]
            for i,target in active:
                choice=decision(i,reviewer) if round_index==rounds-1 else ('accept' if round_index%2==0 else 'reject')
                opinions.append(dict(target=target.model_dump(mode='json'),decision=choice,
                    reason='SELF_AUTHORED_SOFTWARE_ONLY',expected_previous_id=previous.get((reviewer,i))))
            event=sessions.submit(root/'session',dict(version='0.1.0',session_id=manifest.session_id,
                submission_id=f'synthetic-round-{round_index}-r{reviewer}',
                reviewer=dict(reviewer_id=f'r{reviewer:03}',display_name='Synthetic',declared_role='software test'),opinions=opinions))
            for offset,(i,_) in enumerate(active):
                previous[(reviewer,i)]=stable_id('sessionopinion',{'event_id':event.event_id,'opinion_index':offset})
    verified=sessions.inspect(root/'session')
    assert verified.writable and not verified.issues
    meta=dict(case=case,units=units,reviewers=reviewers,rounds=rounds,targets=len(targets),
        events=reviewers*rounds,opinions=len(active)*reviewers*rounds,active_targets=len(active),
        scopes=[target_scope(t) for t in targets],target_keys=[(t.kind,t.material_id) for t in targets],
        build_wall_ns=time.perf_counter_ns()-started,
        fixture_identity=manifest.session_id,files=hashes(root))
    assert len(verified.opinions)==meta['opinions']
    assert len(list((root/'session/events').glob('*.json')))==meta['events']
    save(root/'fixture.json',meta)
    return meta


def check(result,meta,operation):
    r=meta['reviewers']
    if operation=='inspect':
        assert result.writable and not result.issues and len(result.targets)==meta['targets']
        assert len(result.opinions)==meta['opinions'] and not result.release_allowed
        assert result.medical_review=='unreviewed' and not any(t.history_invalid for t in result.targets)
        assert sum(len(t.latest_opinion_ids) for t in result.targets)==meta['active_targets']*r
        indices={tuple(key):i for i,key in enumerate(meta['target_keys'])}
        for row in result.targets:
            i=indices[(row.target.kind,row.target.material_id)]
            state=('pending' if not r or i%5 in (0,3) else 'agreement' if i%5==1
                   else 'disagreement' if i%5==2 else 'insufficient_opinions')
            assert row.agreement_state==state
            assert len(row.latest_opinion_ids)==(r if i%5 else 0)
            assert row.unable_to_judge_count==(r if i%5==3 else r-1 if i%5==4 and r else 0)
        return
    assert result.metrics_available and result.reviewer_count==r and result.target_count==meta['targets']
    assert len(result.event_ids)==meta['events'] and result.medical_gate=='blocked'
    assert not result.release_allowed and not result.training_allowed and not result.phase02_complete
    assert not result.declared_agreement_complete and not result.diagnostic_codes
    counts={scope:Counter(i%5 for i,s in enumerate(meta['scopes']) if s==scope) for scope in SCOPES}
    for row in result.coverage:
        b=counts[row.scope]; n=sum(b.values())
        expected=(n,b[0]+b[3],b[4],b[1],b[2],b[3]*r+b[4]*(r-1)) if r else (n,n,0,0,0,0)
        assert (row.total,row.pending,row.insufficient_opinions,row.agreement,row.disagreement,row.unable_votes)==expected
    assert len(result.reviewers)==4*r and len(result.pairwise)==4*math.comb(r,2)
    for row in result.reviewers:
        b=counts[row.scope]; total=sum(b.values())-b[0]
        decisive=b[1]+b[2]+(b[4] if row.reviewer_id=='r000' else 0)
        assert (row.targets,row.decisive,row.unable)==(total,decisive,total-decisive)
    for row in result.pairwise:
        b=counts[row.scope]; comparable=b[1]+b[2]
        matched=b[1]+(b[2] if int(row.reviewer_a[1:])%2==int(row.reviewer_b[1:])%2 else 0)
        assert (row.overlap,row.comparable,row.matched,row.conflicting,row.unable,row.agreement_fraction)==(
            sum(b.values())-b[0],comparable,matched,comparable-matched,b[3]+b[4],matched/comparable if comparable else None)


def worker(fixture,workspace,operation,mode):
    from medicine_agent.analysis.review_progress import ReviewProgressService
    from medicine_agent.domain.ids import content_hash
    def deny_network(event,args):
        if event in ('socket.connect','socket.getaddrinfo'): raise RuntimeError('NETWORK_FORBIDDEN')
    sys.addaudithook(deny_network)
    meta=json.loads((fixture/'fixture.json').read_text('utf-8'))
    assert hashes(fixture)==meta['files'] and not workspace.exists()
    service=ReviewProgressService(fixture/'packages',workspace)
    call=service.report if operation=='report' else service.sessions.inspect
    initial_identity=None
    if mode=='reused':
        initial=call(fixture/'session')
        check(initial,meta,operation)
        initial_identity=content_hash(initial.model_dump(mode='json'))
        del initial
    peak_before=COMMON['peak_working_set']()
    start,cpu=time.perf_counter_ns(),time.process_time_ns()
    result=call(fixture/'session')
    cpu_ns,wall_ns=time.process_time_ns()-cpu,time.perf_counter_ns()-start
    peak_after=COMMON['peak_working_set']()
    check(result,meta,operation)
    identity=content_hash(result.model_dump(mode='json'))
    assert initial_identity is None or initial_identity==identity
    assert hashes(fixture)==meta['files']
    return dict(status='passed',case=meta['case'],operation=operation,workspace_mode=mode,
        targets=meta['targets'],reviewers=meta['reviewers'],history_rounds=meta['rounds'],
        events=meta['events'],opinions=meta['opinions'],wall_ns=wall_ns,cpu_ns=cpu_ns,
        lifetime_peak_before_bytes=peak_before,lifetime_peak_after_bytes=peak_after,
        memory_status='measured' if peak_after is not None else 'not_evaluated',
        logical_result_sha256=identity,fixture_identity=meta['fixture_identity'],
        oracle_passed=True,fixture_unchanged=True)


def negative_checks(fixture,output):
    from medicine_agent.analysis.review_progress import ReviewProgressService
    from medicine_agent.analysis.models import AnalysisError
    results={}
    for kind in ('source','event'):
        copy=output/('negative-'+kind)
        copy.mkdir()
        for name in ('packages','session','preparation'):
            shutil.copytree(fixture/name,copy/name)
        api=ReviewProgressService(copy/'packages',copy/'cache')
        assert api.report(copy/'session').metrics_available
        if kind=='source':
            package=next((copy/'packages').glob('*.medpkg'))
            data=bytearray(package.read_bytes()); data[-1]^=1; package.write_bytes(data)
            try:
                api.report(copy/'session')
                raise AssertionError('mutated source must fail')
            except AnalysisError as exc:
                assert exc.code=='SESSION_SNAPSHOT_INVALID'
                results[kind]=dict(status='passed',actual_code=exc.code,after_workspace_warmup=True)
        else:
            path=next((copy/'session/events').glob('*.json'))
            data=json.loads(path.read_text('utf-8'))
            data['event']['submission']['opinions'][0]['reason']='CHANGED_SYNTHETIC_REASON'
            save(path,data)  # Intentionally do not reseal the wrapper hash.
            report=api.report(copy/'session')
            assert not report.metrics_available and report.engineering_gate=='blocked'
            assert 'SESSION_EVENT_INVALID' in report.diagnostic_codes and not report.coverage and not report.pairwise
            results[kind]=dict(status='passed',actual_codes=report.diagnostic_codes,after_workspace_warmup=True)
    save(output/'negative-checks.json',results)


def suite(output,smoke):
    base=(ROOT/'artifacts/b18-d02').resolve(); output=output.resolve()
    assert base.is_relative_to(ROOT) and output.is_relative_to(base) and output!=base
    output.mkdir(parents=True,exist_ok=False)
    protected=COMMON['protected']()
    save(output/'protected-before.json',protected)
    save(output/'environment.json',dict(python=sys.version,executable=sys.executable,
        os=platform.platform(),machine=platform.machine(),cpu_count=os.cpu_count(),
        pydantic=version('pydantic'),project=version('medicine-agent'),
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        fixture_builder='self-authored adapter + test PreparationModel; no external model',
        measurement='production inspect/report API call; no process startup/build/service construction/oracle',
        memory='Windows lifetime peak includes imports, input hash and reused-mode warm call; never subtract peaks',
        cache='fresh/reused workspace, NOT OS cold/warm cache; no cache purging'))
    cases=['u2-r2-h1'] if smoke else list(CASES)
    samples=[]; failure=None
    try:
        for case in cases:
            meta=build_fixture(output/'fixtures'/case,case)
            save(output/(case+'-build.json'),meta)
        negative_checks(output/'fixtures/u2-r2-h1',output)
        started=time.monotonic()
        for case in cases:
            for operation in ('inspect','report'):
                for mode in ('fresh','reused'):
                    for repeat in range(2 if smoke else 4):
                        label=f'{case}-{operation}-{mode}-'+('discard' if repeat==0 else f'rep-{repeat}')
                        if time.monotonic()-started>1800:
                            raise RuntimeError('SUITE_LAUNCH_BUDGET_EXCEEDED')
                        command=[sys.executable,'-I','-B',str(Path(__file__).resolve()),'--worker',
                            '--fixture',str(output/'fixtures'/case),'--workspace',str(output/'workspaces'/label),
                            '--operation',operation,'--mode',mode]
                        try:
                            child=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',timeout=120,cwd=ROOT)
                        except subprocess.TimeoutExpired:
                            save(output/(label+'.json'),dict(status='timeout',timeout_seconds=120))
                            raise RuntimeError('SAMPLE_TIMEOUT')
                        (output/(label+'.stdout.log')).write_text(child.stdout,encoding='utf-8')
                        (output/(label+'.stderr.log')).write_text(child.stderr,encoding='utf-8')
                        result=json.loads(child.stdout)
                        save(output/(label+'.json'),dict(result,exit_code=child.returncode,discard=repeat==0))
                        if child.returncode or result.get('status')!='passed': raise RuntimeError('SAMPLE_FAILED')
                        if repeat: samples.append(result)
    except Exception as exc:
        failure=dict(exception_type=type(exc).__name__,code=str(exc) if isinstance(exc,RuntimeError) else 'SETUP_OR_RESULT_FAILED')
    aggregates=[]
    if not failure:
        for case in cases:
            for operation in ('inspect','report'):
                all_rows=[s for s in samples if s['case']==case and s['operation']==operation]
                assert len({s['logical_result_sha256'] for s in all_rows})==1
                for mode in ('fresh','reused'):
                    rows=[s for s in all_rows if s['workspace_mode']==mode]
                    ns=[s['wall_ns'] for s in rows]
                    aggregates.append(dict(case=case,operation=operation,workspace_mode=mode,samples=len(rows),
                        median_wall_ns=statistics.median(ns),p95_nearest_rank_wall_ns=max(ns),
                        lifetime_peak_bytes=[s['lifetime_peak_after_bytes'] for s in rows]))
    after=COMMON['protected']()
    save(output/'protected-after.json',after)
    success=not failure and protected==after
    save(output/'summary.json',dict(status='executed_pending_review' if success else 'failed',
        smoke=smoke,profiles=len(cases),cells=len(cases)*4,measured_samples=len(samples),
        failure=failure,protected_unchanged=protected==after,results=aggregates,
        scope='synthetic committed events and source binding only; no clinical/cross-platform/capacity SLO',
        non_additivity='inspect and report are independent experiments; do not subtract medians as stage cost'))
    print(json.dumps(dict(output=str(output),failure=failure,measured_samples=len(samples),protected_unchanged=protected==after)))
    return 0 if success else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path); parser.add_argument('--smoke',action='store_true')
    parser.add_argument('--worker',action='store_true'); parser.add_argument('--fixture',type=Path)
    parser.add_argument('--workspace',type=Path); parser.add_argument('--operation',choices=['inspect','report'])
    parser.add_argument('--mode',choices=['fresh','reused'])
    args=parser.parse_args()
    if args.worker:
        try: print(json.dumps(worker(args.fixture,args.workspace,args.operation,args.mode)))
        except Exception as exc:
            print(json.dumps(dict(status='failed',exception_type=type(exc).__name__,code=getattr(exc,'code','WORKER_FAILED'))))
            raise SystemExit(1)
    else:
        if args.output is None: parser.error('--output is required')
        raise SystemExit(suite(args.output,args.smoke))


if __name__=='__main__': main()
