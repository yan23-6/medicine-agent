from __future__ import annotations

import json

from medicine_agent.domain.clinical import (
    CanonicalCase,
    CaseUncertainty,
    ClinicalObservation,
    Encounter,
    HistoricalRecord,
    ObservationCategory,
)
from medicine_agent.domain.ids import stable_id
from medicine_agent.domain.models import IssueSeverity, SkillIssue
from medicine_agent.runtime.base import SkillContext, manifest_path
from medicine_agent.runtime.manifest import load_manifest
from medicine_agent.semantics import validate_semantic_context
from medicine_agent.skills.case_distillation.models import (
    CaseDistillationInput,
    CaseDistillationOutput,
)


class CaseDistillationSkill:
    manifest = load_manifest(manifest_path(__file__))
    input_model = CaseDistillationInput
    output_model = CaseDistillationOutput

    def execute(
        self, value: CaseDistillationInput, context: SkillContext
    ) -> CaseDistillationOutput:
        del context
        validate_semantic_context(value.semantic_context, required_profiles={"common"})
        raw_case = value.raw_case
        issues: list[SkillIssue] = []
        uncertainties: list[CaseUncertainty] = []
        encounters: list[Encounter] = []

        for raw_encounter in raw_case.encounters:
            encounter_id = stable_id(
                "enc",
                {
                    "case_ref": raw_case.case_ref,
                    "encounter_key": raw_encounter.encounter_key,
                    "sequence": raw_encounter.sequence,
                },
            )
            observations: list[ClinicalObservation] = []
            diagnoses: list[HistoricalRecord] = []
            actions: list[HistoricalRecord] = []
            for ordinal, field in enumerate(raw_encounter.fields):
                category = field.category or ObservationCategory.OTHER
                identity = {
                    "encounter_id": encounter_id,
                    "ordinal": ordinal,
                    "raw_key": field.raw_key,
                    "raw_value": field.raw_value,
                    "evidence_refs": field.evidence_refs,
                }
                if category in {
                    ObservationCategory.HISTORICAL_DIAGNOSIS,
                    ObservationCategory.HISTORICAL_ACTION,
                }:
                    record = HistoricalRecord(
                        record_id=stable_id("hist", identity),
                        raw_key=field.raw_key,
                        kind=category.value,
                        event_type=field.normalized_concept,
                        raw_text=_raw_text(field.raw_value),
                        raw_value=field.raw_value,
                        normalized_value=field.normalized_value,
                        effective_time=field.effective_time,
                        information_origin=field.information_origin,
                        actor_refs=field.performer_refs,
                        evidence_refs=field.evidence_refs,
                        source_path=field.source_path,
                        context=field.context,
                    )
                    if category == ObservationCategory.HISTORICAL_DIAGNOSIS:
                        diagnoses.append(record)
                    else:
                        actions.append(record)
                else:
                    observations.append(
                        ClinicalObservation(
                            observation_id=stable_id("obs", identity),
                            raw_key=field.raw_key,
                            raw_text=_raw_text(field.raw_value),
                            raw_value=field.raw_value,
                            raw_type=field.raw_type,
                            normalized_text=field.normalized_text,
                            concept=field.normalized_concept,
                            value=field.normalized_value,
                            category=category,
                            categories=field.categories,
                            certainty=field.certainty,
                            polarity=field.polarity,
                            status=field.status,
                            effective_time=field.effective_time,
                            body_sites=field.body_sites,
                            method=field.method,
                            interpretations=field.interpretations,
                            information_origin=field.information_origin,
                            performer_refs=field.performer_refs,
                            evidence_refs=field.evidence_refs,
                            mapping_status=field.mapping_status,
                            mapping_candidates=field.mapping_candidates,
                            mapping_rule_version=field.mapping_rule_version,
                            source_path=field.source_path,
                            context=field.context,
                        )
                    )
                if field.category is None:
                    issues.append(
                        SkillIssue(
                            code="UNMAPPED_CASE_FIELD_PRESERVED",
                            severity=IssueSeverity.WARNING,
                            message=f"Unmapped case field preserved: {field.raw_key}",
                            path=stable_id("field", identity),
                        )
                    )
                if field.correction_candidates:
                    uncertainties.append(
                        CaseUncertainty(
                            uncertainty_id=stable_id("unc", identity),
                            applies_to_ref=stable_id("field", identity),
                            raw_key=field.raw_key,
                            raw_text=_raw_text(field.raw_value),
                            raw_value=field.raw_value,
                            correction_candidates=field.correction_candidates,
                            evidence_refs=field.evidence_refs,
                            source_path=field.source_path,
                            context=field.context,
                        )
                    )
            encounters.append(
                Encounter(
                    encounter_id=encounter_id,
                    source_encounter_key=raw_encounter.encounter_key,
                    identifiers=raw_encounter.identifiers,
                    sequence=raw_encounter.sequence,
                    date_raw=raw_encounter.date_raw,
                    subject_age=raw_encounter.subject_age,
                    period=raw_encounter.period,
                    status=raw_encounter.status,
                    encounter_classes=raw_encounter.encounter_classes,
                    encounter_types=raw_encounter.encounter_types,
                    service_types=raw_encounter.service_types,
                    priority=raw_encounter.priority,
                    participants=raw_encounter.participants,
                    service_provider_ref=raw_encounter.service_provider_ref,
                    location_refs=raw_encounter.location_refs,
                    parent_encounter_ref=raw_encounter.parent_encounter_ref,
                    observations=observations,
                    historical_diagnoses=diagnoses,
                    historical_actions=actions,
                )
            )

        case_id = stable_id(
            "case",
            {
                "case_ref": raw_case.case_ref,
                "source_id": raw_case.source_id,
                "encounters": [item.model_dump(mode="json") for item in encounters],
            },
        )
        return CaseDistillationOutput(
            canonical_case=CanonicalCase(
                case_id=case_id,
                semantic_registry_id=value.semantic_context.registry_id,
                semantic_registry_version=value.semantic_context.registry_version,
                enabled_profiles=value.semantic_context.enabled_profiles,
                identifiers=raw_case.identifiers,
                source_ids=list(
                    dict.fromkeys([raw_case.source_id, *raw_case.related_source_ids])
                ),
                source_use_scope=raw_case.source_use_scope,
                language=raw_case.language,
                jurisdiction=raw_case.jurisdiction,
                case_types=raw_case.case_types,
                tags=raw_case.tags,
                patient=raw_case.patient,
                encounters=encounters,
                uncertainties=uncertainties,
            ),
            issues=issues,
        )


def _raw_text(value: object) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
