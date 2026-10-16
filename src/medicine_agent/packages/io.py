from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from medicine_agent.domain.ids import file_sha256
from medicine_agent.domain.models import (
    IssueSeverity, QualityReport, SkillIssue, ExperimentalPackageManifest,
    SourceDocument, DocumentFragment, EvidenceRecord, KnowledgeCandidate, RelationCandidate,
    RawFieldObservation, RunRecord,
)
from pydantic import ValidationError


def write_jsonl(path: Path, values: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        for value in values:
            stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True))
            stream.write("\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def validate_package_path(package_path: Path) -> QualityReport:
    issues: list[SkillIssue] = []
    manifest_path = package_path / "manifest.json"
    if not manifest_path.exists():
        return QualityReport(
            valid=False,
            issues=[
                SkillIssue(
                    code="PACKAGE_MANIFEST_MISSING",
                    severity=IssueSeverity.ERROR,
                    message="manifest.json is missing",
                )
            ],
        )
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        ExperimentalPackageManifest.model_validate(manifest)
        if manifest["protocol_version"] != "0.1.0-experimental":
            raise ValueError("Unsupported package protocol")
        required = {"sources.jsonl", "fragments.jsonl", "evidence.jsonl", "knowledge.jsonl",
                    "relations.jsonl", "raw_fields.jsonl", "runs.jsonl"}
        if not required <= manifest["files"].keys():
            raise ValueError("Manifest omits required files")
    except (OSError, ValueError, ValidationError, TypeError):
        return QualityReport(
            valid=False,
            issues=[
                SkillIssue(
                    code="PACKAGE_MANIFEST_INVALID",
                    severity=IssueSeverity.ERROR,
                    message="manifest.json is not valid JSON",
                )
            ],
        )
    for relative_name, expected in manifest.get("files", {}).items():
        path = package_path / relative_name
        if not path.resolve().is_relative_to(package_path.resolve()):
            issues.append(SkillIssue(code="PACKAGE_PATH_INVALID", severity=IssueSeverity.ERROR,
                message="Package resource escapes package directory"))
            continue
        if not path.exists():
            issues.append(
                SkillIssue(
                    code="PACKAGE_FILE_MISSING",
                    severity=IssueSeverity.ERROR,
                    message=f"Package file is missing: {relative_name}",
                    path=relative_name,
                )
            )
            continue
        actual = file_sha256(path.read_bytes())
        if actual != expected:
            issues.append(
                SkillIssue(
                    code="PACKAGE_CHECKSUM_MISMATCH",
                    severity=IssueSeverity.ERROR,
                    message=f"Checksum mismatch: {relative_name}",
                    path=relative_name,
                )
            )
    if any(issue.code in {"PACKAGE_PATH_INVALID", "PACKAGE_FILE_MISSING"} for issue in issues):
        return QualityReport(valid=False, issues=issues)
    try:
        evidence_records = read_jsonl(package_path / "evidence.jsonl")
        knowledge = read_jsonl(package_path / "knowledge.jsonl")
        relations = read_jsonl(package_path / "relations.jsonl")
        sources = read_jsonl(package_path / "sources.jsonl")
        fragments = read_jsonl(package_path / "fragments.jsonl")
        raw_fields = read_jsonl(package_path / "raw_fields.jsonl")
        runs = read_jsonl(package_path / "runs.jsonl")
        for records, model, identity in ((sources, SourceDocument, "source_id"),
            (fragments, DocumentFragment, "fragment_id"),
            (evidence_records, EvidenceRecord, "evidence_id"),
            (knowledge, KnowledgeCandidate, "knowledge_id"),
            (relations, RelationCandidate, "relation_id")):
            for item in records:
                model.model_validate(item)
            if len({item[identity] for item in records}) != len(records):
                raise ValueError("Duplicate identity")
        for records, model in ((raw_fields, RawFieldObservation), (runs, RunRecord)):
            for item in records:
                model.model_validate(item)
        evidence = {item["evidence_id"] for item in evidence_records}
        source_ids = {item["source_id"] for item in sources}
        fragment_ids = {item["fragment_id"] for item in fragments}
        knowledge_ids = {item["knowledge_id"] for item in knowledge}
        if set(manifest["source_ids"]) != source_ids:
            raise ValueError("Manifest source identity differs")
        if any(item["source_knowledge_id"] not in knowledge_ids or
               item["target_knowledge_id"] not in knowledge_ids for item in relations):
            raise ValueError("Broken relation endpoint")
        if any(item["source_id"] not in source_ids for item in fragments + evidence_records):
            raise ValueError("Broken source reference")
        if any(item["fragment_id"] not in fragment_ids for item in evidence_records):
            raise ValueError("Broken fragment reference")
        from medicine_agent.packages.tcm import read_graph
        read_graph(package_path)
        from medicine_agent.packages.corrections import read_corrections
        read_corrections(package_path)
        from medicine_agent.packages.owned import read_owned_cache
        read_owned_cache(package_path)
    except (OSError, ValueError, KeyError, TypeError, ValidationError):
        return QualityReport(valid=False, issues=[SkillIssue(code="PACKAGE_CONTENT_INVALID",
            severity=IssueSeverity.ERROR, message="Invalid package records or identities")])
    for item in knowledge + relations:
        for evidence_id in item.get("evidence_refs", []):
            if evidence_id not in evidence:
                issues.append(
                    SkillIssue(
                        code="EVIDENCE_TRACE_BROKEN",
                        severity=IssueSeverity.ERROR,
                        message=f"Missing evidence reference: {evidence_id}",
                        path=item.get("knowledge_id"),
                    )
                )
    for item in raw_fields:
        status = item.get("mapping_status")
        if status == "ambiguous":
            issues.append(
                SkillIssue(
                    code="AMBIGUOUS_FIELD_MAPPING",
                    severity=IssueSeverity.WARNING,
                    message=f"Ambiguous field mapping preserved: {item.get('raw_key', '')}",
                    path=item.get("observation_id"),
                )
            )
        elif status == "unmapped":
            issues.append(
                SkillIssue(
                    code="UNMAPPED_FIELD_PRESERVED",
                    severity=IssueSeverity.WARNING,
                    message=f"Unmapped field preserved: {item.get('raw_key', '')}",
                    path=item.get("observation_id"),
                )
            )
    counts = {
        "sources": len(read_jsonl(package_path / "sources.jsonl")),
        "fragments": len(read_jsonl(package_path / "fragments.jsonl")),
        "evidence": len(evidence),
        "raw_fields": len(raw_fields),
        "knowledge": len(knowledge),
        "relations": len(read_jsonl(package_path / "relations.jsonl")),
        "runs": len(runs),
    }
    return QualityReport(
        valid=not any(issue.severity == IssueSeverity.ERROR for issue in issues),
        issues=issues,
        counts=counts,
    )

