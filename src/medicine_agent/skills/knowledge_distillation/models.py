from __future__ import annotations

from pydantic import Field

from medicine_agent.domain.models import (
    EvidenceRecord,
    KnowledgeCandidate,
    RelationCandidate,
    StrictModel,
)


class KnowledgeDistillationInput(StrictModel):
    evidence: list[EvidenceRecord]
    use_model: bool = False


class KnowledgeDistillationOutput(StrictModel):
    knowledge: list[KnowledgeCandidate] = Field(default_factory=list)
    relations: list[RelationCandidate] = Field(default_factory=list)

