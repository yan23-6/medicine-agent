from __future__ import annotations

from pydantic import Field

from medicine_agent.domain.clinical import CanonicalCase, SafetyContext, TCMReasoningGraph
from medicine_agent.domain.models import SkillIssue, StrictModel
from medicine_agent.semantics import SemanticContext


class TCMReasoningInput(StrictModel):
    canonical_case: CanonicalCase
    safety_context: SafetyContext
    semantic_context: SemanticContext = Field(
        default_factory=lambda: SemanticContext(
            enabled_profiles=["common", "tcm", "safety"]
        )
    )


class TCMReasoningOutput(StrictModel):
    reasoning_graph: TCMReasoningGraph
    issues: list[SkillIssue] = Field(default_factory=list)
