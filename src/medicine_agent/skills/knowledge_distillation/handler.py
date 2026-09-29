from __future__ import annotations

from pydantic import ValidationError

from medicine_agent.domain.ids import stable_id
from medicine_agent.domain.models import EvidenceRecord, GenerationMethod, KnowledgeCandidate
from medicine_agent.runtime.base import SkillContext, manifest_path
from medicine_agent.runtime.errors import ModelConfigMissingError, OutputSchemaInvalidError
from medicine_agent.runtime.manifest import load_manifest
from medicine_agent.skills.knowledge_distillation.models import (
    KnowledgeDistillationInput,
    KnowledgeDistillationOutput,
    GeneratedKnowledgePayload,
)


class KnowledgeDistillationSkill:
    manifest = load_manifest(manifest_path(__file__))
    input_model = KnowledgeDistillationInput
    output_model = KnowledgeDistillationOutput

    def execute(
        self, value: KnowledgeDistillationInput, context: SkillContext
    ) -> KnowledgeDistillationOutput:
        if value.use_model and context.model_client is None:
            raise ModelConfigMissingError("A model client is required when use_model is true")
        knowledge: list[KnowledgeCandidate] = []
        groups = [value.evidence] if value.combine_evidence and value.evidence else [
            [item] for item in value.evidence
        ]
        for group in groups:
            readable_parts = [_readable_text(item) for item in group]
            readable = "\n\n".join(readable_parts)
            if value.use_model:
                assert context.model_client is not None
                generated = context.model_client.generate_json(
                    system=(
                        "Extract only information supported by the supplied evidence. "
                        "Return JSON with label and statement."
                    ),
                    user=readable,
                    schema={
                        "type": "object",
                        "required": ["label", "statement"],
                        "properties": {
                            "label": {"type": "string"},
                            "statement": {"type": "string"},
                        },
                    },
                )
                try:
                    parsed = GeneratedKnowledgePayload.model_validate(generated)
                except ValidationError as exc:
                    raise OutputSchemaInvalidError(
                        "Model output failed the knowledge payload schema",
                        details={"errors": exc.errors(include_url=False)},
                    ) from exc
                label = parsed.label
                statement = parsed.statement
                method = GenerationMethod.MODEL
            else:
                label = readable.splitlines()[0][:80]
                statement = readable
                method = GenerationMethod.RULE
            evidence_refs = [item.evidence_id for item in group]
            knowledge.append(
                KnowledgeCandidate(
                    knowledge_id=stable_id(
                        "kn",
                        {
                            "kind": "source_statement",
                            "statement": statement,
                            "evidence_refs": evidence_refs,
                        },
                    ),
                    kind="source_statement",
                    label=label,
                    statement=statement,
                    evidence_refs=evidence_refs,
                    generation_method=method,
                )
            )
        return KnowledgeDistillationOutput(knowledge=knowledge)


def _readable_text(item: EvidenceRecord) -> str:
    if item.correction_status == "confirmed" and item.corrected_text:
        return item.corrected_text
    return item.raw_text

