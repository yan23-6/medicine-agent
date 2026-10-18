"""Versioned management contracts; coverage is not medical approval or execution."""
from typing import Literal

from pydantic import Field, field_validator, model_validator

from medicine_agent.domain.models import StrictModel

UnitKind = Literal['physical_page', 'text_line', 'structured_unit', 'image', 'unknown']
Stage = Literal['extraction', 'semantic_candidate']
Fingerprint = str


class CoveragePolicy(StrictModel):
    analysis_policy: str | None = None
    context_policy: str | None = None
    semantic_version: str | None = None


class CoverageHistory(StrictModel):
    source_sha256: Fingerprint | None = Field(default=None, pattern='^[0-9a-f]{64}$')
    unit_kind: UnitKind = 'unknown'
    units: list[int] = Field(default_factory=list, max_length=100000)
    stage: Stage
    reference: str = Field(min_length=1, max_length=512)

    @field_validator('units', mode='before')
    @classmethod
    def bounded_units(cls, values):
        if not isinstance(values, list) or any(type(v) is not int or not 1 <= v <= 100000 for v in values):
            raise ValueError('Units must be positive bounded integers')
        return sorted(set(values))


class CoverageRequest(StrictModel):
    version: Literal['0.1.0'] = '0.1.0'
    source_sha256: Fingerprint = Field(pattern='^[0-9a-f]{64}$')
    unit_kind: UnitKind
    document_unit_count: int = Field(ge=1, le=100000, strict=True)
    units: list[int] = Field(min_length=1, max_length=100000)
    policy: CoveragePolicy = Field(default_factory=lambda: CoveragePolicy(
        analysis_policy='source-faithfulness-v3', context_policy='previous-unit-plus-current-v1',
        semantic_version='0.3.2'))
    history: list[CoverageHistory] = Field(default_factory=list, max_length=10000)

    @field_validator('units', mode='before')
    @classmethod
    def normalize_units(cls, values):
        if not isinstance(values, list) or any(type(v) is not int for v in values):
            raise ValueError('Units must be integer lists')
        return sorted(set(values))

    @model_validator(mode='after')
    def valid_range(self):
        if self.unit_kind == 'unknown' or any(not 1 <= u <= self.document_unit_count for u in self.units):
            raise ValueError('Specify a known unit kind and in-bounds units')
        return self


class CoverageAddress(StrictModel):
    archive: str
    archive_sha256: str
    bundle_id: str
    package_id: str
    manifest_sha256: str
    component: str
    active: bool
    family: str | None = None
    parent: str | None = None
    resources: list[str]


class CoverageRecord(StrictModel):
    source_sha256: str | None = None
    source_id: str | None = None
    unit_kind: UnitKind = 'unknown'
    document_unit_count: int | None = None
    units: list[int] = Field(default_factory=list)
    stage: Stage
    state: Literal['verified', 'historical_pending', 'unknown', 'partial_failed']
    reason: str
    policy: CoveragePolicy = Field(default_factory=CoveragePolicy)
    extraction_methods: list[str] = Field(default_factory=list)
    adapter_versions: dict[str, str] = Field(default_factory=dict)
    address: CoverageAddress | None = None
    history_reference: str | None = None
    integrity_basis: list[str] = Field(default_factory=list)


class CoverageIssue(StrictModel):
    code: str
    archive: str | None = None
    reason: str


class CoverageInventory(StrictModel):
    version: Literal['0.1.0'] = '0.1.0'
    records: list[CoverageRecord]
    issues: list[CoverageIssue]


class CoverageDecision(StrictModel):
    unit: int
    action: Literal['covered', 'held', 'needs_check', 'proposed']
    stage: Stage | None = None
    reason: str
    record_indexes: list[int] = Field(default_factory=list)


class CoveragePlan(StrictModel):
    version: Literal['0.1.0'] = '0.1.0'
    source_sha256: str
    unit_kind: UnitKind
    document_unit_count: int
    policy: CoveragePolicy
    inventory: CoverageInventory
    decisions: list[CoverageDecision]
    unresolved_record_indexes: list[int]
    execution: Literal['plan_only'] = 'plan_only'


COVERAGE_MODELS = (CoveragePolicy, CoverageHistory, CoverageRequest, CoverageAddress,
                   CoverageRecord, CoverageIssue, CoverageInventory, CoverageDecision, CoveragePlan)
