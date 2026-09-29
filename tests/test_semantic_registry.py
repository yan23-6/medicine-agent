import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from medicine_agent.semantics import (
    SemanticContext,
    SemanticRegistry,
    load_semantic_registry,
    validate_semantic_context,
    validate_semantic_registry,
)
from medicine_agent.runtime.errors import SemanticContractError
from medicine_agent.bootstrap import create_facade
from medicine_agent.domain.clinical import (
    CanonicalCase,
    ClinicalObservation,
    ClinicalReasoningGraph,
    ReasoningNode,
    SafetyContext,
)
from medicine_agent.domain.models import SkillInvocation, SkillStatus


CASE_FIXTURE = Path(__file__).parent / "fixtures" / "t02" / "chest_bi_case.json"


def test_unified_semantic_registry_is_valid_and_has_expected_profiles() -> None:
    report = validate_semantic_registry()
    registry = load_semantic_registry()

    assert report["valid"] is True
    assert report["version"] == "0.1.0"
    assert {profile.profile_id for profile in registry.profiles} == {
        "common",
        "tcm",
        "western",
        "safety",
        "formula",
    }
    assert report["counts"]["fields"] == len(registry.fields)


def test_specialized_profiles_do_not_redefine_common_or_each_other() -> None:
    registry = load_semantic_registry()
    fields = {field.field_id: field for field in registry.fields}

    for profile in registry.profiles:
        for field_ref in profile.field_refs:
            field = fields[field_ref]
            if field.scope == "specialized":
                assert field.owner_profile == profile.profile_id
                assert field.field_id.startswith(f"{profile.profile_id}.")


def test_schema_bindings_point_to_real_schema_fields_and_semantics() -> None:
    registry = load_semantic_registry()
    models = {
        model.__name__: model
        for model in (
            CanonicalCase,
            ClinicalObservation,
            ClinicalReasoningGraph,
            ReasoningNode,
            SafetyContext,
        )
    }
    semantic_fields = {field.field_id for field in registry.fields}

    assert registry.schema_bindings
    for binding in registry.schema_bindings:
        assert binding.schema_object in models
        assert binding.schema_field in models[binding.schema_object].model_fields
        assert binding.semantic_field_ref in semantic_fields


def test_specialized_profile_requires_declared_inheritance_chain() -> None:
    context = SemanticContext(enabled_profiles=["formula"])

    with pytest.raises(SemanticContractError, match="missing inherited profiles"):
        validate_semantic_context(context, required_profiles=set())


def test_duplicate_semantic_function_is_rejected() -> None:
    payload = load_semantic_registry().model_dump(mode="json")
    duplicate = copy.deepcopy(payload["fields"][0])
    duplicate["field_id"] = "common.duplicate_id"
    payload["fields"].append(duplicate)

    with pytest.raises(ValidationError, match="duplicate semantic_key"):
        SemanticRegistry.model_validate(payload)


def test_skill_rejects_unsupported_semantic_registry_version() -> None:
    payload = json.loads(CASE_FIXTURE.read_text("utf-8"))
    payload["semantic_context"] = {
        "registry_id": "medicine-agent.semantic-registry",
        "registry_version": "99.0.0",
        "enabled_profiles": ["common"],
    }
    result = create_facade().invoke_skill(
        SkillInvocation(
            task_id="semantic-version-mismatch",
            skill_id="case-distillation",
            input_data=payload,
        )
    )

    assert result.status == SkillStatus.FAILURE
    assert result.output is None
    assert result.issues[0].code == "SEMANTIC_CONTRACT_INVALID"
