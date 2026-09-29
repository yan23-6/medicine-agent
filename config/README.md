# 本地 LLM 配置

## 唯一配置入口

真实 LLM 统一使用：

```text
config/llm.local.toml
```

程序的 `llm-smoke` 和带 `--live-model` 的流水线默认读取该文件，不需要再传配置路径。当前只要求 OpenAI-compatible 文本模型能够调用 `/chat/completions` 并返回 JSON，不要求视觉能力。

## 安全边界

- `config/llm.local.toml` 已被 `.gitignore` 排除，不能提交到 Git；
- AI 和自动化程序不得读取、复述或打印该文件内容；
- 密钥不得进入日志、测试快照、知识包、运行记录、周报或错误报告；
- 仓库只提交不含真实密钥的 `config/llm.example.toml`；
- 可以检查本地文件是否存在、是否被忽略，但不能把内容作为验收证据。

可运行以下命令确认忽略规则：

```powershell
git check-ignore config/llm.local.toml
```

命令应输出 `config/llm.local.toml`。

## 本地填写方法

如果本地文件不存在，先复制模板：

```powershell
Copy-Item config/llm.example.toml config/llm.local.toml
```

然后只在本机编辑 `config/llm.local.toml`：

```toml
[llm]
provider = "openai-compatible"
base_url = "https://你的服务商地址/v1"
api_key = "你的真实密钥"
model = "服务商要求的准确模型名"
timeout_seconds = 60
max_retries = 2
```

`base_url` 填 API 根地址。运行时会自动拼接 `/chat/completions`，因此不要把该路径重复写入 `base_url`。

如果不希望密钥写入文件，可以在文件的 `api_key` 中保留非空占位值，并在当前 PowerShell 会话设置：

```powershell
$env:MEDICINE_AGENT_LLM_API_KEY = "你的真实密钥"
```

运行时会优先使用环境变量，且不会把密钥写回文件。

## 配置后直接调用

连接检查：

```powershell
uv run medicine-agent llm-smoke
```

真实模型最小闭环：

```powershell
uv run medicine-agent pipeline tests/fixtures/basic.md `
  --output-root artifacts/acceptance/t01/live-packages `
  --live-model `
  --combine-evidence
```

两个命令都默认读取 `config/llm.local.toml`。只有使用其他配置文件时才需要显式增加 `--config <path>`。

自动测试默认使用 FakeModel，不读取本地密钥，也不访问网络。完整 T01 验收要求见 `tasks/phases/01-skill-foundation/ONLINE_ACCEPTANCE.md`。

