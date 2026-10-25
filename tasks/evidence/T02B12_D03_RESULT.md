# T02-B12-D03 执行结果（非敏感）

> 2026-10-24；状态：**executed_pending_review，待 Codex 核验**。
> 执行单：tasks/evidence/T02B12_D03_EXECUTION.md（未改动）。本文件只含计数、哈希、测试名与错误码。
> 运行目录：`artifacts/b12-d03/b12-d03-20261024T200634-26d2/`（新建，未覆盖旧目录；`schemas/review-session/` 执行前不存在）。

## 1. 基线

- HEAD `773d7d8cfef73cd89a893d375c44ef3cb37d8a9c`；Python 3.13.15；pytest 9.1.1；基线 `git status --short` 20 行（Codex 已有未提交工作，未清理）。
- 基线 SHA256：`domain/review_session.py` `b49ea90b…a445d16`；`analysis/review_snapshot.py` `ac3e88af…3937a72`；`T02B12_REVIEW_SESSION_DESIGN.md` `f3daea35…d840fab`；`contracts.py` `15fd7033…a4a285`；`cli.py` `d3856cbb…89cf5a2`；`tests/test_review_session_contract.py` `f5c2ded1…9b2ceee`。
- 编辑前副本已保存：`contracts.before.py`、`cli.before.py`、`test_review_session_contract.before.py`（后者哈希等于基线）。

## 2. 四处接入与 CLI 差异

`git diff --numstat`：`contracts.py` 6 插入 / 3 删除，`cli.py` 1 插入 / 1 删除——严格等于执行单规定的接入点，无其他改动：

1. `export_schemas` 的 contract_set 校验集合追加 `'review-session'`；
2. 新增分支 `if contract_set == 'review-session': from …review_session import REVIEW_SESSION_MODELS; common_models = REVIEW_SESSION_MODELS`（直接赋值，未拼 `COMMON_MODELS`，嵌套依赖走 `$defs`）；
3. 跳过 Skill 导出的管理契约集合追加 `'review-session'`；
4. `contract_version` 映射追加 `'review-session': '0.1.0'`；
5. `cli.py` 仅 `--contract-set` 的 choices 追加 `'review-session'`（未动默认值、命令或错误处理）。

## 3. Schema 导出

命令：`.venv/Scripts/python.exe -m medicine_agent.cli export-schemas --contract-set review-session --output-dir schemas/review-session`（退出码 0，0.73 秒，`PYTHONDONTWRITEBYTECODE=1`）。

生成 12 个文件（11 份 `common/<模型>.schema.json` + `schema-index.json`），无 `skills/`；index 的 `contract_set=review-session`、`contract_version=0.1.0`，`files` 恰为 11 项且哈希相符。

| 文件 | SHA256 |
|---|---|
| `schema-index.json` | `e9d9195afb5cfcd0098a6707a0003f99822d47c11228b786045f08d56de2dae0` |
| `common/SessionSnapshotBinding.schema.json` | `d2a4b197709ebc3f12e125c5d68a16ba4eba9a3265ff10e14be819ff3ad4400f` |
| `common/SessionReviewer.schema.json` | `01958e1fd048be55ae8cda1f909a37503e11aff7a507fc382760711477b49561` |
| `common/SessionTarget.schema.json` | `c5a96fb9cbd6b4518ea421016bca9f664c81167f9d2bd60d3ed0280a074a9851` |
| `common/SessionOpinion.schema.json` | `538467a2f17a9eb5cecac434a888d6c42e8c3f5fef21bcfc5cb68df1a6faaf95` |
| `common/SessionSubmission.schema.json` | `ef62979413ae363e1e8e178b32ee5e9d397d74432658776b8483d637006f4606` |
| `common/ReviewSessionManifest.schema.json` | `7e6eb57212ac440c16f6c61446aa64d650a62b5c4d43636a101970ab6dcc7ee0` |
| `common/SessionEvent.schema.json` | `2d03f326820fa719d4eebf7873388029b4b7429d98b0148dcd510d268d671762` |
| `common/SessionOpinionRecord.schema.json` | `cbf3370e524f46fac7022637f7a04d8a247d1f509ab5862b08f73f072a048274` |
| `common/SessionIssue.schema.json` | `b160b324159c32476ba5ddd23d972e15c8e934998bbe14222811ca9768d592db` |
| `common/TargetReviewSummary.schema.json` | `0eeda4329ffe8adde4c08508332d5becc78b58c08b23286d015b06d2489d8676` |
| `common/ReviewSessionView.schema.json` | `84aa766d86d5abd0ac7f341ca583fb5ec2821f032ac8afe02538ea24daa0bd7e` |

## 4. 14 行矩阵（新增 95 例，原 7 例未改）

| # | 用例 | 结果 |
|---|---|---|
| 1 | `test_reviewer_id_rejects_invalid_values[7]`、`test_reviewer_id_normalization_cannot_create_a_second_voter`、`test_reviewer_display_and_role_must_be_nonblank[2]`、`test_reviewer_identity_status_cannot_be_authenticated` | 11 passed |
| 2 | `test_material_identity_matches_kind[5]`、`test_candidate_requires_review_target_and_others_forbid_it`、`test_three_material_kinds_round_trip` | 7 passed |
| 3 | `test_four_decisions_with_reason_are_kept[4]`、`test_unknown_decision_and_bad_reason_rejected[3]` | 7 passed |
| 4 | `test_non_revise_decision_cannot_carry_proposed_value[3×2]`、`test_anomaly_cannot_carry_proposed_value`、`test_source_correction_must_be_nonblank_text[3]`、`test_revision_values_round_trip_and_may_be_absent` | 11 passed |
| 5 | `test_expected_previous_id_must_be_an_opinion_id`、`test_opinion_index_rejects_non_integer[-1/True/'0'/1.5]`、`test_opinion_index_zero_accepted` | 6 passed |
| 6 | `test_submission_id_rejects_invalid_values[4]`、`test_submission_opinion_list_bounds`、`test_batch_rejects_duplicate_material_or_two_snapshots[2]`、`test_batch_accepts_distinct_materials_of_one_snapshot` | 8 passed |
| 7 | `test_binding_resource_set_is_exact[missing/extra/wrong_name/manifest_mismatch]`、`test_source_archives_must_be_plain_medpkg_names[4]`、`test_binding_round_trips_without_touching_files` | 9 passed |
| 8 | `test_event_and_record_require_utc[naive/+8]`、`test_utc_timestamps_round_trip_through_json`、`test_opinion_record_is_a_derived_projection` | 4 passed |
| 9 | `test_manifest_medical_boundaries_are_fixed[3]`、`test_view_medical_boundaries_are_fixed[3]`、`test_manifest_defaults_stay_unreviewed` | 7 passed |
| 10 | `test_agreement_cannot_be_marked_awaiting_adjudication`、`test_summary_rejects_duplicate_and_bad_counts`、`test_disagreement_stays_awaiting_adjudication` | 3 passed |
| 11 | `test_invalid_history_view_cannot_be_writable[issues/history_invalid]`、`test_clean_view_can_be_writable` | 3 passed |
| 12 | `test_unknown_field_rejected[11 模型]`、`test_explicit_unknown_version_rejected[manifest/event/submission/view]`、`test_python_construction_defaults_version`、`test_frozen_model_tuple_has_eleven_entries` | 17 passed |
| 13 | `test_api_export_matches_repository_snapshot`（11 项、无 skills、逐字节等于 `schemas/review-session`） | 1 passed |
| 14 | `test_cli_export_and_legacy_contract_sets_unchanged`（CLI 结果 = API 结果；10 个旧契约逐字节等于仓库旧快照） | 1 passed |

全部为结构/跨字段检查；未做来源存在性、内容 ID 生成或历史链校验，这些仍是运行时职责。

## 5. 每次运行（独立日志与 JUnit，未覆盖）

| 尝试 | 命令 | 退出码 | 终端 | JUnit tests/fail/err/skip | 耗时 |
|---|---|---|---|---|---|
| attempt-01 contract | `pytest tests/test_review_session_contract.py … --junitxml attempt-01-contract.xml` | 1 | 11 failed, 91 passed | 102 / 11 / 0 / 0 | 3.30 s（XML 3.22） |
| attempt-02 contract | 同上，新 basetemp 与 `attempt-02-contract.xml` | 0 | 102 passed | 102 / 0 / 0 / 0 | 2.79 s（XML 2.76） |
| attempt-01 related | `pytest tests/test_contracts_and_runs.py tests/test_reviews.py tests/test_review_preparation.py …` | 0 | 43 passed | 43 / 0 / 0 / 0 | 42.63 s（XML 42.60） |

`git diff --check` 退出码 0（仅 Git 的 CRLF 提示）。

**attempt-01 的 11 个失败**：全部来自我新增的 `test_unknown_field_rejected` 参数化写错——`parametrize` 传了字典的键（模型类本身）而不是 (模型, 样本) 对，调用 `model.model_dump()` 报 `TypeError: missing 1 required positional argument: 'self'`。属新增测试自身笔误，未触及模型；改为按 `(model, value)` 参数化后 attempt-02 全通过。同时把 `record.model_fields` 改为 `type(record).model_fields` 消除 Pydantic 2.11 弃用警告。attempt-01 的 log/XML 均保留，未被覆盖。

## 6. 结束态核对

- 新契约 11 份 Schema 哈希 11/11 相符；旧 10 个契约共 330 份 Schema 文件哈希全部相符（t01 33、t02 74、t02p 52、tcm 71、review 18、correction 18、owned-analysis 19、learning 26、coverage 9、review-preparation 10），无缺失、无篡改。
- 旧契约字节对照：矩阵第 14 行用 API 把 10 个旧契约导出到新临时目录，与仓库旧快照（含 schema-index.json）逐字节相同；`git status` 下 `schemas/` 未出现任何 `M` 项。
- 未改文件哈希不变：`review_session.py` `b49ea90b…`、`review_snapshot.py` `ac3e88af…`、设计 `f3daea35…`。
- 源码变化严格限于 `contracts.py`（6/3）与 `cli.py`（1/1）；未改模型、旧 tests、旧 Schema、设计、执行单、既有 RESULT、md/docs/log/config/pdfs/注册表。
- 测试文件：相对编辑前副本 **424 行插入、1 行删除**，唯一删除是 import 行被替换为含新符号的一行；原 7 个用例与 4 个原辅助函数（`reviewer`/`target`/`opinion`/`binding`）源码未变，新内容全部追加在文件末尾。Codex 可用 `test_review_session_contract.before.py` 直接比对。
- 受保护输入：包 153943 字节 / `50742f7c…f7786d`，包目录 4 文件、准备目录 7 文件，与 D01 基线逐文件比对无差异。
- 未 commit/push、未联网、未装依赖、未 OCR/蒸馏/模型调用、未读本地模型配置、未运行真实快照、未解包真实材料；按执行单未跑全量。

## 7. skip / not_checked

- skip：无。异常：仅 attempt-01 的自身测试笔误（已保留证据）。
- not_checked：会话运行时（创建/读取/提交、锁与批事务、历史与幂等、视图、业务 CLI、迁移）未实现也未验证；Schema 与结构契约通过不代表原包绑定、内容 ID、真实独立专家或医学确认。

## 8. 运行证据

| 文件 | SHA256 |
|---|---|
| `attempt-01-contract.log` | `6a2279f60a2b59f8521e5d0832fb08fae2e5dbc352ac5e9a717879452f6b4371` |
| `attempt-01-contract.xml` | `e58bdb731f2465e67b84ffd9bdbdfabeef329ac346da4bdcdf23ea3065fdb670` |
| `attempt-02-contract.log` | `3bc4502958b930fd28437ee39af0b4f1a8c3d6c881b2123ac0552396789e66f5` |
| `attempt-02-contract.xml` | `70d8149714f1efd118bb178e4014c6a217dd09cfb7e24697b2de141f42a48d05` |
| `attempt-01-related.log` | `37874f8bcc318d1bea8207b811a7f5427351e9b84533a0755e25962769ede78d` |
| `attempt-01-related.xml` | `d7e401da9d75a6ec11e62a9892219dd40319d8670839c075fd9aeba8e6f2914e` |
| `contracts.before.py` | `15fd703390179ca54620e0262c48867cd367cfbb92139f6acade7ae0a2a4a285` |
| `cli.before.py` | `d3856cbb7dc1b548660871930062cd8498c75b89218618a3cf42c441929cf5a2` |
| `test_review_session_contract.before.py` | `f5c2ded1a2a2d8b719ae70dcad2de7920c396e3ae6a54ad147be5ea789b2ceee` |
| `verify_d03.py` | `70cff2669ab34ed8e96573fd132a8bec992109ccacbcd3f6c04ead8c0f457dd3` |

`contract-tmp/`、`contract-tmp-02/`、`related-tmp/` 为 pytest 临时目录，保留在忽略目录内；`summary.json` 汇总上述统计。

## 9. 结论

`D03 executed_pending_review`：review-session/0.1.0 已按四处固定接入点导出 12 个文件，14 行矩阵全部通过（102 passed），旧 10 契约逐字节未变、受保护输入未变。**不能据此声称会话功能、运行时或医学门通过**，等 Codex 核验。

## Codex核验（2026-10-24）

D03 verified（子步骤done）。独立核对summary的所有watched哈希、10份运行证据哈希、两轮contract及related JUnit、编辑前全部既有函数源码，以及341份Schema索引哈希（旧330+新11），均相符；源包目录和准备目录逐文件仍与基线一致。源码diff仅规定的导出分派和CLI choices，未变更既有包/医学契约。

首轮11项失败日志/XML实际保留，均为新增测试把模型类误当实例的参数化错误；修正后102 passed和相关43 passed可信，未见放宽模型或旧测试。Codex不重复运行已通过的整套；本次没有全量或运行时验收。会话Schema工程检查点通过，真实会话读写等仍待实现。

用户新增全项目约束已同步：现有数据包结构为默认兼容基线，推理/编排变化优先包外；仅必要且兼容扩展无法解决的事实表达/完整性问题才版本化改结构，需旧包兼容、迁移/回滚和验收依据。此原则不把实验协议冒称正式包v0。
