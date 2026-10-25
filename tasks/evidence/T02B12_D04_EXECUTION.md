# T02-B12-D04：会话CLI、运行时固定矩阵与回归

> 2026-10-24；ready，尚未执行。CURRENT子步骤；DeepSeek执行，Codex核验。

## 当前基线与目标

D01—D03已核验。现有.medpkg及旧医学结构保持兼容；会话为包外review-session/0.1.0，不改包。Codex已实现`analysis/review_sessions.py`的create/inspect/submit、逐评审者历史链、整批提交、幂等与只读异常视图；初始4项合成回归通过（最终版15.06秒）。大矩阵、CLI、迁移/并发/故障与全量验收尚未完成。

本单仅做明确CLI映射和测试/验证。不改变历史/事务/医学设计，不改运行时核心；发现产品错误停止交回Codex。会话不能冒称专家认证、临床结论或抗完整目录恶意回滚。

## 启动与允许范围

工作区D:/test/tongyongzhengliu，按AGENTS顺序读取任务入口，再读md第04/09/18章、D-14、B12设计（重点第五/六节）、D03核验段和`T02B12_SESSION_RUNTIME_PROGRESS.md`。读核心/模型、现有analysis/cli.py、初始tests/test_review_sessions.py及已有合成夹具。

只允许修改/新建：

- `src/medicine_agent/analysis/cli.py`：新增下述三个命令与对应早期分派，不改变旧命令；
- `tests/test_review_sessions.py`：保留原4项测试及辅助函数源码，追加新测试/辅助函数与必要import；
- `src/medicine_agent/analysis/README.md`：仅追加三个命令的使用说明/边界及自制输入示例；
- `tasks/evidence/T02B12_D04_RESULT.md`及STATE/CURRENT/HANDOFF的事实进度；
- `artifacts/b12-d04/<唯一新目录>/`：每次日志/XML、脚本/子进程脚本、合成临时数据、真实空白安全检查的新会话/缓存、哈希与摘要。

禁止改核心review_sessions.py、review_snapshot.py、任何domain模型/Schema/注册表、其他源码/tests/设计/执行单/既有证据、md/docs/log/config/pdfs及既有运行目录。不commit/push、联网、装依赖、OCR/蒸馏/模型API/训练，不读本地模型配置。真实正文仅可由本地脚本读写到忽略运行目录，不能进DeepSeek上下文或终端日志。

执行期间双方不并发修改。先记录HEAD/status/diff统计；保存analysis/cli.py、README、初始测试副本；记录核心/模型/设计/341份Schema和受保护真实源目录的名称/大小/SHA256。现有未提交改动不能清理、回滚或覆盖。

## 固定CLI接入

在analysis/cli.add_commands内新增三个平级action，所有路径参数必填(type=Path)，无HOME默认、config参数或模型实例：

1. review-session-create：--preparation-dir、--output-dir、--packages、--workspace。
2. review-session-inspect：--session-dir、--packages、--workspace；可选--include-opinions(store_true)。
3. review-session-submit：--session-dir、--input-file、--packages、--workspace。

在execute的模型配置及旧业务分支之前早期分派这些action，惰性导入ReviewSessionService。只调用已实现API，不通过PackageCatalog/FileLearningService写包。

- create返回manifest.model_dump(mode='json')。
- submit输入通过review_snapshot._read_file(limit=64MiB)与_json_object做严格JSON读入，显式要求version='0.1.0'；解析/读取/版本非法统一AnalysisError('SESSION_REQUEST_INVALID', 固定非敏感消息) from None。API继续验证SessionSubmission；不能直接接收准备表。成功仅返回version、event_id、session_id、submission_id、opinion_count、reviewer_identity='self_declared'、medical_review='unreviewed'、release_allowed=false，不输出理由/纠正值。
- inspect默认返回version、session_id、snapshot_id、writable、opinion_count、target_count、state_counts（按agreement_state统计）、issues（model_dump列表）、reviewer_identity、medical_review、release_allowed。--include-opinions才返回完整ReviewSessionView。默认摘要不含理由或proposed_value；writable=false的inspect仍成功返回0并展示issues，submit失败走既有PlatformError出口。

不修改顶层cli.py、contracts.py或能力注册。README追加示例：固定paths、不覆盖输出、从同一快照取完整target、一名声明评审者填写独立输入、submission_id幂等、expected_previous_id归属本评审者本材料、无法判断/分歧不改医学状态；--include-opinions包含意见正文，不给模型读取真实输出。示例只用自制占位材料。

## 固定运行时验证矩阵

用现有exported/material/session/request夹具，所有故障只注入临时合成材料。必要时生成自洽的manifest/event：按设计content_hash、stable_id重算、保留包装键，不能因只坏哈希而替代更深层验证。每行至少一项，要求分别则参数化。故障注入后记录基线，断言产品调用未改写既有源包/快照/健康事件。

| # | 操作 | 固定预期 |
|---|---|---|
| 1 | create到已存在目录/文件；会话目录与packages/workspace/原准备目录嵌套或相同，分别测试 | 已存在SESSION_EXISTS（独立安全路径）；嵌套SESSION_PATH_INVALID；不覆盖 |
| 2 | 改session.json哈希、缺显式version、未知version、重复键、未知包装键、伪造session_id分别测试 | SESSION_MANIFEST_INVALID；不得回显注入正文 |
| 3 | 重签manifest但改binding中source_archives哈希/准备ID/snapshot_id（类型合法），以及副本正文改字节 | SESSION_SNAPSHOT_INVALID；不继承原认可 |
| 4 | 三类合法材料提交分别成功；不存在material_id、错误snapshot_id、candidate精确ReviewTarget指纹错分别测试 | 合法只存独立事件；非法SESSION_TARGET_INVALID，原包不变 |
| 5 | 批提交一项合法、一项非法目标；一项合法、一项过时前序，分别测试 | 整批拒绝，事件集合/字节无变化，无部分新意见 |
| 6 | 两个声明ID同决定达到agreement；accept/reject分歧；两个revise不同proposed_value分歧；全部unable；一名明确+一名unable | agreement仅意见一致且医学仍未审；分歧awaiting_adjudication；无明确pending；一名明确insufficient_opinions，unable单列 |
| 7 | 同规范化reviewer_id大小写/空白更新；使用别人的opinion_id作前序；旧前序/不存在前序分别测试 | 同人仍一票；错误前序SESSION_STALE_WRITE；不按时间选票 |
| 8 | 同submission_id相同内容重试（包括该人已有后续意见后）；同ID改决定/理由/评审者 | 相同返回原event_id不新增；不同SESSION_SUBMISSION_CONFLICT |
| 9 | 修改事件原文而不改哈希；重复键、未知版本/包装键、文件名与event_id不符、非规范化已落盘payload分别测试 | inspect记录SESSION_EVENT_INVALID；健康原意见可审计；所有目标history_invalid/pending，writable=false；submit SESSION_HISTORY_INVALID |
| 10 | 自洽重签事件但session_id/target不属于当前绑定 | 整事件隔离为SESSION_EVENT_INVALID，不能留半个有效批 |
| 11 | 同评审者同材料构造两个根/分支；前序指向不存在记录；删除被后继引用的事件，分别测试 | SESSION_HISTORY_INVALID，目标history_invalid、不能选异常链头，整个会话不可写；健康独立链意见保留 |
| 12 | 以不同event_id自洽构造同submission_id的两个事件 | issue SESSION_SUBMISSION_CONFLICT，全局history_invalid/pending，不选择新事件覆盖旧事件 |
| 13 | 遗留安全普通.pending-session-event-*.tmp；未知其他文件/子目录；链接或reparse资源（无权限可skip并说明） | 安全临时文件忽略且不自动删除，健康提交可继续；未知/链接资源issue阻写。只用桩时标明不是实链验收 |
| 14 | os.link失败；os.fsync失败；目标事件文件已存在（可直接对静态_publish做合成目标碰撞测试） | SESSION_COMMIT_FAILED，健康文件不覆盖、无可见半事件；只清理本次临时文件，不删除已有目标 |
| 15 | event已原子发布但pending.unlink模拟失败（仅针对本次临时文件） | submit仍成功；遗留临时文件不影响inspect/幂等，不能产生“实际成功却报告失败” |
| 16 | 持锁的独立子进程占用.session-write.lock；create目标侧边锁被独立进程持有 | SESSION_BUSY，无事件/目标覆盖；释放后健康操作可继续。子进程设置超时，只清理自己启动的进程，不删除锁/改ACL |
| 17 | _history或重建后、提交前改变合成会话manifest/快照/源包/事件集合，分别测试 | SESSION_CHANGED；不提交新事件，不以已变状态继续 |
| 18 | 降低MAX_EVENT_BYTES/MAX_HISTORY_BYTES/MAX_EVENTS触发读入或提交上限，分别测试；API传非有限proposed_value | SESSION_LIMIT_EXCEEDED，非有限请求SESSION_REQUEST_INVALID；不造大文件或截断历史 |
| 19 | 复制完整合成会话和同名同字节源包到新位置，保留已有事件；新workspace读取、幂等重试和追加新独立评审 | session_id、旧event/opinion_id与原理由均保留，包哈希不变，正确继续历史；不修改旧会话 |
| 20 | 三命令subprocess完整小闭环；默认摘要及include-opinions；非法/重复键/缺版本/未知版本/准备表submit输入；损坏会话inspect与submit | 成功退出0；错误非敏感JSON退出1；inspect坏历史退出0且writable=false；默认不泄漏意见理由/纠正值；数据不进包 |

额外断言：真实专家认证、完整目录抗回滚、跨平台原子发布不在此矩阵覆盖，不能把软件检查写成这些能力。数据兼容规则D-14不是要求改当前包；任何试图改模型/Schema才能通过的情况停止交Codex。

## 执行、日志与固定验证

每次命令独立log/XML和basetemp（attempt-01、02…），保存命令/退出码/耗时。首轮就留日志，禁止覆盖失败证据。新测试夹具/断言笔误可只修新增部分并说明，产品或设计冲突则停止，不改核心、不削弱预期错误码。

设置PYTHONDONTWRITEBYTECODE=1，先仅运行时文件，通过再相关、最后一次全量；静态确认没有live调用，不确定则停止报告。

```powershell
.venv/Scripts/python.exe -m pytest tests/test_review_sessions.py -o addopts='' -q -p no:cacheprovider --basetemp artifacts/b12-d04/<run>/runtime-tmp --junitxml artifacts/b12-d04/<run>/attempt-01-runtime.xml
.venv/Scripts/python.exe -m pytest tests/test_review_session_contract.py tests/test_review_snapshot.py tests/test_review_preparation.py tests/test_reviews.py -o addopts='' -q -p no:cacheprovider --basetemp artifacts/b12-d04/<run>/related-tmp --junitxml artifacts/b12-d04/<run>/attempt-01-related.xml
.venv/Scripts/python.exe -m pytest -o addopts='' -q -p no:cacheprovider --basetemp artifacts/b12-d04/<run>/full-tmp --junitxml artifacts/b12-d04/<run>/attempt-01-full.xml
git diff --check
```

不要在失败后跑依赖步骤或重复成功整套。JUnit与终端交叉核对，不手数点。原4项测试及辅助函数保持不变，不允许只patch核心返回值冒充端到端正确性；故障注入针对真实合成目录和明确边界。

## 真实空白安全检查（仅前述检查通过后）

只由本地Python脚本读取真实材料，脚本输出限哈希/计数/布尔，不让模型看到正文。

- 输入固定：`artifacts/b7-real-compat/model-knowledge`及`artifacts/b11-review-preparation/materials/preparation_718bf6c856acd871970f3eea/`；包153943字节，SHA256 50742f7c32f7178c562ba2927ae070feac1e82696f7f86792157090fe2f7786d。
- 使用`ReviewSessionService(packages, <run>/real-cache).create(preparation, <run>/real-session)`后inspect；全部输出目录为本次新路径且互不嵌套。禁止submit任何真实意见，不通过CLI打印完整真实view，不输出复制的preparation正文。
- 断言0意见/0事件，757个材料目标（188原文+541候选+28异常）、全部pending/无issues、writable=true仅指工程可接收明确意见、医学仍unreviewed、release_allowed=false；副本7文件哈希与原快照相同。
- 检查原包目录及准备目录前后文件集合/大小/哈希不变。新会话含原文副本，只留ignored artifacts，不提交/上传。
- 缺文件/哈希不符/权限或读入异常：记录真实阻塞并停止，不重蒸馏、不补材料、不上传。

最后只读验证341份Schema索引、核心/模型/设计等基线哈希不变；源码差异仅允许的analysis/cli新增分支及README，旧命令回归不得放宽。

## 交回

RESULT含20行矩阵→用例/结果、每轮命令/JUnit/失败修正、CLI与文档差异、真实0意见检查摘要、341份Schema和受保护输入哈希、允许范围对照、核心基线与运行文件哈希、skip/not_checked和平台边界。成功executed_pending_review、产品异常stopped；不写B12 done、不归档完整验收、不推进NEXT、不做发行构建。用户通知Codex核验后，再决定修复或最终发行验收。
