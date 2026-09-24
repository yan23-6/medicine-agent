from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SkillStatus(StrEnum):
    SUCCESS = "success"
    PARTIAL = "partial_success"
    FAILURE = "failure"
    REVIEW = "needs_review"


class IssueSeverity(StrEnum):
    WARNING = "warning"
    ERROR = "error"


class GenerationMethod(StrEnum):
    RULE = "rule"
    MODEL = "model"
    HUMAN = "human"
    IMPORTED = "imported"


class ReviewStatus(StrEnum):
    UNREVIEWED = "unreviewed"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class FieldMappingStatus(StrEnum):
    MAPPED = "mapped"
    AMBIGUOUS = "ambiguous"
    UNMAPPED = "unmapped"
    REJECTED = "rejected"


class CorrectionStatus(StrEnum):
    NONE = "none"
    PROPOSED = "proposed"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class SourceMetadata(StrictModel):
    title: str | None
    author: str | None
    edition: str | None
    publication_year: int | None
    publisher: str | None
    isbn: str | None


class SourceDocument(StrictModel):
    source_id: str
    file_name: str
    media_type: str
    sha256: str
    metadata: SourceMetadata


class DocumentFragment(StrictModel):
    fragment_id: str
    source_id: str
    ordinal: int
    text: str
    start_line: int
    end_line: int


class EvidenceRecord(StrictModel):
    evidence_id: str
    source_id: str
    fragment_id: str
    raw_text: str
    corrected_text: str | None = None
    correction_status: CorrectionStatus = CorrectionStatus.NONE
    location: dict[str, Any]
    context: str | None = None


class FieldMappingCandidate(StrictModel):
    canonical_field: str
    rationale: str
    confidence: float | None = Field(default=None, ge=0, le=1)


class RawFieldObservation(StrictModel):
    observation_id: str
    source_id: str
    raw_key: str
    raw_value: Any
    occurrence: int
    location: dict[str, Any]
    context: str | None = None
    raw_type: str
    mapping_status: FieldMappingStatus
    mapping_candidates: list[FieldMappingCandidate] = Field(default_factory=list)
    mapping_rule_version: str | None = None
    review_status: ReviewStatus = ReviewStatus.UNREVIEWED


class KnowledgeCandidate(StrictModel):
    knowledge_id: str
    kind: str
    label: str
    statement: str
    evidence_refs: list[str] = Field(min_length=1)
    generation_method: GenerationMethod
    review_status: ReviewStatus = ReviewStatus.UNREVIEWED


class RelationCandidate(StrictModel):
    relation_id: str
    relation_type: str
    source_knowledge_id: str
    target_knowledge_id: str
    evidence_refs: list[str] = Field(default_factory=list)
    generation_method: GenerationMethod
    review_status: ReviewStatus = ReviewStatus.UNREVIEWED


class SkillIssue(StrictModel):
    code: str
    severity: IssueSeverity
    message: str
    path: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class SkillManifest(StrictModel):
    skill_id: str
    version: str
    name: str
    description: str
    entrypoint: str
    input_model: str
    output_model: str
    permissions: list[str] = Field(default_factory=list)


class SkillInvocation(StrictModel):
    task_id: str
    skill_id: str
    skill_version: str | None = None
    input_data: dict[str, Any]
    caller: str = "human"


class SkillResult(StrictModel):
    invocation_id: str
    task_id: str
    skill_id: str
    skill_version: str
    status: SkillStatus
    output: dict[str, Any] | None = None
    issues: list[SkillIssue] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    generation_method: GenerationMethod = GenerationMethod.RULE
    review_status: ReviewStatus = ReviewStatus.UNREVIEWED
    runtime: dict[str, Any] = Field(default_factory=dict)
    started_at: datetime
    completed_at: datetime
    duration_ms: int = Field(ge=0)


class QualityReport(StrictModel):
    valid: bool
    issues: list[SkillIssue] = Field(default_factory=list)
    counts: dict[str, int] = Field(default_factory=dict)


class ExperimentalPackageManifest(StrictModel):
    package_id: str
    package_version: str
    protocol_version: str
    status: str
    source_ids: list[str]
    created_at: datetime
    files: dict[str, str]

