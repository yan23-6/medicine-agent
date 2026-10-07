# 开发与运行

## 环境

- uv 0.12.18 或兼容版本；
- uv 管理的 CPython 3.13.15；
- 项目依赖以 `uv.lock` 为准；
- 不需要 Docker、外部数据库或真实 LLM 才能运行默认测试。

uv 已加入当前 Windows 用户 PATH；新终端可以直接使用。若当前终端尚未刷新 PATH，可临时使用：

```powershell
$uv = "$env:USERPROFILE\.local\bin\uv.exe"
& $uv sync
& $uv run pytest
```

其他机器安装 uv 后可直接使用 `uv sync` 和 `uv run`。不得依赖当前机器的绝对 Python 路径。

## 常用命令

```powershell
uv run medicine-agent list-skills
uv run medicine-agent describe-skill material-ingestion
uv run medicine-agent export-schemas --output-dir schemas/t01
uv run medicine-agent export-schemas --contract-set t02 --output-dir schemas/t02
uv run medicine-agent validate-semantics
uv run medicine-agent pipeline tests/fixtures/basic.md --output-root artifacts/packages
uv run medicine-agent validate-package <package-path>
uv run medicine-agent query-package <package-path> --text 发热
uv run medicine-agent trace-evidence <package-path> <knowledge-id>
```

默认闭环使用确定性 FakeModel。实验产物写入被 Git 忽略的 `artifacts/`。

字段歧义和多段证据验收可以执行：

```powershell
uv run medicine-agent pipeline tests/fixtures/basic.md `
  --output-root artifacts/packages `
  --raw-fields-file tests/fixtures/ambiguous_fields.json `
  --combine-evidence
```

`--raw-fields-file` 必须是有序 JSON 数组，不能使用会提前覆盖重复 key 的普通 JSON 对象。T01 与 T02-A 的版本化契约分别位于 `schemas/t01/` 和 `schemas/t02/`；重新导出后必须运行测试，确认变更是显式且可审核的。

医学字段、关系、值类型、术语体系元数据和专业分流只在 `src/medicine_agent/semantics/registry.json` 维护。`registry.py` 负责结构与引用校验，`schemas/t02/common/SemanticRegistry.schema.json` 是导出快照，不是第二个编辑源。新增或修改物理 Schema 字段时，应在同一注册表的 `schema_bindings` 中建立绑定，并执行语义校验和完整测试。

每次 Skill 调用产生唯一运行身份和稳定输入/输出身份。进程内可通过 Facade 的 `get_run` 查询；进入实验知识包的前序运行记录保存在 `runs.jsonl`，不得包含密钥或完整请求头。

## 真实 LLM

在 `config/llm.local.toml` 中填写 `base_url`、`api_key` 和 `model`，不要提交该文件，也不要把密钥发到聊天、日志或测试快照中。

配置后显式测试：

```powershell
uv run medicine-agent llm-smoke
uv run medicine-agent pipeline tests/fixtures/basic.md --output-root artifacts/packages --live-model
```

环境变量 `MEDICINE_AGENT_LLM_API_KEY` 可以覆盖配置文件中的密钥。

配置不完整时，CLI 返回结构化 `MODEL_CONFIG_MISSING`，不会发出网络请求。真实模型响应必须先通过调用方 Pydantic Schema 校验，才能成为知识候选。

## 当前能力边界

- 仅支持 UTF-8 Markdown/TXT；
- 当前知识蒸馏只验证协议和证据闭环，不代表完整医学抽取；
- T02-A 病例与中医推理输出均为 `unreviewed`、`research_candidate_only`，不能用于临床决策；
- 实验知识包不是正式知识包 v0；
- 尚未实现 Agent、MCP、REST、LadybugDB、PDF/DOCX/OCR 或正式蒸馏。

