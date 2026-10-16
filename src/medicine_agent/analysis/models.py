from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from medicine_agent.domain.models import StrictModel, SourceMetadata
from medicine_agent.domain.tcm_knowledge import KnowledgeCategory


class AnalysisError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class DocumentPosition(StrictModel):
    unit: int = Field(ge=1)
    page: int | None = None
    structure_path: str | None = None
    region: list[float] | None = None
    page_size: list[float] | None = None
    coordinate_unit: str | None = None
    origin: str | None = None
    rotation: int = 0
    render_scale: float = 1


class DocumentBlock(StrictModel):
    text: str
    position: DocumentPosition
    confidence: float | None = None


class DocumentUnit(StrictModel):
    index: int = Field(ge=1)
    method: str
    blocks: list[DocumentBlock] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ExtractionInput(StrictModel):
    path: str
    unit: int = Field(ge=1)
    force_ocr: bool = False
    timeout_seconds: int = Field(default=120, ge=1, le=3600)


class PackageClassification(StrictModel):
    knowledge_categories: list[KnowledgeCategory] = Field(default_factory=list)
    subjects: list[str] = Field(default_factory=list)
    material_types: list[Literal["textbook", "paper", "physician_experience", "case_record",
        "clinical_record", "specialty_material", "unknown"]] = Field(default_factory=list)
    medical_profiles: list[Literal["common", "tcm", "western", "safety", "formula"]] = Field(
        default_factory=lambda: ["common"])
    knowledge_layers: list[Literal["general_pathomechanism", "physician_experience", "individual_case"]] = Field(default_factory=list)
    status: Literal["unclassified", "declared", "candidate"] = "unclassified"
    basis: list[str] = Field(default_factory=list)


class PackageRevision(StrictModel):
    family: str
    task_id: str
    source_sha256: str
    parent: str | None
    sequence: int = Field(ge=1)
    units: list[int]
    review_status: Literal["unreviewed"] = "unreviewed"
    warnings: list[str] = Field(default_factory=list)
    allowed_use: str | None = None
    runtime: dict[str, Any] | None = None
    processing_scope: dict[str, Any] | None = None
    classification: PackageClassification = Field(default_factory=PackageClassification)
    changes: dict[str, list[int]]


class AnalysisRequest(StrictModel):
    paths: list[str] = Field(min_length=1)
    units: list[int] | None = None
    mode: Literal["extractive", "model"] = "model"
    force_ocr: bool = False
    metadata: SourceMetadata = Field(default_factory=lambda: SourceMetadata(
        title=None, author=None, edition=None, publication_year=None,
        publisher=None, isbn=None,
    ))
    allowed_use: str = Field(min_length=1)
    parent_package: str | None = None
    timeout_seconds: int = Field(default=120, ge=1, le=3600)
    max_attempts: int = Field(default=2, ge=1, le=5)
    classification: PackageClassification = Field(default_factory=PackageClassification)


class TaskCheckpoint(StrictModel):
    task_id: str
    parent_task_id: str
    role: str
    status: str
    unit_count: int
    extracted: int
    analyzed: int
    next_unit: int | None
    package_path: str | None = None
    errors: list[dict[str, Any]] = Field(default_factory=list)
