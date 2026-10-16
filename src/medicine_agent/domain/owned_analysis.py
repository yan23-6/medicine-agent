"""Operational ownership and portable checkpoints; no patient identity semantics."""
from typing import Any, Literal
from pydantic import Field, field_validator, model_validator

from medicine_agent.analysis.models import AnalysisRequest, DocumentUnit
from medicine_agent.domain.models import (StrictModel, EvidenceRecord, DocumentFragment,
                                          KnowledgeCandidate, RelationCandidate)
from medicine_agent.domain.tcm_knowledge import TCMKnowledgeGraph


class OwnedAnalysisRequest(AnalysisRequest):
    owner_id: str | None = Field(default=None, min_length=1, max_length=128)

    @field_validator('owner_id')
    @classmethod
    def declared_owner(cls, value):
        if value is not None and value != value.strip():
            raise ValueError('Owner ID must be nonblank without surrounding whitespace')
        return value


class UnitAnalysis(StrictModel):
    current_evidence: list[EvidenceRecord]
    fragments: list[DocumentFragment]
    knowledge: list[KnowledgeCandidate]
    relations: list[RelationCandidate]
    tcm_graph: TCMKnowledgeGraph | None
    warnings: list[str]


class CachedAnalysisUnit(StrictModel):
    ordinal: int = Field(ge=1)
    predecessor_unit: int | None = Field(default=None, ge=1)
    extraction: DocumentUnit
    analysis: UnitAnalysis


class OwnedAnalysisCache(StrictModel):
    version: Literal['0.1.0'] = '0.1.0'
    owner_id: str = Field(min_length=1, max_length=128)
    derivation_id: str | None = None
    content_package_id: str
    source_sha256: str = Field(pattern='^[0-9a-f]{64}$')
    source_id: str
    runtime: dict[str, Any]
    options_fingerprint: str = Field(pattern='^[0-9a-f]{64}$')
    document_unit_count: int = Field(ge=1)
    units: list[CachedAnalysisUnit] = Field(min_length=1)
    reused_from_package_id: str | None = None
    reused_analysis_units: list[int] = Field(default_factory=list)
    reused_extraction_units: list[int] = Field(default_factory=list)
    invalidated_context_units: list[int] = Field(default_factory=list)

    @model_validator(mode='after')
    def check_units(self):
        ids = [u.ordinal for u in self.units]
        if len(set(ids)) != len(ids) or ids != sorted(ids) or ids[-1] > self.document_unit_count:
            raise ValueError('Cached units must be unique, ordered and within the document')
        for unit in self.units:
            if unit.extraction.index != unit.ordinal:
                raise ValueError('Cached extraction refers to another unit')
            if unit.predecessor_unit != (unit.ordinal - 1 if unit.ordinal - 1 in ids else None):
                raise ValueError('Cached analysis has the wrong adjacent context')
        for values in (self.reused_analysis_units, self.reused_extraction_units, self.invalidated_context_units):
            if values != sorted(set(values)) or not set(values) <= set(ids):
                raise ValueError('Invalid reuse summary')
        if not set(self.reused_analysis_units) <= set(self.reused_extraction_units):
            raise ValueError('Analysis reuse requires verified extraction')
        return self


OWNED_MODELS = (OwnedAnalysisRequest, UnitAnalysis, CachedAnalysisUnit, OwnedAnalysisCache)
