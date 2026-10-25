# T02-B20 五类知识最小合成生产消费与复核准备闭环

> in_progress；D01 ready_for_execution，待DeepSeek固定执行；2026-10-25。

## 本版本接手

先读RESUME.md了解本次汇总改动、已确认边界、proposals未确认设计与本地前置。用户已授权本次本地commit，未授权push；下方D01执行范围/禁止事项仍适用于执行方，提交不改变ready_for_execution状态，也不构成思维实现许可。

## 依据与分工

总体分层口径：数据与思维的主体职责/业务逻辑分开，公共Schema、语义、模型适配、存储、运行时和注册入口可共用，不要求严格隔离，不新增隔离重构。B20归数据业务验证；AI后续设计/派单/实现/评审须明确所属职责与跨层接口。思维实现确认门不变。

思维层设计确认门已生效：当前新设计未获用户确认。B20只验证独立数据闭环，不实现思维策略；将来任务一旦涉及病例驱动检索/联想/候选推演等新增或实质扩展实现，必须先停止并询问用户是否确认本次设计，记录明确确认的版本/范围后才编码或委派。详见overall/规则与变更策略.md。

B19已Codex核验、回读原产品并归档；其TXT/theory结果不能代替五类实际运行闭环。B20沿用现有category/group/field，区分类型能表示、最小软件闭环、真实材料医学确认，不改包或新增医学字典。只CURRENT正式，NEXT不执行。

Codex定方向、设计、冻结采集器并核验；DeepSeek只做固定重复构造/查询/独立机械校验/证据，不并发改文件、不调预期或扩医学判断。

## 设计已完成

设计evidence/T02B20_DESIGN.md；执行单evidence/T02B20_D01_EXECUTION.md；采集器tasks/benchmarks/b20_five_types_check.py（SHA见执行单），复用冻结B19和D01保护函数。五行映射来自既有test_all_five_categories_and_theory_without_symptoms与唯一注册表，无新Schema。

Codex已验证全部5类图类型/证据，foundation/case两端实际smoke通过：2包/2原文/2节点/2字段/4候选/6空白会话目标，0意见，状态未审、禁发布训练。555保护文件/349Schema不变。证据artifacts/b20-d01/codex-design-smoke-final-20261025/和codex-design-verification.json。完整5类产包/查询/准备矩阵未执行，留给DeepSeek。

## 当前只执行D01

DeepSeek按执行单运行1次完整5类：5条contract、5个实际自制包、共同查询5节点、逐类查询各1节点、准备5原文/5节点/5字段/10候选、空白会话15目标/0意见。checks应8行，全量正式矩阵尚未运行。只写新artifacts、RESULT及3状态事实进度，停executed_pending_review；不归档/不改NEXT，不写医学/许可/性能门passed。

错误留证交Codex，不改三脚本、设计、执行单、生产src/tests、349Schema/字段或原包来全绿。每类只1字段：case_history不是CanonicalCase/诊次链；formula_original_composition不是配伍/剂量/安全处方，其他类别同样不等于完整业务或医学认可。完整能力缺口后续按原产品目标重评，不因最小验证通过自动消失。

无新真实资料/模型服务/网络/依赖/OCR/真实蒸馏/训练，不读模型配置，不改docs/log/pdfs，无commit/push。下一步无需新文件或权限，直接按D01执行。
