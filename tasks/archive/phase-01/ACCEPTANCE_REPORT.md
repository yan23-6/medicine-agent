# T01 阶段验收报告

> 验收日期：2026-09-29
> 结论：15 项全部通过，用户已确认，T01 完成
> 在线模型：OpenAI-compatible，`deepseek-flash`

## 1. 已交付产物

- `schemas/t01/`：公共模型和 6 个 Skill 的版本化 JSON Schema 及校验索引；
- Schema 导出命令与契约快照回归测试；
- 唯一 `RunRecord`、稳定输入输出身份、内存运行记录存储；
- `validate_package`、`query_package`、`trace_evidence`、`get_run` 中立 Facade；
- 有序原始字段输入、重复 key、同 key 异义、不同 key 同义和未映射字段保留；
- `raw_fields.jsonl`、`runs.jsonl` 与字段质量警告；
- 多段证据合并、查询和全部证据回溯；
- 结构化 CLI 错误输出；
- 15 项自动测试及人工构造测试夹具；
- wheel 和 sdist 构建与独立安装检查。

## 2. 验收结果

| 检查 | 结果 | 证据摘要 |
| --- | --- | --- |
| 当前环境测试 | 通过 | `15 passed` |
| 新隔离环境恢复 | 通过 | 按锁文件安装 18 个包后 `15 passed` |
| Schema 契约 | 通过 | 34 个 JSON 文件，重新导出与快照逐字节一致 |
| Skill 登记 | 通过 | 6 个 Skill 均有版本、状态、输入和输出 Schema |
| CLI | 通过 | 9 个命令可发现 |
| 字段保留 | 通过 | 7 条原始观察全部入包，重复出现序号为 1、2 |
| 字段质量语义 | 通过 | 歧义和未映射字段分别返回稳定警告 |
| 多段证据 | 通过 | 1 条知识引用并返回 3 条证据 |
| 幂等性 | 通过 | 两次运行得到同一 `package_id` |
| 运行身份 | 通过 | 相同输入具有相同内容身份、不同运行 ID |
| 包校验与 Trace | 通过 | 包有效，查询可回到三段原文及位置 |
| 损坏包阻断 | 通过 | 返回校验和错误、证据断裂和查询阻断 |
| 构建产物 | 通过 | wheel 与 sdist 均成功生成 |
| wheel 内容 | 通过 | 包含运行代码、`skill.toml` 和 `SKILL.md`，未发现本地密钥或缓存目录 |
| wheel 独立安装 | 通过 | 新环境可列出 Skill 并运行最小闭环 |
| 真实 LLM 冒烟 | 通过 | Schema 有效，`ok=True`，未输出密钥或请求头 |
| 真实模型流水线 | 通过 | 生成 1 条模型知识，实验包有效，可回溯 3 条证据 |

## 3. 关键命令

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m medicine_agent.cli export-schemas --output-dir schemas/t01
.venv\Scripts\python.exe -m medicine_agent.cli pipeline tests/fixtures/basic.md `
  --output-root artifacts/acceptance/t01/packages `
  --raw-fields-file tests/fixtures/ambiguous_fields.json `
  --combine-evidence
.venv\Scripts\python.exe -m medicine_agent.cli validate-package <package-path>
.venv\Scripts\python.exe -m medicine_agent.cli trace-evidence <package-path> <knowledge-id>
```

构建与隔离环境产物位于被 Git 忽略的 `artifacts/acceptance/t01/`，它们只用于验收，不是正式知识包。

## 4. 在线验收结果

用户配置、命令、通过条件和脱敏回报方式见 `ONLINE_ACCEPTANCE.md`。

执行 `llm-smoke` 后确认：

```text
provider = openai-compatible
model = deepseek-flash
schema_valid = true
response.ok = true
```

运行时只读取本地配置，没有输出密钥、Authorization 请求头或完整请求。

随后执行：

```powershell
uv run medicine-agent llm-smoke
uv run medicine-agent pipeline tests/fixtures/basic.md `
  --output-root artifacts/acceptance/t01/live-packages `
  --live-model `
  --combine-evidence
```

首次真实流水线调用因模型返回内容不符合 `GeneratedKnowledgePayload` 而得到 `OUTPUT_SCHEMA_INVALID`，流程在构建知识包前终止，没有留下被标记为可用的半成品。诊断调用和第二次完整流水线通过，得到：

- 包 ID：`pkg_9def3cee77fcafa1ddb434d3`；
- 1 个来源、3 个片段、3 条证据和 1 条模型知识；
- 包校验 `valid=true`，无质量问题；
- Query 和 Trace 均从知识返回全部 3 条原文证据；
- 生成方法标记为 `model`，审核状态保持 `unreviewed`。

首次失败证明外部模型输出存在非确定性。T01 已做到 Schema 不合格即阻断；自动修复和受控重试作为 T02 的明确需求，不把一次重跑成功解释为模型始终稳定。

本地配置文件仍被 Git 忽略且未被跟踪。生成包位于被 Git 忽略的 `artifacts/acceptance/t01/`，不属于正式知识包。

技术检查已经全部通过，用户已于 2026-09-29 确认继续推进，T01 标记为 `done`。

## 5. 能力边界

- 当前知识蒸馏仍是结构验证，不代表完整中医语义抽取；
- 当前实验包不是正式知识包 v0；
- 尚未实现 Agent、MCP、REST、Web、LadybugDB、PDF/DOCX/OCR 或正式蒸馏；
- 本次未修改 `docs` 原始资料，也未生成正式医学知识或训练数据。
