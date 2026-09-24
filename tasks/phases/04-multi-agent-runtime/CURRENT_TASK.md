# 阶段 04 当前任务草案

> 状态：idea  
> 预定任务：T04 三 Agent 编排与病例运行时

预定首先实现 OrchestratorAgent、KnowledgeBuilderAgent 和 EvidenceReviewAgent。它们调用已经验收的 Skill，不重新实现知识逻辑。任务应验证路由、状态、失败恢复、最小权限、候选写入和评审门。

如果进入阶段时西医与 SafetyGateSkill 已稳定，可同时加入西医和安全并行路径；否则只预留接口，不虚构能力。Agent 数量根据实际职责重新确认，不以六个为必须部署数量。

