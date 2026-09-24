# T01 Skill 基础设施技术设计

> 状态：approved-for-implementation
> 适用范围：T01 可调用 Skill 基础与最小知识闭环
> 决策日期：2026-09-24

## 1. 设计结论

T01 建立平台原生、可独立运行的 Skill 软件层。核心能力不绑定 Codex、Cursor 或某一家模型服务；这些环境以后通过适配层调用同一套运行时。`SKILL.md` 只承担人类与智能体可读说明，不能代替 manifest、Schema、执行入口、实现和测试。

本阶段只实现同步、单进程、单材料的最小闭环。批处理、异步任务、断点恢复、数据库、MCP、REST 和 Agent 均延期，但当前接口不得阻止后续增加这些能力。

## 2. 开发环境与前置条件

任务开始时当前机器没有 Python、Python Launcher 或 `uv`。现已完成以下环境配置，并将其作为其他环境复现本项目的前置要求：

1. 安装 `uv`；
2. 由 `uv` 管理 CPython 3.13 和项目虚拟环境；
3. 在 `pyproject.toml` 声明受支持 Python 范围，并用 `.python-version` 固定本项目开发版本；
4. 生成并提交 `uv.lock`，保证依赖可复现；
5. 验证 `uv run`、测试命令和 CLI 能在干净环境运行。

T01 的开发基线选择 CPython 3.13，当前安装版本为 3.13.15，uv 为 0.12.18。它只锁定当前参考实现，不永久锁死整个平台；阶段 03 接入 LadybugDB 前重新验证兼容范围。其他机器仍须按锁文件自行恢复环境，不能假定用户级安装随仓库复制。

## 3. 工程结构

计划采用 `src` 布局：

```text
src/medicine_agent/
  domain/              # 来源、证据、知识、关系、质量等核心模型
  runtime/             # Skill 注册、发现、调用、校验和运行记录
  model_adapters/      # FakeModel 与 OpenAI-compatible 适配器
  skills/              # 六个最小 Skill 包
  packages/            # 实验知识包构建、读取、校验和查询
  cli/                 # list、describe、invoke、pipeline、validate、query
tests/
  fixtures/
  unit/
  contract/
  integration/
config/
  llm.example.toml
  llm.local.toml       # 本地密钥文件，不进入 Git
```

每个 Skill 包至少包含：

```text
skill-name/
  SKILL.md             # 简洁用途、边界和调用说明
  skill.toml           # 身份、版本、入口、Schema、权限和能力状态
  models.py            # 输入输出 Pydantic 模型
  handler.py           # 可执行入口
  errors.py            # Skill 特有错误映射（确有需要时）
```

公共语义只定义一次。Skill 不复制来源、证据、调用信封或错误的公共模型。

## 4. 数据契约

采用 Pydantic 2 系列作为 Python 内部模型和运行时校验层，并导出标准 JSON Schema 作为语言无关契约。Pydantic 模型是实现源，导出的 Schema 必须进入契约测试，防止未声明变化。

T01 至少定义：

- `SourceDocument`、`DocumentFragment`；
- `EvidenceRecord`；
- `RawFieldObservation`、`FieldMappingCandidate`；
- `KnowledgeCandidate`、`RelationCandidate`；
- `SkillManifest`、`SkillInvocation`、`SkillResult`；
- `RunRecord`、`QualityReport`、`ValidationIssue`；
- `ExperimentalPackageManifest`。

字段缺失使用 JSON `null`，不使用空字符串冒充缺失。Schema 要求来源信息键存在，但允许其值为 `null`；未知值不能由模型猜测补齐。

## 5. 原始字段与语义歧义

任何输入字段先进入 `RawFieldObservation`，至少保存：

- 原始 key、原始 value 和出现序号；
- 所在文件、片段、路径或位置；
- 上下文和作用域；
- 原始数据类型；
- 规范字段候选及每个候选的依据；
- 映射状态：`mapped`、`ambiguous`、`unmapped` 或 `rejected`；
- 使用的映射规则与版本；
- 人工审核状态。

处理规则：

1. 不同 key 表示同一语义时，可以映射到同一规范字段，但所有原始 key/value 仍保留；
2. 同一 key 在不同位置表达不同语义时，按上下文、路径、资料类型和出现位置分别建记录，禁止按 key 名直接合并；
3. 同一 key 重复出现且值不同，保留每次出现，不采用后值覆盖前值；
4. 无法确认语义的字段进入 `ambiguous` 或 `unmapped`，继续随实验包交付并进入质量报告；
5. 未识别数据不得静默删除、塞入错误的规范字段或由 LLM 自行选择唯一解释。

项目级统一知识包协议说明书负责定义规范字段字典、语义、允许作用域、映射状态和规则版本。单个知识包只声明它采用的协议与映射规则版本，不能重新定义同名规范字段。

## 6. Skill 注册和调用

注册表读取受信任的内置 Skill manifest，校验身份、语义版本、入口和 Schema。T01 不从知识包或任意外部路径加载可执行代码。

首版接口支持：

- `list_skills()`：列出身份、版本、状态和 Schema；
- `describe_skill(skill_id, version)`：读取 manifest 和契约；
- `invoke(request)`：校验输入、调用实现、校验输出并生成运行记录；
- 明确的能力不存在、版本不兼容和依赖不可用错误。

统一结果信封至少包含调用身份、Skill 身份、状态、输出、问题列表、证据引用、生成方式、审核状态、模型/规则/工具版本、开始结束时间和可复现信息。业务失败作为结构化结果返回；进程级故障才作为未处理异常进入顶层保护。

## 7. LLM 适配

T01 同时实现：

1. `ModelClient` 抽象接口；
2. 确定性的 `FakeModelClient`，供全部自动测试使用；
3. `OpenAICompatibleModelClient`，从本地配置读取 `base_url`、`api_key`、`model`、超时和重试次数；
4. 显式在线冒烟测试，不纳入默认离线测试。

真实配置写入 `config/llm.local.toml`，该文件被 Git 忽略。环境变量 `MEDICINE_AGENT_LLM_API_KEY` 优先于文件密钥。日志、异常、运行记录和测试输出必须脱敏；模型响应先通过 Schema 校验，再成为候选对象。

模型适配层只负责请求、响应、重试和调用元数据，不承担医学事实发布。业务 Skill 不直接依赖供应商 SDK。

## 8. 证据与多段整理

允许将同一明确处理范围内的多段内容整理为一条知识候选，但必须：

- 使用 `evidence_refs` 引用全部依据；
- 在断言级标明每项内容对应的证据；
- 记录整理范围和生成方式；
- 不用常识补出原文没有的连接关系；
- 跨范围组合或语义连接不明确时标为待复核候选。

原始文本、OCR/转录值、纠正候选和确认状态分离。`raw_text` 不可覆盖；只有确认后的 `corrected_text` 可以作为默认可读展示，且查询必须能同时返回原值。

## 9. 稳定身份与幂等

来源文件使用内容摘要和显式来源身份生成稳定 ID；片段和证据 ID 由来源 ID、结构路径、位置和规范化输入共同派生；知识与关系候选由类型、规范内容、作用域和证据集合派生。

所有参与哈希的数据先进行确定性 JSON 规范化。时间戳、运行 ID、模型随机输出和本地绝对路径不得进入内容身份。重复执行可以产生新的运行记录，但不得产生不同的内容身份或无控制重复对象。

## 10. 实验知识包

T01 使用可读的目录型实验包，建议包含：

```text
manifest.json
sources.jsonl
fragments.jsonl
evidence.jsonl
raw_fields.jsonl
knowledge.jsonl
relations.jsonl
runs.jsonl
quality/report.json
checksums.json
```

这是验证 Build、Validate、Query、Trace 和 Round-trip 的实验格式，不是阶段 03 的正式知识包 v0。构建采用临时目录，全部校验通过后再原子切换为可用状态；失败产物只能保留为诊断结果，不能标记为可用包。

## 11. CLI 与测试

CLI 首版使用标准项目入口，至少支持：

- 列出和查看 Skill；
- 调用单个 Skill；
- 运行最小端到端闭环；
- 校验实验包；
- 按稳定 ID 查询并回溯证据；
- 显式运行真实 LLM 冒烟测试。

测试采用 `pytest`，覆盖单元、Schema 契约、错误语义、幂等、往返和端到端闭环。默认测试不得访问网络。测试材料使用人工构造、无隐私且许可清晰的 Markdown/TXT，其中必须包含空来源字段、重复 key、同 key 异义、未映射字段、多段证据、否定和不支持格式。

## 12. 主要错误语义

T01 至少稳定区分：

- `SKILL_NOT_FOUND`；
- `SKILL_VERSION_UNSUPPORTED`；
- `DEPENDENCY_UNAVAILABLE`；
- `INPUT_SCHEMA_INVALID`；
- `OUTPUT_SCHEMA_INVALID`；
- `UNSUPPORTED_FORMAT`；
- `MODEL_CONFIG_MISSING`；
- `MODEL_CALL_FAILED`；
- `AMBIGUOUS_FIELD_MAPPING`；
- `UNMAPPED_FIELD_PRESERVED`；
- `PACKAGE_VALIDATION_FAILED`；
- `EVIDENCE_TRACE_BROKEN`；
- `INTERNAL_ERROR`。

错误码区分失败和警告。例如未映射字段必须保留并产生警告，不应导致整份材料丢失；证据引用断裂则必须阻止实验包成为可用状态。

## 13. 实施顺序

1. 配置开发环境和项目骨架；
2. 建立公共模型、JSON Schema 导出和错误语义；
3. 实现 Skill manifest、注册表和 Runner；
4. 实现 FakeModel 与真实模型适配器；
5. 实现材料、证据和最小知识 Skill；
6. 实现实验包构建校验、查询和质量 Skill；
7. 完成 CLI、测试夹具和端到端验收；
8. 用本地真实配置执行一次显式 LLM 冒烟测试；
9. 记录验收结果后进入 T02 评审。

本顺序不改变 T01 是一个完整任务，不将内部步骤提升为互相独立的阶段任务。

Codex、MCP 与未来插件的适配边界见 [ADAPTER_DESIGN.md](ADAPTER_DESIGN.md)。T01 只实现其依赖的中立 Facade 和 DTO，不实现传输层。


