from __future__ import annotations

from pydantic import Field

from medicine_agent.domain.clinical import CanonicalCase, RawCaseRecord
from medicine_agent.domain.models import SkillIssue, StrictModel
from medicine_agent.semantics import SemanticContext


class CaseDistillationInput(StrictModel):
    raw_case: RawCaseRecord
    semantic_context: SemanticContext = Field(default_factory=SemanticContext)


class CaseDistillationOutput(StrictModel):
    canonical_case: CanonicalCase
    issues: list[SkillIssue] = Field(default_factory=list)
