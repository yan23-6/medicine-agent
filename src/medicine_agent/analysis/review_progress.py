"""Read-only coverage and pairwise comparisons; no expert or medical approval."""
from collections import defaultdict
from itertools import combinations

from pydantic import ValidationError

from medicine_agent.analysis.models import AnalysisError
from medicine_agent.analysis.review_sessions import ReviewSessionService
from medicine_agent.domain.ids import canonical_json, stable_id
from medicine_agent.domain.review_progress import (
    MaterialReviewCoverage, ReviewerAgreementPair, ReviewerCoverage, ReviewProgressReport, SCOPES,
)
from medicine_agent.domain.review_session import ReviewSessionView


MAX_REVIEWERS = 100
MAX_TARGETS = 100000


def _fail(code):
    raise AnalysisError(code, 'Review progress computation failed: ' + code) from None


def _scope(target):
    return 'candidate_' + target.review_target.scope if target.kind == 'candidate' else target.kind


def _identity(target):
    return target.kind, target.material_id


def _finish(data):
    report = ReviewProgressReport(report_id='reviewprogress_' + '0' * 24, **data)
    report.report_id = stable_id('reviewprogress', report.model_dump(mode='json', exclude={'report_id'}))
    return report


def _summarize(verified_view):
    """Internal projection. Public callers must use report() to validate sources."""
    try:
        view = ReviewSessionView.model_validate(verified_view.model_dump(mode='json'))
        if len(view.targets) > MAX_TARGETS:
            _fail('REVIEW_PROGRESS_LIMIT_EXCEEDED')
        header = dict(session_id=view.manifest.session_id, snapshot_id=view.manifest.binding.snapshot_id,
            event_ids=sorted({r.event_id for r in view.opinions}), target_count=len(view.targets))
        diagnostics = sorted({issue.code for issue in view.issues})
        if not view.writable or diagnostics or any(t.history_invalid for t in view.targets):
            return _finish(dict(**header, reviewer_count=None, metrics_available=False,
                coverage=[], reviewers=[], pairwise=[], diagnostic_codes=diagnostics or ['SESSION_HISTORY_INVALID'],
                declared_agreement_complete=False, engineering_gate='blocked'))
        records = {r.opinion_id: r for r in view.opinions}
        if len(records) != len(view.opinions):
            _fail('REVIEW_PROGRESS_INPUT_INVALID')
        totals = {scope: dict(total=0, pending=0, insufficient_opinions=0,
            agreement=0, disagreement=0, unable_votes=0) for scope in SCOPES}
        votes = defaultdict(lambda: {scope: {} for scope in SCOPES})
        seen_targets = set()
        for row in view.targets:
            target = row.target
            key, scope = _identity(target), _scope(target)
            if key in seen_targets or target.snapshot_id != header['snapshot_id']:
                _fail('REVIEW_PROGRESS_INPUT_INVALID')
            seen_targets.add(key)
            latest = [records[oid] for oid in row.latest_opinion_ids]
            ids = [r.reviewer.reviewer_id for r in latest]
            if len(ids) != len(set(ids)) or any(r.opinion.target != target for r in latest):
                _fail('REVIEW_PROGRESS_INPUT_INVALID')
            decisive = [r for r in latest if r.opinion.decision != 'unable_to_judge']
            choices = {canonical_json([r.opinion.decision, r.opinion.proposed_value]) for r in decisive}
            state = ('pending' if not decisive else 'insufficient_opinions' if len(decisive) == 1 else
                'agreement' if len(choices) == 1 else 'disagreement')
            unable = len(latest) - len(decisive)
            if state != row.agreement_state or unable != row.unable_to_judge_count:
                _fail('REVIEW_PROGRESS_INPUT_INVALID')
            totals[scope]['total'] += 1
            totals[scope][state] += 1
            totals[scope]['unable_votes'] += unable
            for record in latest:
                votes[record.reviewer.reviewer_id][scope][key] = (
                    record.opinion.decision, canonical_json(record.opinion.proposed_value))
        ids = sorted(votes)
        if len(ids) > MAX_REVIEWERS:
            _fail('REVIEW_PROGRESS_LIMIT_EXCEEDED')
        reviewers = []
        for reviewer_id in ids:
            for scope in SCOPES:
                local = votes[reviewer_id][scope]
                unable = sum(v[0] == 'unable_to_judge' for v in local.values())
                reviewers.append(ReviewerCoverage(reviewer_id=reviewer_id, scope=scope,
                    targets=len(local), decisive=len(local) - unable, unable=unable))
        pairs = []
        for a, b in combinations(ids, 2):
            for scope in SCOPES:
                left, right = votes[a][scope], votes[b][scope]
                common = left.keys() & right.keys()
                comparable = [key for key in common if left[key][0] != 'unable_to_judge'
                    and right[key][0] != 'unable_to_judge']
                matched = sum(left[key] == right[key] for key in comparable)
                pairs.append(ReviewerAgreementPair(reviewer_a=a, reviewer_b=b, scope=scope,
                    overlap=len(common), comparable=len(comparable), matched=matched,
                    conflicting=len(comparable) - matched, unable=len(common) - len(comparable),
                    agreement_fraction=matched / len(comparable) if comparable else None))
        return _finish(dict(**header, reviewer_count=len(ids), metrics_available=True,
            coverage=[MaterialReviewCoverage(scope=scope, **totals[scope]) for scope in SCOPES],
            reviewers=reviewers, pairwise=pairs, diagnostic_codes=[], engineering_gate='passed',
            declared_agreement_complete=bool(view.targets) and all(t.agreement_state == 'agreement' for t in view.targets)))
    except AnalysisError:
        raise
    except (ValidationError, ValueError, TypeError, KeyError, AttributeError, RecursionError):
        _fail('REVIEW_PROGRESS_INPUT_INVALID')


class ReviewProgressService:
    """No writes to session or source packages; only existing private caches."""

    def __init__(self, packages, workspace):
        self.sessions = ReviewSessionService(packages, workspace)

    def report(self, session_dir) -> ReviewProgressReport:
        return _summarize(self.sessions.inspect(session_dir))
