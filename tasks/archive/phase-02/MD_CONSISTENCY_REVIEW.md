# 推进前 Markdown 一致性核对（2026-10-15）

> 本次先核对再编码；docs 参考材料、log 周报及被忽略的运行产物不作为稳定规范修改。

## 历史：最初发现并先行处理（归属限制随后撤销）

- md/README 的当前阶段仍指 T01；md/16、overall 总表还留有 T02-P/B0 建设中说法，与已验收产物不符。
- B2 草案未约束同用户复用；产品尚无用户归属与可迁移分析缓存，不能写成已有。
- 单次查询已覆盖多包，但关联只展开一层且可带出未选用版本；嵌套用户目录的 links 尚未发现。
- 来源文本已随证据保存；第二份资料必须独立采集，不得拿旧资料摘要冒充其原文。
- 临床、数据库、正式包及问诊仍属后续阶段；既有验收/基线与早期报告是历史记录，不回写为当前实现。

## 本次同步范围

稳定设计、总体需求、当前/下一任务、受影响的阶段03/04草案、运行说明及根规则同步；医学字段说明由唯一注册表生成，字段意义未变。根历史稿与历史任务仅标明历史属性，原始验收数据不重写。测试夹具与各 Skill 文档未改变专业输入输出；用户归属属于产品任务/包元数据。

## 检查清单（项目维护文件全量读取）

- `AGENTS.md`：现行设计/维护说明；检查需求与状态。
- `DEVELOPMENT.md`：现行设计/维护说明；检查需求与状态。
- `README.md`：现行设计/维护说明；检查需求与状态。
- `中医病机知识蒸馏Skill-Agent平台需求分析与技术评审.md`：历史基线/验收；与当前状态分开解释。
- `通用知识解构Skill-需求分析与技术评审.md`：历史基线/验收；与当前状态分开解释。
- `项目阶段进展记录.md`：历史基线/验收；与当前状态分开解释。
- `config/AGENTS.md`：现行设计/维护说明；检查需求与状态。
- `config/README.md`：现行设计/维护说明；检查需求与状态。
- `md/01-产品目标与边界.md`：现行设计/维护说明；检查需求与状态。
- `md/02-整体技术架构.md`：现行设计/维护说明；检查需求与状态。
- `md/03-三层病机结构与对齐.md`：现行设计/维护说明；检查需求与状态。
- `md/04-知识包与证据数据模型.md`：现行设计/维护说明；检查需求与状态。
- `md/05-知识蒸馏Skill与构建流水线.md`：现行设计/维护说明；检查需求与状态。
- `md/06-Agent平台与任务编排.md`：现行设计/维护说明；检查需求与状态。
- `md/07-运行时推演与上下文记忆.md`：现行设计/维护说明；检查需求与状态。
- `md/08-热插拔与跨环境安装.md`：现行设计/维护说明；检查需求与状态。
- `md/09-评审评价与临床验证.md`：现行设计/维护说明；检查需求与状态。
- `md/10-医疗安全与数据治理.md`：现行设计/维护说明；检查需求与状态。
- `md/11-实施路线与论文设计.md`：现行设计/维护说明；检查需求与状态。
- `md/12-接口与扩展约定.md`：现行设计/维护说明；检查需求与状态。
- `md/13-方剂药物层与后训练方案.md`：现行设计/维护说明；检查需求与状态。
- `md/14-中西医临床认知与多智能体架构.md`：现行设计/维护说明；检查需求与状态。
- `md/15-Skill运行规范与知识包生产消费闭环.md`：现行设计/维护说明；检查需求与状态。
- `md/16-PDF资料处理与数据包更新.md`：现行设计/维护说明；检查需求与状态。
- `md/17-中医知识节点与疗效证据.md`：现行设计/维护说明；检查需求与状态。
- `md/18-候选复核与更正记录.md`：现行设计/维护说明；检查需求与状态。
- `md/README.md`：现行设计/维护说明；检查需求与状态。
- `md/中医字段说明书.generated.md`：注册表生成；核对语义来源。
- `tasks/README.md`：现行设计/维护说明；检查需求与状态。
- `tasks/STATE.md`：现行设计/维护说明；检查需求与状态。
- `tests/fixtures/basic.md`：测试夹具/说明，非产品需求。
- `tests/fixtures/t02p/README.md`：测试夹具/说明，非产品需求。
- `tasks/overall/技术与能力总表.md`：现行设计/维护说明；检查需求与状态。
- `tasks/overall/终极需求.md`：现行设计/维护说明；检查需求与状态。
- `tasks/overall/规则与变更策略.md`：现行设计/维护说明；检查需求与状态。
- `tasks/phases/01-skill-foundation/ACCEPTANCE_PLAN.md`：历史基线/验收；与当前状态分开解释。
- `tasks/phases/01-skill-foundation/ACCEPTANCE_REPORT.md`：历史基线/验收；与当前状态分开解释。
- `tasks/phases/01-skill-foundation/ADAPTER_DESIGN.md`：历史基线/验收；与当前状态分开解释。
- `tasks/phases/01-skill-foundation/CURRENT_TASK.md`：历史基线/验收；与当前状态分开解释。
- `tasks/phases/01-skill-foundation/FUTURE.md`：历史基线/验收；与当前状态分开解释。
- `tasks/phases/01-skill-foundation/NEXT_TASK.md`：历史基线/验收；与当前状态分开解释。
- `tasks/phases/01-skill-foundation/ONLINE_ACCEPTANCE.md`：历史基线/验收；与当前状态分开解释。
- `tasks/phases/01-skill-foundation/README.md`：历史基线/验收；与当前状态分开解释。
- `tasks/phases/01-skill-foundation/TECHNICAL_DESIGN.md`：历史基线/验收；与当前状态分开解释。
- `tasks/phases/02-tcm-distillation/CURRENT_TASK.md`：现行设计/维护说明；检查需求与状态。
- `tasks/phases/02-tcm-distillation/FUTURE.md`：现行设计/维护说明；检查需求与状态。
- `tasks/phases/02-tcm-distillation/FUTURE_SKILL_DESIGN.md`：现行设计/维护说明；检查需求与状态。
- `tasks/phases/02-tcm-distillation/GENERALITY_AUDIT.md`：现行设计/维护说明；检查需求与状态。
- `tasks/phases/02-tcm-distillation/MILESTONES.md`：现行设计/维护说明；检查需求与状态。
- `tasks/phases/02-tcm-distillation/NEXT_TASK.md`：现行设计/维护说明；检查需求与状态。
- `tasks/phases/02-tcm-distillation/README.md`：现行设计/维护说明；检查需求与状态。
- `tasks/phases/02-tcm-distillation/REQUIREMENTS_RECHECK.md`：现行设计/维护说明；检查需求与状态。
- `tasks/phases/02-tcm-distillation/REVIEW.md`：现行设计/维护说明；检查需求与状态。
- `tasks/phases/02-tcm-distillation/SEMANTIC_CONTRACT_ACCEPTANCE.md`：历史基线/验收；与当前状态分开解释。
- `tasks/phases/02-tcm-distillation/SOURCE_PLAN.md`：现行设计/维护说明；检查需求与状态。
- `tasks/phases/02-tcm-distillation/T02A_ACCEPTANCE.md`：历史基线/验收；与当前状态分开解释。
- `tasks/phases/02-tcm-distillation/T02A_TASK_BASELINE.md`：历史基线/验收；与当前状态分开解释。
- `tasks/phases/02-tcm-distillation/T02B0_ACCEPTANCE.md`：历史基线/验收；与当前状态分开解释。
- `tasks/phases/02-tcm-distillation/T02B0_TASK_BASELINE.md`：历史基线/验收；与当前状态分开解释。
- `tasks/phases/02-tcm-distillation/T02B1_ACCEPTANCE.md`：历史基线/验收；与当前状态分开解释。
- `tasks/phases/02-tcm-distillation/T02B_CLINICAL_DRAFT.md`：现行设计/维护说明；检查需求与状态。
- `tasks/phases/02-tcm-distillation/T02P_ACCEPTANCE.md`：历史基线/验收；与当前状态分开解释。
- `tasks/phases/02-tcm-distillation/T02P_TASK_BASELINE.md`：历史基线/验收；与当前状态分开解释。
- `tasks/phases/03-package-storage/CURRENT_TASK.md`：未来草案；不伪装当前实现。
- `tasks/phases/03-package-storage/FUTURE.md`：未来草案；不伪装当前实现。
- `tasks/phases/03-package-storage/NEXT_TASK.md`：未来草案；不伪装当前实现。
- `tasks/phases/03-package-storage/README.md`：未来草案；不伪装当前实现。
- `tasks/phases/04-multi-agent-runtime/CURRENT_TASK.md`：未来草案；不伪装当前实现。
- `tasks/phases/04-multi-agent-runtime/FUTURE.md`：未来草案；不伪装当前实现。
- `tasks/phases/04-multi-agent-runtime/NEXT_TASK.md`：未来草案；不伪装当前实现。
- `tasks/phases/04-multi-agent-runtime/README.md`：未来草案；不伪装当前实现。
- `tasks/phases/05-formula-platform/CURRENT_TASK.md`：未来草案；不伪装当前实现。
- `tasks/phases/05-formula-platform/FUTURE.md`：未来草案；不伪装当前实现。
- `tasks/phases/05-formula-platform/NEXT_TASK.md`：未来草案；不伪装当前实现。
- `tasks/phases/05-formula-platform/README.md`：未来草案；不伪装当前实现。
- `tasks/phases/06-evaluation-training/CURRENT_TASK.md`：未来草案；不伪装当前实现。
- `tasks/phases/06-evaluation-training/FUTURE.md`：未来草案；不伪装当前实现。
- `tasks/phases/06-evaluation-training/NEXT_TASK.md`：未来草案；不伪装当前实现。
- `tasks/phases/06-evaluation-training/README.md`：未来草案；不伪装当前实现。
- `src/medicine_agent/analysis/README.md`：现行设计/维护说明；检查需求与状态。
- `src/medicine_agent/semantics/README.md`：现行设计/维护说明；检查需求与状态。
- `src/medicine_agent/skills/case_distillation/SKILL.md`：工具规范；本次专业输入输出不变。
- `src/medicine_agent/skills/document_extraction/SKILL.md`：工具规范；本次专业输入输出不变。
- `src/medicine_agent/skills/evidence_grounding/SKILL.md`：工具规范；本次专业输入输出不变。
- `src/medicine_agent/skills/knowledge_distillation/SKILL.md`：工具规范；本次专业输入输出不变。
- `src/medicine_agent/skills/knowledge_package_build_validate/SKILL.md`：工具规范；本次专业输入输出不变。
- `src/medicine_agent/skills/knowledge_package_query/SKILL.md`：工具规范；本次专业输入输出不变。
- `src/medicine_agent/skills/material_ingestion/SKILL.md`：工具规范；本次专业输入输出不变。
- `src/medicine_agent/skills/quality_evaluation/SKILL.md`：工具规范；本次专业输入输出不变。
- `src/medicine_agent/skills/tcm_knowledge_analysis/SKILL.md`：工具规范；本次专业输入输出不变。
- `src/medicine_agent/skills/tcm_reasoning/SKILL.md`：工具规范；本次专业输入输出不变。

当前项目维护范围共 94 个 Markdown；首次读取还包含本机依赖缓存副本，其非项目规范，已从维护清单排除，不修改第三方依赖。


## 历史：用户再次纠正后的差距（已由B2实现覆盖）

作者不构成更新权限。之前核对只针对旧理解；已同步第19章、设计入口、受影响稳定文档、整体需求、当前阶段和存储草案。旧归属限制实验及测试仍需代码层撤销，新的多基础包派生入口尚未实现验收；这是已识别的实现差距，不是已完成能力。

本次代码修正前已复核现行第19章、CURRENT_TASK、运行入口及旧拒绝分支。采用 components 自包含目录保留来源身份；本轮撤销错误作者测试，新增第三人气/热、多次派生、原包缺失与独立安装检查。历史拒绝实验仅归档，不作为现行约束。


## 2026-10-15 单文件交付澄清

用户本次澄清：最终数据包是文件，固定目录同时存包和统一说明书。已撤销第19章“自包含目录作为最终包”约定；对齐稳定设计、总体需求、当前任务及阶段03草案。目录实现仅内部原型，文件封装/固定路径尚未验收。


## 2026-10-16 最终实现核对

现行规则统一为：每包一个.medpkg文件、固定用户知识目录及统一说明书、任何贡献者可基于多基础文件学习、同概念保留独立来源、旧知识和完整历史自包含。components/links/reviews/history都是包内资源；目录API仅内部兼容。上文初始归属限制和文件未实现状态均为当时审计记录，不再是现行设计。

已同步稳定设计04/08/15/16/17/18/19、总览、总体需求/能力、当前阶段任务/里程碑、03/04草案及产品使用说明。字段说明从唯一注册表及操作契约重新生成；医学字典仍0.3.1，不新增第二字典。文件复核/更正在私有快照构建，原子交付后才可读；文件默认采用最高有效来源版本，显式固定选择优先，区别于B1旧目录接口。

完整测试、发行物和文档链接检查结果见 T02B2_ACCEPTANCE.md。docs/log未修改，原PDF未提交，未读取本地密钥。临床金标准、T02-A用户评审、正式v0/数据库及问诊边界保持。


## 2026-10-16 B3推进前复核

已重新读取STATE、总体需求/能力、当前与下一任务及受影响稳定设计。全量97份维护Markdown读取、链接与生成说明检查通过；核实教材、运行代码、模型配置存在和B2发行产物。将B3草案升为正式当前任务并归档B2；同步总体能力、阶段、稳定设计16与根入口。此次只做已有功能真实质量核验，未改变数据结构/角色/医学字段，未来03/04设计不受影响，无需凑改。


## 2026-10-16 B3结束核对

本轮没有产品代码或Schema变更；真实产物与质量问题均已记录。同步STATE、CURRENT/NEXT、阶段入口/里程碑、总体能力、稳定设计16/17与根入口；B2基线归档。下一步由“增加新页”改为先修本轮实际问题，不把文档已写当代码已修。docs/log与未来未受影响草案保持。


## B4编码前核对

重新读取现行任务、总体需求和稳定来源设计；已有99份维护Markdown全量检查。用户新要求已同步稳定16/17、总体需求/能力、当前/下一任务、阶段及受影响03存储草案。B3完成任务另存历史；不把拟修复写成已实现。代码将保留旧包与证据，说明书由唯一语义源生成。


## B4实际完成核对

已完成原文优先修复与同3页复验：133个不同用例、最终wheel源码资源一致、独立安装仅单文件迁移通过；113条OCR及位置完全保留，旧包/PDF不变。3条不可靠建议显式歧义并保存原值，不宣称医学正确或完整理解。STATE/CURRENT、稳定设计与总表已同步；旧B3报告和原包保持历史，不把旧报告中的待修结论混为当前状态。下一草案为小范围增量学习，需重评范围/外发授权。详见T02B4_ACCEPTANCE.md。


## B5启动及结束复核

启动前读取103份维护Markdown并检查本地引用，核实B4包/原PDF/运行时及既有发行文件。用户新要求“每步同步STATE/HANDOFF”已同步AGENTS、稳定md入口、tasks规则和总体变更规则。B5重评后建立正式任务，保留B4基线。结束同步阶段、总体能力和稳定19的真实匹配不足；既有多基础完整继承原则不变，未改产品代码/语义/Schema，不更改未受影响的03/04草案；后续B6启动前再评审。docs/log不改。
