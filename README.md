# 中西医知识蒸馏与智能体平台

本仓库当前处于需求设计与 Skill 基础建设准备阶段。仓库中的设计描述目标能力，不代表对应代码、Skill、Agent、Schema、知识包或服务已经实现。

## 从哪里开始

- 了解稳定设计：[md/README.md](md/README.md)
- 了解当前真实状态：[tasks/STATE.md](tasks/STATE.md)
- 了解任务规则：[tasks/README.md](tasks/README.md)
- 了解终极需求：[tasks/overall/终极需求.md](tasks/overall/终极需求.md)
- 执行当前任务：[tasks/phases/01-skill-foundation/CURRENT_TASK.md](tasks/phases/01-skill-foundation/CURRENT_TASK.md)

当用户询问“下一步要干什么”时，应先读取 `AGENTS.md` 和 `tasks/STATE.md`，再返回当前阶段的正式任务和下一任务预告。不得根据设计文档假定尚未实现的能力存在。

## 当前结论

当前下一步是从零建立可调用 Skill 基础，以及材料摄取、证据定位、最小知识蒸馏、知识包构建校验、知识包查询和质量评价组成的最小生产消费闭环。在该闭环验收前，不启动整本教材或批量医案的正式蒸馏，也不实现多 Agent。

`docs` 保存导师原始资料，默认只读；`log` 只在用户明确要求时更新。

