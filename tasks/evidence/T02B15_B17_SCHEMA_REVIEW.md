# B15—B17最终公开契约补漏

2026-10-25。本轮仍为B15/B16/B17三个正式任务，无第4项执行。

最终回读overall/规则与变更策略.md第4节发现“新公开结构必须版本化并生成Schema”：初次三个报告虽带版本，却没有对应导出Schema，前次完成口径欠缺这项要求。暂停最终完成声明，CURRENT回到B17整合收尾，先补最早契约缺口；原回归和历史档案保留，不改写历史。

补充设计与实现：stdlib唯一结构源runtime_readiness_schemas.py，独立runtime-readiness/0.1.0四Schema（EnvironmentPreflightReport、WheelhouseReadinessReport、OCRResourceReport、OCRResourceDescription），仓库导出4文件+索引。不依赖Pydantic启动，可独立python -m导出；现有export-schemas早期分派注册同一源，旧345Schema与索引不变。失败wheelhouse报告补齐统一必需字段，不再输出缩略形状。未知字段/缺字段/版本/状态/SHA/资源行等约束不混入医学字段。

95项定向（原74+新增16契约+既有5契约）通过，5.98秒。契约检查明确只解释当前使用的JSON Schema关键字子集，覆盖实际报告与反例、固定快照字节/索引、主CLI和-S无依赖导出；未装第三方验证器，不宣称全面Draft2020-12规范一致性认证。

新发行122项源文件/资源wheel/sdist一致；全新安装python -I可导出与仓库逐字节一致的四Schema，自制OCR/实际缺模型阻断/无网络及恢复哈希再次通过。readiness-final-full为补齐后的最终全量，未完成前本文件不作为最终done；通过后由补充归档和STATE给出真实结果。

原产品01/04/08/09/16、最终需求与规则检查结论：补齐操作契约满足既有要求，不新增医学Schema，不改包/身份/原始材料；独立运行、受控准备、医学与软件门分开均保持。完成最终全量后追加验收，再恢复B18 ready，本轮停止。


最终结果：549 passed/2 skipped，JUnit 621.50秒，原包/345旧Schema不变；四新Schema及索引已验收。[补充归档](../archive/phase-02/T02B15_B17_SCHEMA_FINAL_ACCEPTANCE.md)。三任务最终done，B18恢复ready而不执行。
