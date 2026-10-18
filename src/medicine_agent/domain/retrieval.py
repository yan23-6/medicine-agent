"""Public contracts for rebuildable multidimensional and local-graph views."""
from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator

from medicine_agent.domain.models import StrictModel
from medicine_agent.domain.tcm_knowledge import KnowledgeAddress


class KnowledgeFacets(StrictModel):
    """Derived query dimensions; never an independent medical assertion."""

    source_types: list[str] = Field(default_factory=list)
    knowledge_types: list[str] = Field(default_factory=list)
    tcm_layers: list[str] = Field(default_factory=list)
    evidence_states: list[str] = Field(default_factory=list)
    applicability: list[str] = Field(default_factory=list)
    governance_states: list[str] = Field(default_factory=list)
    field_ids: list[str] = Field(default_factory=list)


class LocalKnowledgeQuery(StrictModel):
    text: str | None = None
    knowledge_id: str | None = None
    seed_addresses: list[KnowledgeAddress] = Field(default_factory=list)
    subject: str | None = None
    material_type: str | None = None
    medical_profile: str | None = None
    knowledge_layer: str | None = None
    knowledge_category: str | None = None
    knowledge_type: str | None = None
    evidence_state: str | None = None
    topic: str | None = None
    tcm_layer: str | None = None
    max_hops: int = Field(default=2, ge=0, le=8)
    max_nodes: int = Field(default=50, ge=1, le=500)

    @model_validator(mode="after")
    def require_seed(self):
        if not (self.text or self.knowledge_id or self.seed_addresses):
            raise ValueError("text, knowledge_id, or seed_addresses is required")
        if len({(a.package_id, a.node_id) for a in self.seed_addresses}) != len(self.seed_addresses):
            raise ValueError("seed_addresses must be unique")
        return self


class LocalGraphNode(StrictModel):
    address: KnowledgeAddress
    title: str
    statement: str
    facets: KnowledgeFacets
    role: str


class LocalGraphEdge(StrictModel):
    association_id: str
    source: KnowledgeAddress
    target: KnowledgeAddress
    relation: str
    rationale: str
    status: str
    resolution: str


class ConceptLinkCandidate(StrictModel):
    source: KnowledgeAddress
    target: KnowledgeAddress
    candidate_type: str
    score: float = Field(ge=0, le=1)
    matched_terms: list[str] = Field(default_factory=list)
    rationale: str
    status: str = "candidate"


class RetrievalAudit(StrictModel):
    requested_max_hops: int
    requested_max_nodes: int
    visited_nodes: int
    traversed_edges: int
    truncated: bool = False
    missing_seed_addresses: list[KnowledgeAddress] = Field(default_factory=list)
    filters: dict[str, Any] = Field(default_factory=dict)


class LocalKnowledgeGraph(StrictModel):
    nodes: list[LocalGraphNode] = Field(default_factory=list)
    edges: list[LocalGraphEdge] = Field(default_factory=list)
    audit: RetrievalAudit


RETRIEVAL_MODELS = (
    KnowledgeFacets,
    LocalKnowledgeQuery,
    LocalGraphNode,
    LocalGraphEdge,
    ConceptLinkCandidate,
    RetrievalAudit,
    LocalKnowledgeGraph,
)
