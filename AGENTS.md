# 项目执行规则

本仓库同时包含稳定设计、实验实现和历史验收。任何 AI 都必须依据当前文件与实际产物工作，不依赖聊天记忆。

## 启动顺序

每次执行项目前依次读取：

1. `tasks/STATE.md`
2. `tasks/CURRENT.md`
3. `tasks/HANDOFF.md`
4. `tasks/NEXT.md`
5. `tasks/ROADMAP.md`
6. 当前任务引用的稳定设计和 Schema

然后检查前置产物是否真实存在。仓库中只有 `tasks/CURRENT.md` 是正式任务；`NEXT.md` 和路线图不得直接执行。

## 执行与状态

- 前置缺失时，当前工作改为补齐最早缺失能力或记录明确阻塞；
- 每完成一个可核验步骤，立即同步 `STATE.md`、`HANDOFF.md` 和 `CURRENT.md`；
- 只有产物存在且验收通过才能写 `done`；
- 设计目标、历史结果和当前实现必须明确区分；
- 不从 `tasks/archive/`、`log/` 或聊天记录推断当前文件仍存在；
- 当前任务完成后，先归档验收，再把 `NEXT.md` 重评为新的 `CURRENT.md`。

## 需求变更

任何需求变化都要检查并同步：

- `md/` 稳定设计；
- `tasks/overall/` 最终需求和能力口径；
- `tasks/ROADMAP.md`；
- `CURRENT.md` 与 `NEXT.md`；
- 受影响代码、Schema、测试和说明。

Agent/Skill 定位变化必须同步职责、调用关系、输入输出、依赖、交付、验收和旧名称对应关系。

## 内容边界

- `md/`：稳定产品与技术设计，不记录阶段进度；
- `tasks/overall/`：最终需求、能力定义和决策规则；
- `tasks/phases/`：阶段目标和阶段门；
- `tasks/archive/`：历史验收，只读参考；
- `tasks/evidence/`：当前任务的非敏感证据摘要；
- `docs/`：遵守 `docs/AGENTS.md`，默认只读；
- `log/`：只有用户明确要求时才修改；
- `pdfs/`：本地原始资料，禁止提交或复制进测试/发行物；
- `artifacts/`：真实运行产物，禁止提交；
- `config/llm.local.toml`：只由运行时读取，禁止复述、记录或提交。

不得先蒸馏正式知识包再补 Skill、Schema 或验证规则。Agent 只能调用已实现、登记并验收的 Skill。软件测试不等于医学正确性。

## 面向用户

最终答复使用简洁中文，明确：已完成什么、真实阻塞是什么、现在需要提供文件/权限还是可以直接开始下一步。已有授权不重复索要，历史授权不扩大到新材料或新服务。
