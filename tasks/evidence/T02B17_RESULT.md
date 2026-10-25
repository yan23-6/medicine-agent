# B17 本地OCR资源就绪与缺失阻断验收

2026-10-25，done，三任务第3项。实施前设计见[T02B17_DESIGN.md](T02B17_DESIGN.md)。

交付stdlib独立资源API/CLI、RapidOCR3.10.0默认配置/资源表及三份模型的版本化哈希描述；只提交描述，不复制ONNX。当前三份ONNX合计31749509字节，哈希同时与本地供应商资源表声明一致。未知后端not_evaluated，缺件/内容变化/链接/异常大小blocked，不自动下载。capabilities明确availability_basis/native_runtime与资源状态；TXT/MD仍支持。实际OCR前核验并显式传三个model_path，缺失报OCR_RESOURCES_UNAVAILABLE。

三模块定向74 passed（3.66秒），B17的20项同进程下载守卫回归另通过（2.04秒）。全量533 passed/2 skipped，618.45秒（命令总619.093秒），JUnit 535/0失败/0错误/2跳过与日志一致。跳过仍为既有Windows真实建链权限，不冒称真实链接验收。全量收集后将新增OCR守卫用例改为同进程worker核心，以保证monkeypatch覆盖实际推理；额外20项通过，不需要因仅该测试加强而重跑整套。

121源文件/资源在新wheel/sdist逐字节一致、禁入路径0；隔离安装依赖来自既有物理快照，python -I从新site-packages运行，console和模块API一致。自制中文图片实际OCR2块，审计hook阻止网络、DownloadFile.run守卫覆盖同进程推理，0下载分支；移走隔离环境det模型先阻断，finally恢复且SHA一致。权威证据b17-installed-smoke-02.json；首轮用extract_unit子进程，守卫未传入子进程，不能据首轮宣称拦截覆盖，已明确纠正。

B15追加非法版本/非字符串Requires-Python负例，发现packaging可接收list但后续AttributeError；入口先检类型后通过；B16摘要改为有界读取。首个全量在已知定向失败后取消不作验收，b17-full-cancelled.json及原日志保留；最终用b17-full-02。首次文档审计发现README结尾空行，规范化后通过，没有改旧包或Schema。

345旧Schema与索引、原真实包及7份准备文件、语义注册表全部与本轮基线逐字节哈希相同。原包153943字节/SHA256 50742f7c32f7178c562ba2927ae070feac1e82696f7f86792157090fe2f7786d，仍0真实意见。没有新真实资料OCR/LLM/蒸馏/训练/外发/commit/push，不读LLM配置，不改docs/log/pdfs。

当前只证明Windows/Python3.13、已安装依赖基线及RapidOCR3.10.0；资源就绪与自制识字不等于原生多平台全面兼容、OCR质量金标准、资源再分发许可、供应链签名或医学验收。真实离线wheel集合仍缺33依赖，不声称空缓存离线安装。证据目录artifacts/solo-next/20261025T110558Z/，主要b17-full-02.log/xml/json、b17-final-release-audit.json、b17-installed-smoke-02.json、final-audit.json及最终独立证据清单。


## 最终公开契约补充验收（2026-10-25）

初次完成检查遗漏了overall“新公开结构必须生成Schema”；已暂停最终完成、回B17整合补齐runtime-readiness/0.1.0四Schema。原历史档案不改写，以[补充验收](../archive/phase-02/T02B15_B17_SCHEMA_FINAL_ACCEPTANCE.md)共同说明最终完成。最终全量549 passed/2 skipped（JUnit 621.50秒），95项定向、122源资源发行、新安装四Schema字节一致及同进程无下载OCR正负例通过。旧345Schema及12索引不变，新增4份包外操作Schema+索引，总349；数据包与来源身份不变。B18仅登记ready，本轮停止。


最终独立证据清单artifacts/solo-next/20261025T110558Z/final-evidence-manifest.json，109项，SHA256 f0807460c7e4cbfc6c723ee70b3c7abf5d1de3cf2f00381cad10360edb34dc5c；排除自身/可变任务摘要，不宣称外部可信签名。所有所列产物哈希逐项复核一致。
