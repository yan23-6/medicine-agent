# Codex 与 MCP 适配层契约设计

> 状态：design-baseline
> 当前范围：约束 T01 公共接口，不在 T01 实现 MCP 服务或 Codex 插件

## 1. 定位

核心平台、MCP 和 Codex Skill 分层：

```text
Codex Skill / 其他智能体工作流
  → MCP、REST 或进程内适配器
  → Application Facade
  → Skill Registry 与 Skill Runner
  → 知识包查询、证据追溯和质量服务
```

- 核心平台保存真实能力与业务规则；
- MCP 暴露结构化工具、鉴权、权限和受控操作；
- Codex Skill 说明何时调用哪些工具、如何处理失败以及如何组织结果；
- Codex Skill 不复制医学逻辑，不直接读取数据库，不绕开安全门；
- 平台不能依赖 Codex 才能运行。

## 2. T01 必须预留的中立接口

T01 的 CLI、未来 MCP 和未来 REST 共用以下应用服务，不各自实现业务逻辑：

- `list_skills`：列出身份、版本、状态和输入输出 Schema；
- `describe_skill`：读取单个 Skill 的 manifest 与契约；
- `invoke_skill`：提交统一调用请求并返回统一结果信封；
- `validate_package`：验证实验包或正式包；
- `query_package`：按稳定身份或查询条件读取对象；
- `trace_evidence`：从知识或关系回到证据与来源；
- `get_run`：读取调用状态、问题和版本信息。

T01 可以只实现进程内 Facade 和 CLI，但输入输出必须是可序列化、可生成 JSON Schema 的 DTO。

## 3. MCP 工具映射原则

未来 MCP 工具采用面向用户目标的窄工具，不使用一个带大量 mode 的万能工具。初始候选映射为：

| MCP 工具 | 核心接口 | 当前安全性质 |
| --- | --- | --- |
| `list_skills` | `list_skills` | 只读 |
| `describe_skill` | `describe_skill` | 只读 |
| `invoke_skill` | `invoke_skill` | 取决于目标 Skill，必须动态检查权限 |
| `validate_knowledge_package` | `validate_package` | 只读 |
| `query_knowledge_package` | `query_package` | 只读 |
| `trace_knowledge_evidence` | `trace_evidence` | 只读 |
| `get_skill_run` | `get_run` | 只读且受调用者权限限制 |

工具必须声明输入 Schema、输出 Schema、稳定标识、错误语义和准确的只读/破坏性/开放世界注解。MCP 返回中的 `structuredContent` 对应平台 DTO；文本内容只用于简要说明，不能成为唯一结果。密钥、访问令牌和不必要的患者数据不得进入工具结果。

## 4. Codex Skill 设计

Codex Skill 是适配工作流，不是平台中的医学 Skill 实现。首个适配 Skill 预计围绕“构建并验证知识包”这一完整用户目标，说明：

1. 先查询能力与版本；
2. 调用材料、证据、蒸馏和包构建能力；
3. 检查结构化警告与错误；
4. 执行查询和证据回溯；
5. 未实现能力返回缺失，不由 Codex 自由补写；
6. 只有用户明确要求时才执行发布或其他写操作。

`SKILL.md` 保持简洁；详细 Schema 由 MCP 工具和平台协议提供，不复制到指令正文。Codex 激活描述围绕用户目标编写，不使用“处理所有医学任务”一类过宽描述。

## 5. 插件封装方向

未来优先使用可移植插件布局：

```text
medicine-agent-plugin/
  plugin.json
  mcp.json
  skills/
    build-medical-knowledge-package/
      SKILL.md
```

必要时增加 OpenAI 专用扩展或 `.codex-plugin/plugin.json` 兼容层，但它们不能改变核心接口。MCP 动态提供 Skill 当前只作为可选发布方式，不成为运行必需条件；适配 Skill 应随插件版本形成可审核快照。

## 6. 版本与错误透传

- 适配器版本、MCP 工具版本、平台版本、Skill 版本和知识包协议版本分别记录；
- MCP 与 Codex 不把 `证据不足` 改写为否定，也不把 `待复核` 改写为成功；
- 核心错误码原样进入结构化结果，适配层只增加传输或鉴权错误；
- 请求 ID、调用 ID 和任务 ID贯穿各层；
- 新增可选字段保持兼容，改变语义需要提升主版本并提供迁移说明。

## 7. 实现门

只有 T01 的 Facade、Schema、Runner、错误和最小闭环通过验收后，才实现 MCP 服务与 Codex 插件。实现时重新核对官方 SDK、插件 manifest 和安全要求，并用直接请求、间接请求、非法输入和越界请求分别测试。

