from __future__ import annotations

from pathlib import Path

from medicine_agent.packages.io import validate_package_path
from medicine_agent.runtime.base import SkillContext, manifest_path
from medicine_agent.runtime.manifest import load_manifest
from medicine_agent.skills.quality_evaluation.models import (
    QualityEvaluationInput,
    QualityEvaluationOutput,
)


class QualityEvaluationSkill:
    manifest = load_manifest(manifest_path(__file__))
    input_model = QualityEvaluationInput
    output_model = QualityEvaluationOutput

    def execute(
        self, value: QualityEvaluationInput, context: SkillContext
    ) -> QualityEvaluationOutput:
        del context
        return QualityEvaluationOutput(report=validate_package_path(Path(value.package_path)))

