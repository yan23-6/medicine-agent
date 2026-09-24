from __future__ import annotations

from pathlib import Path

from medicine_agent.packages.io import read_jsonl, validate_package_path
from medicine_agent.runtime.base import SkillContext, manifest_path
from medicine_agent.runtime.errors import PackageValidationError
from medicine_agent.runtime.manifest import load_manifest
from medicine_agent.skills.knowledge_package_query.models import (
    KnowledgePackageQueryInput,
    KnowledgePackageQueryOutput,
)


class KnowledgePackageQuerySkill:
    manifest = load_manifest(manifest_path(__file__))
    input_model = KnowledgePackageQueryInput
    output_model = KnowledgePackageQueryOutput

    def execute(
        self, value: KnowledgePackageQueryInput, context: SkillContext
    ) -> KnowledgePackageQueryOutput:
        del context
        path = Path(value.package_path).resolve()
        report = validate_package_path(path)
        if not report.valid:
            raise PackageValidationError("Cannot query an invalid package")
        knowledge = read_jsonl(path / "knowledge.jsonl")
        query_text = value.text.casefold() if value.text else None
        matches = [
            item
            for item in knowledge
            if (value.knowledge_id and item.get("knowledge_id") == value.knowledge_id)
            or (
                query_text
                and query_text
                in f"{item.get('label', '')} {item.get('statement', '')}".casefold()
            )
        ]
        evidence_ids = {
            evidence_id
            for item in matches
            for evidence_id in item.get("evidence_refs", [])
        }
        evidence = [
            item
            for item in read_jsonl(path / "evidence.jsonl")
            if item.get("evidence_id") in evidence_ids
        ]
        return KnowledgePackageQueryOutput(matches=matches, evidence=evidence)

