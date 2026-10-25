# B12快照核心进展与交接

2026-10-24。用户已恢复Codex沿CURRENT推进，重复验证交DeepSeek执行，Codex核验。D01 verified保留。

## 已完成与证据

- 已形成T02B12_REVIEW_SESSION_DESIGN.md：冻结快照核心行为；会话历史/独立意见/分歧/迁移的约束已整理，会话Schema尚未冻结或实现。
- 新增analysis/review_snapshot.py：固定7文件、大小限制、重复键/非有限数/版本、类型/稳定ID、空白模板、源包字节绑定、重建报告及展示材料比对，读前后变化检测。只写独立私有缓存，不写源包、准备目录或意见。
- 新增tests/test_review_snapshot.py：健康只读与稳定身份、伪造指纹/来源/计数且同步重算ID与哈希、恶意manifest路径拒绝。初始5 passed（7.01秒）；随后仅补异常抑制、非目录workspace拒绝的防御，最终复跑结果见下文追加记录。
- 本地真实完整空白快照经新API重建报告相同；188证据、541目标（63节点/478字段）、27gap/1隔离项、意见0；medical_review=unreviewed、release_allowed=false。
- 真实验证摘要：`artifacts/b12-snapshot-core/20261024T113451449663Z/verification.json`，snapshot_id为snapshot_115dd968d0d993ffce557d9c，manifest_sha256为b7a75bdabc88c41d847e1e653bdd75f63021e1265cc5fce91d29b5812673c90d；源包目录及原准备目录前后全部文件哈希相同。

## 尚未完成

D02坏输入矩阵、定向/全量与Codex核验尚未完成；快照核心不能写“已验收”。partial/empty暂不支持创建会话，明确拒绝。接口是内部Python管理API，不是已登记Skill或CLI。不存在复核会话/意见写入、自动医学确认或完整B12交付。

## 交接

DeepSeek只执行T02B12_D02_EXECUTION.md：追加固定合成矩阵、执行一次定向/相关/全量、保存JUnit与摘要。不得改核心或自行修复失败。Codex停止并发修改，用户通知后再核验。无新资料、模型调用或服务授权需要。

## 最终交接基线

最终核心版本复跑：5 passed in 7.42s；git diff --check通过（仅Git换行提示）。未跑全量、未构建发行物；D02负责补矩阵和固定回归。

- `src/medicine_agent/analysis/review_snapshot.py` SHA256 `ac3e88afef6c81a11f2344e284b1178b39fab5d76dca36851c311ed4c3937a72`。

- `tests/test_review_snapshot.py` SHA256 `667dba650bcbf074892acbcbba1f28fb3350cecfe8f89e2acb9567bcc8ccbbce`。

- `tasks/evidence/T02B12_REVIEW_SESSION_DESIGN.md` SHA256 `b0851f8dac722f18ec53542e7cc95c1d3b1a504a8af97870838166914dcf5153`。
