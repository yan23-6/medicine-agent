"""Declared-opinion statistics, with explicit nonclinical denominators."""
from datetime import UTC, datetime
import json
from pathlib import Path
import subprocess
import sys

import pytest
from pydantic import ValidationError

from medicine_agent.analysis import review_progress as module
from medicine_agent.analysis.models import AnalysisError
from medicine_agent.analysis.review_progress import ReviewProgressService, _summarize
from medicine_agent.bootstrap import create_facade
from medicine_agent.contracts import export_schemas
from medicine_agent.domain.ids import canonical_json, stable_id
from medicine_agent.domain.review_progress import ReviewProgressReport, ReviewerAgreementPair, MaterialReviewCoverage
from medicine_agent.domain.review_session import (
    ReviewSessionView, SessionOpinion, SessionOpinionRecord, SessionReviewer, SessionIssue, TargetReviewSummary,
)
from test_review_session_contract import manifest_of, target as synthetic_target
from test_review_sessions import session, request as submission
from test_review_snapshot import exported, material, snapshot


def view(votes=()):
    """Self-authored typed view; integration below uses actual validated sessions."""
    targets = {kind: synthetic_target(kind) for kind in ('source_annotation', 'candidate', 'anomaly')}
    targets['candidate_node'] = targets.pop('candidate')
    fact = targets['candidate_node'].model_dump(mode='json')
    fact['material_id'] = 'reviewitem_' + '3' * 24
    fact['review_target'].update(scope='fact', group_id='g', fact_index=0)
    targets['candidate_fact'] = type(targets['candidate_node']).model_validate(fact)
    records, latest = [], {}
    for index, (reviewer, scope, decision, value) in enumerate(votes, 1):
        r = SessionReviewer(reviewer_id=reviewer, display_name='Synthetic reviewer', declared_role='synthetic')
        key = (scope, r.reviewer_id)
        record = SessionOpinionRecord(opinion_id='sessionopinion_' + f'{index:024x}',
            event_id='sessionevent_' + f'{index:024x}', opinion_index=0, created_at=datetime(2026, 1, 1, tzinfo=UTC),
            reviewer=r, opinion=SessionOpinion(target=targets[scope].model_copy(deep=True), decision=decision,
                reason='PRIVATE_REASON_DO_NOT_EXPORT', proposed_value=value,
                expected_previous_id=latest[key].opinion_id if key in latest else None))
        records.append(record)
        latest[key] = record
    rows = []
    for scope, target in targets.items():
        entries = [record for (kind, _), record in latest.items() if kind == scope]
        explicit = [r for r in entries if r.opinion.decision != 'unable_to_judge']
        if not explicit:
            state = 'pending'
        elif len(explicit) == 1:
            state = 'insufficient_opinions'
        else:
            values = [canonical_json([r.opinion.decision, r.opinion.proposed_value]) for r in explicit]
            state = 'agreement' if len(set(values)) == 1 else 'disagreement'
        rows.append(TargetReviewSummary(target=target, agreement_state=state,
            adjudication_state='awaiting_adjudication' if state == 'disagreement' else 'not_required',
            latest_opinion_ids=[r.opinion_id for r in entries], unable_to_judge_count=len(entries)-len(explicit)))
    return ReviewSessionView(manifest=manifest_of(), opinions=records, targets=rows, issues=[], writable=True)


def pair(report, scope='candidate_node'):
    return next(p for p in report.pairwise if p.scope == scope)


def test_blank_and_empty_are_not_perfect_agreement():
    report = _summarize(view())
    assert report.metrics_available and report.reviewer_count == 0 and not report.pairwise
    assert all(c.pending == c.total for c in report.coverage)
    empty = view(); empty.targets = []
    assert not _summarize(empty).declared_agreement_complete
    assert not report.declared_agreement_complete
    assert report.medical_gate == 'blocked' and not report.release_allowed and not report.training_allowed


@pytest.mark.parametrize('a,b,comparable,matched,conflicting,unable,rate', [
    (('accept', None), ('accept', None), 1, 1, 0, 0, 1),
    (('accept', None), ('reject', None), 1, 0, 1, 0, 0),
    (('unable_to_judge', None), ('unable_to_judge', None), 0, 0, 0, 1, None),
    (('accept', None), ('unable_to_judge', None), 0, 0, 0, 1, None),
    (('revise', {'a': 1, 'b': 2}), ('revise', {'b': 2, 'a': 1}), 1, 1, 0, 0, 1),
    (('revise', 'PRIVATE_VALUE_A'), ('revise', 'PRIVATE_VALUE_B'), 1, 0, 1, 0, 0),
])
def test_pair_denominators_and_corrections(a, b, comparable, matched, conflicting, unable, rate):
    report = _summarize(view([('a', 'candidate_node', *a), ('b', 'candidate_node', *b)]))
    row = pair(report)
    assert (row.overlap, row.comparable, row.matched, row.conflicting, row.unable,
        row.agreement_fraction) == (1, comparable, matched, conflicting, unable, rate)
    assert all(p.agreement_fraction is None for p in report.pairwise if p.scope != 'candidate_node')
    assert 'PRIVATE_' not in report.model_dump_json()


def test_distinct_materials_have_no_comparable_denominator():
    report = _summarize(view([('a', 'candidate_node', 'accept', None), ('b', 'source_annotation', 'accept', None)]))
    assert len(report.pairwise) == 4
    assert all(p.overlap == 0 and p.agreement_fraction is None for p in report.pairwise)


def test_latest_normalized_identity_has_one_vote_and_does_not_confirm_fields():
    report = _summarize(view([('a', 'candidate_node', 'accept', None),
        (' A ', 'candidate_node', 'reject', None), ('b', 'candidate_node', 'reject', None)]))
    assert report.reviewer_count == 2 and pair(report).matched == 1
    own = next(r for r in report.reviewers if r.reviewer_id == 'a' and r.scope == 'candidate_node')
    assert own.targets == 1
    assert next(c for c in report.coverage if c.scope == 'candidate_fact').pending == 1
    assert not report.declared_agreement_complete


def test_declared_complete_still_never_opens_medical_training_or_release_gates():
    votes = [(r, scope, 'accept', None) for scope in ('candidate_node', 'candidate_fact', 'source_annotation', 'anomaly') for r in ('a', 'b')]
    report = _summarize(view(votes))
    assert report.declared_agreement_complete and report.medical_gate == 'blocked'
    assert not report.phase02_complete and not report.release_allowed and not report.training_allowed


def test_bad_history_only_returns_diagnostics():
    data = view([('a', 'candidate_node', 'accept', None)])
    data.issues = [SessionIssue(code='SESSION_EVENT_INVALID')]
    data.writable = False
    report = _summarize(data)
    assert not report.metrics_available and report.reviewer_count is None
    assert not report.coverage and not report.reviewers and not report.pairwise
    assert report.engineering_gate == 'blocked' and report.diagnostic_codes == ['SESSION_EVENT_INVALID']


@pytest.mark.parametrize('damage', ['missing_id', 'wrong_target', 'duplicate_reviewer', 'wrong_unable', 'duplicate_target'])
def test_inconsistent_view_never_silently_computes_partial_metrics(damage):
    data = view([('a', 'candidate_node', 'accept', None), ('a', 'candidate_node', 'reject', None)])
    row = next(r for r in data.targets if r.target.kind == 'candidate' and r.target.review_target.scope == 'node')
    if damage == 'missing_id': row.latest_opinion_ids = ['sessionopinion_'+'f'*24]
    elif damage == 'wrong_target': data.opinions[-1].opinion.target.snapshot_id = 'snapshot_'+'f'*24
    elif damage == 'duplicate_reviewer': row.latest_opinion_ids = [r.opinion_id for r in data.opinions]
    elif damage == 'wrong_unable': row.unable_to_judge_count = 1
    else: data.targets.append(data.targets[0].model_copy(deep=True))
    with pytest.raises(AnalysisError) as exc:
        _summarize(data)
    assert exc.value.code == 'REVIEW_PROGRESS_INPUT_INVALID' and 'PRIVATE_' not in str(exc.value)


@pytest.mark.parametrize('limit', ['MAX_REVIEWERS', 'MAX_TARGETS'])
def test_resources_are_refused_not_truncated(monkeypatch, limit):
    data = view([('a', 'candidate_node', 'accept', None), ('b', 'candidate_node', 'accept', None)])
    monkeypatch.setattr(module, limit, 1)
    with pytest.raises(AnalysisError) as exc: _summarize(data)
    assert exc.value.code == 'REVIEW_PROGRESS_LIMIT_EXCEEDED'


def test_report_identity_is_deterministic_and_models_reject_false_denominators():
    data = view([('a', 'candidate_node', 'accept', None), ('b', 'candidate_node', 'accept', None)])
    report = _summarize(data)
    data.opinions.reverse(); data.targets.reverse()
    assert _summarize(data) == report
    assert report.report_id == stable_id('reviewprogress', report.model_dump(mode='json', exclude={'report_id'}))
    with pytest.raises(ValidationError):
        ReviewerAgreementPair(reviewer_a='a', reviewer_b='b', scope='anomaly',
            overlap=0, comparable=0, matched=0, conflicting=0, unable=0, agreement_fraction=1)
    with pytest.raises(ValidationError):
        MaterialReviewCoverage(scope='anomaly', total=1, pending=0, insufficient_opinions=0,
            agreement=0, disagreement=0, unable_votes=0)
    payload = report.model_dump(mode='json'); payload['release_allowed'] = True
    with pytest.raises(ValidationError): ReviewProgressReport.model_validate(payload)


def test_service_cli_and_source_readonly(session, exported):
    service, root, _, target = session
    service.submit(root, submission(session))
    service.submit(root, submission(session, reviewer='b', submission='second', decision='reject'))
    before = snapshot(root), snapshot(exported[1])
    progress = ReviewProgressService(exported[1], exported[2]).report(root)
    assert progress.reviewer_count == 2 and any(p.conflicting for p in progress.pairwise)
    completed = subprocess.run([sys.executable, '-m', 'medicine_agent.cli', 'analyze',
        'review-session-progress', '--session-dir', str(root), '--packages', str(exported[1]),
        '--workspace', str(exported[2])], capture_output=True, encoding='utf-8', timeout=60)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert json.loads(completed.stdout) == progress.model_dump(mode='json')
    assert 'Self authored software opinion' not in completed.stdout
    assert (snapshot(root), snapshot(exported[1])) == before
    (root / 'events' / 'unknown.json').write_text('{}', encoding='utf-8')
    injected = snapshot(root)
    diagnostic = ReviewProgressService(exported[1], exported[2]).report(root)
    assert not diagnostic.metrics_available and not diagnostic.pairwise and diagnostic.reviewer_count is None
    assert diagnostic.diagnostic_codes == ['SESSION_EVENT_INVALID']
    assert snapshot(root) == injected and snapshot(exported[1]) == before[1]


def test_progress_schema_export_and_legacy_schema_bytes(tmp_path):
    index = export_schemas(create_facade(), tmp_path / 'progress', contract_set='review-progress')
    assert len(index['files']) == 4 and index['contract_version'] == '0.1.0'
    for name in [*index['files'], 'schema-index.json']:
        assert (tmp_path / 'progress' / name).read_bytes() == (Path('schemas/review-progress') / name).read_bytes()
    for contract in ('t01', 't02', 't02p', 'tcm', 'review', 'correction', 'owned-analysis',
            'learning', 'coverage', 'review-preparation', 'review-session'):
        output = tmp_path / contract
        old = export_schemas(create_facade(), output, contract_set=contract)
        for name in [*old['files'], 'schema-index.json']:
            assert (output / name).read_bytes() == (Path('schemas') / contract / name).read_bytes()
