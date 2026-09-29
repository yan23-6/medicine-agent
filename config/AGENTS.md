# LLM 配置目录规则

- `llm.local.toml` 是用户本地真实配置，只能由运行时读取。
- 不得读取、复述、显示、提交或复制 `llm.local.toml` 的内容。
- 可以只检查该文件是否存在，以及是否被 `.gitignore` 排除。
- 不得把 API 密钥、Authorization 请求头或完整请求写入日志、测试、知识包、运行记录或报告。
- 仓库只能提交不含真实密钥的 `llm.example.toml` 和配置说明。
- 默认在线命令读取 `config/llm.local.toml`；除非用户指定其他文件，不得创建第二套真实密钥配置。
