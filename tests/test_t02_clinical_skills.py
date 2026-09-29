import json
from collections import Counter
from pathlib import Path

import pytest
from pydantic import ValidationError

from medicine_agent.bootstrap import create_facade
from medicine_agent.domain.clinical import CodeableConcept, RangeValue
from medicine_agent.domain.models import SkillInvocation, SkillStatus


FIXTURE = Path(__file__).parent / "fixtures" / "t02" / "chest_bi_case.json"


def _case_input() -> dict:
    return json.loads(FIXTURE.read_text("utf-8"))


def _distill_case() -> tuple[object, dict]:
    facade = create_facade()
    result = facade.invoke_skill(
        SkillInvocation(
            task_id="t02-case-distillation",
            skill_id="case-distillation",
            input_data=_case_input(),
        )
    )
    assert result.output is not None
    return result, result.output["canonical_case"]


def test_case_distillation_preserves_uncertainty_and_separates_history() -> None:
    result, case = _distill_case()

    assert result.status == SkillStatus.PARTIAL
    encounter = case["encounters"][0]
    assert len(encounter["historical_diagnoses"]) == 1
    assert len(encounter["historical_actions"]) == 1
    assert all(
        item["raw_text"] != "历史记录采用针灸及益气通络思路"
        for item in encounter["observations"]
    )
    assert {item["raw_text"] for item in case["uncertainties"]} == {
        "食后腹胀",
        "脉弓玄细，略有歇止",
        "排眠不佳",
    }
    assert any(issue.code == "UNMAPPED_CASE_FIELD_PRESERVED" for issue in result.issues)


def test_case_distillation_preserves_every_raw_field_and_context() -> None:
    raw_input = _case_input()["raw_case"]
    _, case = _distill_case()
    encounter = case["encounters"][0]
    canonical_records = (
        encounter["observations"]
        + encounter["historical_diagnoses"]
        + encounter["historical_actions"]
    )

    assert encounter["source_encounter_key"] == raw_input["encounters"][0]["encounter_key"]
    assert Counter(item["raw_value"] for item in raw_input["encounters"][0]["fields"]) == Counter(
        item["raw_text"] for item in canonical_records
    )
    risk_signal = next(
        item for item in encounter["observations"] if item["raw_key"] == "近期变化"
    )
    assert risk_signal["context"] == "原医案近期变化段"


def test_tcm_reasoning_is_evidence_linked_unreviewed_and_non_actionable() -> None:
    _, case = _distill_case()
    facade = create_facade()
    result = facade.invoke_skill(
        SkillInvocation(
            task_id="t02-tcm-reasoning",
            skill_id="tcm-reasoning",
            input_data={
                "canonical_case": case,
                "safety_context": {
                    "status": "unassessed",
                    "assessed_by": None,
                    "source": "t02_fixture",
                    "unmet_requirements": ["independent_chest_pain_safety_assessment"],
                },
            },
        )
    )

    assert result.status == SkillStatus.PARTIAL
    assert result.output is not None
    graph = result.output["reasoning_graph"]
    assert graph["actionability"] == "research_candidate_only"
    assert graph["treatment_recommendations"] == []
    assert graph["protocol_version"] == "0.4.0-draft"
    assert graph["semantic_registry_version"] == "0.1.0"
    assert set(graph["medical_systems"]) == {"general", "tcm"}
    labels = {node["label"]: node for node in graph["nodes"]}
    assert labels["气虚候选"]["role"] == "primary"
    assert labels["血瘀候选"]["role"] == "primary"
    assert labels["痰湿兼夹候选"]["role"] == "candidate"
    assert labels["热证低证据候选"]["role"] == "candidate"
    assert labels["热证低证据候选"]["confidence"] == "low"
    assert labels["热证低证据候选"]["missing_evidence"]
    inferred = [
        node for node in graph["nodes"] if node["assertion_status"] == "rule_inferred"
    ]
    assert inferred
    assert all(node["evidence_refs"] for node in inferred)
    assert all(node["medical_system"] == "tcm" for node in inferred)
    assert all(node["evidence_links"] for node in inferred)
    assert all(node["review_status"] == "unreviewed" for node in inferred)
    assert {issue.code for issue in result.issues} == {
        "MEDICAL_REFERENCE_GAP",
        "SAFETY_STATUS_NOT_CLEARED",
    }


def test_tcm_reasoning_rejects_missing_safety_context() -> None:
    _, case = _distill_case()
    result = create_facade().invoke_skill(
        SkillInvocation(
            task_id="t02-missing-safety",
            skill_id="tcm-reasoning",
            input_data={"canonical_case": case},
        )
    )

    assert result.status == SkillStatus.FAILURE
    assert result.output is None
    assert result.issues[0].code == "INPUT_SCHEMA_INVALID"


def test_case_contract_preserves_structured_values_codes_time_and_multiple_sources() -> None:
    result = create_facade().invoke_skill(
        SkillInvocation(
            task_id="t02-generality-contract",
            skill_id="case-distillation",
            input_data={
                "raw_case": {
                    "case_ref": "GENERAL-CASE-001",
                    "identifiers": [
                        {"system": "urn:local:pseudonym", "value": "P-001"}
                    ],
                    "source_id": "src_note",
                    "related_source_ids": ["src_lab"],
                    "source_use_scope": "local_research_test_only",
                    "language": "zh-CN",
                    "patient": {
                        "sex": "female",
                        "age": 42,
                        "privacy_labels": [{"text": "deidentified"}],
                    },
                    "encounters": [
                        {
                            "encounter_key": "outpatient-1",
                            "sequence": 1,
                            "period": {
                                "raw": "2026-09-01 上午",
                                "point": "2026-09-01T09:00:00+08:00",
                                "precision": "minute",
                                "certainty": "approximate",
                            },
                            "status": "completed",
                            "encounter_classes": [{"text": "outpatient"}],
                            "fields": [
                                {
                                    "raw_key": "实验室结果",
                                    "raw_value": {
                                        "display": "血糖 6.2 mmol/L",
                                        "numeric": 6.2,
                                        "unit": "mmol/L",
                                    },
                                    "raw_type": "structured_cell",
                                    "category": "laboratory",
                                    "normalized_concept": {
                                        "text": "血糖",
                                        "codings": [
                                            {
                                                "system": "http://loinc.org",
                                                "code": "example-only",
                                                "display": "Glucose",
                                            }
                                        ],
                                    },
                                    "normalized_value": {
                                        "value_type": "quantity",
                                        "quantity": {
                                            "value": 6.2,
                                            "unit": "mmol/L",
                                            "system": "http://unitsofmeasure.org",
                                            "code": "mmol/L",
                                        },
                                    },
                                    "status": "final",
                                    "effective_time": {
                                        "point": "2026-09-01T08:30:00+08:00",
                                        "precision": "minute",
                                        "certainty": "exact",
                                    },
                                    "information_origin": "device",
                                    "evidence_refs": ["ev_lab_001"],
                                    "mapping_status": "mapped",
                                    "mapping_rule_version": "test-1",
                                }
                            ],
                        }
                    ],
                }
            },
        )
    )

    assert result.status == SkillStatus.SUCCESS
    assert result.output is not None
    case = result.output["canonical_case"]
    assert case["source_ids"] == ["src_note", "src_lab"]
    assert case["identifiers"][0]["value"] == "P-001"
    encounter = case["encounters"][0]
    assert encounter["status"] == "completed"
    observation = encounter["observations"][0]
    assert observation["raw_value"]["numeric"] == 6.2
    assert observation["raw_text"].startswith("{")
    assert observation["concept"]["codings"][0]["system"] == "http://loinc.org"
    assert observation["value"]["value_type"] == "quantity"
    assert observation["value"]["quantity"]["value"] == 6.2
    assert observation["effective_time"]["certainty"] == "exact"
    assert observation["information_origin"] == "device"


def test_negated_observation_is_not_used_as_positive_reasoning_support() -> None:
    case_input = _case_input()
    field = case_input["raw_case"]["encounters"][0]["fields"][4]
    case_input["raw_case"]["encounters"][0]["fields"] = [
        {**field, "raw_value": "无乏力", "normalized_text": "乏力", "polarity": "absent"}
    ]
    facade = create_facade()
    distilled = facade.invoke_skill(
        SkillInvocation(
            task_id="t02-negated-distillation",
            skill_id="case-distillation",
            input_data=case_input,
        )
    )
    assert distilled.output is not None
    reasoned = facade.invoke_skill(
        SkillInvocation(
            task_id="t02-negated-reasoning",
            skill_id="tcm-reasoning",
            input_data={
                "canonical_case": distilled.output["canonical_case"],
                "safety_context": {
                    "status": "cleared",
                    "source": "test_only",
                },
            },
        )
    )

    assert reasoned.output is not None
    labels = {node["label"] for node in reasoned.output["reasoning_graph"]["nodes"]}
    assert "气虚候选" not in labels


def test_generic_contract_rejects_semantically_empty_typed_values() -> None:
    with pytest.raises(ValidationError):
        CodeableConcept()
    with pytest.raises(ValidationError):
        RangeValue(value_type="range")
