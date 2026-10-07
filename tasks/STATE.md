# 项目执行状态

> 状态更新时间：2026-09-29
> 当前阶段：02 中医知识与病例蒸馏
> 当前任务：T02-A 病例与病机推理契约及离线闭环
> 当前任务状态：review
> 下一任务草案：T02-B 教材证据与人工金标准闭环；资料可用后重新评审

## 1. 已存在

- 中西医平台需求与技术设计文档；
- 通用医学主干、中医与西医分支设计；
- Agent、Skill、知识包和病例数据模型的逻辑边界；
- LadybugDB、MCP、REST API、医疗安全和后训练方向；
- 导师参考材料；
- 项目任务系统和阶段需求草案。
- T01 技术设计与 Codex/MCP 适配契约；
- uv 管理的 CPython 3.13 开发环境、`pyproject.toml` 与依赖锁文件；
- 第一版 Skill Registry、Runner、中立 Facade、统一 DTO 和错误信封；
- 六个 T01 通用实验 Skill、FakeModel、OpenAI-compatible 模型适配器和 CLI；
- 可生成、校验、查询并回溯证据的目录型实验包；
- 第一批单元、契约和端到端测试。
- 版本化 JSON Schema 快照、契约导出命令和回归测试；
- 唯一运行记录、稳定内容身份、运行记录存储和完整中立 Facade；
- 字段歧义保留、多段证据查询回溯和对应质量警告；
- 2026-09-29 T01 当前环境与新隔离环境自动测试均为 `15 passed`，CLI 可列出 9 个命令；
- wheel/sdist 构建、内容检查、wheel 独立安装和闭环验收；
- T01 验收计划与当前差距矩阵。
- 真实 OpenAI-compatible LLM 连接、Schema 冒烟和真实模型最小流水线验收；
- 真实模型生成的实验包通过 Validate、Query 和 Trace，1 条知识可回溯 3 条证据。
- T02-A 的 RawCase、CanonicalCase、Encounter、不确定项、安全上下文和中医推理图契约；
- 可注册调用的 `case-distillation` 与 `tcm-reasoning` 两个确定性基线 Skill；
- 一份去标识胸痹病例夹具、T02 Schema 快照和边界回归测试；
- 当前 Skill 注册表共 8 个 Skill，完整离线回归为 `29 passed`，wheel/sdist 构建通过；
- T02 病例契约通用性审计与第一轮整改完成，契约升级为 `0.4.0`，两个 T02 Skill 升级为 `0.3.0`，不再只支持单来源文本型胸痹样例；
- 建立 `src/medicine_agent/semantics/registry.json` 作为唯一机器可读语义源：67 个字段、10 类关系、15 个权威来源、5 个 Profile 和 43 条实际 Schema 字段绑定；通用、中医、西医、安全、方剂字段已分流，Skill 调用会校验语义版本与启用 Profile。

## 2. 尚不存在

- 完整或可发布的核心平台；
- 已实现的 Agent；
- 完整中医、西医、方剂或安全 Skill，以及经过医学复核的病例推理 Skill；
- 冻结的正式知识包 v0 Schema；
- LadybugDB 导入与查询实现；
- 正式金标准、正式知识包和自动蒸馏结果；
- Web、MCP 或 REST 服务；
- 医学评测基线和后训练资产；
- PDF、DOCX、OCR、批处理、断点恢复和正式发布服务。

## 3. 当前禁止假定

- 不得假定 `SKILL.md` 即等于可调用 Skill；
- 不得假定连接 LLM 后自动具备医学抽取、病例标准化或知识包能力；
- 不得要求使用尚未实现的 Skill 蒸馏材料；
- 不得开始批量或正式知识包蒸馏；
- 不得把设计文档中的 Agent 角色写成已运行组件；
- 不得直接把导师资料改写成正式知识或训练数据。

## 4. 当前进入条件

T01 的实现、离线测试、隔离环境、构建验收和真实 LLM 在线验收均已完成，用户已于 2026-09-29 确认继续。T01 标记为 `done`。

T02 采用分段推进。T02-A 已完成实现、通用性与语义契约整改及自动检查，当前进入用户评审；详见 `tasks/phases/02-tcm-distillation/T02A_ACCEPTANCE.md`、`GENERALITY_AUDIT.md` 和 `SEMANTIC_CONTRACT_ACCEPTANCE.md`。缺少《中医诊断学》《中医内科学》等固定版本资料时，不定稿医学金标准，不开始整书或批量蒸馏。

## 5. 状态更新规则

T02-A 当前保持 `review`，只有用户确认后才标记 `done`。T02-B 只有在补充资料可用或 T02-A 暴露的缺口明确后重新评审，不自动扩张范围。

