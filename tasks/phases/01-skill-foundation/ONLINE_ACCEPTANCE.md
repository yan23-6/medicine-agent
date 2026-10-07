# T01 真实 LLM 在线验收指引

> 状态：done
> 安全要求：API 密钥只写入被 Git 忽略的本地配置或环境变量，不发送到聊天，不写入日志和报告

## 1. 准备配置

从 `config/llm.example.toml` 复制出 `config/llm.local.toml`，填写：

```toml
[llm]
provider = "openai-compatible"
base_url = "https://你的服务地址/v1"
api_key = "你的本地密钥"
model = "服务商要求的准确模型名"
timeout_seconds = 60
max_retries = 2
```

`base_url` 应是 API 根地址，运行时会继续拼接 `/chat/completions`。如果服务商给出的地址已经包含该路径，需要改成它的上一级根地址。

也可以不把真实密钥写入文件：文件中保留非空占位值，在当前 PowerShell 会话中设置 `MEDICINE_AGENT_LLM_API_KEY`，运行时会用环境变量覆盖文件值。

## 2. 验收前检查

```powershell
git check-ignore config/llm.local.toml
uv run medicine-agent llm-smoke
```

第一条必须输出 `config/llm.local.toml`，证明密钥文件被 Git 忽略。

第二条成功时应满足：

- 进程退出码为 0；
- 输出 `schema_valid: true`；
- 输出 `response.ok: true`；
- 不出现 API 密钥、Authorization 请求头或完整请求内容。

当前实现只校验 `ok` 是布尔值，因此验收时必须人工确认它确实为 `true`；后续应把契约收紧为只能接受 `true`。

## 3. 运行真实模型最小闭环

```powershell
uv run medicine-agent pipeline tests/fixtures/basic.md `
  --output-root artifacts/acceptance/t01/live-packages `
  --live-model `
  --combine-evidence
```

检查输出：

- 状态为成功；
- 模型输出通过 Pydantic/Schema 校验；
- 返回 package 路径和知识对象；
- 没有密钥或请求头；
- 产物只位于被忽略的 `artifacts/acceptance/t01/`。

随后对命令返回的具体包目录执行：

```powershell
uv run medicine-agent validate-package <package-path>
uv run medicine-agent query-package <package-path>
```

校验必须有效，查询必须能返回知识和来源证据。

## 4. 用户验收结论

用户只需要把以下非敏感信息告知执行者：

- `llm-smoke` 是否退出成功；
- `schema_valid` 和 `response.ok` 是否均为 `true`；
- pipeline 是否成功；
- validate 是否有效；
- query 是否能回溯证据；
- 使用的提供商类型和模型名称；
- 若失败，只提供错误码和脱敏后的错误消息。

不得发送 `config/llm.local.toml` 内容、API 密钥或完整请求头。

以上全部通过后，才能更新 `ACCEPTANCE_REPORT.md`、`tasks/STATE.md` 和阶段状态，并由用户确认 T01 完成。
