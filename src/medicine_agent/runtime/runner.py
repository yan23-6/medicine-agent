from __future__ import annotations

from datetime import UTC, datetime
from time import perf_counter
from typing import Any
from uuid import uuid4

from pydantic import ValidationError

from medicine_agent.domain.ids import stable_id
from medicine_agent.domain.models import (
    GenerationMethod,
    IssueSeverity,
    ReviewStatus,
    RunRecord,
    SkillInvocation,
    SkillIssue,
    SkillResult,
    SkillStatus,
)
from medicine_agent.runtime.base import SkillContext
from medicine_agent.runtime.errors import PlatformError
from medicine_agent.runtime.registry import SkillRegistry
from medicine_agent.runtime.run_store import InMemoryRunRecordStore, RunRecordStore


def _collect_evidence_refs(value: Any) -> list[str]:
    found: set[str] = set()

    def visit(item: Any) -> None:
        if isinstance(item, dict):
            refs = item.get("evidence_refs")
            if isinstance(refs, list):
                found.update(ref for ref in refs if isinstance(ref, str))
            for child in item.values():
                visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)

    visit(value)
    return sorted(found)


class SkillRunner:
    def __init__(
        self,
        registry: SkillRegistry,
        context: SkillContext | None = None,
        run_store: RunRecordStore | None = None,
    ) -> None:
        self.registry = registry
        self.context = context or SkillContext()
        self.run_store = run_store or InMemoryRunRecordStore()

    def invoke(self, invocation: SkillInvocation) -> SkillResult:
        started = datetime.now(UTC)
        start_clock = perf_counter()
        invocation_id = f"run_{uuid4().hex}"
        input_id = stable_id(
            "input",
            {
                "skill_id": invocation.skill_id,
                "version": invocation.skill_version,
                "input": invocation.input_data,
            },
        )
        version = invocation.skill_version or "unresolved"
        input_schema_id = "unavailable"
        output_schema_id = "unavailable"
        output_id: str | None = None
        generation_method = GenerationMethod.RULE
        review_status = ReviewStatus.UNREVIEWED
        evidence_refs: list[str] = []
        runtime: dict[str, Any] = {"runner_version": "0.2.0"}
        model_client = self.context.model_client
        if model_client is not None:
            runtime.update(
                {
                    "model_provider": model_client.provider,
                    "model": model_client.model,
                }
            )
        try:
            skill = self.registry.resolve(invocation.skill_id, invocation.skill_version)
            version = skill.manifest.version
            input_schema_id = f"{skill.manifest.skill_id}@{version}:input"
            output_schema_id = f"{skill.manifest.skill_id}@{version}:output"
            try:
                value = skill.input_model.model_validate(invocation.input_data)
            except ValidationError as exc:
                status = SkillStatus.FAILURE
                payload = None
                issues = [
                    SkillIssue(
                        code="INPUT_SCHEMA_INVALID",
                        severity=IssueSeverity.ERROR,
                        message="Skill input failed schema validation",
                        details={"errors": exc.errors(include_url=False)},
                    )
                ]
                return self._finalize(
                    invocation=invocation,
                    invocation_id=invocation_id,
                    input_id=input_id,
                    output_id=output_id,
                    version=version,
                    input_schema_id=input_schema_id,
                    output_schema_id=output_schema_id,
                    status=status,
                    payload=payload,
                    issues=issues,
                    evidence_refs=evidence_refs,
                    generation_method=generation_method,
                    review_status=review_status,
                    runtime=runtime,
                    started=started,
                    start_clock=start_clock,
                )
            output = skill.execute(value, self.context)
            try:
                validated = skill.output_model.model_validate(output)
            except ValidationError as exc:
                status = SkillStatus.FAILURE
                payload = None
                issues = [
                    SkillIssue(
                        code="OUTPUT_SCHEMA_INVALID",
                        severity=IssueSeverity.ERROR,
                        message="Skill output failed schema validation",
                        details={"errors": exc.errors(include_url=False)},
                    )
                ]
                return self._finalize(
                    invocation=invocation,
                    invocation_id=invocation_id,
                    input_id=input_id,
                    output_id=output_id,
                    version=version,
                    input_schema_id=input_schema_id,
                    output_schema_id=output_schema_id,
                    status=status,
                    payload=payload,
                    issues=issues,
                    evidence_refs=evidence_refs,
                    generation_method=generation_method,
                    review_status=review_status,
                    runtime=runtime,
                    started=started,
                    start_clock=start_clock,
                )
            payload: dict[str, Any] | None = validated.model_dump(mode="json")
            issues = list(getattr(validated, "issues", []))
            status = SkillStatus.PARTIAL if issues else SkillStatus.SUCCESS
            evidence_refs = _collect_evidence_refs(payload)
            methods = {
                item
                for item in self._collect_values(payload, "generation_method")
                if item in {method.value for method in GenerationMethod}
            }
            if GenerationMethod.MODEL.value in methods:
                generation_method = GenerationMethod.MODEL
            output_id = stable_id("output", payload)
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
        return self._finalize(
            invocation=invocation,
            invocation_id=invocation_id,
            input_id=input_id,
            output_id=output_id,
            version=version,
            input_schema_id=input_schema_id,
            output_schema_id=output_schema_id,
            status=status,
            payload=payload,
            issues=issues,
            evidence_refs=evidence_refs,
            generation_method=generation_method,
            review_status=review_status,
            runtime=runtime,
            started=started,
            start_clock=start_clock,
        )

    @staticmethod
    def _collect_values(value: Any, key: str) -> list[Any]:
        found: list[Any] = []
        if isinstance(value, dict):
            if key in value:
                found.append(value[key])
            for child in value.values():
                found.extend(SkillRunner._collect_values(child, key))
        elif isinstance(value, list):
            for child in value:
                found.extend(SkillRunner._collect_values(child, key))
        return found

    def _finalize(
        self,
        *,
        invocation: SkillInvocation,
        invocation_id: str,
        input_id: str,
        output_id: str | None,
        version: str,
        input_schema_id: str,
        output_schema_id: str,
        status: SkillStatus,
        payload: dict[str, Any] | None,
        issues: list[SkillIssue],
        evidence_refs: list[str],
        generation_method: GenerationMethod,
        review_status: ReviewStatus,
        runtime: dict[str, Any],
        started: datetime,
        start_clock: float,
    ) -> SkillResult:
        completed = datetime.now(UTC)
        duration_ms = max(0, int((perf_counter() - start_clock) * 1000))
        result = SkillResult(
            invocation_id=invocation_id,
            task_id=invocation.task_id,
            skill_id=invocation.skill_id,
            skill_version=version,
            input_id=input_id,
            output_id=output_id,
            status=status,
            output=payload,
            issues=issues,
            evidence_refs=evidence_refs,
            generation_method=generation_method,
            review_status=review_status,
            runtime=runtime,
            started_at=started,
            completed_at=completed,
            duration_ms=duration_ms,
        )
        self.run_store.save(
            RunRecord(
                invocation_id=invocation_id,
                task_id=invocation.task_id,
                caller=invocation.caller,
                skill_id=invocation.skill_id,
                skill_version=version,
                input_id=input_id,
                output_id=output_id,
                input_schema_id=input_schema_id,
                output_schema_id=output_schema_id,
                status=status,
                issues=issues,
                evidence_refs=evidence_refs,
                generation_method=generation_method,
                review_status=review_status,
                runtime=runtime,
                started_at=started,
                completed_at=completed,
                duration_ms=duration_ms,
            )
        )
        return result

