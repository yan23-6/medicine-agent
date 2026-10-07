from __future__ import annotations

from typing import Any

from medicine_agent.domain.models import (
    RunRecord,
    SkillInvocation,
    SkillManifest,
    SkillResult,
    SkillStatus,
)
from medicine_agent.runtime.errors import PlatformError, RunNotFoundError
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

    def validate_package(self, package_path: str) -> dict[str, Any]:
        return self._require_output(
            self.invoke_skill(
                SkillInvocation(
                    task_id="facade-validate-package",
                    skill_id="quality-evaluation",
                    input_data={"package_path": package_path},
                    caller="facade",
                )
            )
        )

    def query_package(
        self,
        package_path: str,
        *,
        knowledge_id: str | None = None,
        text: str | None = None,
    ) -> dict[str, Any]:
        return self._require_output(
            self.invoke_skill(
                SkillInvocation(
                    task_id="facade-query-package",
                    skill_id="knowledge-package-query",
                    input_data={
                        "package_path": package_path,
                        "knowledge_id": knowledge_id,
                        "text": text,
                    },
                    caller="facade",
                )
            )
        )

    def trace_evidence(self, package_path: str, knowledge_id: str) -> dict[str, Any]:
        result = self.query_package(package_path, knowledge_id=knowledge_id)
        return {
            "knowledge_id": knowledge_id,
            "matches": result["matches"],
            "evidence": result["evidence"],
        }

    def get_run(self, invocation_id: str) -> RunRecord:
        record = self.runner.run_store.get(invocation_id)
        if record is None:
            raise RunNotFoundError(f"Run not found: {invocation_id}")
        return record

    def list_runs(self) -> list[RunRecord]:
        return self.runner.run_store.list_records()

    @staticmethod
    def _require_output(result: SkillResult) -> dict[str, Any]:
        if result.status not in {SkillStatus.SUCCESS, SkillStatus.PARTIAL}:
            issue = result.issues[0] if result.issues else None
            raise PlatformError(
                issue.message if issue else "Skill invocation failed",
                details={"issues": [item.model_dump(mode="json") for item in result.issues]},
            )
        return result.output or {}

