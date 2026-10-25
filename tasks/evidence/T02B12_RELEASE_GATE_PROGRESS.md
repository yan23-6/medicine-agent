# B12发行验收交接进展

2026-10-25。Codex已核验D04，当前进入最后的工程发行验证；未标B12 done，未归档完整验收、未推进NEXT。

## 已核验

- D04源码差异为analysis/cli.py +72/-0及README +30/-0，原测试/辅助函数未改变；最终运行时68 passed/1 skipped、相关197 passed/1 skipped、全量435 passed/2 skipped的JUnit和日志一致。
- 8项watched哈希、除summary自哈希外的运行文件哈希、341份Schema实际哈希及源包/准备目录基线核对相符。
- 真实新会话文件在沙箱下拒绝读取，已通过正规只读权限流程核验其manifest完整哈希/会话稳定ID、0事件、7文件副本及未审/禁止发布状态；未改ACL或正文，原始包仍153943字节/50742f7c…f7786d。
- D04 summary.json错误地包含自身旧哈希，已在其RESULT末尾核验段记录独立实际哈希，不覆盖旧证据。D05采用独立清单排除自身。

## 剩余与交接

最终门审查见T02B12_FINAL_GATE_REVIEW.md。D04的3项限额检查实际走inspect读取分支，发布前submit的3项分支仍需针对性补测；无需改核心/模型或包结构。

D05 ready，尚未执行：DeepSeek按T02B12_D05_EXECUTION.md追加3项测试、只跑这3项，再离线构建wheel/sdist、安装到全新隔离环境，用python -I完成自制资料的API/CLI/迁移闭环，最后查发行资源、341份Schema、本地文档链接及受保护路径。若生产代码无变化不重复D04的全量基线；缓存/权限/产品问题明确停止交Codex，不联网或改数据协议。

独立环境不得复制真实原件/包/准备材料，只能使用自制TXT及本地SyntheticModel；没有真实外发/OCR/蒸馏、真实意见或医学审核。Windows/文件系统、实链权限skip及无可信锚点的回滚边界保留。

执行期间双方不并发修改。D05完成由用户通知Codex核验实际归档与安装证据，届时才决定B12工程归档及B13重评；医学、许可、病例、规模与跨源门仍独立。

## 交接基线

- `src/medicine_agent/analysis/review_sessions.py` SHA256 `cf4295cb1487539d9cd691fa2268619ed735c82df10ae30085bd048ddb633119`。
- `src/medicine_agent/analysis/cli.py` SHA256 `8a2a871cb6c2e3d6248a2c367e5b4b14511a0e7c295932dae6cf76e55ba49ed8`。
- `tests/test_review_sessions.py` SHA256 `40216434bd72c92587003773010e4888ccb9539bcae87701198335dd9948c54c`。
- `src/medicine_agent/domain/review_session.py` SHA256 `b49ea90b0c53777436a5011f0f6ee5c4abd82989b012d675da11693aea445d16`。
- `tasks/evidence/T02B12_REVIEW_SESSION_DESIGN.md` SHA256 `3c82ac5d715f79db927cf6fbc3798785e8eb2a851be6fdc2ffebaa951587842d`。
- `pyproject.toml` SHA256 `38564486bae6ac387707ecf51633ba7997f943a20c0c507e4aeef4fcf2ea6ae8`。
