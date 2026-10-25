# T02-B12-D01 执行结果摘要（非敏感）

> 2026-10-24；状态：**executed_pending_review，待 Codex 核验**。
> 执行单：tasks/evidence/T02B12_D01_EXECUTION.md（未改动）。本文件不含原文、候选正文、理由或密钥。

## 1. 基线与运行目录

- HEAD `773d7d8cfef73cd89a893d375c44ef3cb37d8a9c`；`git status --short` 为三份任务文档已修改加执行单未跟踪（与执行单预期一致，未清理、未回滚）。
- `git diff --stat`：CURRENT +12/−2、HANDOFF +8、STATE +12/−2。
- Python 3.13.15（`.venv/Scripts/python.exe`），pytest 9.1.1，`PYTHONDONTWRITEBYTECODE=1`。
- 本次唯一运行目录：`artifacts/b12-d01/b12-d01-20261024T192606-b6ad/`（新建，未覆盖既有目录）。
- 步骤1 记录：`step1-baseline.log`、`protected-inputs-baseline.json`。

基线受保护输入：包 153943 字节、SHA256 `50742f7c32f7178c562ba2927ae070feac1e82696f7f86792157090fe2f7786d`（与执行单一致）；包目录顶层 4 个文件；准备目录 7 个文件。

## 2. 逐项核查结果（15 条检查，0 失败）

| # | 项目 | 结果 |
|---|---|---|
| 1 | 目录恰为 7 个普通文件、无子目录/链接/reparse point、每个条目解析后仍在准备目录内 | passed |
| 2 | `manifest.files` 恰为 6 份正文；键均为纯文件名（无 `/`、`\`、`:`、`..`、绝对路径）；逐文件实际 SHA256 等于声明 | passed |
| 2b | `manifest.json`、`preparation.json` 用 `object_pairs_hook` 显式拒绝重复键 | passed（未触发） |
| 3 | `ReviewPreparationReport`/`ReviewPreparationExport` 类型校验；version 0.1.0、status complete、preparation_id 一致、medical_review=unreviewed、release_allowed=false | passed |
| 4 | 按 prepare 同法重算 `stable_id('preparation', model_dump(exclude={'preparation_id'}))` | passed（等于 `preparation_718bf6c856acd871970f3eea`） |
| 5 | 数组实测计数：sources 188、candidates 541、node 63、fact 478、stated 345、inferred 133、gap 27、rejected_candidate 1、issues 0 | passed |
| 5b | `report.counts` 映射后与数组实测一致 | passed |
| 6 | 全部 source/candidate/anomaly 的 worksheet.reviewer/decision/reason 为 null、submitted=false（只统计字段名与数量） | passed（28 个 anomaly，计 0 非空） |
| 6b | review_records 长度 0；全部候选 user_review_state=unreviewed；异常 writable_review_target 全为 false | passed |
| 7 | 两个 Schema 目录：schema-index 列出的 28 份文件（review-preparation 10 + review 18）全部存在且 SHA256 相符 | passed（28/28） |
| 8 | 步骤1 与步骤2 结束时包目录与准备目录的文件集合、大小、哈希全部不变 | passed |

明细见 `verify-check.json`（每项 expected/actual/status，只有计数、哈希与字段名）。

## 3. 代码位置表（只记现状，未编码）

所有行号经本轮读取核对；`tcm.py` 实际路径为 `src/medicine_agent/packages/tcm.py`（执行单写作 `analysis/packages/tcm.py`，见第 7 节）。

| 检查项 | 现有生成/校验符号及位置 | 是否已有准备目录读入入口 | 后续设计待定点 |
|---|---|---|---|
| manifest资源集合与路径边界 | 生成 `analysis/review_preparation.py:227`（`files = {p.name: file_sha256(...)}`）、`:229`（写 `manifest.json`）；类型 `domain/review_preparation.py:118-124`；导出目标边界 `analysis/review_preparation.py:217-219`、`:231-233` | 无：仅有导出写入，`src` 内无读取 `preparation.json`/`manifest.json` 的实现（`grep` 确认只有写入与文档说明） | 待 Codex 设计：读入时的资源白名单、越界/链接判定规则 |
| 导出文件哈希 | `domain/ids.py:21 file_sha256`；计算点 `analysis/review_preparation.py:227` | 无 | 待 Codex 设计：读入校验的哈希口径——导出时检查不等于导入校验 |
| Report稳定ID | `domain/ids.py:17 stable_id`；生成点 `analysis/review_preparation.py:143`；同法用于 annotation `:170`、reviewitem `:201`、anomaly `:208`、review `analysis/reviews.py:95` | 无 | 待 Codex 设计：重算时排除字段集合与版本兼容 |
| 来源/材料身份 | 包哈希前后双检 `analysis/review_preparation.py:91-96`；来源哈希写入引文 `:200` 与 `domain/review_preparation.py:44-46`（`PreparationQuote.source_sha256`） | 无 | 待 Codex 设计：材料身份是否需组合包指纹、manifest_sha 与 source_sha256 |
| ReviewTarget定位和fingerprint | 生成 `analysis/reviews.py:127-128`（`build_review_queue`）；校验 `analysis/reviews.py:14-26`（`:24` digest 比对）；模型 `domain/reviews.py:9-22` | 无：目标只能由活的包索引构建 | 待 Codex 设计：脱离包目录后的指纹重验方式；本单该项 not_checked |
| expected_previous_id与意见历史 | `analysis/reviews.py:29-76 read_reviews`（链完整性 `:53-65`）、`:79-101 record_review`（`:91` stale 检查）；合并 `analysis/review_preparation.py:31-63`；字段 `domain/review_preparation.py:61` | 无：读取的是包内 `reviews/`，不是准备目录 | 待 Codex 设计：快照历史与会话历史的衔接、事务粒度 |
| worksheet与ReviewRequest决定差异 | 空表 `domain/review_preparation.py:23-28`（`submitted: Literal[False]`）；正式意见 `domain/reviews.py:25-45`（decision 三值 + reviewer/reason 非空）；队列取值 `analysis/reviews.py:152-154` | 无 | 待 Codex 设计：`unable_to_judge` 与 ReviewRequest 三值的映射与拒绝规则 |
| gap/隔离项的不可写边界 | `domain/review_preparation.py:66-86`（`:78 writable_review_target Literal[False]`，`:80-86` kind 与载荷一致性）；计数分离 `analysis/review_preparation.py:123-124`；不入队列：`build_review_queue` 只遍历节点/字段 `analysis/reviews.py:118-128` | 无 | 待 Codex 设计：gap/隔离项在会话中的只读展示与回指原页入口 |

`src/medicine_agent/packages/tcm.py:13 read_graph`（`_bundle` 中 `analysis/review_preparation.py:172`）负责图谱读取，属包内材料解析，不是准备目录读入。

## 4. 步骤4：固定合成回归

- 命令：见 `step4-pytest.log`；`--basetemp artifacts/b12-d01/b12-d01-20261024T192606-b6ad/pytest-tmp`。
- 退出码 0，耗时 46.13 秒，进度行 38 个点（38 passed，0 failed/error/skip）。
- 注意：`pyproject.toml` 的 `addopts="-q"` 与命令行 `-q` 叠加成 `-qq`，pytest 省略了末尾汇总行，通过数由进度字符计数得出，未重跑。
- 两个测试文件内的 `subprocess` 调用只启动本地 `medicine_agent.cli` 读写临时合成包；项目内无 `conftest.py`（仅 `.uv-cache` 内有第三方文件，不参与收集）。
- `git diff --check` 退出码 0。

## 5. 产物与哈希

| 文件 | 字节 | SHA256 |
|---|---|---|
| `verify_snapshot.py` | 15242 | `e15d2429a016a92acd38f15d98bf8a5c091c69842f9d2c41964efde8407b701d` |
| `protected-inputs-baseline.json` | 2032 | `5fa991b75f84e57f1029059dd6a695b32018ba3bd23da0af831d51c1e096fb3c` |
| `step1-baseline.log` | 661 | `5915907458e4ca8ab88c5b505d4a6122031aa76791f469b3249c50f6ead7be08` |
| `step4-pytest.log` | 311 | `7403a8607ffcaf4be846ac1f75fb654469c82b778e74504f28ca6cbeca7f5665` |
| `verify-check.json` | 4486 | `cb2533176b19347d8850c27ed8d302caf2a231bbd4f86aaa9f8b91089ee8bd73` |
| `verify-recheck.json` | 165 | `d76eb4665b840769e8ff92c92b816af4520f5c0ab425adb92d01591c664820d5` |

`pytest-tmp/` 保留本次测试临时目录（1964 个文件），在 `artifacts/` 下且被 Git 忽略。

## 6. 开始/结束对照与工作区变化

- 包目录与准备目录：步骤1 基线 vs 步骤2 结束、以及 pytest 之后 `--mode recheck`，三次比对均无差异（文件集合、大小、SHA256）。
- 受保护输入未变；未执行 commit/push、未安装依赖、未联网、未 OCR、未蒸馏、未调用模型、未读本地模型配置。
- 本轮对 Git 工作区的新增变化仅为：本文件（`tasks/evidence/T02B12_D01_RESULT.md`）与 STATE/HANDOFF/CURRENT 的进度同步；`src`、`tests`、`schemas`、`md`、`docs`、`log`、`config`、`pdfs`、归档、原包、原准备目录均未改动。

## 7. 与执行单的偏差

1. 执行单列出的 `src/medicine_agent/analysis/packages/tcm.py` 不存在；实际为 `src/medicine_agent/packages/tcm.py`。已按实际路径阅读，未创建任何文件。
2. `-qq` 导致 pytest 汇总行缺失（见第 4 节），通过数由进度点计数，未重跑。

## 8. not_checked 与边界

- **材料来源身份与目标指纹相对源包重验：not_checked**。本单只核对准备目录自身的 manifest 声明哈希与类型字段，未从 `.medpkg` 重算每个目标的 fingerprint，因此 **B12 快照可信校验未完成**，不能据此宣称完成。
- 准备目录**读入校验器仍不存在**（上表 8 行"读入入口"全为无），本单只提供现状位置，不构成实现或设计结论。
- 未做医学评审、未生成意见、未推进 NEXT、未创建 B12 验收归档、未改变 release_allowed 或 medical_review。

## Codex核验结论（2026-10-24）

D01 verified（本子步骤done）；B12整体仍paused，未完成可信快照校验。核验读取实际脚本、JSON和日志，并独立复算manifest正文哈希、Report稳定ID、757份空白模板及受保护输入与基线差异；6份运行证据大小/SHA256全部匹配RESULT，15条检查记录均为true。核对pytest日志38个通过标记和退出码0；未重跑测试。git diff --check通过，跟踪文件变化仅三份任务入口；两份未跟踪文件为执行单与RESULT。

执行偏差处理：packages/tcm.py应相对src/medicine_agent解析，执行单缩写表达不够明确，实际读取src/medicine_agent/packages/tcm.py正确，无需修复；addopts与命令行-q叠加只影响汇总显示，不影响退出码，本次不重跑，后续命令只保留一处-q或明确覆盖addopts。

临时脚本仅用于本次已知健康快照：其manifest键/资源集合检查失败后仍会继续按声明路径读哈希；preparation.json解析异常分支还可能引用未赋值的prep变量。两点未由当前健康输入触发，不影响本次现状核查，但不能复用为正式B12读入校验器。正式实现必须先拒绝非法路径再读取、异常安全且无部分写入，并用合成坏输入验证。无需DeepSeek在D01范围内追加修复。

材料来源身份与目标指纹相对源包重验继续not_checked；不授予医学/发布许可，不推进NEXT。下一步应由Codex制定B12设计和受限实现执行单，当前没有可直接执行的新DeepSeek任务。
