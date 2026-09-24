from __future__ import annotations

from pydantic import Field

from medicine_agent.domain.models import DocumentFragment, SourceDocument, SourceMetadata, StrictModel


class MaterialIngestionInput(StrictModel):
    path: str
    metadata: SourceMetadata


class MaterialIngestionOutput(StrictModel):
    source: SourceDocument
    fragments: list[DocumentFragment] = Field(default_factory=list)

