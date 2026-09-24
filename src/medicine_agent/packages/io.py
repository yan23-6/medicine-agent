from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from medicine_agent.domain.ids import file_sha256
from medicine_agent.domain.models import IssueSeverity, QualityReport, SkillIssue


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
    except (OSError, json.JSONDecodeError):
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
    evidence = {item["evidence_id"] for item in read_jsonl(package_path / "evidence.jsonl")}
    knowledge = read_jsonl(package_path / "knowledge.jsonl")
    for item in knowledge:
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
    counts = {
        "sources": len(read_jsonl(package_path / "sources.jsonl")),
        "fragments": len(read_jsonl(package_path / "fragments.jsonl")),
        "evidence": len(evidence),
        "raw_fields": len(read_jsonl(package_path / "raw_fields.jsonl")),
        "knowledge": len(knowledge),
        "relations": len(read_jsonl(package_path / "relations.jsonl")),
    }
    return QualityReport(
        valid=not any(issue.severity == IssueSeverity.ERROR for issue in issues),
        issues=issues,
        counts=counts,
    )

