# 当前项目状态

思维层新设计待用户确认：开始相关新增或实质扩展实现前必须停止并询问，明确确认设计版本/范围后才编码或委派，通用“继续”不替代确认。独立数据层B20仍可按原执行单推进。规则见overall/规则与变更策略.md；分层口径已按用户澄清：数据层与思维层主体职责、侧重点和业务代码逻辑分开，公共Schema、语义、模型适配、存储、运行时与Skill注册允许共用；不要求严格进程/部署/模块加载/故障隔离，不将共享入口列为待修隔离缺口或新增重构任务。AI设计/派单/实现/评审须明确数据业务、思维业务或公共能力及跨层接口；保持数据功能/接口/旧包兼容，共享变更按影响回归。

新增`proposals/`候选设计目录（`proposals/AGENTS.md`声明draft/unconfirmed）：存放docs两份材料的分析、现有Schema映射、15单元结构验收集与开放问题，禁止当作实现依据或据此编码/派单，思维层确认门不变。该分析实测真实包478字段全属`tcm_foundation`、包内`relations`0条；属待定结论，未升格。该目录保持待定状态，本次仅纳入汇总版本，不升格设计。

本版本接手索引见RESUME.md：汇总B12—B19工程、B20待执行设计及proposals未确认分析；两份docs Word原件随版本纳入，真实材料/运行产物/密钥不提交。思维设计确认门不变，本次提交不构成实现授权。

2026-10-25；G2仍in_progress。唯一CURRENT为B20五类知识最小合成生产消费与复核准备闭环，设计与小样完成，D01 ready_for_execution，完整5类实际矩阵未执行。

B19已按限定单文件TXT/theory合成兼容范围done归档：1/5/20来源/27阶段、1543项证据/555保护文件/349Schema经Codex核验，新工作区再次查询20来源身份/证据/owner通过。见evidence/T02B19_CODEX_REVIEW.md、T02B19_PRODUCT_REVIEW.md、archive/phase-02/T02B19_ACCEPTANCE.md。它不证明五类全面运行或医学正确。

B20设计evidence/T02B20_DESIGN.md、执行单evidence/T02B20_D01_EXECUTION.md；冻结采集器tasks/benchmarks/b20_five_types_check.py引用既有五行category/group/field，无新字典/结构。Codex5类类型/证据检查、foundation/case两端实际smoke通过（2包/6空白目标/0意见），555保护文件/349Schema不变；证据artifacts/b20-d01/codex-design-verification.json。正式五类产包/分类查询/共同查询/准备/空白会话矩阵交DeepSeek，完成停executed_pending_review等Codex。

分工保持Codex方向/设计/小样/核验，DeepSeek固定重复运行/机械核对/证据；不并发修改，不让执行方自行补医学解释、改预期或重设计包。病例历史不等于病例标准化/诊次链，组成字段不等于方药剂量/安全处方；结构、软件运行、真实资料和医学确认分层，不扩称五类业务已完成。

原真实包artifacts/b7-real-compat/model-knowledge/bundle_a7c24a2ba66c6200241e87e0.medpkg，153943字节/SHA256 50742f7c32f7178c562ba2927ae070feac1e82696f7f86792157090fe2f7786d；7准备文件artifacts/b11-review-preparation/materials/preparation_718bf6c856acd871970f3eea/未变。188证据/63节点/478字段/27gap+1隔离，757目标/0真实意见，医学未审、禁发布训练；原PDF246页/34—38不重复。

生产代码/测试、349Schema/语义注册表/旧包与来源身份不改，549 passed/2环境skip、122发行资源旧基线保留，不重复全量/发行。医学金标准/病例确认/许可/真实跨源/容量SLO/跨平台和33项离线依赖材料仍缺，正式包v0/数据库/问诊/安全处方/产品接口/后训练未完成。无新外发/真实资料OCR/真实蒸馏/LLM/训练/安装，不读模型配置、不修改docs原件/log/pdfs；本次用户另行授权本地commit，未授权push。无需用户新文件或权限。

启动按STATE→CURRENT→HANDOFF→NEXT→ROADMAP→当前稳定设计/Schema，只CURRENT正式；旧执行单是冻结历史，不重复运行。
