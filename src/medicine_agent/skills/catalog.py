from __future__ import annotations

from medicine_agent.runtime.registry import SkillRegistry
from medicine_agent.skills.evidence_grounding.handler import EvidenceGroundingSkill
from medicine_agent.skills.knowledge_distillation.handler import KnowledgeDistillationSkill
from medicine_agent.skills.knowledge_package_build_validate.handler import (
    KnowledgePackageBuildValidateSkill,
)
from medicine_agent.skills.knowledge_package_query.handler import KnowledgePackageQuerySkill
from medicine_agent.skills.material_ingestion.handler import MaterialIngestionSkill
from medicine_agent.skills.quality_evaluation.handler import QualityEvaluationSkill


def build_registry() -> SkillRegistry:
    return SkillRegistry(
        [
            MaterialIngestionSkill(),
            EvidenceGroundingSkill(),
            KnowledgeDistillationSkill(),
            KnowledgePackageBuildValidateSkill(),
            KnowledgePackageQuerySkill(),
            QualityEvaluationSkill(),
        ]
    )

