# B7 本地与远程数据包核查

> 核查日期：2026-10-18。仅记录 Git 和当前工作区，不代表已经检查其他电脑、GitHub Releases 或外部备份。

## 结论

- `git fetch origin` 成功；远程只有 `master` 分支，指向 `3d9163ea2b6712ca1e1f71b10002ca092e78b44a`，未发现远程 tag。
- `git ls-tree -r --name-only origin/master` 未发现 `.medpkg` 或 artifacts 成品；`git log --all -- '*.medpkg'` 无记录。
- B4/B5 真实运行验收报告随代码保存，但真实知识包在 `.gitignore` 排除的 `artifacts/` 中。报告证明当时曾产包，不证明当前克隆拥有文件。
- B4 报告记录：`artifacts/b4-quality/knowledge/bundle_bd668c695f761309551e81c4.medpkg`。
- B5 报告记录：`artifacts/b5-incremental/knowledge/bundle_2c58e2c337aab6daa6da31cb.medpkg`，143,145 字节。报告明确说明普通 clone 不会带走运行产物。
- 当前工作区只有 B7 extractive 包及其隔离副本；它们不包含 `tcm.json`，不能代替 B4/B5 中医语义包。
- 产品默认知识目录 `<用户目录>/MedicineAgent/knowledge/` 当前不存在，未从该位置发现遗留旧包。

## 推进方式

用户已恢复本地模型配置，且明确允许发送教材物理页34—38的 OCR 文本到配置模型服务，仅用于 B7 复验。因此本次使用独立真实模型任务重建，不以恢复旧包为唯一前置，也不声称已验证真实旧包兼容。

## 交付与恢复边界

Git 代码/文档备份与真实知识包备份是两件事。不得为补齐旧结果强制提交被忽略的原文、知识包或密钥。新包形成后在证据摘要记录文件名、字节数、SHA256、来源范围、格式版本和验收状态；需要异地长期备份时另行选择获授权的存储目的地，不能仅依赖 Git 提交或本机 artifacts。
