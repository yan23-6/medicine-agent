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
uv run medicine-agent pipeline tests/fixtures/basic.md --output-root artifacts/packages
uv run medicine-agent validate-package <package-path>
uv run medicine-agent query-package <package-path> --text 发热
```

默认闭环使用确定性 FakeModel。实验产物写入被 Git 忽略的 `artifacts/`。

## 真实 LLM

在 `config/llm.local.toml` 中填写 `base_url`、`api_key` 和 `model`，不要提交该文件，也不要把密钥发到聊天、日志或测试快照中。

配置后显式测试：

```powershell
uv run medicine-agent llm-smoke
uv run medicine-agent pipeline tests/fixtures/basic.md --output-root artifacts/packages --live-model
```

环境变量 `MEDICINE_AGENT_LLM_API_KEY` 可以覆盖配置文件中的密钥。

## 当前能力边界

- 仅支持 UTF-8 Markdown/TXT；
- 当前知识蒸馏只验证协议和证据闭环，不代表完整医学抽取；
- 实验知识包不是正式知识包 v0；
- 尚未实现 Agent、MCP、REST、LadybugDB、PDF/DOCX/OCR 或正式蒸馏。

