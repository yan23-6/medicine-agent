# B16 验收结果

2026-10-25，done。设计见[T02B16_DESIGN.md](T02B16_DESIGN.md)。B15+B16定向52 passed（B16新增34），1.15秒；119源文件/资源wheel与sdist字节一致，全新安装console入口与python -I模块入口验证合成完整材料正例。本地真实发行目录只含项目wheel，内容核验通过但缺33个活动依赖（含Pydantic），正确blocked，没有联网补齐。

ZIP逐成员RECORD/SHA256、标签、冻结版本、活动闭包/markers/extras、缺件、歧义、路径、元数据、限额和输入重复键回归通过。原始成员名在Windows会被ZipInfo规范化：前两轮有同一失败（各1 failed），最初仅改构造仍复现，随后确认需同时检查orig_filename与filename，补核心检查后通过；未降低期望错误码。失败日志保留。实际负例始终阻断，没有执行wheel内容。

metadata_resolution通过仅表示当前平台的显式材料自洽，不是签名认证、真实安装、原生运行或OCR资源就绪。345旧Schema/真实包/7准备文件未变，无新外发/模型/OCR/蒸馏/医学意见/commit/push。

证据目录artifacts/solo-next/20261025T110558Z/：b16-target/02/03.log、b16-release-final.log、b16-final-release-audit.json、b16-wheelhouse-smoke.json。隔离依赖仍用既有已安装快照物理复制，不冒称空缓存离线安装。


后续整合核验：B17整合时摘要读取增加显式字节上限，当前34项；整体全量通过。历史52项是当时B15+B16合并数，不改写历史。


## 最终公开契约补充验收（2026-10-25）

初次完成检查遗漏了overall“新公开结构必须生成Schema”；已暂停最终完成、回B17整合补齐runtime-readiness/0.1.0四Schema。原历史档案不改写，以[补充验收](../archive/phase-02/T02B15_B17_SCHEMA_FINAL_ACCEPTANCE.md)共同说明最终完成。最终全量549 passed/2 skipped（JUnit 621.50秒），95项定向、122源资源发行、新安装四Schema字节一致及同进程无下载OCR正负例通过。旧345Schema及12索引不变，新增4份包外操作Schema+索引，总349；数据包与来源身份不变。B18仅登记ready，本轮停止。
