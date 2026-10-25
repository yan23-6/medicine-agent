# T02-B14 复核覆盖与声明意见统计验收

2026-10-25；done（工程统计，不是医学或阶段02完成）。

## 交付

- domain/review_progress.py的review-progress/0.1.0独立4模型、4份Schema及index；旧341份Schema导出字节不变，不改.medpkg或语义字典。
- ReviewProgressService.report先用B12 inspect验证源包/快照/历史；只读统计四类材料覆盖、每声明ID最新意见覆盖、分组pairwise明确分母；同ID更新不重复计票，无重叠或unable分母0时fraction=null。
- 有界100声明ID/100000目标，超限拒绝不截断；不可用/坏历史仅诊断，不给部分比较结果。报告确定性ID绑定session/snapshot/有效事件，不输出原文/意见理由或纠正值。
- CLI analyze review-session-progress与export-schemas新契约选项；不新增Agent/Skill、不读模型配置或外发资料。

## 实际验证

- 定向21 passed（7.56秒）；全量459 passed/2 skipped（618.84秒），JUnit 461/0失败/0错误/2跳过。实链权限的两项skip延续，未改ACL，不能写跨平台实链已验证。
- 真实空白只读报告：757目标分组188原文/63节点/478字段/28异常，0评审、无可比较对，全部pending；medical_gate=blocked，发布/训练/阶段02完成均false，源包/原7文件哈希不变。
- 新wheel/sdist的117项源码/资源双向逐字节一致，禁止路径命中0。wheel212794字节/SHA256 35d06ddfc55f3b14b56d8b7d767efb4009cb94bda1adfaa6575b270221c2c0b4；sdist167141字节/SHA256 59621d5c43977eded37449d97184b88ecc586dbd2de5b9d82e52f107ebc0669f。
- 全新site-packages/python -I读取自制迁移会话：3声明ID、12个pairwise分组行，API/CLI相同、5份新Schema文件相同、源包/会话不变、无正文泄漏。沿用38个本地依赖分发物理快照，不冒称空缓存安装通过。
- 345份Schema与文档/受保护路径审计通过；最终复查/证据清单见tasks/evidence/T02B14_RESULT.md。

## 产品复查与限制

tasks/evidence/T02B14_PRODUCT_REVIEW.md已回读原始产品设计和最终需求，结论符合。声明一致不是专家认证/医学正确性；真实意见0；医学/许可/病例/跨源/规模/训练门未自动解除。当前仅Windows/Python3.13及当前依赖快照，不承诺跨平台、全依赖版本范围或整体目录防回滚。

允许仅将已评审的下一工程任务登记CURRENT ready；用户本轮3个正式任务已完成，不执行第4项。
