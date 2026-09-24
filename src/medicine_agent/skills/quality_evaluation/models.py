from __future__ import annotations

from medicine_agent.domain.models import QualityReport, StrictModel


class QualityEvaluationInput(StrictModel):
    package_path: str


class QualityEvaluationOutput(StrictModel):
    report: QualityReport

