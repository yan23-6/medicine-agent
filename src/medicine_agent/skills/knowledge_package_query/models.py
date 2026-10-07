from __future__ import annotations

from pydantic import Field, model_validator

from medicine_agent.domain.models import StrictModel


class KnowledgePackageQueryInput(StrictModel):
    package_path: str
    knowledge_id: str | None = None
    text: str | None = None

    @model_validator(mode="after")
    def require_query(self) -> "KnowledgePackageQueryInput":
        if not self.knowledge_id and not self.text:
            raise ValueError("knowledge_id or text is required")
        return self


class KnowledgePackageQueryOutput(StrictModel):
    matches: list[dict] = Field(default_factory=list)
    evidence: list[dict] = Field(default_factory=list)

