# T01 阶段验收计划与现状矩阵

> 审计日期：2026-09-29
> 当前结论：15 项技术检查全部通过，等待用户确认验收报告
> 用途：记录执行前基线；实际完成证据写入后续 `ACCEPTANCE_REPORT.md`

当前汇总：15 项通过，0 项阻塞。

## 1. 状态含义

- `通过`：已有实现和本次可复现检查支持；
- `部分通过`：核心能力存在，但契约、覆盖或产物不完整；
- `待验收`：尚无足够实现或检查证据；
- `阻塞`：需要用户输入或外部服务后才能检查。

## 2. 验收矩阵

| # | T01 验收项 | 当前状态 | 当前证据 | 收尾要求 |
| --- | --- | --- | --- | --- |
| 1 | 干净环境可以安装或初始化 | 通过 | 新隔离环境按锁文件安装，完整测试通过 | 已记录到验收报告 |
| 2 | 可列出 Skill、版本、输入输出 Schema 和状态 | 通过 | 6 个 Skill 均返回版本、状态和 Schema；`schemas/t01` 已生成 | 契约快照已进入回归测试 |
| 3 | 一条命令或程序调用完成最小生产消费闭环 | 通过 | CLI 与 `run_minimal_pipeline` 存在，端到端测试通过 | 在干净环境复验 |
| 4 | 实验知识包通过结构和完整性校验 | 通过 | Build/Validate 与包校验测试通过 | 增加失败包和 Schema 契约覆盖 |
| 5 | 查询结果可以回到证据和原文位置 | 通过 | Facade 查询与 Trace 返回 3 条完整证据 | 已覆盖单证据和多证据 |
| 6 | 重复输入具有稳定身份 | 通过 | 两次 CLI 闭环产生相同 `package_id`；运行 ID 独立 | 内容身份和运行身份已分离 |
| 7 | 无效输入和依赖错误具有稳定语义 | 通过 | 测试覆盖注册、版本、输入、模型输出、模型调用、包与证据错误 | CLI 配置失败返回结构化错误 |
| 8 | 默认测试不依赖真实密钥 | 通过 | 5 个离线测试使用 FakeModel | 保持在线测试显式触发 |
| 9 | 自动测试全部通过且可复现 | 通过 | 当前环境和新隔离环境均为 `15 passed` | 默认测试保持离线 |
| 10 | 文档明确不具备完整中医蒸馏能力 | 通过 | README、STATE 和阶段文档均声明边界 | 完成实现后再次同步 |
| 11 | 未把 Agent 虚构为已实现 | 通过 | 当前无 Agent 代码，文档标明尚不存在 | 保持边界 |
| 12 | `docs` 原始材料未被修改 | 通过 | 本次审计前工作区仅有未提交周报 | 收尾验收再次检查 `docs` 差异 |
| 13 | 真实 OpenAI-compatible 冒烟通过且无密钥泄露 | 通过 | `llm-smoke` 返回 Schema 有效且 `ok=True`；真实流水线、Validate、Query、Trace 完整通过 | 已记录脱敏摘要和一次被正确阻断的 Schema 失败 |
| 14 | 缺失、重复、异义和未映射字段不丢失 | 通过 | 7 条有序观察全部进入 `raw_fields.jsonl`，歧义与未映射产生警告 | 已覆盖完整路径 |
| 15 | 多段整理的知识可以回到全部证据 | 通过 | 1 条合并知识引用并返回 3 条证据 | 已覆盖查询和 Trace |

## 3. 额外契约缺口

以下额外契约缺口已经补齐并进入自动测试或构建检查：

- `RunRecord` 实体和实际运行记录存储；
- `ApplicationFacade.validate_package`；
- `ApplicationFacade.query_package`；
- `ApplicationFacade.trace_evidence`；
- `ApplicationFacade.get_run`；
- CLI 通过 Facade 调用上述能力；
- 模型响应的输出 Schema 校验；
- wheel/sdist 内容检查。

## 4. 当前可复现检查

2026-09-29 已执行：

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m medicine_agent.cli --help
.venv\Scripts\python.exe -m medicine_agent.cli list-skills
```

结果：

- 自动测试：当前环境和新隔离环境均为 `15 passed`；
- CLI：成功显示 9 个命令；
- Registry：成功列出 6 个最小 Skill；
- 真实 LLM 冒烟返回 Schema 有效且 `ok=True`；
- 真实模型流水线首次输出不符合 Schema 时被正确阻断，重跑后完成 Build、Validate、Query 和 Trace；
- 未读取本地密钥配置；
- 新隔离环境、wheel 安装、wheel/sdist 内容和最小闭环均已验收。

## 5. 状态更新规则

1. 执行过程中只在本矩阵记录中间证据，不提前把阶段标记为完成；
2. 全部必需项通过后创建 `ACCEPTANCE_REPORT.md`；
3. 用户确认验收报告后，更新 `tasks/STATE.md`、阶段 README 和当前任务状态；
4. T02 进入前必须基于最终 Schema、真实错误分布、可用材料和专家条件重写需求。
