"""Single-file delivery schemas; internal layout does not define user permissions."""
from typing import Literal
from pydantic import Field, model_validator
from medicine_agent.domain.models import StrictModel
from medicine_agent.domain.owned_analysis import OwnedAnalysisRequest
from medicine_agent.domain.tcm_knowledge import KnowledgeAddress


class LearningRequest(OwnedAnalysisRequest):
    base_packages: list[str] = Field(default_factory=list,description='已完成的数据包文件；作为完整知识基础，不是新资料或更新权限')

    @model_validator(mode='after')
    def check_bases(self):
        if len(set(self.base_packages)) != len(self.base_packages):
            raise ValueError('Base package paths must be unique')
        return self


class BundleComponent(StrictModel):
    path: str = Field(description='归档文件内部的来源分区路径，由运行时管理')
    package_id: str = Field(description='原来源包身份，复制后保持稳定以回溯原节点')
    manifest_sha256: str = Field(pattern='^[0-9a-f]{64}$')
    active: bool = Field(default=True,description='该来源版本是否进入默认知识视图；历史内容仍保存在文件内')


class ConceptGroup(StrictModel):
    concept_id: str = Field(description='候选概念入口身份，不替代来源节点')
    label: str = Field(description='规范化标题或别名，用于候选查找，不代表医学同义结论')
    members: list[KnowledgeAddress] = Field(min_length=2,description='关联的各来源节点地址；每个节点的原文、解释和字段独立保留')
    status: Literal['candidate'] = 'candidate'
    matching_method: Literal['normalized_title_or_alias'] = 'normalized_title_or_alias'


class DerivedBundle(StrictModel):
    version: Literal['0.1.0'] = '0.1.0'
    bundle_id: str = Field(description='由文件内容清单、来源分区、关联和贡献记录计算的数据包身份')
    contributor_id: str | None = Field(default=None,description='本次贡献者的可选声明；不限制任何人的继续学习或更新')
    base_package_ids: list[str] = Field(description='本次继承的基础数据包身份；实际必要来源内容同时内置')
    components: list[BundleComponent] = Field(min_length=1,description='文件内完整保存的来源包及版本，包含原文、字段、分类和更正历史')
    files: dict[str, str] = Field(description='关联、复核记录和基础包血缘快照的包内路径到SHA256校验和')
    concept_groups: list[ConceptGroup] = Field(default_factory=list,description='统一候选概念入口和独立来源成员，便于联合分析')
    unresolved_package_ids: list[str] = Field(default_factory=list,description='原先已缺失的外部联系；保留引用并明确未解析，不伪造内容')
    status: Literal['research_candidate'] = 'research_candidate'


LEARNING_MODELS = (LearningRequest, BundleComponent, ConceptGroup, DerivedBundle)
