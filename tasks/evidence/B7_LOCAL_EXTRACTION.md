# B7 本地提取证据摘要

> 日期：2026-10-18
> 性质：可提交的非敏感摘要；真实包、OCR 正文、任务数据库和 PDF 位于被忽略目录。

- 教材：246 页；SHA256 `031007fc2caa796ed6b72f8b6ea4a512a861660e84349c936a5160782b0dded9`；
- 处理范围：物理页 34—38；
- 任务：`learning_222400b0ee2c4877919d99971a5cf2f0`；
- 子任务：`analysis_1375f48f59c74c3dbff1d58682fc2b7e`；
- 调用：5 次 document-extraction、5 次 knowledge-distillation、1 次 build-validate，全部 success；
- OCR 块数：39、37、37、35、40，共 188；
- 本地包：`bundle_76afd4ccabb3d9021e5a9b7d.medpkg`，98,294 字节；
- 包 SHA256：`4964e2fb644b3aa0be5d10ee89ed5ab24b8e0aea032631d80014d09217af56ba`；
- 隔离验证：1 个组件、188 条证据、5 条 extractive 知识记录，可按知识 ID 查询并回溯证据；
- 边界：包内无 `tcm.json`，不代表真实中医语义分析通过。
