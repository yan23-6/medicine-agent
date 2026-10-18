# 阶段04：地图式多轮辨证与多 Agent

> 状态：idea；阶段03完成门满足后重评。

目标：基于 CanonicalCase 和正式可查询知识包，实现局部图召回、多个辨证候选、支持/反证/冲突、信息增益追问、剪枝、停止条件和安全升级。

只有当 TCMReasoningSkill、SafetyGateSkill、评测数据和权限边界成立时才启用对应 Agent。西医专业 Agent 不属于当前路线。
