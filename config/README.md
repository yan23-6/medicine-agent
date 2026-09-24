# 本地 LLM 配置

T01 将通过统一模型适配接口调用真实 LLM。开发者和本地运行者在
`config/llm.local.toml` 中填写自己的 OpenAI-compatible API 信息。

该文件已被 `.gitignore` 排除，禁止提交、复制到日志、测试快照、知识包或错误报告中。仓库只提交不含密钥的 `llm.example.toml`。

使用方法：

1. 打开 `config/llm.local.toml`；
2. 填写 `base_url`、`api_key` 和 `model`；
3. 保留 `provider = "openai-compatible"`；
4. 实现完成后，通过专门的显式在线冒烟测试验证连接。

运行时只记录提供商类型、基础地址的安全标识、模型名称和非敏感参数，不记录 API 密钥或完整请求头。自动测试默认使用确定性 FakeModel，不依赖真实密钥或网络。

如部署环境不允许在文件中保存密钥，运行时还必须支持用环境变量覆盖 `api_key`；具体环境变量名称固定为 `MEDICINE_AGENT_LLM_API_KEY`。

