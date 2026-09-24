from __future__ import annotations

import json
import os
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from medicine_agent.domain.ids import file_sha256, stable_id
from medicine_agent.domain.models import ExperimentalPackageManifest
from medicine_agent.packages.io import validate_package_path, write_jsonl
from medicine_agent.runtime.base import SkillContext, manifest_path
from medicine_agent.runtime.errors import PackageValidationError
from medicine_agent.runtime.manifest import load_manifest
from medicine_agent.skills.knowledge_package_build_validate.models import (
    KnowledgePackageBuildValidateInput,
    KnowledgePackageBuildValidateOutput,
)


class KnowledgePackageBuildValidateSkill:
    manifest = load_manifest(manifest_path(__file__))
    input_model = KnowledgePackageBuildValidateInput
    output_model = KnowledgePackageBuildValidateOutput

    def execute(
        self, value: KnowledgePackageBuildValidateInput, context: SkillContext
    ) -> KnowledgePackageBuildValidateOutput:
        del context
        identity = {
            "source": value.source.model_dump(mode="json"),
            "fragments": [item.model_dump(mode="json") for item in value.fragments],
            "evidence": [item.model_dump(mode="json") for item in value.evidence],
            "knowledge": [item.model_dump(mode="json") for item in value.knowledge],
            "relations": [item.model_dump(mode="json") for item in value.relations],
            "raw_fields": [item.model_dump(mode="json") for item in value.raw_fields],
        }
        package_id = stable_id("pkg", identity)
        output_root = Path(value.output_root).resolve()
        output_root.mkdir(parents=True, exist_ok=True)
        target = output_root / package_id
        if target.exists():
            report = validate_package_path(target)
            if not report.valid:
                raise PackageValidationError(
                    f"Existing package is invalid: {target}",
                    details={"issues": [item.model_dump(mode="json") for item in report.issues]},
                )
            manifest = ExperimentalPackageManifest.model_validate_json(
                (target / "manifest.json").read_text(encoding="utf-8")
            )
            return KnowledgePackageBuildValidateOutput(
                package_path=str(target), manifest=manifest, report=report
            )

        temp_root = Path(tempfile.mkdtemp(prefix="medicine-agent-", dir=output_root))
        work = temp_root / package_id
        work.mkdir()
        try:
            payloads = {
                "sources.jsonl": [value.source.model_dump(mode="json")],
                "fragments.jsonl": [item.model_dump(mode="json") for item in value.fragments],
                "evidence.jsonl": [item.model_dump(mode="json") for item in value.evidence],
                "raw_fields.jsonl": [item.model_dump(mode="json") for item in value.raw_fields],
                "knowledge.jsonl": [item.model_dump(mode="json") for item in value.knowledge],
                "relations.jsonl": [item.model_dump(mode="json") for item in value.relations],
            }
            for file_name, items in payloads.items():
                write_jsonl(work / file_name, items)
            checksums = {
                file_name: file_sha256((work / file_name).read_bytes())
                for file_name in payloads
            }
            manifest = ExperimentalPackageManifest(
                package_id=package_id,
                package_version="0.1.0-experimental",
                protocol_version="0.1.0-experimental",
                status="candidate",
                source_ids=[value.source.source_id],
                created_at=datetime.now(UTC),
                files=checksums,
            )
            (work / "manifest.json").write_text(
                manifest.model_dump_json(indent=2), encoding="utf-8", newline="\n"
            )
            (work / "checksums.json").write_text(
                json.dumps(checksums, ensure_ascii=False, sort_keys=True, indent=2),
                encoding="utf-8",
                newline="\n",
            )
            report = validate_package_path(work)
            quality_dir = work / "quality"
            quality_dir.mkdir()
            (quality_dir / "report.json").write_text(
                report.model_dump_json(indent=2), encoding="utf-8", newline="\n"
            )
            if not report.valid:
                raise PackageValidationError(
                    "Experimental package validation failed",
                    details={"issues": [item.model_dump(mode="json") for item in report.issues]},
                )
            os.replace(work, target)
            return KnowledgePackageBuildValidateOutput(
                package_path=str(target), manifest=manifest, report=report
            )
        finally:
            if temp_root.exists():
                shutil.rmtree(temp_root)

