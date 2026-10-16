"""User-entered review opinions; never a replacement for medical source data."""
from datetime import datetime
from typing import Literal
from pydantic import Field, JsonValue, field_validator, model_validator
from medicine_agent.domain.models import StrictModel
from medicine_agent.domain.tcm_knowledge import KnowledgeAddress


class ReviewTarget(StrictModel):
    address: KnowledgeAddress
    scope: Literal['node', 'fact']
    group_id: str | None = None
    fact_index: int | None = Field(default=None, ge=0)
    fingerprint: str = Field(pattern='^[0-9a-f]{64}$')

    @model_validator(mode='after')
    def check_scope(self):
        if self.scope == 'fact' and (not self.group_id or self.fact_index is None):
            raise ValueError('Fact review requires group identity and occurrence index')
        if self.scope == 'node' and (self.group_id is not None or self.fact_index is not None):
            raise ValueError('Node review must not include a field occurrence')
        return self


class ReviewRequest(StrictModel):
    target: ReviewTarget
    decision: Literal['confirmed', 'needs_revision', 'rejected']
    reviewer: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    proposed_value: JsonValue = None
    expected_previous_id: str | None = None
    origin: Literal['user_entered'] = 'user_entered'

    @field_validator('reviewer', 'reason')
    @classmethod
    def nonempty(cls, value):
        if not value.strip():
            raise ValueError('Reviewer and reason must not be blank')
        return value.strip()

    @model_validator(mode='after')
    def check_correction(self):
        if self.decision != 'needs_revision' and self.proposed_value is not None:
            raise ValueError('A correction candidate requires needs_revision')
        return self


class ReviewRecord(StrictModel):
    version: Literal['0.1.0'] = '0.1.0'
    review_id: str
    created_at: datetime
    request: ReviewRequest

    @field_validator('created_at')
    @classmethod
    def timezone_required(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError('Review time requires a timezone')
        return value


REVIEW_MODELS = (ReviewTarget, ReviewRequest, ReviewRecord)
