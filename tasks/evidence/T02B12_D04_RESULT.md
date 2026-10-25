# T02-B12-D04 执行结果（非敏感）

> 2026-10-24；状态：**executed_pending_review，待 Codex 核验**。
> 执行单：tasks/evidence/T02B12_D04_EXECUTION.md（未改动）。本文件只含计数、哈希、测试名与错误码，不含真实原文、理由或配置。
> 运行目录：`artifacts/b12-d04/b12-d04-20261024T203638-9fe9/`（新建；真实空白会话仅在此忽略目录内）。

## 1. 基线

- HEAD `773d7d8cfef73cd89a893d375c44ef3cb37d8a9c`；Python 3.13.15；pytest 9.1.1；基线 `git status --short` 32 行（含 Codex 未提交工作，未清理）。
- 基线 SHA256：`review_sessions.py` `cf4295cb…7633119`、`review_snapshot.py` `ac3e88af…3937a72`、`domain/review_session.py` `b49ea90b…a445d16`、设计 `3c82ac5d…587842d`、`analysis/cli.py` `c96700f7…7c4912d`、`tests/test_review_sessions.py` `656688bc…32767d1`、`analysis/README.md` `2cc00474…90b6fe9`。
- 编辑前副本：`analysis_cli.before.py`、`test_review_sessions.before.py`、`README.before.md`（哈希均等于基线）。

## 2. CLI 接入（不改旧命令）

`git diff --numstat`：`analysis/cli.py` **72 插入 / 0 删除**，`analysis/README.md` **30 插入 / 0 删除**——纯追加，旧命令与旧分支未动。

- `add_commands` 新增三个平级 action（`review-session-create/inspect/submit`），所有路径参数 `type=Path, required=True`，无 HOME 默认、无 `--config`、无模型实例。
- `execute` 在模型配置与旧业务分支之前早期分派，惰性导入 `ReviewSessionService`；只调用已实现 API，不经过 `PackageCatalog`/`FileLearningService`。
- create 返回 `manifest.model_dump(mode='json')`；inspect 默认返回摘要（version、session_id、snapshot_id、writable、opinion_count、target_count、state_counts、issues、reviewer_identity、medical_review、release_allowed），`--include-opinions` 才返回完整 view；submit 用 `review_snapshot._read_file(limit=64MiB)` + `_json_object` 严格读入并要求 `version=0.1.0`，非法统一 `SESSION_REQUEST_INVALID`（固定消息、`from None`），成功只返回 version/event_id/session_id/submission_id/opinion_count/reviewer_identity/medical_review/release_allowed，不含理由与纠正值。
- README 追加三命令用法、互不嵌套/不覆盖、幂等与 `expected_previous_id` 归属、unable/分歧不改医学状态、`--include-opinions` 的本地边界，示例全部为占位材料。

## 3. 20 行运行时矩阵（新增 65 例 + 原 4 例）

| # | 用例 | 结果 |
|---|---|---|
| 1 | `test_create_rejects_existing_or_nested_target[existing_dir/existing_file/in_packages/in_workspace/same_as_preparation]` → SESSION_EXISTS / SESSION_PATH_INVALID，不覆盖、不改输入 | 5 passed |
| 2 | `test_session_manifest_corruption_rejected[sha_mismatch/missing_version/unknown_version/duplicate_key/unknown_wrapper_key/forged_session_id/marker_in_field]` → SESSION_MANIFEST_INVALID，注入标记未回显 | 7 passed |
| 3 | `test_resigned_binding_mismatch_rejected[source_archives/preparation_id/snapshot_id]`、`test_copied_snapshot_body_change_rejected` → SESSION_SNAPSHOT_INVALID | 4 passed |
| 4 | `test_three_material_kinds_submit_and_invalid_targets_rejected`（三类合法提交成功；不存在 material_id / 错 snapshot_id / 指纹错 → SESSION_TARGET_INVALID，包与快照不变） | 1 passed |
| 5 | `test_batch_with_bad_target_writes_nothing`、`test_batch_with_stale_previous_writes_nothing` → 整批拒绝，事件字节无变化 | 2 passed |
| 6 | `test_two_declared_ids_same_decision_agree_without_medical_confirmation`、`test_accept_reject_disagreement_stays_awaiting`、`test_revision_values_disagree_when_different`、`test_all_unable_is_pending_and_one_decisive_is_insufficient` | 4 passed |
| 7 | `test_previous_must_belong_to_same_reviewer_and_material`（旧头/他人意见/不存在前序 → SESSION_STALE_WRITE） | 1 passed |
| 8 | `test_same_submission_retry_is_idempotent_even_after_later_opinions`、`test_same_submission_id_with_different_content_conflicts[decision/reason/reviewer]` | 4 passed |
| 9 | `test_corrupt_event_is_isolated_and_blocks_writes[content/duplicate_key/unknown_version/unknown_wrapper_key/wrong_filename/non_canonical]` → SESSION_EVENT_INVALID，全目标 pending+history_invalid、writable=false、健康意见可审计、submit SESSION_HISTORY_INVALID | 6 passed |
| 10 | `test_self_consistent_foreign_event_isolated[foreign_session/foreign_target]` → 整个事件隔离，无半个有效批 | 2 passed |
| 11 | `test_second_root_for_same_reviewer_and_material_is_history_invalid`、`test_dangling_predecessor_is_history_invalid`、`test_deleted_event_breaks_successor_chain` → SESSION_HISTORY_INVALID，健康独立链意见保留 | 3 passed |
| 12 | `test_duplicate_submission_across_events_is_conflict` → SESSION_SUBMISSION_CONFLICT，全局 pending、不选新事件覆盖旧事件 | 1 passed |
| 13 | `test_safe_pending_file_ignored_and_not_deleted`（安全临时文件忽略、不删除、健康提交继续）、`test_unknown_event_resource_blocks_writes[file/directory]`、`test_reparse_events_resource_skipped_without_link_privilege` | 3 passed + 1 skipped |
| 14 | `test_link_failure_rolls_back`、`test_fsync_failure_rolls_back`、`test_publish_collision_never_replaces_existing_target` → SESSION_COMMIT_FAILED，无可见半事件、已有目标不被覆盖、无残留临时文件 | 3 passed |
| 15 | `test_publish_success_survives_staging_cleanup_failure`（清理失败仍成功返回，遗留临时文件不影响 inspect/幂等） | 1 passed |
| 16 | `test_busy_writer_lock_reports_session_busy`、`test_busy_create_lock_reports_session_busy`（独立子进程持 `msvcrt` 锁，超时终止）→ SESSION_BUSY，释放后健康操作继续 | 2 passed |
| 17 | `test_change_during_submit_detected[manifest/snapshot/package/events]` → SESSION_CHANGED，不发布新事件 | 4 passed |
| 18 | `test_event_byte_limit`、`test_history_byte_limit`、`test_event_count_limit` → SESSION_LIMIT_EXCEEDED；`test_non_finite_proposed_value_rejected`（inf）→ SESSION_REQUEST_INVALID | 4 passed |
| 19 | `test_moved_session_keeps_identity_and_continues`（复制会话与同字节包到新位置：session_id/opinion_id/理由保留、幂等重试同 event_id、可追加新评审者、旧会话与包哈希不变） | 1 passed |
| 20 | `test_cli_create_inspect_submit_roundtrip`、`test_cli_submit_rejects_invalid_request_files[duplicate_key/missing_version/unknown_version/preparation]`、`test_cli_inspect_and_submit_on_corrupt_session`（成功退 0；非法退 1 且 code 非敏感；坏历史 inspect 退 0 且 writable=false；默认不泄漏理由/纠正值） | 6 passed |

额外断言未覆盖：真实专家认证、抗完整目录回滚、跨平台原子发布；本矩阵只证明软件边界。

## 4. 每次运行（独立日志与 JUnit，未覆盖）

| 尝试 | 命令 | 退出码 | 终端 | JUnit tests/fail/err/skip | 耗时 |
|---|---|---|---|---|---|
| attempt-01 runtime | `pytest tests/test_review_sessions.py … --junitxml attempt-01-runtime.xml` | 1 | 67 passed, 1 failed, 1 skipped | 69 / 1 / 0 / 1 | 242.94 s（XML 242.85） |
| attempt-02 runtime-fix | 同上 `-k test_second_root_for_same_reviewer_and_material`，新 basetemp | 0 | 1 passed | 1 / 0 / 0 / 0 | 5.40 s（XML 5.37） |
| attempt-03 runtime | 全文件干净重跑，新 basetemp/XML | 0 | 68 passed, 1 skipped | 69 / 0 / 0 / 1 | 245.49 s（XML 245.45） |
| attempt-01 related | `pytest test_review_session_contract test_review_snapshot test_review_preparation test_reviews` | 0 | 197 passed, 1 skipped | 198 / 0 / 0 / 1 | 119.35 s（XML 119.26） |
| attempt-01 full | `pytest`（一次全量） | 0 | 435 passed, 2 skipped | 437 / 0 / 0 / 2 | 645.18 s（XML 645.16） |

`git diff --check` 退出码 0。两处 skip 均为环境性：`test_reparse_events_resource_skipped_without_link_privilege`（本机无建链权限，OSError，未改 ACL、未提权）与 D02 遗留的 `test_real_symlink_rejected_or_skipped`。

**attempt-01 的唯一失败是新增测试的逻辑笔误**：我在人为写入两条同源事件（构造分支）**之后**才提交健康意见，产品正确返回 `SESSION_HISTORY_INVALID`（坏历史阻写）。改为先提交健康独立意见、再注入分支，并断言该意见仍在视图中可审计；未改核心、未放宽任何错误码。attempt-02 定向验证，attempt-03 为全文件干净结果。

## 5. 真实空白安全检查（只读真实输入，脚本输出仅哈希/计数/布尔）

脚本 `real_blank_check.py`（本地运行，退出码 0，3.34 秒）；`real-blank-check.json`：

- 会话 `reviewsession_de0706fb28ac22aef548d3eb`；**0 意见、0 事件**；目标 **757**（source_annotation 188 + candidate 541 + anomaly 28），全部 `pending`，`issues=[]`，`writable=true`（仅指工程可接收明确意见）；`medical_review=unreviewed`、`release_allowed=false`。
- 副本 7 文件字节与原快照相同；包 `50742f7c…f7786d` / 153943 字节与执行单一致。
- 包目录与准备目录执行前后文件集合/大小/SHA256 全部相同；未 submit 任何真实意见，未通过 CLI 打印真实 view，未输出复制正文。真实会话含原文副本，仅留在忽略的 `artifacts/`。

## 6. 结束态核对

- 341 份 Schema（11 个契约集：t01 33、t02 74、t02p 52、tcm 71、review 18、correction 18、owned-analysis 19、learning 26、coverage 9、review-preparation 10、review-session 11）哈希 **341/341** 相符。
- 未改哈希：`review_sessions.py` `cf4295cb…`、`review_snapshot.py` `ac3e88af…`、`domain/review_session.py` `b49ea90b…`、设计 `3c82ac5d…`。
- 源码差异仅 `analysis/cli.py`（+72/−0）与 `analysis/README.md`（+30/−0）；`git status` 相对基线只多这两项（外加本 RESULT 与状态文件）。未改 `src/medicine_agent/cli.py`、`contracts.py`、其他源码/tests/Schema/设计。
- 测试文件相对编辑前副本 **769 行插入、0 删除**；原 4 项测试与既有辅助函数（`session` fixture、`request`）源码未变，新内容全部追加。
- 受保护输入（包目录 4 文件、准备目录 7 文件）与 D01 基线逐文件比对无差异。
- 未 commit/push、未联网、未装依赖、未 OCR/蒸馏/模型调用、未读本地模型配置。

## 7. 运行证据（节选）

| 文件 | SHA256 |
|---|---|
| `attempt-01-runtime.xml` / `.log` | `dc4f5678…5e832` / `561a1ac8…20686f` |
| `attempt-02-runtime-fix.xml` / `.log` | `976d5922…6aa6c` / `5fa0eabc…64c3d64` |
| `attempt-03-runtime.xml` / `.log` | `0194b72a…9b7ac` / `da95c4cb…5a70923` |
| `attempt-01-related.xml` / `.log` | `968c6bcb…7e616` / `b02e47b0…d8ee4` |
| `attempt-01-full.xml` / `.log` | `a5f3dcba…6bdd` / `b6b67d27…e9145866` |
| `analysis_cli.before.py` | `c96700f7…7c4912d` |
| `test_review_sessions.before.py` | `656688bc…32767d1` |
| `README.before.md` | `2cc00474…90b6fe9` |
| `real-blank-check.json` / `.log` | `33ffd968…f671a770` / `b9a3c840…897739c4d` |
| `real_blank_check.py` / `verify_d04.py` | `f473d113…08a3b4a3` / `1978313d…cccedd7d` |

完整哈希见 `summary.json`；`runtime-tmp*/`、`related-tmp/`、`full-tmp/`、`real-cache/`、`real-session/` 为忽略目录内的临时产物。

## 8. skip / not_checked 与平台边界

- skip 2：真实建链权限不足（本次 1 项 + D02 遗留 1 项），均未改 ACL/提权，不以桩冒充实链验收。
- 平台边界：Windows 协作创建锁与 `os.link` 原子发布依赖目标文件系统支持；跨平台原子性、真实专家认证、抗完整目录恶意回滚不在本单范围。
- not_checked：发行构建、独立 wheel 运行、完整 B12 验收、`NEXT` 推进。

## 9. 结论

`D04 executed_pending_review`：三个 CLI 已按固定接入点追加（旧命令零改动），20 行运行时矩阵与真实空白 0 意见检查通过，全量 435 passed/2 skipped，341 份 Schema 与受保护输入未变。**B12 仍未整体验收**，等 Codex 核验。

## Codex核验（2026-10-25）

D04 verified（运行时/CLI软件检查点通过，不等于完整B12）。独立核对8项watched哈希、运行证据清单（除错误自哈希项外全部匹配）、5份JUnit及失败定位、全部原测试/辅助函数源码、CLI纯追加diff、原包与准备目录哈希，均符合执行范围。全量435 passed/2 skipped为保留的执行日志，不冒称Codex重跑全量。

真实新会话文件在沙箱下拒绝读取，已经工具权限审核以只读脚本核验：manifest完整哈希/会话稳定ID正确，0事件、7副本哈希相同、unreviewed且release_allowed=false；未修改文件/权限、未输出正文。脚本的757目标/0意见证据和真实输入未变相符。链接权限skip与跨平台/外部可信身份/抗一致目录回滚限制保留。

证据瑕疵：summary.json的run_files列入其自身旧哈希，必然不能作为该文件校验依据。当前文件独立SHA256为d9781325594b05ad8c0000b11f728083cbd397ab62e3b57e1d101d5f253e64db；其他证据哈希均匹配。原文件不覆盖，下一轮改为摘要写完后生成独立文件清单且不包含清单自身，避免自引用。

剩余验证：D04的3项限额测试实际覆盖inspect读入分支，未单独命中submit发布前的大小/累计字节/事件数上限。由D05补3项有明确预期的提交边界测试，不改核心或Schema；同时进行本地离线发行、独立wheel/API/CLI、文档引用和受保护路径检查。D04现有通过结论仅限其实际覆盖范围；B12继续in_progress，不提前归档或推进NEXT。
