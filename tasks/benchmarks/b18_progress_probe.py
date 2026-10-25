"""Frozen internal B18-D01 experiment. Not a product API or source validator."""
from datetime import UTC, datetime
import argparse
import ctypes
import hashlib
from importlib.metadata import version
import json
import math
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
CASES = {
    'blank20': (20, 0, 1), 'blank5000': (5000, 0, 1),
    'n20-r2-h1': (20, 2, 1), 'n200-r2-h1': (200, 2, 1),
    'n1000-r2-h1': (1000, 2, 1), 'n5000-r2-h1': (5000, 2, 1),
    'n200-r10-h1': (200, 10, 1), 'n1000-r10-h1': (1000, 10, 1),
    'n200-r10-h3': (200, 10, 3), 'n1000-r2-h3': (1000, 2, 3),
    'n1000-r10-h3': (1000, 10, 3), 'n1000-r2-h10': (1000, 2, 10),
}


def peak_working_set():
    """Windows process-lifetime peak, NOT a phase delta or Python heap size."""
    if sys.platform != 'win32':
        return None
    from ctypes import wintypes
    class Counters(ctypes.Structure):
        _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD)] + [
            (name, ctypes.c_size_t) for name in ('PeakWorkingSetSize', 'WorkingSetSize',
            'QuotaPeakPagedPoolUsage', 'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage',
            'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage')]
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    psapi = ctypes.WinDLL('psapi', use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    value = Counters()
    value.cb = ctypes.sizeof(value)
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(value), value.cb):
        return None
    return value.PeakWorkingSetSize


def make_view(n, reviewers, rounds):
    from medicine_agent.domain.review_session import PREPARATION_RESOURCE_NAMES, ReviewSessionView
    stamp = datetime(2026, 1, 1, tzinfo=UTC)
    manifest = dict(session_id='reviewsession_'+'3'*24, created_at=stamp,
        binding=dict(snapshot_id='snapshot_'+'1'*24, preparation_id='preparation_'+'2'*24,
            manifest_sha256='a'*64, snapshot_files={name:'a'*64 for name in PREPARATION_RESOURCE_NAMES},
            source_archives={'synthetic-does-not-exist.medpkg':'b'*64}))
    rows, opinions = [], []
    for i in range(n):
        scope = ('source_annotation', 'candidate_node', 'candidate_fact', 'anomaly')[i % 4]
        kind = 'candidate' if scope.startswith('candidate_') else scope
        prefix = {'candidate':'reviewitem', 'source_annotation':'annotation', 'anomaly':'anomaly'}[kind]
        target = dict(snapshot_id='snapshot_'+'1'*24, kind=kind, material_id=prefix+f'_{i:024x}')
        if kind == 'candidate':
            target['review_target'] = dict(address={'package_id':'synthetic', 'node_id':f'node-{i}'},
                scope=scope.removeprefix('candidate_'), fingerprint='a'*64)
            if scope == 'candidate_fact':
                target['review_target'].update(group_id='synthetic-group', fact_index=0)
        latest = {}
        if i % 5 and reviewers:
            for round_index in range(rounds):
                for reviewer in range(reviewers):
                    number = len(opinions)+1
                    decision = ('accept' if i % 5 == 1 else
                        ('accept' if reviewer % 2 == 0 else 'reject') if i % 5 == 2 else
                        'unable_to_judge' if i % 5 == 3 else
                        ('accept' if reviewer == 0 else 'unable_to_judge'))
                    if round_index != rounds-1:
                        decision = 'accept' if round_index % 2 == 0 else 'reject'
                    opinion_id = f'sessionopinion_{number:024x}'
                    opinions.append(dict(opinion_id=opinion_id, event_id=f'sessionevent_{number:024x}',
                        opinion_index=0, created_at=stamp,
                        reviewer=dict(reviewer_id=f'r{reviewer:03}', display_name='Synthetic', declared_role='software only'),
                        opinion=dict(target=target, decision=decision, reason='SYNTHETIC_REASON_NOT_EXPORTED',
                            expected_previous_id=latest.get(reviewer))))
                    latest[reviewer] = opinion_id
        state = ('pending' if not reviewers or i % 5 in (0,3) else
            'agreement' if i % 5 == 1 else 'disagreement' if i % 5 == 2 else 'insufficient_opinions')
        rows.append(dict(target=target, agreement_state=state,
            adjudication_state='awaiting_adjudication' if state == 'disagreement' else 'not_required',
            latest_opinion_ids=list(latest.values()),
            unable_to_judge_count=(reviewers if i % 5 == 3 else reviewers-1 if i % 5 == 4 and reviewers else 0)))
    return ReviewSessionView(manifest=manifest, opinions=opinions, targets=rows, issues=[], writable=True)


def oracle(report, n, reviewers, rounds):
    """Closed-form expectations independent of the production vote algorithm."""
    b = n//20
    assert report.metrics_available and report.reviewer_count == reviewers and report.target_count == n
    assert len(report.event_ids) == n*4//5*reviewers*rounds
    assert not report.declared_agreement_complete and report.medical_gate == 'blocked'
    assert not report.release_allowed and not report.training_allowed and not report.phase02_complete
    assert len(report.reviewers) == 4*reviewers and len(report.pairwise) == 4*math.comb(reviewers, 2)
    for row in report.coverage:
        assert (row.total,row.pending,row.insufficient_opinions,row.agreement,row.disagreement,row.unable_votes) == (
            (n//4,2*b,b,b,b,b*(2*reviewers-1)) if reviewers else (n//4,n//4,0,0,0,0))
    for row in report.reviewers:
        decisive = 3*b if row.reviewer_id == 'r000' else 2*b
        assert (row.targets,row.decisive,row.unable) == (4*b,decisive,4*b-decisive)
    for row in report.pairwise:
        same = int(row.reviewer_a[1:]) % 2 == int(row.reviewer_b[1:]) % 2
        matched = 2*b if same else b
        assert (row.overlap,row.comparable,row.matched,row.conflicting,row.unable,row.agreement_fraction) == (
            4*b,2*b,matched,2*b-matched,2*b,matched/(2*b))


def worker(case):
    from medicine_agent.analysis.review_progress import _summarize
    from medicine_agent.domain.ids import canonical_json
    n, reviewers, rounds = CASES[case]
    before = peak_working_set()
    start = time.perf_counter_ns()
    view = make_view(n, reviewers, rounds)
    build_ns = time.perf_counter_ns()-start
    def fingerprint():
        return hashlib.sha256(canonical_json(view.model_dump(mode='json')).encode()).hexdigest()
    initial = fingerprint()
    after_build = peak_working_set()
    start, cpu = time.perf_counter_ns(), time.process_time_ns()
    report = _summarize(view)
    cpu_ns, wall_ns = time.process_time_ns()-cpu, time.perf_counter_ns()-start
    after_projection = peak_working_set()
    assert fingerprint() == initial
    oracle(report, n, reviewers, rounds)
    assert 'SYNTHETIC_REASON' not in report.model_dump_json()
    return dict(status='passed', case=case, targets=n, declared_reviewers=reviewers, history_rounds=rounds,
        opinion_records=len(view.opinions), synthetic_event_ids=len(report.event_ids),
        build_wall_ns=build_ns, projection_wall_ns=wall_ns, projection_cpu_ns=cpu_ns,
        peak_after_import_bytes=before, peak_after_build_and_input_hash_bytes=after_build,
        lifetime_peak_after_projection_bytes=after_projection,
        memory_status='measured' if after_projection is not None else 'not_evaluated',
        report_id=report.report_id, input_sha256=initial, oracle_passed=True, input_unchanged=True)


def protected():
    paths = [ROOT/p for p in ('pyproject.toml','uv.lock','AGENTS.md')]
    for directory in ('src','tests','schemas','md','tasks/overall'):
        paths += [p for p in (ROOT/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc']
    paths += [ROOT/'artifacts/b7-real-compat/model-knowledge/bundle_a7c24a2ba66c6200241e87e0.medpkg']
    paths += list((ROOT/'artifacts/b11-review-preparation/materials/preparation_718bf6c856acd871970f3eea').glob('*'))
    return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths) if p.is_file()}


def suite(output, smoke=False):
    base = (ROOT/'artifacts/b18-d01').resolve()
    output = output.resolve()
    if not base.is_relative_to(ROOT.resolve()) or not output.is_relative_to(base) or output == base:
        raise ValueError('Use a fresh directory within artifacts/b18-d01')
    output.mkdir(parents=True, exist_ok=False)
    def save(name, value):
        (output/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    baseline = protected()
    save('protected-before.json',baseline)
    save('environment.json',dict(python=sys.version,os=platform.platform(),machine=platform.machine(),
        cpu_count=os.cpu_count(),pydantic=version('pydantic'),project=version('medicine-agent'),
        executable=sys.executable,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        fixture='modulo-5-v1, deterministic, no PRNG',measurement='typed view revalidation + projection + report ID',
        not_checked=['source binding','real event history','service end-to-end','medical validity','capacity SLO']))
    cases = ('blank20','n20-r2-h1','n200-r10-h3') if smoke else tuple(CASES)
    samples, failure = [], None
    started = time.monotonic()
    for case in cases:
        for repetition in range(2 if smoke else 4):
            label = f'{case}-'+('warmup' if repetition == 0 else f'rep-{repetition}')
            command = [sys.executable,'-I','-B',str(Path(__file__).resolve()),'--worker',case]
            if time.monotonic()-started > 600:
                failure = dict(sample=label,code='SUITE_TIME_BUDGET_EXCEEDED'); break
            try:
                child = subprocess.run(command,capture_output=True,text=True,encoding='utf-8',timeout=120,cwd=ROOT)
                (output/(label+'.stdout.log')).write_text(child.stdout,encoding='utf-8')
                (output/(label+'.stderr.log')).write_text(child.stderr,encoding='utf-8')
                result = json.loads(child.stdout)
                save(label+'.json',dict(result,exit_code=child.returncode,warmup=repetition==0))
                if child.returncode or result.get('status') != 'passed':
                    failure=dict(sample=label,code='SAMPLE_FAILED'); break
                if repetition:
                    samples.append(result)
            except subprocess.TimeoutExpired:
                save(label+'.json',dict(status='timeout',timeout_seconds=120))
                failure=dict(sample=label,code='SAMPLE_TIMEOUT'); break
            except (OSError,ValueError):
                failure=dict(sample=label,code='WORKER_OR_RESULT_INVALID'); break
        if failure: break
    aggregates=[]
    if not failure:
        for case in cases:
            rows=[r for r in samples if r['case']==case]
            assert len({r['report_id'] for r in rows})==len({r['input_sha256'] for r in rows})==1
            values=sorted(r['projection_wall_ns'] for r in rows)
            aggregates.append(dict(case=case,samples=len(rows),median_projection_wall_ns=statistics.median(values),
                p95_nearest_rank_projection_wall_ns=values[math.ceil(.95*len(values))-1],
                lifetime_peak_after_projection_bytes=[r['lifetime_peak_after_projection_bytes'] for r in rows]))
    after=protected()
    save('protected-after.json',after)
    unchanged=baseline==after
    save('summary.json',dict(status='executed_pending_review' if not failure and unchanged else 'failed',
        experiment='B18-D01 internal evidence, not a public product contract',smoke=smoke,
        profiles=len(cases),measured_samples=len(samples),warmup_per_profile=1,
        repeats=1 if smoke else 3,failure=failure,protected_unchanged=unchanged,results=aggregates,
        notes=['fresh process per sample; warmup is not same-process cache warming',
               'p95 nearest-rank over 3 samples equals max; exploratory only',
               'Windows lifetime peak includes imports/build/input hash; never subtract peaks',
               'no package/source/event verification; history means synthetic opinion records only']))
    print(json.dumps(dict(output=str(output),failure=failure,protected_unchanged=unchanged,measured_samples=len(samples))))
    return 0 if not failure and unchanged else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--worker',choices=CASES)
    group.add_argument('--output',type=Path)
    parser.add_argument('--smoke',action='store_true')
    args=parser.parse_args()
    if args.worker:
        try:
            print(json.dumps(worker(args.worker)))
        except Exception as exc:
            print(json.dumps(dict(status='failed',exception_type=type(exc).__name__,code=getattr(exc,'code','PROBE_FAILED'))))
            raise SystemExit(1)
    else:
        raise SystemExit(suite(args.output,args.smoke))


if __name__=='__main__':
    main()
