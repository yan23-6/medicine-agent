from __future__ import annotations

from importlib.resources import files
from typing import Literal, Self

from pydantic import Field, model_validator

from medicine_agent.domain.models import StrictModel


class ValueTypeDefinition(StrictModel):
    value_type_id: str
    definition: str
    representation: str


class SemanticFieldDefinition(StrictModel):
    field_id: str
    semantic_key: str
    label_zh: str
    definition: str
    scope: Literal["common", "specialized"]
    owner_profile: str
    value_type: str
    cardinality: str
    null_semantics: str
    allowed_on: list[str] = Field(min_length=1)
    source_refs: list[str] = Field(default_factory=list)
    example: str | None = None
    prohibited_interpretation: str | None = None


class RelationDefinition(StrictModel):
    relation_id: str
    label_zh: str
    definition: str
    direction: str
    source_types: list[str] = Field(min_length=1)
    target_types: list[str] = Field(min_length=1)
    evidence_required: bool
    prohibited_interpretation: str | None = None


class TerminologySystemDefinition(StrictModel):
    terminology_id: str
    name: str
    uri: str | None = None
    version_policy: str
    availability: Literal["reference_only", "not_loaded", "project_internal"]
    license_note: str
    source_url: str


class SourceDefinition(StrictModel):
    source_id: str
    title: str
    publisher: str
    version_or_date: str | None = None
    url: str
    use_scope: str


class SemanticProfileDefinition(StrictModel):
    profile_id: str
    label_zh: str
    purpose: str
    inherits: list[str] = Field(default_factory=list)
    field_refs: list[str] = Field(default_factory=list)
    terminology_refs: list[str] = Field(default_factory=list)
    routing_rule: str


class SchemaBindingDefinition(StrictModel):
    binding_id: str
    schema_object: str
    schema_field: str
    semantic_field_ref: str


class GovernanceDefinition(StrictModel):
    normative_registry: str
    unknown_field_policy: str
    unknown_concept_policy: str
    profile_override_policy: str
    ai_usage_policy: str
    change_policy: str


class SemanticContext(StrictModel):
    registry_id: str = "medicine-agent.semantic-registry"
    registry_version: str = "0.1.0"
    enabled_profiles: list[str] = Field(default_factory=lambda: ["common"])
    terminology_versions: dict[str, str] = Field(default_factory=dict)


class SemanticRegistry(StrictModel):
    registry_id: str
    version: str
    status: Literal["draft", "review", "released"]
    value_types: list[ValueTypeDefinition] = Field(min_length=1)
    fields: list[SemanticFieldDefinition] = Field(min_length=1)
    relations: list[RelationDefinition] = Field(min_length=1)
    terminology_systems: list[TerminologySystemDefinition] = Field(min_length=1)
    sources: list[SourceDefinition] = Field(min_length=1)
    profiles: list[SemanticProfileDefinition] = Field(min_length=1)
    schema_bindings: list[SchemaBindingDefinition] = Field(default_factory=list)
    governance: GovernanceDefinition

    @model_validator(mode="after")
    def validate_uniqueness_and_routing(self) -> Self:
        _require_unique("value_type_id", [item.value_type_id for item in self.value_types])
        _require_unique("field_id", [item.field_id for item in self.fields])
        _require_unique("semantic_key", [item.semantic_key for item in self.fields])
        _require_unique("relation_id", [item.relation_id for item in self.relations])
        _require_unique(
            "terminology_id",
            [item.terminology_id for item in self.terminology_systems],
        )
        _require_unique("source_id", [item.source_id for item in self.sources])
        _require_unique("profile_id", [item.profile_id for item in self.profiles])
        _require_unique("binding_id", [item.binding_id for item in self.schema_bindings])
        _require_unique(
            "schema binding target",
            [f"{item.schema_object}.{item.schema_field}" for item in self.schema_bindings],
        )

        value_types = {item.value_type_id for item in self.value_types}
        fields = {item.field_id: item for item in self.fields}
        terminologies = {item.terminology_id for item in self.terminology_systems}
        sources = {item.source_id for item in self.sources}
        profile_ids = {item.profile_id for item in self.profiles}

        for field in self.fields:
            if field.value_type not in value_types:
                raise ValueError(
                    f"field {field.field_id} uses unknown value type {field.value_type}"
                )
            missing_sources = sorted(set(field.source_refs) - sources)
            if missing_sources:
                raise ValueError(
                    f"field {field.field_id} references unknown sources: {missing_sources}"
                )
            expected_prefix = (
                "common." if field.scope == "common" else f"{field.owner_profile}."
            )
            if not field.field_id.startswith(expected_prefix):
                raise ValueError(
                    f"field {field.field_id} must use namespace {expected_prefix}"
                )
            if field.scope == "common" and field.owner_profile != "common":
                raise ValueError(f"common field {field.field_id} must be owned by common")
            if field.scope == "specialized" and field.owner_profile not in profile_ids:
                raise ValueError(
                    f"specialized field {field.field_id} has unknown owner profile"
                )

        for profile in self.profiles:
            missing_fields = sorted(set(profile.field_refs) - fields.keys())
            if missing_fields:
                raise ValueError(
                    f"profile {profile.profile_id} references unknown fields: {missing_fields}"
                )
            missing_terms = sorted(set(profile.terminology_refs) - terminologies)
            if missing_terms:
                raise ValueError(
                    f"profile {profile.profile_id} references unknown terminologies: {missing_terms}"
                )
            missing_parents = sorted(set(profile.inherits) - profile_ids)
            if missing_parents:
                raise ValueError(
                    f"profile {profile.profile_id} inherits unknown profiles: {missing_parents}"
                )
            for field_ref in profile.field_refs:
                field = fields[field_ref]
                if field.scope == "specialized" and field.owner_profile != profile.profile_id:
                    raise ValueError(
                        f"profile {profile.profile_id} cannot own field {field_ref}"
                    )
        for binding in self.schema_bindings:
            if binding.semantic_field_ref not in fields:
                raise ValueError(
                    f"binding {binding.binding_id} references unknown field "
                    f"{binding.semantic_field_ref}"
                )
        return self


def _require_unique(label: str, values: list[str]) -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    if duplicates:
        raise ValueError(f"duplicate {label}: {sorted(duplicates)}")


def load_semantic_registry() -> SemanticRegistry:
    registry_path = files("medicine_agent.semantics").joinpath("registry.json")
    return SemanticRegistry.model_validate_json(registry_path.read_text(encoding="utf-8"))


def validate_semantic_registry() -> dict[str, object]:
    registry = load_semantic_registry()
    return {
        "valid": True,
        "registry_id": registry.registry_id,
        "version": registry.version,
        "status": registry.status,
        "counts": {
            "value_types": len(registry.value_types),
            "fields": len(registry.fields),
            "relations": len(registry.relations),
            "terminology_systems": len(registry.terminology_systems),
            "sources": len(registry.sources),
            "profiles": len(registry.profiles),
            "schema_bindings": len(registry.schema_bindings),
        },
    }


def validate_semantic_context(
    context: SemanticContext, *, required_profiles: set[str]
) -> None:
    from medicine_agent.runtime.errors import SemanticContractError

    registry = load_semantic_registry()
    if context.registry_id != registry.registry_id:
        raise SemanticContractError(
            "Semantic registry identity does not match the runtime registry",
            details={"expected": registry.registry_id, "actual": context.registry_id},
        )
    if context.registry_version != registry.version:
        raise SemanticContractError(
            "Semantic registry version is unsupported",
            details={"expected": registry.version, "actual": context.registry_version},
        )
    available_profiles = {profile.profile_id for profile in registry.profiles}
    enabled_profiles = set(context.enabled_profiles)
    if len(enabled_profiles) != len(context.enabled_profiles):
        raise SemanticContractError(
            "Semantic context contains duplicate profiles",
            details={"enabled_profiles": context.enabled_profiles},
        )
    unknown_profiles = sorted(enabled_profiles - available_profiles)
    if unknown_profiles:
        raise SemanticContractError(
            "Semantic context enables unknown profiles",
            details={"unknown_profiles": unknown_profiles},
        )
    missing_profiles = sorted(required_profiles - enabled_profiles)
    if missing_profiles:
        raise SemanticContractError(
            "Semantic context is missing required profiles",
            details={"missing_profiles": missing_profiles},
        )
    profile_map = {profile.profile_id: profile for profile in registry.profiles}
    missing_inherited = sorted(
        {
            inherited
            for profile_id in enabled_profiles
            for inherited in profile_map[profile_id].inherits
            if inherited not in enabled_profiles
        }
    )
    if missing_inherited:
        raise SemanticContractError(
            "Semantic context is missing inherited profiles",
            details={"missing_profiles": missing_inherited},
        )
    available_terminologies = {
        item.terminology_id for item in registry.terminology_systems
    }
    unknown_terminologies = sorted(
        set(context.terminology_versions) - available_terminologies
    )
    if unknown_terminologies:
        raise SemanticContractError(
            "Semantic context declares unknown terminology systems",
            details={"unknown_terminologies": unknown_terminologies},
        )
