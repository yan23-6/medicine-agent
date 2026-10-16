from __future__ import annotations

from medicine_agent.runtime.registry import SkillRegistry
from medicine_agent.skills.case_distillation.handler import CaseDistillationSkill
from medicine_agent.skills.evidence_grounding.handler import EvidenceGroundingSkill
from medicine_agent.skills.knowledge_distillation.handler import KnowledgeDistillationSkill
from medicine_agent.skills.knowledge_package_build_validate.handler import (
    KnowledgePackageBuildValidateSkill,
)
from medicine_agent.skills.knowledge_package_query.handler import KnowledgePackageQuerySkill
from medicine_agent.skills.material_ingestion.handler import MaterialIngestionSkill
from medicine_agent.skills.quality_evaluation.handler import QualityEvaluationSkill
from medicine_agent.skills.tcm_reasoning.handler import TCMReasoningSkill
from medicine_agent.skills.document_extraction.handler import DocumentExtractionSkill
from medicine_agent.skills.tcm_knowledge_analysis.handler import TCMKnowledgeAnalysisSkill


def build_registry() -> SkillRegistry:
    return SkillRegistry(
        [
            MaterialIngestionSkill(),
            EvidenceGroundingSkill(),
            KnowledgeDistillationSkill(),
            KnowledgePackageBuildValidateSkill(),
            KnowledgePackageQuerySkill(),
            QualityEvaluationSkill(),
            CaseDistillationSkill(),
            TCMReasoningSkill(),
            DocumentExtractionSkill(),
            TCMKnowledgeAnalysisSkill(),
        ]
    )

