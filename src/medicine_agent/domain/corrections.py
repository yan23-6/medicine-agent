"""Versioned operational provenance for explicit user corrections."""
from typing import Literal
from pydantic import Field, model_validator
from medicine_agent.domain.models import StrictModel
from medicine_agent.domain.reviews import ReviewRecord
from medicine_agent.domain.tcm_knowledge import TCMKnowledgeGraph
from medicine_agent.analysis.models import PackageRevision


class CorrectionRequest(StrictModel):
    parent_path: str = Field(min_length=1)
    review_ids: list[str] = Field(min_length=1)

    @model_validator(mode='after')
    def unique_reviews(self):
        if len(set(self.review_ids)) != len(self.review_ids):
            raise ValueError('Review IDs must be unique')
        return self


class CorrectionEvent(StrictModel):
    parent_package_id: str
    package_id: str
    parent_revision: PackageRevision
    parent_graph: TCMKnowledgeGraph
    reviews: list[ReviewRecord] = Field(min_length=1)
    review_history: list[ReviewRecord] = Field(min_length=1)
    node_mapping: dict[str, str]
    # Digests of unchanged source, evidence and other inherited resources.
    preserved_files: dict[str, str]
    origin: Literal['user_entered'] = 'user_entered'


class CorrectionBundle(StrictModel):
    version: Literal['0.1.0'] = '0.1.0'
    history: list[CorrectionEvent] = Field(min_length=1)


CORRECTION_MODELS = (CorrectionRequest, CorrectionEvent, CorrectionBundle)
