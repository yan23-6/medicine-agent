# 开发与运行

## 环境

- uv 0.12.18 或兼容版本；
- uv 管理的 CPython 3.13.15；
- 项目依赖以 `uv.lock` 为准；
- 不需要 Docker、外部数据库或真实 LLM 才能运行默认测试。

请先确认当前解释器满足 `pyproject.toml` 的 Python 版本要求；系统默认 `python` 不一定等于项目环境。
若终端PATH中没有uv，可显式使用已经受控安装的uv路径，例如本工作区的工具：

```powershell
$uv = ".tools/bin/uv.exe"
& $uv sync
& $uv run pytest
```

其他机器安装 uv 后可直接使用 `uv sync` 和 `uv run`。不得依赖当前机器的绝对 Python 路径。

本地环境诊断可直接运行 `.venv/Scripts/python.exe -m medicine_agent.preflight`；
缺少医学依赖时仍能启动。`medicine-agent-preflight`、`medicine-agent-wheelhouse`
和`medicine-agent-ocr-resources`三个console入口在安装当前wheel后提供；旧editable元数据可能需要重新受控安装才能更新入口。
预检/离线wheel集合/OCR资源是三种独立检查，详见[文件分析说明](src/medicine_agent/analysis/README.md)。
版本快照不是哈希锁，复制已安装依赖不是空缓存离线解析，资源检查不自动下载。

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

- 文件入口支持 PDF、DOCX、UTF-8 Markdown/TXT、PNG/JPEG 及本地 OCR；其他格式尚未支持；
- 当前已有结构化中医候选分析及复核/更正软件首版，不代表医学正确性或完整问诊验收；
- T02-A 病例与中医推理输出均为 `unreviewed`、`research_candidate_only`，不能用于临床决策；
- 实验知识包不是正式知识包 v0；
- 受控总智能体/数据分析 Agent、断点续跑和包目录查询已有首版；MCP/REST 服务、LadybugDB、正式医学蒸馏与完整问诊尚未实现。


产品入口使用 `analyze submit <新资料> --base-package <包1.medpkg> --base-package <包2.medpkg> --allowed-use <用途>`；owner-id 可选，仅记录贡献。最终单文件放固定用户目录，操作命令见 [数据分析说明](src/medicine_agent/analysis/README.md)。目录 API 仅内部兼容；精确缓存与新资料学习分开。当前能力和验收边界见 [tasks/STATE.md](tasks/STATE.md)。

新资料处理前用 `analyze coverage --packages <包目录> --workspace <独立缓存>` 只读盘点；加 `--input-file <CoverageRequest.json>` 生成最早缺失阶段计划。契约为 `schemas/coverage/`，源码为 `domain/coverage.py`；用 `export-schemas --contract-set coverage --output-dir schemas/coverage` 重建，`python -m pytest tests/test_coverage.py` 验证。它不是新Agent/Skill，不调用模型或自动派发；旧包可选字段缺失保留待核而非要求重蒸馏。

复核准备使用 `analyze review-prepare --packages <包目录> --workspace <独立缓存> --output-dir <新目录>`；契约为review-preparation/0.1.0，独立导出全部原文、候选、异常、空白模板和质量门。用 `python -m pytest tests/test_review_preparation.py tests/test_reviews.py` 检查。完整数据含原文，只放本地运行产物，不提交；准备完成不等于专家确认或可发布。
