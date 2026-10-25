"""Package-external, nonclinical statistics of declared review opinions."""
from typing import Annotated, Literal

from pydantic import Field, model_validator

from medicine_agent.domain.models import StrictModel


ReviewScope = Literal['source_annotation', 'candidate_node', 'candidate_fact', 'anomaly']
SCOPES = ('source_annotation', 'candidate_node', 'candidate_fact', 'anomaly')
Count = Annotated[int, Field(ge=0, strict=True)]
ReviewerId = Annotated[str, Field(min_length=1, max_length=128, pattern=r'^[a-z0-9][a-z0-9._-]*$')]


class MaterialReviewCoverage(StrictModel):
    scope: ReviewScope
    total: Count
    pending: Count
    insufficient_opinions: Count
    agreement: Count
    disagreement: Count
    unable_votes: Count

    @model_validator(mode='after')
    def partition(self):
        if self.total != self.pending + self.insufficient_opinions + self.agreement + self.disagreement:
            raise ValueError('Material states must partition the group')
        return self


class ReviewerCoverage(StrictModel):
    reviewer_id: ReviewerId
    scope: ReviewScope
    targets: Count
    decisive: Count
    unable: Count

    @model_validator(mode='after')
    def partition(self):
        if self.targets != self.decisive + self.unable:
            raise ValueError('Reviewer targets must partition into explicit and unable decisions')
        return self


class ReviewerAgreementPair(StrictModel):
    reviewer_a: ReviewerId
    reviewer_b: ReviewerId
    scope: ReviewScope
    overlap: Count
    comparable: Count
    matched: Count
    conflicting: Count
    unable: Count
    agreement_fraction: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode='after')
    def denominator(self):
        if self.reviewer_a >= self.reviewer_b:
            raise ValueError('Pair members must be distinct canonical ordered identities')
        if self.overlap != self.comparable + self.unable or self.comparable != self.matched + self.conflicting:
            raise ValueError('Pair counts must use explicit comparable denominators')
        if self.comparable == 0:
            if self.agreement_fraction is not None:
                raise ValueError('No comparable opinions requires a null fraction')
        elif self.agreement_fraction is None or abs(self.agreement_fraction - self.matched / self.comparable) > 1e-12:
            raise ValueError('Agreement fraction must match the declared denominator')
        return self


class ReviewProgressReport(StrictModel):
    version: Literal['0.1.0'] = '0.1.0'
    report_id: str = Field(pattern=r'^reviewprogress_[0-9a-f]{24}$')
    session_id: str = Field(pattern=r'^reviewsession_[0-9a-f]{24}$')
    snapshot_id: str = Field(pattern=r'^snapshot_[0-9a-f]{24}$')
    event_ids: list[Annotated[str, Field(pattern=r'^sessionevent_[0-9a-f]{24}$')]]
    target_count: Count
    reviewer_count: Count | None
    metrics_available: bool
    coverage: list[MaterialReviewCoverage]
    reviewers: list[ReviewerCoverage]
    pairwise: list[ReviewerAgreementPair]
    diagnostic_codes: list[str]
    declared_agreement_complete: bool
    engineering_gate: Literal['passed', 'blocked']
    medical_gate: Literal['blocked'] = 'blocked'
    license_gate: Literal['not_evaluated'] = 'not_evaluated'
    performance_gate: Literal['not_evaluated'] = 'not_evaluated'
    reviewer_identity: Literal['self_declared'] = 'self_declared'
    measurement_scope: Literal['latest_self_declared_opinions_only'] = 'latest_self_declared_opinions_only'
    phase02_complete: Literal[False] = False
    release_allowed: Literal[False] = False
    training_allowed: Literal[False] = False

    @model_validator(mode='after')
    def report_boundary(self):
        if self.event_ids != sorted(set(self.event_ids)) or self.diagnostic_codes != sorted(set(self.diagnostic_codes)):
            raise ValueError('Provenance and diagnostics must be deterministic sets')
        if not self.metrics_available:
            if (self.reviewer_count is not None or self.coverage or self.reviewers or self.pairwise or
                    self.declared_agreement_complete or self.engineering_gate != 'blocked' or not self.diagnostic_codes):
                raise ValueError('Unhealthy history permits diagnostics only')
            return self
        if self.reviewer_count is None or self.engineering_gate != 'passed' or self.diagnostic_codes:
            raise ValueError('Available statistics require a healthy engineering state')
        if {c.scope for c in self.coverage} != set(SCOPES) or len(self.coverage) != len(SCOPES):
            raise ValueError('All four material groups must be explicit')
        if sum(c.total for c in self.coverage) != self.target_count:
            raise ValueError('Material groups must partition all targets')
        reviewer_keys = {(r.reviewer_id, r.scope) for r in self.reviewers}
        ids = {r.reviewer_id for r in self.reviewers}
        if (len(ids) != self.reviewer_count or len(reviewer_keys) != len(self.reviewers) or
                reviewer_keys != {(r, scope) for r in ids for scope in SCOPES}):
            raise ValueError('Reviewer coverage must contain exactly four groups per identity')
        pair_keys = {(p.reviewer_a, p.reviewer_b, p.scope) for p in self.pairwise}
        expected_pairs = {(a, b, scope) for a in ids for b in ids if a < b for scope in SCOPES}
        if pair_keys != expected_pairs or len(pair_keys) != len(self.pairwise):
            raise ValueError('Pairwise matrix must include zero-overlap groups exactly once')
        complete = self.target_count > 0 and sum(c.agreement for c in self.coverage) == self.target_count
        if self.declared_agreement_complete != complete:
            raise ValueError('Declared coverage must not infer completion from an empty set')
        return self


REVIEW_PROGRESS_MODELS = (MaterialReviewCoverage, ReviewerCoverage, ReviewerAgreementPair, ReviewProgressReport)
