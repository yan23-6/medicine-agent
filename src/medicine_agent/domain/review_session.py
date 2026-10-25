"""Independent declared review opinions; never authenticated medical approval.

Versioned management contracts. Persistence and content identities require runtime
validation in addition to these structural and cross-field checks.
"""
from datetime import datetime, timedelta
import re
from typing import Annotated, Literal

from pydantic import Field, JsonValue, field_validator, model_validator

from medicine_agent.domain.models import StrictModel
from medicine_agent.domain.reviews import ReviewTarget


Sha256 = Annotated[str, Field(pattern=r'^[0-9a-f]{64}$')]
SnapshotId = Annotated[str, Field(pattern=r'^snapshot_[0-9a-f]{24}$')]
SessionId = Annotated[str, Field(pattern=r'^reviewsession_[0-9a-f]{24}$')]
EventId = Annotated[str, Field(pattern=r'^sessionevent_[0-9a-f]{24}$')]
OpinionId = Annotated[str, Field(pattern=r'^sessionopinion_[0-9a-f]{24}$')]

PREPARATION_RESOURCE_NAMES = frozenset({'manifest.json', 'preparation.json', 'README.md',
    'source-annotations.md', 'candidates.md', 'anomalies.md', 'quality-gates.md'})


def _text(value):
    value = value.strip()
    if not value:
        raise ValueError('Explicit nonblank text is required')
    return value


def _utc(value):
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError('An explicit UTC timestamp is required')
    return value


class SessionSnapshotBinding(StrictModel):
    snapshot_id: SnapshotId
    preparation_id: str = Field(pattern=r'^preparation_[0-9a-f]{24}$')
    manifest_sha256: Sha256
    snapshot_files: dict[str, Sha256] = Field(min_length=7, max_length=7)
    source_archives: dict[str, Sha256] = Field(min_length=1, max_length=10000)

    @model_validator(mode='after')
    def resources_match(self):
        if set(self.snapshot_files) != PREPARATION_RESOURCE_NAMES:
            raise ValueError('Snapshot must bind exactly the seven preparation files')
        if self.snapshot_files['manifest.json'] != self.manifest_sha256:
            raise ValueError('Manifest binding must match the manifest resource')
        if any(not name or any(c in name for c in '/\\:') or
                not name.lower().endswith('.medpkg') for name in self.source_archives):
            raise ValueError('Source archives must be medpkg filenames without paths')
        return self


class SessionReviewer(StrictModel):
    reviewer_id: str = Field(min_length=1, max_length=128, pattern=r'^[a-z0-9][a-z0-9._-]*$')
    display_name: str = Field(min_length=1, max_length=256)
    declared_role: str = Field(min_length=1, max_length=128)
    identity_status: Literal['self_declared'] = 'self_declared'

    @field_validator('reviewer_id', mode='before')
    @classmethod
    def normalize_id(cls, value):
        # Prevent capitalization/outer whitespace from creating a second voter.
        return value.strip().casefold() if isinstance(value, str) else value

    @field_validator('display_name', 'declared_role')
    @classmethod
    def nonblank(cls, value):
        return _text(value)


class SessionTarget(StrictModel):
    snapshot_id: SnapshotId
    kind: Literal['source_annotation', 'candidate', 'anomaly']
    material_id: str = Field(min_length=1, max_length=80)
    review_target: ReviewTarget | None = None

    @model_validator(mode='after')
    def target_kind(self):
        prefix = {'source_annotation': 'annotation', 'candidate': 'reviewitem', 'anomaly': 'anomaly'}[self.kind]
        if re.fullmatch(prefix + r'_[0-9a-f]{24}', self.material_id) is None:
            raise ValueError('Material identity must match target kind')
        if (self.kind == 'candidate') != (self.review_target is not None):
            raise ValueError('Only candidates require and may carry a ReviewTarget')
        return self


class SessionOpinion(StrictModel):
    target: SessionTarget
    decision: Literal['accept', 'revise', 'reject', 'unable_to_judge']
    reason: str = Field(min_length=1, max_length=8000)
    proposed_value: JsonValue = None
    expected_previous_id: OpinionId | None = None

    @field_validator('reason')
    @classmethod
    def nonblank(cls, value):
        return _text(value)

    @model_validator(mode='after')
    def correction_boundary(self):
        if self.proposed_value is not None:
            if self.decision != 'revise' or self.target.kind == 'anomaly':
                raise ValueError('Only source/candidate revision opinions allow correction candidates')
            if self.target.kind == 'source_annotation' and (
                    not isinstance(self.proposed_value, str) or not self.proposed_value.strip()):
                raise ValueError('Source correction candidates must be nonblank text')
        return self


class SessionSubmission(StrictModel):
    version: Literal['0.1.0'] = '0.1.0'
    session_id: SessionId
    submission_id: str = Field(min_length=1, max_length=128, pattern=r'^[A-Za-z0-9][A-Za-z0-9._-]*$')
    reviewer: SessionReviewer
    opinions: list[SessionOpinion] = Field(min_length=1, max_length=1000)

    @model_validator(mode='after')
    def one_opinion_per_target(self):
        keys = [(o.target.snapshot_id, o.target.kind, o.target.material_id) for o in self.opinions]
        if len(set(keys)) != len(keys):
            raise ValueError('One submission may contain only one opinion per material')
        if len({key[0] for key in keys}) != 1:
            raise ValueError('A submission must address exactly one snapshot')
        return self


class ReviewSessionManifest(StrictModel):
    version: Literal['0.1.0'] = '0.1.0'
    session_id: SessionId
    created_at: datetime
    binding: SessionSnapshotBinding
    reviewer_identity: Literal['self_declared'] = 'self_declared'
    medical_review: Literal['unreviewed'] = 'unreviewed'
    release_allowed: Literal[False] = False

    _utc_time = field_validator('created_at')(_utc)


class SessionEvent(StrictModel):
    """One atomic batch; runtime checks content ID and every previous opinion."""
    version: Literal['0.1.0'] = '0.1.0'
    event_id: EventId
    created_at: datetime
    submission: SessionSubmission

    _utc_time = field_validator('created_at')(_utc)


class SessionOpinionRecord(StrictModel):
    """Derived from an event and list index, not an independently writable file."""
    opinion_id: OpinionId
    event_id: EventId
    opinion_index: int = Field(ge=0, strict=True)
    created_at: datetime
    reviewer: SessionReviewer
    opinion: SessionOpinion

    _utc_time = field_validator('created_at')(_utc)


class SessionIssue(StrictModel):
    code: str = Field(min_length=1, max_length=128)
    event_file: str | None = None


class TargetReviewSummary(StrictModel):
    target: SessionTarget
    agreement_state: Literal['pending', 'insufficient_opinions', 'agreement', 'disagreement']
    adjudication_state: Literal['not_required', 'awaiting_adjudication']
    latest_opinion_ids: list[OpinionId]
    unable_to_judge_count: int = Field(ge=0, strict=True)
    history_invalid: bool = False

    @model_validator(mode='after')
    def no_implicit_adjudication(self):
        if (self.agreement_state == 'disagreement') != (self.adjudication_state == 'awaiting_adjudication'):
            raise ValueError('Disagreements must remain awaiting adjudication')
        if len(set(self.latest_opinion_ids)) != len(self.latest_opinion_ids):
            raise ValueError('Latest opinion identities must be unique')
        return self


class ReviewSessionView(StrictModel):
    version: Literal['0.1.0'] = '0.1.0'
    manifest: ReviewSessionManifest
    opinions: list[SessionOpinionRecord]
    targets: list[TargetReviewSummary]
    issues: list[SessionIssue]
    writable: bool
    reviewer_identity: Literal['self_declared'] = 'self_declared'
    medical_review: Literal['unreviewed'] = 'unreviewed'
    release_allowed: Literal[False] = False

    @model_validator(mode='after')
    def invalid_history_blocks_writes(self):
        if self.writable and (self.issues or any(t.history_invalid for t in self.targets)):
            raise ValueError('Invalid session history cannot permit writes')
        return self


REVIEW_SESSION_MODELS = (SessionSnapshotBinding, SessionReviewer, SessionTarget, SessionOpinion,
    SessionSubmission, ReviewSessionManifest, SessionEvent, SessionOpinionRecord, SessionIssue,
    TargetReviewSummary, ReviewSessionView)
