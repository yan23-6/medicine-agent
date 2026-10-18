"""Read-only preparation contracts, never expert approval or review writes."""
from typing import Literal
from pydantic import Field, JsonValue, field_validator, model_validator

from medicine_agent.domain.models import StrictModel, EvidenceRecord, SourceDocument
from medicine_agent.domain.coverage import CoverageAddress, CoverageInventory, UnitKind
from medicine_agent.domain.reviews import ReviewTarget, ReviewRecord
from medicine_agent.domain.tcm_knowledge import AnalysisGap, RejectedAnalysisCandidate


class ReviewPreparationRequest(StrictModel):
    version: Literal['0.1.0'] = '0.1.0'
    archives: list[str] = Field(default_factory=list, max_length=10000)

    @field_validator('archives')
    @classmethod
    def filenames_only(cls, values):
        if any(not v or '/' in v or '\\' in v or ':' in v or not v.lower().endswith('.medpkg') for v in values):
            raise ValueError('Use complete medpkg filenames, not paths')
        return sorted(set(values))


class PreparationWorksheet(StrictModel):
    reviewer: str | None = None
    decision: Literal['accept', 'revise', 'reject', 'unable_to_judge'] | None = None
    reason: str | None = None
    # These are unsubmitted preparation fields, not ReviewRequest decisions.
    submitted: Literal[False] = False


class SourceAnnotation(StrictModel):
    annotation_id: str
    source: SourceDocument
    evidence: EvidenceRecord
    unit_kind: UnitKind
    origins: list[CoverageAddress]
    flags: list[str] = Field(default_factory=list)
    worksheet: PreparationWorksheet = Field(default_factory=PreparationWorksheet)


class PreparationQuote(StrictModel):
    evidence_id: str
    text: str
    source_id: str
    source_sha256: str
    location: dict[str, JsonValue]


class CandidateReviewItem(StrictModel):
    item_id: str
    target: ReviewTarget
    title: str
    categories: list[str]
    field_id: str | None = None
    value: JsonValue = None
    fact_state: str | None = None
    reason: str | None = None
    quotes: list[PreparationQuote]
    flags: list[str]
    user_review_state: Literal['unreviewed', 'confirmed', 'needs_revision', 'rejected', 'history_invalid']
    expected_previous_id: str | None = None
    origins: list[CoverageAddress]
    worksheet: PreparationWorksheet = Field(default_factory=PreparationWorksheet)


class PreparationAnomaly(StrictModel):
    anomaly_id: str
    kind: Literal['graph_gap', 'node_gap', 'rejected_candidate']
    package_id: str
    node_id: str | None = None
    occurrence: int = Field(ge=0)
    gap: AnalysisGap | None = None
    rejected: RejectedAnalysisCandidate | None = None
    evidence: list[EvidenceRecord]
    unresolved_evidence_ids: list[str] = Field(default_factory=list)
    origins: list[CoverageAddress]
    worksheet: PreparationWorksheet = Field(default_factory=PreparationWorksheet)
    writable_review_target: Literal[False] = False

    @model_validator(mode='after')
    def valid_audit_kind(self):
        if (self.kind == 'rejected_candidate') != (self.rejected is not None) or (self.kind != 'rejected_candidate') != (self.gap is not None):
            raise ValueError('Audit kind must match exactly one original payload')
        if (self.kind == 'node_gap') != (self.node_id is not None):
            raise ValueError('Only node gaps carry a node address')
        return self


class PreparationIssue(StrictModel):
    code: str
    archive: str | None = None
    severity: Literal['warning', 'error'] = 'error'
    reason: str


class PreparationQualityGate(StrictModel):
    name: Literal['engineering', 'source', 'medical', 'license', 'performance', 'training', 'case_baseline', 'cross_source']
    status: Literal['passed', 'blocked', 'not_evaluated']
    reasons: list[str]


class ReviewPreparationReport(StrictModel):
    version: Literal['0.1.0'] = '0.1.0'
    preparation_id: str
    status: Literal['complete', 'partial', 'empty']
    coverage: CoverageInventory
    sources: list[SourceAnnotation]
    candidates: list[CandidateReviewItem]
    anomalies: list[PreparationAnomaly]
    review_records: list[ReviewRecord]
    issues: list[PreparationIssue]
    gates: list[PreparationQualityGate]
    counts: dict[str, int]
    medical_review: Literal['unreviewed'] = 'unreviewed'
    release_allowed: Literal[False] = False


class ReviewPreparationExport(StrictModel):
    version: Literal['0.1.0'] = '0.1.0'
    preparation_id: str
    status: Literal['complete', 'partial', 'empty']
    files: dict[str, str]
    medical_review: Literal['unreviewed'] = 'unreviewed'
    release_allowed: Literal[False] = False


PREPARATION_MODELS = (ReviewPreparationRequest, PreparationWorksheet, SourceAnnotation,
    PreparationQuote, CandidateReviewItem, PreparationAnomaly, PreparationIssue,
    PreparationQualityGate, ReviewPreparationReport, ReviewPreparationExport)
