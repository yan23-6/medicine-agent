from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import Field, JsonValue, model_validator

from medicine_agent.domain.models import (
    FieldMappingCandidate,
    FieldMappingStatus,
    GenerationMethod,
    ReviewStatus,
    StrictModel,
)


class SubjectKind(StrEnum):
    PERSON = "person"
    GROUP = "group"
    UNKNOWN = "unknown"


class ObservationPolarity(StrEnum):
    PRESENT = "present"
    ABSENT = "absent"
    CONDITIONAL = "conditional"
    UNKNOWN = "unknown"


class ObservationStatus(StrEnum):
    PRELIMINARY = "preliminary"
    FINAL = "final"
    AMENDED = "amended"
    CORRECTED = "corrected"
    CANCELLED = "cancelled"
    ENTERED_IN_ERROR = "entered_in_error"
    UNKNOWN = "unknown"


class InformationOrigin(StrEnum):
    PATIENT = "patient"
    FAMILY_OR_CAREGIVER = "family_or_caregiver"
    PRACTITIONER = "practitioner"
    DEVICE = "device"
    DOCUMENT = "document"
    MODEL_DERIVED = "model_derived"
    RULE_DERIVED = "rule_derived"
    UNKNOWN = "unknown"


class TemporalPrecision(StrEnum):
    YEAR = "year"
    MONTH = "month"
    DAY = "day"
    MINUTE = "minute"
    SECOND = "second"
    RANGE = "range"
    RELATIVE = "relative"
    UNKNOWN = "unknown"


class TemporalCertainty(StrEnum):
    EXACT = "exact"
    APPROXIMATE = "approximate"
    UNCERTAIN = "uncertain"
    UNKNOWN = "unknown"


class MedicalSystem(StrEnum):
    GENERAL = "general"
    TCM = "tcm"
    WESTERN = "western"
    SAFETY = "safety"
    INTEGRATIVE = "integrative"
    RESEARCH = "research"
    UNKNOWN = "unknown"


class ObservationCategory(StrEnum):
    CHIEF_COMPLAINT = "chief_complaint"
    HISTORY = "history"
    SYMPTOM = "symptom"
    SIGN = "sign"
    TONGUE = "tongue"
    PULSE = "pulse"
    VITAL_SIGN = "vital_sign"
    MEASUREMENT = "measurement"
    LABORATORY = "laboratory"
    IMAGING = "imaging"
    FUNCTIONAL = "functional"
    SOCIAL = "social"
    LIFESTYLE = "lifestyle"
    FAMILY_HISTORY = "family_history"
    HISTORICAL_DIAGNOSIS = "historical_diagnosis"
    HISTORICAL_ACTION = "historical_action"
    OUTCOME = "outcome"
    OTHER = "other"


class ObservationCertainty(StrEnum):
    ASSERTED = "asserted"
    PROBABLE = "probable"
    POSSIBLE = "possible"
    UNCERTAIN = "uncertain"
    UNKNOWN = "unknown"


class ReasoningNodeType(StrEnum):
    OBSERVATION = "observation"
    FEATURE = "feature"
    ETIOLOGY = "etiology"
    ANATOMICAL_LOCATION = "anatomical_location"
    NATURE = "nature"
    HYPOTHESIS = "hypothesis"
    PATHOMECHANISM = "pathomechanism"
    SYNDROME = "syndrome"
    DIAGNOSIS = "diagnosis"
    DIFFERENTIAL = "differential"
    RISK = "risk"
    CONTRADICTION = "contradiction"
    STATE = "state"
    GOAL = "goal"
    OPERATOR = "operator"
    ACTION = "action"
    OUTCOME = "outcome"
    OTHER = "other"


class ReasoningRole(StrEnum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    CONCOMITANT = "concomitant"
    CANDIDATE = "candidate"
    DIFFERENTIAL = "differential"
    EXCLUDED = "excluded"
    CONTEXT = "context"


class AssertionStatus(StrEnum):
    SOURCE_EXPLICIT = "source_explicit"
    RULE_INFERRED = "rule_inferred"
    MODEL_CANDIDATE = "model_candidate"
    HUMAN_CONFIRMED = "human_confirmed"
    HUMAN_REJECTED = "human_rejected"


class ConfidenceLevel(StrEnum):
    UNKNOWN = "unknown"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EvidenceRole(StrEnum):
    SUPPORTING = "supporting"
    WEAK_SUPPORTING = "weak_supporting"
    COUNTEREVIDENCE = "counterevidence"
    AMBIGUOUS = "ambiguous"
    CONTEXT = "context"


class SafetyStatus(StrEnum):
    UNASSESSED = "unassessed"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    CLEARED = "cleared"


class Identifier(StrictModel):
    system: str | None = None
    value: str = Field(min_length=1)
    use: str | None = None
    type: str | None = None


class Coding(StrictModel):
    system: str = Field(min_length=1)
    code: str = Field(min_length=1)
    display: str | None = None
    version: str | None = None
    user_selected: bool | None = None


class CodeableConcept(StrictModel):
    text: str | None = None
    codings: list[Coding] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_text_or_coding(self) -> Self:
        if not self.text and not self.codings:
            raise ValueError("CodeableConcept requires text or at least one coding")
        return self


class TemporalExtent(StrictModel):
    raw: str | None = None
    point: str | None = None
    start: str | None = None
    end: str | None = None
    precision: TemporalPrecision = TemporalPrecision.UNKNOWN
    certainty: TemporalCertainty = TemporalCertainty.UNKNOWN

    @model_validator(mode="after")
    def require_temporal_content(self) -> Self:
        if not any((self.raw, self.point, self.start, self.end)):
            raise ValueError("TemporalExtent requires raw, point, start, or end")
        return self


class Quantity(StrictModel):
    value: float
    comparator: str | None = None
    unit: str | None = None
    system: str | None = None
    code: str | None = None


class TextValue(StrictModel):
    value_type: Literal["text"]
    text: str


class CodedValue(StrictModel):
    value_type: Literal["coded"]
    concept: CodeableConcept


class QuantityValue(StrictModel):
    value_type: Literal["quantity"]
    quantity: Quantity


class RangeValue(StrictModel):
    value_type: Literal["range"]
    low: Quantity | None = None
    high: Quantity | None = None

    @model_validator(mode="after")
    def require_range_bound(self) -> Self:
        if self.low is None and self.high is None:
            raise ValueError("RangeValue requires a low or high bound")
        return self


class RatioValue(StrictModel):
    value_type: Literal["ratio"]
    numerator: Quantity
    denominator: Quantity


class BooleanValue(StrictModel):
    value_type: Literal["boolean"]
    value: bool


class IntegerValue(StrictModel):
    value_type: Literal["integer"]
    value: int


class DateTimeValue(StrictModel):
    value_type: Literal["date_time"]
    value: str


class PeriodValue(StrictModel):
    value_type: Literal["period"]
    period: TemporalExtent


class ReferenceValue(StrictModel):
    value_type: Literal["reference"]
    reference: str
    display: str | None = None


class MissingValue(StrictModel):
    value_type: Literal["missing"]
    reason: CodeableConcept


ClinicalValue = Annotated[
    TextValue
    | CodedValue
    | QuantityValue
    | RangeValue
    | RatioValue
    | BooleanValue
    | IntegerValue
    | DateTimeValue
    | PeriodValue
    | ReferenceValue
    | MissingValue,
    Field(discriminator="value_type"),
]


class NamedAttribute(StrictModel):
    name: CodeableConcept
    value: ClinicalValue
    evidence_refs: list[str] = Field(default_factory=list)


class Participant(StrictModel):
    actor_ref: str
    role: CodeableConcept | None = None
    period: TemporalExtent | None = None


class PatientProfile(StrictModel):
    subject_kind: SubjectKind = SubjectKind.PERSON
    identifiers: list[Identifier] = Field(default_factory=list)
    sex: str | None = None
    sex_at_birth: CodeableConcept | None = None
    gender: CodeableConcept | None = None
    age: int | None = Field(default=None, ge=0, le=130)
    age_unit: str = "years"
    age_value: Quantity | None = None
    birth_date: str | None = None
    attributes: list[NamedAttribute] = Field(default_factory=list)
    privacy_labels: list[CodeableConcept] = Field(default_factory=list)


class RawCaseField(StrictModel):
    raw_key: str
    raw_value: JsonValue
    raw_type: str = "text"
    category: ObservationCategory | None = None
    categories: list[CodeableConcept] = Field(default_factory=list)
    normalized_text: str | None = None
    normalized_concept: CodeableConcept | None = None
    normalized_value: ClinicalValue | None = None
    certainty: ObservationCertainty = ObservationCertainty.ASSERTED
    polarity: ObservationPolarity = ObservationPolarity.PRESENT
    status: ObservationStatus = ObservationStatus.UNKNOWN
    effective_time: TemporalExtent | None = None
    body_sites: list[CodeableConcept] = Field(default_factory=list)
    method: CodeableConcept | None = None
    interpretations: list[CodeableConcept] = Field(default_factory=list)
    information_origin: InformationOrigin = InformationOrigin.DOCUMENT
    performer_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(min_length=1)
    correction_candidates: list[str] = Field(default_factory=list)
    mapping_status: FieldMappingStatus = FieldMappingStatus.UNMAPPED
    mapping_candidates: list[FieldMappingCandidate] = Field(default_factory=list)
    mapping_rule_version: str | None = None
    source_path: str | None = None
    context: str | None = None


class RawCaseEncounter(StrictModel):
    encounter_key: str
    identifiers: list[Identifier] = Field(default_factory=list)
    sequence: int = Field(ge=1)
    date_raw: str | None = None
    subject_age: Quantity | None = None
    period: TemporalExtent | None = None
    status: str = "unknown"
    encounter_classes: list[CodeableConcept] = Field(default_factory=list)
    encounter_types: list[CodeableConcept] = Field(default_factory=list)
    service_types: list[CodeableConcept] = Field(default_factory=list)
    priority: CodeableConcept | None = None
    participants: list[Participant] = Field(default_factory=list)
    service_provider_ref: str | None = None
    location_refs: list[str] = Field(default_factory=list)
    parent_encounter_ref: str | None = None
    fields: list[RawCaseField] = Field(min_length=1)


class RawCaseRecord(StrictModel):
    case_ref: str
    identifiers: list[Identifier] = Field(default_factory=list)
    source_id: str
    related_source_ids: list[str] = Field(default_factory=list)
    source_use_scope: str
    language: str | None = None
    jurisdiction: str | None = None
    case_types: list[CodeableConcept] = Field(default_factory=list)
    tags: list[CodeableConcept] = Field(default_factory=list)
    patient: PatientProfile
    encounters: list[RawCaseEncounter] = Field(min_length=1)


class ClinicalObservation(StrictModel):
    observation_id: str
    raw_key: str
    raw_text: str
    raw_value: JsonValue
    raw_type: str = "text"
    normalized_text: str | None = None
    concept: CodeableConcept | None = None
    value: ClinicalValue | None = None
    category: ObservationCategory
    categories: list[CodeableConcept] = Field(default_factory=list)
    certainty: ObservationCertainty
    polarity: ObservationPolarity = ObservationPolarity.PRESENT
    status: ObservationStatus = ObservationStatus.UNKNOWN
    effective_time: TemporalExtent | None = None
    body_sites: list[CodeableConcept] = Field(default_factory=list)
    method: CodeableConcept | None = None
    interpretations: list[CodeableConcept] = Field(default_factory=list)
    information_origin: InformationOrigin = InformationOrigin.DOCUMENT
    performer_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(min_length=1)
    mapping_status: FieldMappingStatus = FieldMappingStatus.UNMAPPED
    mapping_candidates: list[FieldMappingCandidate] = Field(default_factory=list)
    mapping_rule_version: str | None = None
    source_path: str | None = None
    context: str | None = None
    generation_method: GenerationMethod = GenerationMethod.IMPORTED
    review_status: ReviewStatus = ReviewStatus.UNREVIEWED


class HistoricalRecord(StrictModel):
    record_id: str
    raw_key: str
    kind: str
    event_type: CodeableConcept | None = None
    raw_text: str
    raw_value: JsonValue
    normalized_value: ClinicalValue | None = None
    status: str = "reported_history"
    effective_time: TemporalExtent | None = None
    information_origin: InformationOrigin = InformationOrigin.DOCUMENT
    actor_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(min_length=1)
    source_path: str | None = None
    context: str | None = None
    review_status: ReviewStatus = ReviewStatus.UNREVIEWED


class CaseUncertainty(StrictModel):
    uncertainty_id: str
    uncertainty_type: str = "transcription_or_mapping"
    applies_to_ref: str | None = None
    raw_key: str
    raw_text: str
    raw_value: JsonValue
    correction_candidates: list[str] = Field(min_length=1)
    evidence_refs: list[str] = Field(min_length=1)
    source_path: str | None = None
    context: str | None = None
    review_status: ReviewStatus = ReviewStatus.UNREVIEWED


class Encounter(StrictModel):
    encounter_id: str
    source_encounter_key: str
    identifiers: list[Identifier] = Field(default_factory=list)
    sequence: int = Field(ge=1)
    date_raw: str | None = None
    subject_age: Quantity | None = None
    period: TemporalExtent | None = None
    status: str = "unknown"
    encounter_classes: list[CodeableConcept] = Field(default_factory=list)
    encounter_types: list[CodeableConcept] = Field(default_factory=list)
    service_types: list[CodeableConcept] = Field(default_factory=list)
    priority: CodeableConcept | None = None
    participants: list[Participant] = Field(default_factory=list)
    service_provider_ref: str | None = None
    location_refs: list[str] = Field(default_factory=list)
    parent_encounter_ref: str | None = None
    observations: list[ClinicalObservation] = Field(default_factory=list)
    historical_diagnoses: list[HistoricalRecord] = Field(default_factory=list)
    historical_actions: list[HistoricalRecord] = Field(default_factory=list)


class CanonicalCase(StrictModel):
    case_id: str
    semantic_registry_id: str
    semantic_registry_version: str
    enabled_profiles: list[str] = Field(min_length=1)
    identifiers: list[Identifier] = Field(default_factory=list)
    source_ids: list[str] = Field(min_length=1)
    source_use_scope: str
    language: str | None = None
    jurisdiction: str | None = None
    case_types: list[CodeableConcept] = Field(default_factory=list)
    tags: list[CodeableConcept] = Field(default_factory=list)
    patient: PatientProfile
    encounters: list[Encounter] = Field(min_length=1)
    uncertainties: list[CaseUncertainty] = Field(default_factory=list)
    provenance_refs: list[str] = Field(default_factory=list)
    review_status: ReviewStatus = ReviewStatus.UNREVIEWED


class SafetyContext(StrictModel):
    status: SafetyStatus
    assessed_by: str | None = None
    source: str
    assessed_at: str | None = None
    scope: str | None = None
    policy_refs: list[str] = Field(default_factory=list)
    alert_refs: list[str] = Field(default_factory=list)
    unmet_requirements: list[str] = Field(default_factory=list)
    restrictions: list[str] = Field(default_factory=list)


class EvidenceLink(StrictModel):
    evidence_ref: str
    role: EvidenceRole
    strength: ConfidenceLevel = ConfidenceLevel.UNKNOWN
    rationale: str | None = None
    applies_to: str | None = None


class ReasoningNode(StrictModel):
    node_id: str
    node_type: ReasoningNodeType
    medical_system: MedicalSystem
    label: str
    concept: CodeableConcept | None = None
    narrative: str | None = None
    role: ReasoningRole
    assertion_status: AssertionStatus
    confidence: ConfidenceLevel = ConfidenceLevel.UNKNOWN
    evidence_refs: list[str] = Field(default_factory=list)
    evidence_links: list[EvidenceLink] = Field(default_factory=list)
    counterevidence_refs: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    applicability: list[str] = Field(default_factory=list)
    valid_time: TemporalExtent | None = None
    encounter_refs: list[str] = Field(default_factory=list)
    generation_method: GenerationMethod
    provenance_refs: list[str] = Field(default_factory=list)
    review_status: ReviewStatus = ReviewStatus.UNREVIEWED


class ReasoningEdge(StrictModel):
    edge_id: str
    source_node_id: str
    target_node_id: str
    relation_type: str
    relation: CodeableConcept | None = None
    polarity: str = "positive"
    condition: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    evidence_links: list[EvidenceLink] = Field(default_factory=list)
    valid_time: TemporalExtent | None = None
    generation_method: GenerationMethod
    provenance_refs: list[str] = Field(default_factory=list)
    review_status: ReviewStatus = ReviewStatus.UNREVIEWED


class ClinicalReasoningGraph(StrictModel):
    graph_id: str
    graph_type: str
    semantic_registry_id: str
    semantic_registry_version: str
    enabled_profiles: list[str] = Field(min_length=1)
    case_id: str
    encounter_refs: list[str] = Field(default_factory=list)
    medical_systems: list[MedicalSystem] = Field(min_length=1)
    protocol_version: str
    nodes: list[ReasoningNode] = Field(default_factory=list)
    edges: list[ReasoningEdge] = Field(default_factory=list)
    safety_context: SafetyContext
    actionability: str
    treatment_recommendations: list[str] = Field(default_factory=list)
    provenance_refs: list[str] = Field(default_factory=list)
    review_status: ReviewStatus = ReviewStatus.UNREVIEWED


class TCMReasoningGraph(ClinicalReasoningGraph):
    tcm_method_profiles: list[str] = Field(default_factory=list)
