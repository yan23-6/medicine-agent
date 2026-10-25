# B12会话运行时核心与D04交接

2026-10-24。D03已核验，Codex继续运行时设计/关键实现，固定CLI和大量参数化验证交DeepSeek。

## 项目约束

用户明确数据层默认保持现有包结构兼容，推理链、编排和会话优先包外实现。规则已同步AGENTS、md第04章、overall最终需求/变更策略/决策D-14、路线图与当前/下一任务；实验协议未定稿不构成任意重做数据结构的理由。此轮.medpkg、旧医学Schema及稳定地址未变，不需要重新蒸馏。

## D03核验

源码diff仅固定导出分派与CLI选项；watched/10份运行证据、失败与成功两轮JUnit、全部既有函数、341份Schema哈希和受保护输入均核对相符。102项契约与43项相关测试为执行者实际日志，不冒称Codex重跑或完整会话验收。详见D03 RESULT核验段。

## 当前实现

新增analysis/review_sessions.py；ReviewSessionService.create/inspect/submit遵守设计第五/六节：复制重验包外快照、规范化封装和稳定身份、逐评审者逐材料历史、整批锁内预验与不可覆盖hard-link发布、幂等、无法判断/分歧视图、异常全局阻写。未知坏事件不推断最终链头；完整目录一致回滚没有可信外部锚点，不宣称能检测。

新增tests/test_review_sessions.py初始4项：独立意见/幂等/无法判断与待仲裁、同人更新及整批过时拒绝、坏事件审计阻写、源包和原快照不变及拒绝覆盖。最终核心（含限额错误映射和Windows创建锁路径规范化）4 passed（15.06秒）。只用合成材料，未创建真实意见或运行新真实会话。

## 交接与未完成

D04 ready，尚未执行：DeepSeek按执行单接三个明确CLI、补20行运行时矩阵、执行相关/全量、只做真实空白会话安全检查（0意见）及非敏感摘要。核心/模型/设计不能自行改，冲突交Codex；每轮独立保存日志/XML。

当前CLI尚未接入；并发/失败恢复/迁移大矩阵、全量与D04核验、独立发行和完整B12验收尚未完成。Windows协作创建锁、事件原子hard-link需要目标文件系统支持，不推断跨平台或医学正确。交接后Codex停止并发改动，用户通知后核验。

## 最终交接基线

- `src/medicine_agent/analysis/review_sessions.py` SHA256 `cf4295cb1487539d9cd691fa2268619ed735c82df10ae30085bd048ddb633119`。
- `tests/test_review_sessions.py` SHA256 `656688bc6da807f7ecaec7a5d62c05216dbdaec433dee7db8223b69a432767d1`。
- `src/medicine_agent/domain/review_session.py` SHA256 `b49ea90b0c53777436a5011f0f6ee5c4abd82989b012d675da11693aea445d16`。
- `src/medicine_agent/analysis/review_snapshot.py` SHA256 `ac3e88afef6c81a11f2344e284b1178b39fab5d76dca36851c311ed4c3937a72`。
- `tasks/evidence/T02B12_REVIEW_SESSION_DESIGN.md` SHA256 `3c82ac5d715f79db927cf6fbc3798785e8eb2a851be6fdc2ffebaa951587842d`。
