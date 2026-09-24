from __future__ import annotations

from medicine_agent.domain.ids import stable_id
from medicine_agent.domain.models import EvidenceRecord
from medicine_agent.runtime.base import SkillContext, manifest_path
from medicine_agent.runtime.manifest import load_manifest
from medicine_agent.skills.evidence_grounding.models import (
    EvidenceGroundingInput,
    EvidenceGroundingOutput,
)


class EvidenceGroundingSkill:
    manifest = load_manifest(manifest_path(__file__))
    input_model = EvidenceGroundingInput
    output_model = EvidenceGroundingOutput

    def execute(
        self, value: EvidenceGroundingInput, context: SkillContext
    ) -> EvidenceGroundingOutput:
        del context
        evidence = [
            EvidenceRecord(
                evidence_id=stable_id(
                    "ev",
                    {"fragment_id": fragment.fragment_id, "raw_text": fragment.text},
                ),
                source_id=fragment.source_id,
                fragment_id=fragment.fragment_id,
                raw_text=fragment.text,
                location={
                    "start_line": fragment.start_line,
                    "end_line": fragment.end_line,
                    "ordinal": fragment.ordinal,
                },
            )
            for fragment in value.fragments
        ]
        return EvidenceGroundingOutput(evidence=evidence)

