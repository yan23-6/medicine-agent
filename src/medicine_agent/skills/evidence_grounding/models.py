from __future__ import annotations

from pydantic import Field

from medicine_agent.domain.models import DocumentFragment, EvidenceRecord, StrictModel


class EvidenceGroundingInput(StrictModel):
    fragments: list[DocumentFragment]


class EvidenceGroundingOutput(StrictModel):
    evidence: list[EvidenceRecord] = Field(default_factory=list)

