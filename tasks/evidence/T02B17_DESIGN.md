# B17 本地OCR资源就绪与缺失阻断设计

2026-10-25，实施前。B16归档后回读原产品01/04/08/09/16和overall：安装依赖、资源本体及实际运行应分别验收。实际RapidOCR3.10.0默认配置/资源表/三份ONNX都存在；现有capabilities只查元数据，OCR缺模型可走后端下载分支。

新增包外`ocr_resources`模块、stdlib独立API `inspect_ocr_resources(model_root=None)` / console `medicine-agent-ocr-resources [--model-root]`。版本化资源描述放在产品资源目录，只含RapidOCR确切版本、默认配置/资源表SHA256、det/cls/rec模型basename/大小/SHA256；不附带ONNX二进制，不重写供应商许可。描述依据实际安装的vendor默认配置和资源表，ONNX哈希须同时与资源表声明相符；这些是当前受测基线，不是供应链签名。

输出ocr-resources/0.1.0，不含绝对路径或URL。默认只读安装分发位置，显式model-root只核验该目录，不暗中改变业务配置。缺后端/模型、hash或配置变化、链接/reparse/越界/大小异常明确blocked；未支持版本/无法识别状态not_evaluated；绝不下载或创建目录。每文件最大512MiB，总1GiB，配置/资源描述最大4MiB。哈希从单一文件句柄计算、核对读前后变化，不宣称抵御有写权限者在检查后的恶意替换。模型推理、原生库、许可仍各自未评估。

`documents.capabilities`追加资源状态/availability_basis/native_runtime，整体available仅在依赖元数据和本地资源都满足时为true；缺OCR不会把TXT/MD从支持格式中删除。`_ocr`先取已核验默认路径，失败抛OCR_RESOURCES_UNAVAILABLE（非敏感）；成功显式传Det/Cls/Rec.model_path进入后端，不走其默认下载模型分支。此为缺资源行为收紧，文本解析/包格式不变；修复/回滚通过受控资源准备或恢复本次代码，禁止静默降级为在线下载。

回归覆盖缺件/改字节/未知版本/配置变更/非法路径/链接/限额/只读、capabilities诚实表达、资源缺失时RapidOCR不被实例化、成功显式路径。使用自制图片作本地实际OCR及隔离安装正负例，禁止新真实PDF/蒸馏。最终统一全量及发行/文档/345旧Schema/原包/7准备材料审计；完成后回读原产品再归档、登记下一任务并停止。
