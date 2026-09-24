from __future__ import annotations

from pydantic import Field

from medicine_agent.domain.models import (
    DocumentFragment,
    EvidenceRecord,
    ExperimentalPackageManifest,
    KnowledgeCandidate,
    QualityReport,
    RawFieldObservation,
    RelationCandidate,
    SourceDocument,
    StrictModel,
)


class KnowledgePackageBuildValidateInput(StrictModel):
    output_root: str
    source: SourceDocument
    fragments: list[DocumentFragment]
    evidence: list[EvidenceRecord]
    knowledge: list[KnowledgeCandidate]
    relations: list[RelationCandidate] = Field(default_factory=list)
    raw_fields: list[RawFieldObservation] = Field(default_factory=list)


class KnowledgePackageBuildValidateOutput(StrictModel):
    package_path: str
    manifest: ExperimentalPackageManifest
    report: QualityReport

