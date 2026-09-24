from __future__ import annotations

from typing import Any

from medicine_agent.domain.models import SkillInvocation, SkillManifest, SkillResult
from medicine_agent.runtime.registry import SkillRegistry
from medicine_agent.runtime.runner import SkillRunner


class ApplicationFacade:
    """Transport-neutral application surface for CLI, MCP, REST, and tests."""

    def __init__(self, registry: SkillRegistry, runner: SkillRunner) -> None:
        self.registry = registry
        self.runner = runner

    def list_skills(self) -> list[SkillManifest]:
        return self.registry.list_manifests()

    def describe_skill(self, skill_id: str, version: str | None = None) -> dict[str, Any]:
        skill = self.registry.resolve(skill_id, version)
        return {
            "manifest": skill.manifest.model_dump(mode="json"),
            "input_schema": skill.input_model.model_json_schema(),
            "output_schema": skill.output_model.model_json_schema(),
        }

    def invoke_skill(self, invocation: SkillInvocation) -> SkillResult:
        return self.runner.invoke(invocation)

