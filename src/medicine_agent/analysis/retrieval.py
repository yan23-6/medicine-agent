"""Deterministic views used by multidimensional and map-like retrieval."""
from __future__ import annotations

from medicine_agent.domain.retrieval import KnowledgeFacets


def derive_facets(node: dict, package: dict) -> dict:
    classification = package.get("classification") or {}
    groups = node.get("groups") or []
    facts = [fact for group in groups for fact in (group.get("facts") or [])]
    knowledge_types = [*(node.get("categories") or []), *(g.get("kind") for g in groups if g.get("kind"))]
    evidence_states = [*(f.get("state", "stated") for f in facts), node.get("review_status", "unreviewed")]
    applicability = [*(node.get("topics") or []), *(classification.get("subjects") or [])]
    governance = [node.get("review_status", "unreviewed"), package.get("state", "research_candidate"),
                  classification.get("status", "unclassified")]
    value = KnowledgeFacets(
        source_types=sorted(set(classification.get("material_types") or [])),
        knowledge_types=sorted(set(knowledge_types)),
        tcm_layers=sorted(set(classification.get("knowledge_layers") or [])),
        evidence_states=sorted(set(evidence_states)),
        applicability=sorted(set(applicability)),
        governance_states=sorted(set(governance)),
        field_ids=sorted({f["field_id"] for f in facts if f.get("field_id")}),
    )
    return value.model_dump(mode="json")


def matches_facets(facets: dict, *, knowledge_type=None, evidence_state=None, topic=None, tcm_layer=None):
    return all(value is None or value in facets[field] for field, value in (
        ("knowledge_types", knowledge_type),
        ("evidence_states", evidence_state),
        ("applicability", topic),
        ("tcm_layers", tcm_layer),
    ))
