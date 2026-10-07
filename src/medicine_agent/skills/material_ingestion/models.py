from __future__ import annotations

from typing import Any

from pydantic import Field

from medicine_agent.domain.models import (
    DocumentFragment,
    FieldMappingCandidate,
    FieldMappingStatus,
    RawFieldObservation,
    ReviewStatus,
    SkillIssue,
    SourceDocument,
    SourceMetadata,
    StrictModel,
)


class RawFieldInput(StrictModel):
    raw_key: str
    raw_value: Any
    location: dict[str, Any] = Field(default_factory=dict)
    context: str | None = None
    mapping_status: FieldMappingStatus | None = None
    mapping_candidates: list[FieldMappingCandidate] = Field(default_factory=list)
    mapping_rule_version: str | None = "t01-explicit-v1"
    review_status: ReviewStatus = ReviewStatus.UNREVIEWED


class MaterialIngestionInput(StrictModel):
    path: str
    metadata: SourceMetadata
    raw_fields: list[RawFieldInput] = Field(default_factory=list)


class MaterialIngestionOutput(StrictModel):
    source: SourceDocument
    fragments: list[DocumentFragment] = Field(default_factory=list)
    raw_fields: list[RawFieldObservation] = Field(default_factory=list)
    issues: list[SkillIssue] = Field(default_factory=list)

