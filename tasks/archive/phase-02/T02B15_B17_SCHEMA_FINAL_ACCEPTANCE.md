# B15—B17公开契约与最终工程验收补充

2026-10-25；状态done（B15/B16/B17同轮最终工程范围，无第4任务）。

原验收档案保留不改写。最终规则检查发现此前缺公开结构Schema，故暂停最终完成声明并回到B17整合；[补漏经过与设计复查](../../evidence/T02B15_B17_SCHEMA_REVIEW.md)明确原结果的不足。本补充与各任务原验收共同构成最终完成依据，不能只引用补漏前的子范围验收。

新runtime-readiness/0.1.0含三个诊断报告与OCR资源描述共4份Schema+索引，stdlib生成器唯一源；主CLI早期分派与无依赖独立导出相同。失败报告保持完整统一结构。旧345Schema及12索引逐字节不变（总349Schema/13索引），不改.medpkg、来源身份、语义注册表、原准备材料。

最终全量549 passed/2 skipped（JUnit 621.50秒、命令总622.201秒），551/0失败/0错误/2跳过。定向95 passed（5.98秒），额外-S无医学依赖导出和反例字段约束通过。无第三方Draft规范验证器，本项目受控关键字子集检查不等于全面JSON Schema规范认证。

新wheel/sdist122项源资源逐字节一致、禁入路径0；全新site-packages/python -I四Schema导出与仓库字节相同，合成中文OCR正例/缺模型前置阻断/资源恢复哈希与无网络审计通过。依赖仍用已有物理快照；实际完整离线wheel集合缺33依赖，不宣称新机离线安装。仅Windows/Python3.13/RapidOCR3.10.0工程范围，医学/许可/病例/真实跨源/规模仍缺。

完成后再次回读原01/04/08/09/16与overall规则：符合独立运行、受控资源、包外操作契约和医学门分离；满足“新公开结构版本化并生成Schema”。B18恢复ready，仅登记未执行，三任务至此结束。

证据artifacts/solo-next/20261025T110558Z/readiness-final-full.log/xml/json、readiness-final-release-audit.json、readiness-final-installed-smoke.json、最终audit与独立证据清单。结果索引[三任务汇总](../../evidence/THREE_TASK_RUN_20261025_B15_B17.md)。
