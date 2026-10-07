from __future__ import annotations

from collections.abc import Iterable

from medicine_agent.domain.clinical import (
    AssertionStatus,
    ClinicalObservation,
    ConfidenceLevel,
    EvidenceLink,
    EvidenceRole,
    MedicalSystem,
    ObservationPolarity,
    ObservationStatus,
    ReasoningEdge,
    ReasoningNode,
    ReasoningNodeType,
    ReasoningRole,
    SafetyStatus,
    TCMReasoningGraph,
)
from medicine_agent.domain.ids import stable_id
from medicine_agent.domain.models import GenerationMethod, IssueSeverity, SkillIssue
from medicine_agent.runtime.base import SkillContext, manifest_path
from medicine_agent.runtime.errors import SemanticContractError
from medicine_agent.runtime.manifest import load_manifest
from medicine_agent.semantics import validate_semantic_context
from medicine_agent.skills.tcm_reasoning.models import (
    TCMReasoningInput,
    TCMReasoningOutput,
)


class TCMReasoningSkill:
    manifest = load_manifest(manifest_path(__file__))
    input_model = TCMReasoningInput
    output_model = TCMReasoningOutput

    def execute(
        self, value: TCMReasoningInput, context: SkillContext
    ) -> TCMReasoningOutput:
        del context
        validate_semantic_context(
            value.semantic_context, required_profiles={"common", "tcm", "safety"}
        )
        case = value.canonical_case
        if (
            case.semantic_registry_id != value.semantic_context.registry_id
            or case.semantic_registry_version != value.semantic_context.registry_version
        ):
            raise SemanticContractError(
                "CanonicalCase semantic registry does not match the reasoning context",
                details={
                    "case_registry_id": case.semantic_registry_id,
                    "case_registry_version": case.semantic_registry_version,
                    "context_registry_id": value.semantic_context.registry_id,
                    "context_registry_version": value.semantic_context.registry_version,
                },
            )
        observations = [
            observation
            for encounter in case.encounters
            for observation in encounter.observations
        ]
        nodes: list[ReasoningNode] = []
        edges: list[ReasoningEdge] = []
        observation_nodes: dict[str, ReasoningNode] = {}
        observation_encounter_refs = {
            observation.observation_id: encounter.encounter_id
            for encounter in case.encounters
            for observation in encounter.observations
        }
        for observation in observations:
            node = ReasoningNode(
                node_id=stable_id("rnode", {"observation_id": observation.observation_id}),
                node_type=ReasoningNodeType.OBSERVATION,
                medical_system=MedicalSystem.GENERAL,
                label=observation.normalized_text or observation.raw_text,
                role=ReasoningRole.CONTEXT,
                assertion_status=AssertionStatus.SOURCE_EXPLICIT,
                confidence=ConfidenceLevel.UNKNOWN,
                evidence_refs=observation.evidence_refs,
                evidence_links=_links(
                    observation.evidence_refs,
                    EvidenceRole.CONTEXT,
                    ConfidenceLevel.UNKNOWN,
                ),
                encounter_refs=[observation_encounter_refs[observation.observation_id]],
                generation_method=GenerationMethod.IMPORTED,
            )
            nodes.append(node)
            observation_nodes[observation.observation_id] = node

        inferred: dict[str, ReasoningNode] = {}

        def add_candidate(
            *,
            key: str,
            label: str,
            matched: list[ClinicalObservation],
            role: ReasoningRole,
            confidence: ConfidenceLevel,
            missing: list[str] | None = None,
            node_type: ReasoningNodeType = ReasoningNodeType.PATHOMECHANISM,
        ) -> ReasoningNode | None:
            if not matched:
                return None
            refs = _evidence_refs(matched)
            encounter_refs = sorted(
                {
                    observation_encounter_refs[item.observation_id]
                    for item in matched
                }
            )
            node = ReasoningNode(
                node_id=stable_id(
                    "rnode",
                    {"case_id": case.case_id, "key": key, "evidence_refs": refs},
                ),
                node_type=node_type,
                medical_system=MedicalSystem.TCM,
                label=label,
                role=role,
                assertion_status=AssertionStatus.RULE_INFERRED,
                confidence=confidence,
                evidence_refs=refs,
                evidence_links=_links(refs, EvidenceRole.SUPPORTING, confidence),
                missing_evidence=missing or [],
                encounter_refs=encounter_refs,
                generation_method=GenerationMethod.RULE,
            )
            nodes.append(node)
            inferred[key] = node
            for observation in matched:
                source = observation_nodes[observation.observation_id]
                edges.append(
                    ReasoningEdge(
                        edge_id=stable_id(
                            "redge",
                            {
                                "source": source.node_id,
                                "target": node.node_id,
                                "relation": "supports_candidate",
                            },
                        ),
                        source_node_id=source.node_id,
                        target_node_id=node.node_id,
                        relation_type="supports_candidate",
                        evidence_refs=observation.evidence_refs,
                        evidence_links=_links(
                            observation.evidence_refs,
                            EvidenceRole.SUPPORTING,
                            confidence,
                        ),
                        generation_method=GenerationMethod.RULE,
                    )
                )
            return node

        qi = _matching(observations, ["乏力", "气短", "劳累"])
        stasis = _matching(observations, ["口唇暗", "瘀点", "舌暗", "胸痛", "闷痛"])
        yang = _matching(observations, ["怕冷", "畏寒", "腰背冷"])
        middle = _matching(observations, ["食后腹胀", "腹胀", "苔微厚"])
        urine_yellow = _matching(observations, ["小便黄"])

        add_candidate(
            key="qi_deficiency",
            label="气虚候选",
            matched=qi,
            role=ReasoningRole.PRIMARY if len(qi) >= 2 else ReasoningRole.CANDIDATE,
            confidence=ConfidenceLevel.MEDIUM if len(qi) >= 2 else ConfidenceLevel.LOW,
            missing=["语声情况", "自汗情况"],
        )
        add_candidate(
            key="blood_stasis",
            label="血瘀候选",
            matched=stasis,
            role=ReasoningRole.PRIMARY if len(stasis) >= 2 else ReasoningRole.CANDIDATE,
            confidence=ConfidenceLevel.HIGH if len(stasis) >= 3 else ConfidenceLevel.MEDIUM,
        )
        add_candidate(
            key="yang_deficiency",
            label="阳虚候选",
            matched=yang,
            role=ReasoningRole.SECONDARY,
            confidence=ConfidenceLevel.LOW,
            missing=["四肢温度", "舌质淡嫩", "脉沉迟"],
        )
        add_candidate(
            key="middle_jiao_dysfunction",
            label="中焦运化不足候选",
            matched=middle,
            role=ReasoningRole.SECONDARY,
            confidence=ConfidenceLevel.LOW,
        )
        if len(middle) >= 2:
            add_candidate(
                key="phlegm_dampness",
                label="痰湿兼夹候选",
                matched=middle,
                role=ReasoningRole.CANDIDATE,
                confidence=ConfidenceLevel.LOW,
                missing=["痰多", "苔腻", "脉滑"],
            )
        add_candidate(
            key="heat_from_yellow_urine",
            label="热证低证据候选",
            matched=urine_yellow,
            role=ReasoningRole.CANDIDATE,
            confidence=ConfidenceLevel.LOW,
            missing=["口渴", "舌红", "脉数", "尿量与饮水情况"],
            node_type=ReasoningNodeType.HYPOTHESIS,
        )

        if "qi_deficiency" in inferred and "blood_stasis" in inferred:
            refs = sorted(
                set(inferred["qi_deficiency"].evidence_refs)
                | set(inferred["blood_stasis"].evidence_refs)
            )
            contradiction = ReasoningNode(
                node_id=stable_id(
                    "rnode", {"case_id": case.case_id, "key": "root_branch"}
                ),
                node_type=ReasoningNodeType.CONTRADICTION,
                medical_system=MedicalSystem.TCM,
                label="本虚与标实并存候选",
                role=ReasoningRole.PRIMARY,
                assertion_status=AssertionStatus.RULE_INFERRED,
                confidence=ConfidenceLevel.MEDIUM,
                evidence_refs=refs,
                evidence_links=_links(
                    refs, EvidenceRole.SUPPORTING, ConfidenceLevel.MEDIUM
                ),
                encounter_refs=sorted(
                    set(inferred["qi_deficiency"].encounter_refs)
                    | set(inferred["blood_stasis"].encounter_refs)
                ),
                generation_method=GenerationMethod.RULE,
            )
            state = ReasoningNode(
                node_id=stable_id(
                    "rnode", {"case_id": case.case_id, "key": "qi_stasis_state"}
                ),
                node_type=ReasoningNodeType.STATE,
                medical_system=MedicalSystem.TCM,
                label="气虚血瘀候选状态",
                role=ReasoningRole.PRIMARY,
                assertion_status=AssertionStatus.RULE_INFERRED,
                confidence=ConfidenceLevel.MEDIUM,
                evidence_refs=refs,
                evidence_links=_links(
                    refs, EvidenceRole.SUPPORTING, ConfidenceLevel.MEDIUM
                ),
                encounter_refs=sorted(
                    set(inferred["qi_deficiency"].encounter_refs)
                    | set(inferred["blood_stasis"].encounter_refs)
                ),
                generation_method=GenerationMethod.RULE,
            )
            nodes.extend([contradiction, state])
            for key in ("qi_deficiency", "blood_stasis"):
                source = inferred[key]
                edges.append(_edge(source, contradiction, "forms_contradiction", refs))
                edges.append(_edge(source, state, "composes_state", refs))

        issues = [
            SkillIssue(
                code="MEDICAL_REFERENCE_GAP",
                severity=IssueSeverity.WARNING,
                message=(
                    "Reasoning is an unreviewed deterministic candidate; fixed-edition "
                    "diagnostic and internal-medicine references are not yet aligned."
                ),
            )
        ]
        if value.safety_context.status != SafetyStatus.CLEARED:
            issues.append(
                SkillIssue(
                    code="SAFETY_STATUS_NOT_CLEARED",
                    severity=IssueSeverity.WARNING,
                    message="Action recommendations are blocked until an independent safety gate is cleared.",
                )
            )
        graph = TCMReasoningGraph(
            graph_id=stable_id(
                "tcmgraph",
                {
                    "case_id": case.case_id,
                    "nodes": [node.node_id for node in nodes],
                    "safety": value.safety_context.model_dump(mode="json"),
                },
            ),
            graph_type="tcm_candidate_reasoning",
            semantic_registry_id=value.semantic_context.registry_id,
            semantic_registry_version=value.semantic_context.registry_version,
            enabled_profiles=value.semantic_context.enabled_profiles,
            case_id=case.case_id,
            encounter_refs=[encounter.encounter_id for encounter in case.encounters],
            medical_systems=[MedicalSystem.GENERAL, MedicalSystem.TCM],
            protocol_version="0.4.0-draft",
            nodes=nodes,
            edges=edges,
            safety_context=value.safety_context,
            actionability="research_candidate_only",
            treatment_recommendations=[],
            tcm_method_profiles=["general_pattern_differentiation_baseline"],
        )
        return TCMReasoningOutput(reasoning_graph=graph, issues=issues)


def _matching(
    observations: Iterable[ClinicalObservation], keywords: list[str]
) -> list[ClinicalObservation]:
    return [
        item
        for item in observations
        if item.polarity != ObservationPolarity.ABSENT
        and item.status
        not in {ObservationStatus.CANCELLED, ObservationStatus.ENTERED_IN_ERROR}
        if any(keyword in (item.normalized_text or item.raw_text) for keyword in keywords)
    ]


def _evidence_refs(observations: Iterable[ClinicalObservation]) -> list[str]:
    return sorted({ref for item in observations for ref in item.evidence_refs})


def _edge(
    source: ReasoningNode,
    target: ReasoningNode,
    relation_type: str,
    evidence_refs: list[str],
) -> ReasoningEdge:
    return ReasoningEdge(
        edge_id=stable_id(
            "redge",
            {
                "source": source.node_id,
                "target": target.node_id,
                "relation": relation_type,
            },
        ),
        source_node_id=source.node_id,
        target_node_id=target.node_id,
        relation_type=relation_type,
        evidence_refs=evidence_refs,
        evidence_links=_links(
            evidence_refs, EvidenceRole.SUPPORTING, ConfidenceLevel.MEDIUM
        ),
        generation_method=GenerationMethod.RULE,
    )


def _links(
    evidence_refs: list[str], role: EvidenceRole, strength: ConfidenceLevel
) -> list[EvidenceLink]:
    return [
        EvidenceLink(evidence_ref=ref, role=role, strength=strength)
        for ref in evidence_refs
    ]
