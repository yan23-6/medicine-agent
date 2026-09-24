from __future__ import annotations

from datetime import UTC, datetime
from time import perf_counter
from typing import Any

from pydantic import ValidationError

from medicine_agent.domain.ids import stable_id
from medicine_agent.domain.models import (
    GenerationMethod,
    IssueSeverity,
    SkillInvocation,
    SkillIssue,
    SkillResult,
    SkillStatus,
)
from medicine_agent.runtime.base import SkillContext
from medicine_agent.runtime.errors import PlatformError
from medicine_agent.runtime.registry import SkillRegistry


class SkillRunner:
    def __init__(self, registry: SkillRegistry, context: SkillContext | None = None) -> None:
        self.registry = registry
        self.context = context or SkillContext()

    def invoke(self, invocation: SkillInvocation) -> SkillResult:
        started = datetime.now(UTC)
        start_clock = perf_counter()
        invocation_id = stable_id(
            "run",
            {
                "task_id": invocation.task_id,
                "skill_id": invocation.skill_id,
                "version": invocation.skill_version,
                "input": invocation.input_data,
            },
        )
        version = invocation.skill_version or "unresolved"
        try:
            skill = self.registry.resolve(invocation.skill_id, invocation.skill_version)
            version = skill.manifest.version
            try:
                value = skill.input_model.model_validate(invocation.input_data)
            except ValidationError as exc:
                completed = datetime.now(UTC)
                return SkillResult(
                    invocation_id=invocation_id,
                    task_id=invocation.task_id,
                    skill_id=invocation.skill_id,
                    skill_version=version,
                    status=SkillStatus.FAILURE,
                    issues=[
                        SkillIssue(
                            code="INPUT_SCHEMA_INVALID",
                            severity=IssueSeverity.ERROR,
                            message="Skill input failed schema validation",
                            details={"errors": exc.errors(include_url=False)},
                        )
                    ],
                    runtime={"runner_version": "0.1.0"},
                    started_at=started,
                    completed_at=completed,
                    duration_ms=max(0, int((perf_counter() - start_clock) * 1000)),
                )
            output = skill.execute(value, self.context)
            try:
                validated = skill.output_model.model_validate(output)
            except ValidationError as exc:
                completed = datetime.now(UTC)
                return SkillResult(
                    invocation_id=invocation_id,
                    task_id=invocation.task_id,
                    skill_id=invocation.skill_id,
                    skill_version=version,
                    status=SkillStatus.FAILURE,
                    issues=[
                        SkillIssue(
                            code="OUTPUT_SCHEMA_INVALID",
                            severity=IssueSeverity.ERROR,
                            message="Skill output failed schema validation",
                            details={"errors": exc.errors(include_url=False)},
                        )
                    ],
                    runtime={"runner_version": "0.1.0"},
                    started_at=started,
                    completed_at=completed,
                    duration_ms=max(0, int((perf_counter() - start_clock) * 1000)),
                )
            status = SkillStatus.SUCCESS
            issues: list[SkillIssue] = []
            payload: dict[str, Any] | None = validated.model_dump(mode="json")
        except PlatformError as exc:
            status = SkillStatus.FAILURE
            payload = None
            issues = [
                SkillIssue(
                    code=exc.code,
                    severity=IssueSeverity.ERROR,
                    message=exc.message,
                    details=exc.details,
                )
            ]
        except Exception as exc:  # Top-level isolation boundary.
            status = SkillStatus.FAILURE
            payload = None
            issues = [
                SkillIssue(
                    code="INTERNAL_ERROR",
                    severity=IssueSeverity.ERROR,
                    message=f"Unhandled {type(exc).__name__}",
                )
            ]
        completed = datetime.now(UTC)
        return SkillResult(
            invocation_id=invocation_id,
            task_id=invocation.task_id,
            skill_id=invocation.skill_id,
            skill_version=version,
            status=status,
            output=payload,
            issues=issues,
            generation_method=GenerationMethod.RULE,
            runtime={"runner_version": "0.1.0"},
            started_at=started,
            completed_at=completed,
            duration_ms=max(0, int((perf_counter() - start_clock) * 1000)),
        )

