from __future__ import annotations

from pathlib import Path
from typing import Any

from medicine_agent.domain.models import SkillInvocation, SkillResult, SkillStatus, SourceMetadata
from medicine_agent.runtime.facade import ApplicationFacade


def _require_success(result: SkillResult) -> dict[str, Any]:
    if result.status != SkillStatus.SUCCESS or result.output is None:
        codes = ", ".join(issue.code for issue in result.issues)
        raise RuntimeError(f"Skill {result.skill_id} failed: {codes}")
    return result.output


def run_minimal_pipeline(
    facade: ApplicationFacade,
    *,
    input_path: Path,
    output_root: Path,
    metadata: SourceMetadata | None = None,
    use_model: bool = False,
) -> dict[str, Any]:
    source_metadata = metadata or SourceMetadata(
        title=None,
        author=None,
        edition=None,
        publication_year=None,
        publisher=None,
        isbn=None,
    )
    ingestion = _require_success(
        facade.invoke_skill(
            SkillInvocation(
                task_id="pipeline-ingest",
                skill_id="material-ingestion",
                input_data={
                    "path": str(input_path),
                    "metadata": source_metadata.model_dump(mode="json"),
                },
            )
        )
    )
    grounding = _require_success(
        facade.invoke_skill(
            SkillInvocation(
                task_id="pipeline-evidence",
                skill_id="evidence-grounding",
                input_data={"fragments": ingestion["fragments"]},
            )
        )
    )
    distilled = _require_success(
        facade.invoke_skill(
            SkillInvocation(
                task_id="pipeline-distill",
                skill_id="knowledge-distillation",
                input_data={"evidence": grounding["evidence"], "use_model": use_model},
            )
        )
    )
    built = _require_success(
        facade.invoke_skill(
            SkillInvocation(
                task_id="pipeline-build",
                skill_id="knowledge-package-build-validate",
                input_data={
                    "output_root": str(output_root),
                    "source": ingestion["source"],
                    "fragments": ingestion["fragments"],
                    "evidence": grounding["evidence"],
                    "knowledge": distilled["knowledge"],
                    "relations": distilled["relations"],
                    "raw_fields": [],
                },
            )
        )
    )
    first_knowledge_id = distilled["knowledge"][0]["knowledge_id"]
    queried = _require_success(
        facade.invoke_skill(
            SkillInvocation(
                task_id="pipeline-query",
                skill_id="knowledge-package-query",
                input_data={
                    "package_path": built["package_path"],
                    "knowledge_id": first_knowledge_id,
                },
            )
        )
    )
    return {
        "package_path": built["package_path"],
        "package_id": built["manifest"]["package_id"],
        "quality": built["report"],
        "query": queried,
    }

