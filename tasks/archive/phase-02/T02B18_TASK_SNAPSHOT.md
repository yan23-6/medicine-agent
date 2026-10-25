# T02-B18 合成规模与资源开销基线

> in_progress；D01 Codex verified；D02 executed_pending_review，待Codex核验；2026-10-25。

## 正式范围与分工

仅本CURRENT正式，NEXT不执行。Codex负责原产品符合性、测量设计、固定采集器、小样验证和结果核验；DeepSeek负责重复采集、机械重算和证据整理。执行期间不并发修改，不让执行方调整设计、预期或生产实现。

数据包结构、来源身份和现有349Schema保持兼容；不因测量更改包、放宽完整性检查或重蒸馏。B18整体尚未验收，性能/医学/临床门不因某个测点完成而通过。

## D01已核验

原执行结果evidence/T02B18_D01_RESULT.md保留为当时待核验记录；最终子步骤判定见evidence/T02B18_D01_CODEX_REVIEW.md。Codex独立核验163项证据哈希、48份样本/stdout、36正式样本、12组median/p95重算、555保护文件及349Schema，全通过，未重跑测量。仅typed-view重验/投影微基准，不检查源包/真实事件/service。

R改变也改变意见总数，不能从D01单独断言pairwise是性能瓶颈；暂不优化。下一步补实际生产API的完整操作基线。

## D02执行结果：executed_pending_review

DeepSeek已按D02执行单执行完毕，停在executed_pending_review，结果见[evidence/T02B18_D02_RESULT.md](evidence/T02B18_D02_RESULT.md)。

- 运行目录artifacts/b18-d02/deepseek-20261025T131045099Z/（新建，未覆盖Codex小样）；退出码0、整次305.96秒、failure=null、protected_unchanged=true。
- 7profile×2操作×2工作区模式=28格、112采集进程（28丢弃+84正式）齐全；7份build≡fixture.json；84份正式样本全passed/oracle/fixture_unchanged/内存measured；E=R×H、O=K×R×H与设计表逐行相符；每profile/operation的6份样本身份一致。
- 独立重算28格中位与nearest-rank p95逐格与summary相等；123项机械检查全通过；两负例正确阻断；349/349Schema、555文件保护映射、git状态前后未变；两采集器/设计/执行单哈希未变。
- 观测：28格约0.62–1.71秒；最小N的u2-r0-h1已需623–663ms，说明该段以源包/快照重建与事件历史重验为基线；峰值约100.7–122.7MiB。inspect/report为独立实验，峰值与中位数均不可相减。
- 本单未归档、未改NEXT、未写性能/医学/阶段门passed；B18是否整体完成由Codex回读原产品目标判断。

本轮不重新运行全量549项或重建发行，无新外发/依赖安装/LLM/真实资料OCR/蒸馏/训练，不读模型配置、不改旧包，不commit/push。下一步无需新文件或权限。
