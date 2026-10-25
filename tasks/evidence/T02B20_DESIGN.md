# B20五类知识最小运行闭环设计

2026-10-25。B19核验/产品复查/归档后启用CURRENT B20。依据原01/04/16/17与overall五类内容目标，区分类型能表示、最小软件运行、真实资料与医学认可，避免从theory扩称全部完成。

## 固定内容映射

只引用既有KnowledgeCategory/GroupKind及唯一语义注册表，沿用tests/test_tcm_knowledge.py::test_all_five_categories_and_theory_without_symptoms的五行正例：

| category | group.kind | field_id |
|---|---|---|
| tcm_foundation | theory | tcm.theory_proposition_text |
| chinese_materia_medica | herb | tcm.herb_origin_species |
| tcm_pattern_differentiation | differentiation | tcm.pathomechanism |
| tcm_formula | formula | tcm.formula_original_composition |
| tcm_clinical_case | case | tcm.case_history |

不新增字段、字典、类别、Schema或包格式，不据测试缺口断言现有结构不足。已有单元用例主要验证图类型；本任务补公开单文件产物、分类消费和通用复核目标能否承载这些既有最小事实。

## 实验与oracle

Codex固定tasks/benchmarks/b20_five_types_check.py，复用冻结B19的只读验证/保护函数。本地确定性FiveModel只替换既有输出中的category/group/field，值和引文均为对应自制TXT原句，无远程LLM或医学推断。每类1行TXT/1独立来源/1节点/1字段，公共token FIVETYPE_SOFTWARE_ONLY，内容明确software-only/no medical assertion。

先对全部5行运行当前registry-backed TCMKnowledgeGraph/validate_graph_evidence，记录5条contract-checks；再经FileLearningService实际构建5个现有格式.medpkg，submit.classification.knowledge_categories固定为该类。每包实际校验1组件/1节点/1组/1字段，类别、组、字段、stated、节点原句、源SHA与未审状态匹配，模型函数每源调用1次。记录包/节点内容SHA及Source/Component/Node地址，不输出原文。

共同查询必须保留5个源事实和证据；随后以knowledge_category逐类查询，分别只命中对应1个节点，类别/组/字段和完整节点内容（除retrieval_facets）不变。不能用len(query.packages)计数，展平medical_nodes；基础校验复用B19的源SHA/证据/owner/内容检查。

ReviewPreparationService对5包实际prepare，必须complete/0 issues/0历史意见，source_evidence=5、nodes=5、facts=5、candidate_targets=10、gaps=0、rejected_candidates=0；所有空白worksheet保持未提交。精确候选地址为每类组件/节点各node与fact目标，不丢类型。

实际export准备目录、ReviewSessionService.create，再通过ReviewProgressService.report重验，必须15目标（原文5/节点5/字段5/异常0）、0评审/0event，全部pending，medical blocked、release/training false。不提交意见，避免人为造医学认可。原包字节/公开目录查询前后字节/349Schema与生产源码不变。

完整正式输出：contract-checks 5行、corpus 5行、checks 8行（joint1+分类5+准备1+空白会话1）；preparation-summary与blank-progress另存。内部实验产物不是产品新公开契约，不注册操作Schema；实际运行数据仍受原既有模型/Schema验证。

## 核验范围与后续判断

每类只取1个注册字段，不能宣称五类完整建模/内容质量均完成。case_history只是原文历史事实，不验证CanonicalCase、诊次边界或临床推理；formula_original_composition不是药物配伍/剂量/安全处方；herb_origin_species不证明药材鉴别/临床使用；pathomechanism不证明辨证正确。无疗效/安全/医学/许可门升级。

Codex先做5行类型/证据检查和foundation/case两个端点的实际软件smoke，结果通过；2包/2原文/2节点/2字段/4候选/6空白目标/0意见，证据artifacts/b20-d01/codex-design-smoke-final-20261025/。完整5类实际矩阵未执行，留给DeepSeek固定运行；不得把smoke当正式完成。

DeepSeek不改脚本/预期/源码/测试/Schema、不扩医学解释；失败留证交回Codex定位是构造器、现有入口还是必要事实缺口，不能自行改包或补造值。完成后Codex核验并回读原产品，分层记录已通过与未检查，再判断验收/下一项。当前不需新真实材料、模型服务或权限。
