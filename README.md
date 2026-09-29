# 中西医知识蒸馏与智能体平台

本项目建设一个“通用医学主干 + 中医专业分支 + 西医专业分支”的知识蒸馏与智能体平台。平台通过可调用 Skill，把教材、论文、医家经验和病例转化为有来源、可校验、可查询、可追溯的知识包；后续再由 Agent 负责任务协作与决策。

当前处于阶段 02 的 T02-A 评审点。仓库已有第一版可运行骨架、六个通用实验 Skill，以及两个中医病例契约基线 Skill；尚未进入正式医学知识蒸馏或多 Agent 阶段。

## 当前运行环境

| 项目 | 当前基线 |
| --- | --- |
| 操作系统 | Windows x64 |
| Python | CPython 3.13.15 |
| 环境与包管理 | uv 0.12.18 |
| Python 版本范围 | `>=3.13,<3.14` |
| 数据模型与校验 | Pydantic 2.13.5 + JSON Schema |
| HTTP/LLM 调用 | httpx 0.28.1 |
| 自动测试 | pytest 9.1.1 |
| 构建后端 | uv_build |
| 默认模型 | 确定性 FakeModel，无需 API 或网络 |
| 真实模型 | OpenAI-compatible API，可选本地配置 |
| 数据库 | 当前阶段未接入；后续默认方向为 LadybugDB |

精确依赖版本以 [uv.lock](uv.lock) 为准。默认开发与测试不需要 Docker、外部数据库或真实 LLM。

## 快速开始

安装 `uv` 后，在项目根目录执行：

```powershell
uv sync
uv run pytest
uv run medicine-agent list-skills
uv run medicine-agent export-schemas --output-dir schemas/t01
uv run medicine-agent export-schemas --contract-set t02 --output-dir schemas/t02
uv run medicine-agent validate-semantics
uv run medicine-agent pipeline tests/fixtures/basic.md --output-root artifacts/packages
```

如果当前 Windows 终端尚未刷新用户 PATH：

```powershell
$uv = "$env:USERPROFILE\.local\bin\uv.exe"
& $uv sync
& $uv run pytest
```

完整命令与配置说明见 [DEVELOPMENT.md](DEVELOPMENT.md)。

## 当前已经实现

- Skill manifest、注册表、版本选择和统一调用入口；
- Pydantic 输入输出模型、版本化 JSON Schema 快照及契约回归测试；
- 统一成功、失败、警告和错误结果信封；
- 每次调用唯一的 RunRecord、稳定输入输出身份和内存运行记录查询；
- `validate_package`、`query_package`、`trace_evidence` 和 `get_run` 中立 Facade；
- `MaterialIngestionSkill`；
- `EvidenceGroundingSkill`；
- 最小版 `KnowledgeDistillationSkill`；
- 最小版 `KnowledgePackageBuildValidateSkill`；
- 最小版 `KnowledgePackageQuerySkill`；
- 最小版 `QualityEvaluationSkill`；
- T02-A 确定性 `CaseDistillationSkill` 与 `TCMReasoningSkill` 基线；
- 唯一机器可读语义注册表，集中维护通用、中医、西医、安全和方剂 Profile、权威来源及 Schema 字段绑定；
- RawCase、CanonicalCase、Encounter、转录不确定项、安全上下文和中医候选推理图契约；
- 去标识胸痹病例测试夹具，并隔离历史诊断、历史行动和现代建议；
- FakeModel 和 OpenAI-compatible 模型适配器；
- 重复 key、同 key 异义、不同 key 同义和未映射字段的原值保留与质量警告；
- 多段证据合并后返回全部证据的查询与回溯；
- Markdown/TXT 测试材料到实验知识包，再到查询和证据回溯的闭环；
- 10 个 CLI 命令、8 个已登记 Skill、29 项自动测试、wheel/sdist 构建和幂等验证。

以上仍是协议与边界基线，不代表完整医学推理能力、医学金标准或正式知识包已经完成。

## 真实 LLM 配置

真实 LLM 只有一个本地配置入口：`config/llm.local.toml`。该文件已被 Git 忽略，配置方法和安全规则见 [config/README.md](config/README.md)。当前只需要支持 JSON 输出的 OpenAI-compatible 文本模型，不要求视觉能力。

在本地文件中填写：

```toml
[llm]
provider = "openai-compatible"
base_url = ""
api_key = ""
model = ""
timeout_seconds = 60
max_retries = 2
```

不要提交或发送真实密钥。配置后显式运行：

```powershell
uv run medicine-agent llm-smoke
uv run medicine-agent pipeline tests/fixtures/basic.md --output-root artifacts/packages --live-model
```

2026-09-29 已完成真实 LLM 冒烟和最小流水线验收，实验包通过校验、查询和证据回溯，T01 已确认完成。

## 当前不包含

- 正式教材或医案批量蒸馏；
- 完整中医、西医、方剂和安全 Skill，以及经过医学复核的病例推理 Skill；
- Agent 与多 Agent 编排；
- MCP、REST API 和 Web；
- LadybugDB 导入与联合查询；
- PDF、DOCX、OCR、批处理和断点恢复；
- 正式知识包 v0、金标准和后训练。

## 文档入口

- [稳定设计总览](md/README.md)
- [统一医学语义说明书](src/medicine_agent/semantics/README.md)
- [当前真实状态](tasks/STATE.md)
- [项目任务规则](tasks/README.md)
- [项目终极需求](tasks/overall/终极需求.md)
- [当前正式任务](tasks/phases/02-tcm-distillation/CURRENT_TASK.md)
- [T02-A 验收报告](tasks/phases/02-tcm-distillation/T02A_ACCEPTANCE.md)
- [T02 数据契约通用性审计](tasks/phases/02-tcm-distillation/GENERALITY_AUDIT.md)
- [统一语义契约验收](tasks/phases/02-tcm-distillation/SEMANTIC_CONTRACT_ACCEPTANCE.md)
- [后续 Skill 能力设计](tasks/phases/02-tcm-distillation/FUTURE_SKILL_DESIGN.md)
- [T01 验收矩阵](tasks/phases/01-skill-foundation/ACCEPTANCE_PLAN.md)
- [T01 技术设计](tasks/phases/01-skill-foundation/TECHNICAL_DESIGN.md)
- [Codex 与 MCP 适配设计](tasks/phases/01-skill-foundation/ADAPTER_DESIGN.md)

当用户询问“下一步做什么”时，应先读取 `AGENTS.md` 和 `tasks/STATE.md`，只执行当前阶段的正式任务。

`docs` 保存导师原始资料，默认只读；`log` 只有在用户明确要求时才更新。
