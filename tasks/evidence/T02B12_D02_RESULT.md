# T02-B12-D02 执行结果（非敏感）

> 2026-10-24；状态：**executed_pending_review，待 Codex 核验**。
> 执行单：tasks/evidence/T02B12_D02_EXECUTION.md（未改动）。本文件只含计数、哈希、测试名与错误码，不含原文、候选正文、理由或密钥。
> 运行目录：`artifacts/b12-d02/b12-d02-20261024T194156-6c16/`（新建，未覆盖旧目录）。

## 1. 基线

- HEAD `773d7d8cfef73cd89a893d375c44ef3cb37d8a9c`；Python 3.13.15；pytest 9.1.1。
- 基线 SHA256：核心 `src/medicine_agent/analysis/review_snapshot.py` = `ac3e88af…3937a72`；测试 `tests/test_review_snapshot.py` = `667dba65…ccbbce`；设计 `T02B12_REVIEW_SESSION_DESIGN.md` = `b0851f8d…dcf5153`。
- 基线 `git status --short`（15 项，含 Codex 已有改动）：`M md/18-…`、`M tasks/{CURRENT,HANDOFF,NEXT,ROADMAP,STATE}.md`、`M tasks/overall/{决策记录,技术与能力总表}.md`、`?? src/medicine_agent/analysis/review_snapshot.py`、`?? tasks/evidence/{T02B12_D01_EXECUTION,T02B12_D01_RESULT,T02B12_D02_EXECUTION,T02B12_REVIEW_SESSION_DESIGN,T02B12_SNAPSHOT_CORE_PROGRESS}.md`、`?? tests/test_review_snapshot.py`。未清理、未回滚。
- 编辑前原文件副本：`test_review_snapshot.before.py`（SHA256 `667dba65…ccbbce`，与基线一致）。

## 2. 20 行合成矩阵

新增 53 个用例；原有 5 个用例未改动（见第 6 节）。

| # | 用例（参数化展开） | 结果 |
|---|---|---|
| 1 | `test_resource_shape_invalid[missing_body]`、`[extra_file]`、`[body_is_directory]` → SNAPSHOT_RESOURCES_INVALID | 3 passed |
| 2 | `test_paths_must_be_disjoint[snapshot_is_packages]`、`[workspace_in_snapshot]`、`[workspace_in_packages]`、`[workspace_is_file]` → SNAPSHOT_PATH_INVALID，且未在快照/包目录内新建缓存，两侧哈希不变 | 4 passed |
| 3 | `test_body_byte_change_without_manifest` → SNAPSHOT_HASH_MISMATCH | 1 passed |
| 4 | `test_declared_path_never_opened[parent]`、`[absolute]`、`[backslash]` → SNAPSHOT_RESOURCES_INVALID，`_read_file` 只读到 7 个已知快照文件，声明的外部路径从未被打开 | 3 passed |
| 5 | `test_duplicate_json_keys_rejected[manifest/preparation]`、`test_invalid_utf8_rejected[…]`、`test_non_object_top_level_rejected[…]` → 均为 SNAPSHOT_JSON_INVALID，无 raw ValidationError/UnboundLocalError | 6 passed |
| 6 | `test_non_finite_number_rejected[NaN]`、`[Infinity]`、`[1e999]`（额外键，解析阶段先拒绝）→ SNAPSHOT_JSON_INVALID | 3 passed |
| 7 | `test_version_must_be_supported[manifest/report]×[unsupported/missing]` → SNAPSHOT_VERSION_UNSUPPORTED | 4 passed |
| 8 | `test_report_id_not_recomputed`（同步改 manifest ID 与正文哈希，不按算法重算）→ SNAPSHOT_ID_MISMATCH | 1 passed |
| 9 | `test_non_complete_status_rejected[partial]`、`[empty]`（report 与 manifest 同步改并重算 ID）→ SNAPSHOT_STATUS_UNSUPPORTED | 2 passed |
| 10 | `test_non_empty_worksheet_rejected[reviewer/decision/reason]×[sources/candidates/anomalies]` → SNAPSHOT_WORKSHEET_NOT_EMPTY | 9 passed |
| 11 | `test_selected_package_missing`、`test_packages_directory_missing` → SNAPSHOT_SOURCE_UNAVAILABLE | 2 passed |
| 12 | `test_source_bytes_changed_after_export`、`test_coverage_archive_hash_tampered`（改 address.archive_sha256 并重算 ID）→ SNAPSHOT_SOURCE_MISMATCH | 2 passed |
| 13 | `test_self_consistent_tampering_fails_rebuild[candidate_item_id]`、`[evidence_text]`、`[anomaly_reason]`、`[coverage_manifest_sha]`（各自重算报告 ID 与 manifest 哈希）→ 均 SNAPSHOT_SOURCE_MISMATCH | 4 passed |
| 14 | `test_presentation_markdown_tampered`（改 Markdown 并更新 manifest 哈希）→ SNAPSHOT_PRESENTATION_MISMATCH | 1 passed |
| 15 | `test_source_append_during_rebuild_detected`（prepare 返回前追加源包字节）→ SNAPSHOT_CHANGED | 1 passed |
| 16 | `test_snapshot_change_after_rebuild_detected`（prepare 返回后改快照 Markdown 字节）→ SNAPSHOT_CHANGED | 1 passed |
| 17 | `test_single_file_limit`、`test_snapshot_total_limit`（monkeypatch 上限）→ SNAPSHOT_LIMIT_EXCEEDED，未创建大文件 | 2 passed |
| 18 | `test_real_symlink_rejected_or_skipped` → **skipped**（本机建链失败：OSError；未改 ACL、未提权）；`test_reparse_branch_via_lstat_stub` → SNAPSHOT_PATH_INVALID（受控 lstat 桩，只补 reparse 分支，不当作真实链接验收） | 1 skipped + 1 passed |
| 19 | `test_moved_snapshot_and_package_keep_identity`（新位置、不嵌套 workspace）→ 成功、snapshot_id 相同、输入哈希不变、仍 unreviewed/release_allowed=false | 1 passed |
| 20 | `test_schema_failure_does_not_leak_injected_content` → SNAPSHOT_SCHEMA_INVALID，注入标记未出现在 message 与格式化 traceback | 1 passed |

汇总：新增 53 例 = 52 passed + 1 skipped，0 failed。

## 3. 命令与统计（JUnit 与终端汇总交叉一致）

| 命令 | 退出码 | 终端汇总 | JUnit tests/fail/err/skip | 耗时 |
|---|---|---|---|---|
| ① 仅快照文件（首轮） | 1 | 3 failed, 54 passed, 1 skipped | —（被②的干净重跑覆盖） | 76.25 s |
| ② `-k test_declared_path_never_opened`（首轮） | 1 | 3 failed | — | 4.47 s |
| ③ 同 ② 修复后 | 0 | 3 passed | — | 4.26 s |
| ④ 仅快照文件（干净） | 0 | 57 passed, 1 skipped | 58 / 0 / 0 / 1 | 76.12 s（XML 76.04） |
| ⑤ 既有相关：`tests/test_review_preparation.py tests/test_reviews.py` | 0 | 38 passed | 38 / 0 / 0 / 0 | 42.45 s（XML 42.41） |
| ⑥ 全量 | 0 | 265 passed, 1 skipped | 266 / 0 / 0 / 1 | 430.44 s（XML 430.42） |

`git diff --check` 退出码 0（仅 Git 的 CRLF 提示，无内容错误）。

## 4. 首轮 3 个失败的定位与处理

- 失败全部在**我新加的断言**中，产品行为正确：三次调用都按要求抛出 `SNAPSHOT_RESOURCES_INVALID`，`load_preparation_snapshot` 未放行。
- 断言错误一：我写 `reads == []`，误以为 manifest 键集校验发生在读取快照文件之前；实际核心先读取 7 个已知快照文件（6 份正文 + manifest），再校验 `manifest.files` 键集——这正是设计“不按未知 manifest 路径读取”的预期顺序。改为断言 7 次读取全部落在快照目录内、且外部 `outside.txt` 从未被打开。
- 断言错误二：同一次修复里我把期望写成 6 个文件，实际为 7 个（漏算 manifest.json），改为 7。
- 处理范围：只改我新增的测试代码；核心、设计、执行单、既有 5 个用例均未改动（核心哈希仍为 `ac3e88af…`）。未因失败放宽任何期望错误码。
- 保留记录：①②两次失败输出见本文件第 3 节与终端日志上下文；②③两次运行共用 `retry-tmp`，首轮 JUnit 被干净重跑覆盖，失败计数以终端汇总为准。

## 5. 结束态核对

- 28 份 Schema（review-preparation 10 + review 18）存在且 SHA256 全相符：28/28，无缺失、无篡改。
- 受保护输入：包 `bundle_a7c24a2b…medpkg` 153943 字节、SHA256 `50742f7c…f7786d`；包目录 4 文件、B11 准备目录 7 文件，与 D01 在本次执行前记录的基线（`artifacts/b12-d01/b12-d01-20261024T192606-b6ad/protected-inputs-baseline.json`）逐文件大小与哈希比对：**无差异**。
- 核心与设计哈希未变：`ac3e88af…3937a72`、`b0851f8d…dcf5153`；`src` 下无被修改的受版本控制文件（`git status` 无 `M src/…`）。
- 测试文件：相对编辑前副本 **376 行插入、0 行删除**；原 5 个用例字节未变（编辑前副本哈希等于基线哈希）。差异摘要由 `git diff --no-index` 得出，供 Codex 核验。
- 新增/修改文件与基线 `git status` 完全一致：无新增越界文件；D02 只写 `tests/test_review_snapshot.py`、本 RESULT、三份任务状态入口及本运行目录。
- 未 commit/push、未联网、未安装依赖、未 OCR/蒸馏、未调用模型、未读本地模型配置、未重跑真实快照、未解包真实材料。

## 6. 运行目录文件与哈希

| 文件 | 字节 | SHA256 |
|---|---|---|
| `snapshot.xml` | 7347 | `8404ea239be488d875b89b7425650b0f2796dc4f8309f0cf8379990093a39fb4` |
| `related.xml` | 5115 | `8db6bd7e1345763dece0ab8dfa2ab5b66731cdb8830ab8cb279050b61b49605d` |
| `full.xml` | 34832 | `ddba56f5597c1d2c6dde4672f2e91b1ce4abfe11805e2a18f60a00ed05a4e2ba` |
| `summary.json` | 2322 | `5f649003a959b3426a2ff67c1c5bdb6d5d11f771840c07aba3dff3b8f29e6af6` |
| `protected-inputs-compare.json` | 459 | `a525a36da4907d80fb1b0e88a80a705a6db1c6153c59e61c88039dadcca40f93` |
| `summarize.py` | 3183 | `db2eb6d344966955ea003edebdb6d1179977d52c6586302add6278df1f63f184` |
| `compare_protected.py` | 2656 | `8af641a6d70d2fb79950d356314e7d78f461fb21a923e570027645e0576f6dc5` |
| `test_review_snapshot.before.py` | 3623 | `667dba650bcbf074892acbcbba1f28fb3350cecfe8f89e2acb9567bcc8ccbbce` |

`snapshot-tmp/`、`related-tmp/`、`full-tmp/`、`retry-tmp/` 为 pytest 临时目录，保留在忽略目录内。

## 7. skip / not_checked

- skip 1 项：`test_real_symlink_rejected_or_skipped`，原因“link creation unavailable in this environment: OSError”（本机无建链权限；按要求不建 ACL、不提权）。reparse 分支由受控 lstat 桩覆盖，不宣称真实链接验收。
- not_checked：无其他。真实快照按执行单不重跑。

## 8. 结论

`D02 executed_pending_review`：固定矩阵已补齐并全部通过（52 passed + 1 环境性 skip），定向、相关与全量回归均通过，受保护输入与核心/设计未变。快照核心仍**不能**写“已验收”——等 Codex 核验测试文件差异、JUnit 与本摘要后判定。

## Codex核验（2026-10-24）

D02 verified（本子步骤done，快照核心工程检查点通过）。独立核对8份运行文件的大小/SHA256、summary中全部watched哈希、三份JUnit数量、受保护目录文件大小/哈希，以及编辑前副本中全部既有函数源码未改变，均相符。原全量证据为265 passed/1 skipped，不宣称Codex重跑了全量。

修正一项测试覆盖：DeepSeek的test_reparse_branch_via_lstat_stub原先返回S_IFLNK，仅覆盖symlink谓词，不能支持“reparse属性分支覆盖”的叙述。Codex改为普通文件模式+st_file_attributes=0x400，针对该测试及3项manifest路径用例复验：4 passed,54 deselected（6.27秒）。核心未变。真实链接仍因权限不足skip，桩通过不等于真实Windows junction验收。

接受新断言修正：先读取7个固定白名单文件再拒绝未知manifest键，符合设计。首轮失败JUnit/原始终端日志未留存于运行目录，只有RESULT自述；这是证据保留缺口，不能独立核实失败过程，后续执行单必须为每次尝试使用独立日志/XML，禁止覆盖。最终通过的实际测试代码、JUnit及哈希足以支持本检查点；没有发现放宽产品错误码或修改核心。

B12整体未完成，医学与发布门不变；Codex接着冻结会话数据契约，未自动进入NEXT。
