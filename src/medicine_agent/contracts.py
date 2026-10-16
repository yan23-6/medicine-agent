from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from medicine_agent.domain.ids import file_sha256
from medicine_agent.domain.clinical import (
    BooleanValue,
    CanonicalCase,
    CaseUncertainty,
    ClinicalReasoningGraph,
    ClinicalObservation,
    Coding,
    CodeableConcept,
    CodedValue,
    DateTimeValue,
    EvidenceLink,
    Encounter,
    HistoricalRecord,
    Identifier,
    IntegerValue,
    MissingValue,
    NamedAttribute,
    PatientProfile,
    Participant,
    PeriodValue,
    Quantity,
    QuantityValue,
    RawCaseEncounter,
    RawCaseField,
    RawCaseRecord,
    RangeValue,
    RatioValue,
    ReferenceValue,
    ReasoningEdge,
    ReasoningNode,
    SafetyContext,
    TCMReasoningGraph,
    TemporalExtent,
    TextValue,
)
from medicine_agent.domain.models import (
    DocumentFragment,
    EvidenceRecord,
    ExperimentalPackageManifest,
    FieldMappingCandidate,
    KnowledgeCandidate,
    QualityReport,
    RawFieldObservation,
    RelationCandidate,
    RunRecord,
    SkillInvocation,
    SkillIssue,
    SkillManifest,
    SkillResult,
    SourceDocument,
    SourceMetadata,
)
from medicine_agent.runtime.facade import ApplicationFacade
from medicine_agent.semantics import SemanticContext, SemanticRegistry


COMMON_MODELS: tuple[type[BaseModel], ...] = (
    SourceMetadata,
    SourceDocument,
    DocumentFragment,
    EvidenceRecord,
    FieldMappingCandidate,
    RawFieldObservation,
    KnowledgeCandidate,
    RelationCandidate,
    SkillIssue,
    SkillManifest,
    SkillInvocation,
    SkillResult,
    RunRecord,
    QualityReport,
    ExperimentalPackageManifest,
)

T02_CLINICAL_MODELS: tuple[type[BaseModel], ...] = (
    SemanticContext,
    SemanticRegistry,
    Identifier,
    Coding,
    CodeableConcept,
    TemporalExtent,
    Quantity,
    TextValue,
    CodedValue,
    QuantityValue,
    RangeValue,
    RatioValue,
    BooleanValue,
    IntegerValue,
    DateTimeValue,
    PeriodValue,
    ReferenceValue,
    MissingValue,
    NamedAttribute,
    Participant,
    PatientProfile,
    RawCaseField,
    RawCaseEncounter,
    RawCaseRecord,
    ClinicalObservation,
    HistoricalRecord,
    CaseUncertainty,
    Encounter,
    CanonicalCase,
    SafetyContext,
    EvidenceLink,
    ReasoningNode,
    ReasoningEdge,
    ClinicalReasoningGraph,
    TCMReasoningGraph,
)

T01_SKILL_IDS = {
    "material-ingestion",
    "evidence-grounding",
    "knowledge-distillation",
    "knowledge-package-build-validate",
    "knowledge-package-query",
    "quality-evaluation",
}


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def export_schemas(
    facade: ApplicationFacade,
    output_root: Path,
    *,
    contract_set: str = "t01",
) -> dict[str, Any]:
    if contract_set not in {"t01", "t02", "t02p", "tcm", 'review', 'correction', 'owned-analysis','learning'}:
        raise ValueError(f"Unsupported contract set: {contract_set}")
    output_root = output_root.resolve()
    written: list[Path] = []
    common_models = COMMON_MODELS + (T02_CLINICAL_MODELS if contract_set == "t02" else ())
    if contract_set in {"t02p", "tcm"}:
        from medicine_agent.analysis.models import (
            AnalysisRequest, DocumentPosition, DocumentBlock, DocumentUnit, ExtractionInput,
            TaskCheckpoint,
            PackageClassification, PackageRevision,
        )
        common_models += (AnalysisRequest, DocumentPosition, DocumentBlock, DocumentUnit,
                          ExtractionInput, TaskCheckpoint, PackageClassification, PackageRevision,
                          SemanticRegistry, SemanticContext)
    if contract_set == 'tcm':
        from medicine_agent.domain.tcm_knowledge import TCM_MODELS
        common_models += TCM_MODELS
    if contract_set == 'review':
        from medicine_agent.domain.reviews import REVIEW_MODELS
        common_models += REVIEW_MODELS
    if contract_set == 'correction':
        from medicine_agent.domain.corrections import CORRECTION_MODELS
        common_models += CORRECTION_MODELS
    if contract_set == 'owned-analysis':
        from medicine_agent.domain.owned_analysis import OWNED_MODELS
        common_models += OWNED_MODELS
    if contract_set == 'learning':
        from medicine_agent.domain.learning import LEARNING_MODELS
        common_models += LEARNING_MODELS
    for model in common_models:
        path = output_root / "common" / f"{model.__name__}.schema.json"
        _write_json(path, model.model_json_schema())
        written.append(path)

    for manifest in facade.list_skills():
        if contract_set in {'review', 'correction', 'owned-analysis','learning'}:
            continue
        if contract_set != 'tcm' and manifest.skill_id == 'tcm-knowledge-analysis':
            continue
        if contract_set in {"t01", "t02"} and manifest.skill_id == "document-extraction":
            continue
        if contract_set == "t01" and manifest.skill_id not in T01_SKILL_IDS:
            continue
        description = facade.describe_skill(manifest.skill_id, manifest.version)
        skill_root = output_root / "skills" / manifest.skill_id / manifest.version
        input_path = skill_root / "input.schema.json"
        output_path = skill_root / "output.schema.json"
        manifest_path = skill_root / "manifest.json"
        _write_json(input_path, description["input_schema"])
        _write_json(output_path, description["output_schema"])
        _write_json(manifest_path, description["manifest"])
        written.extend([input_path, output_path, manifest_path])

    files = {
        path.relative_to(output_root).as_posix(): file_sha256(path.read_bytes())
        for path in sorted(written)
    }
    index = {
        "contract_set": contract_set,
        "contract_version": {"t01": "0.1.0", "t02": "0.4.0", "t02p": "0.2.0", "tcm": "0.2.0", 'review': '0.1.0', 'correction': '0.1.0', 'owned-analysis': '0.2.0','learning':'0.1.0'}[contract_set],
        "files": files,
    }
    _write_json(output_root / "schema-index.json", index)
    return index
