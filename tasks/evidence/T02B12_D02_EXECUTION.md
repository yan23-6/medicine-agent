# T02-B12-D02：快照读入核心的合成矩阵与固定回归

> 2026-10-24；ready，尚未执行。CURRENT下的子步骤；执行者DeepSeek，核验者Codex。

## 目的与已完成部分

Codex已完成`tasks/evidence/T02B12_REVIEW_SESSION_DESIGN.md`的快照核心设计，实现`src/medicine_agent/analysis/review_snapshot.py`与`tests/test_review_snapshot.py`。初始5项合成通过；真实空白快照源包重建报告一致、包和准备目录哈希不变、真实意见0。摘要在`tasks/evidence/T02B12_SNAPSHOT_CORE_PROGRESS.md`。这不是完整B12验收。

你的任务仅为按固定设计补合成测试、运行检查并报告。不要重写核心、设计会话或自行修复失败。执行期间Codex不并发改工作区。

## 启动与允许范围

工作区`D:/test/tongyongzhengliu`。按AGENTS顺序读任务入口，再读第09/18章、本设计、D01核验结论、核心代码及已有5项测试、相关Schema。测试辅助文件只使用合成数据。

允许修改：

- `tests/test_review_snapshot.py`：只追加新测试/测试辅助函数；保留已有5项测试原样，不移动、不削弱断言；可增加所需标准库import。
- `tasks/evidence/T02B12_D02_RESULT.md`：新建非敏感结果。
- `tasks/STATE.md`、`tasks/CURRENT.md`、`tasks/HANDOFF.md`：每步同步D02事实，保留B12 in_progress与未验收边界。
- `artifacts/b12-d02/<唯一新目录>/`：命令日志、JUnit XML、基线和结束哈希、合成pytest临时文件及本地统计脚本。不可覆盖旧目录。

禁止修改src、其他tests、schemas、md、docs、log、config、pdfs、归档、设计/执行单/既有RESULT和原运行目录。禁止commit/push、联网、安装依赖、OCR/蒸馏、模型API、读取本地模型配置、真实材料正文进入模型上下文。D02不重跑真实快照、不解包真实材料；仅以本地哈希脚本核对其未变。

先记录HEAD、git status、git diff --stat；当前已有未提交工作，禁止清理。记录受保护包目录顶层与B11准备目录全部文件的名称/大小/SHA256；记录核心代码、已有测试文件及本设计的基线哈希。基线和结束对比保存在本次新运行目录。

## 固定合成矩阵

复用同文件`exported`、`load`、`rewrite_report`与`test_review_preparation.material`合成夹具。每个坏输入从独立tmp_path导出的健康快照开始。不能对真实目录做任何故障注入。允许按测试需要在合成快照中重算report ID/manifest，目的是确保没有只靠自报哈希通过；不得放宽期望错误码。

每行至少一个用例；标“分别”的必须分别参数化。异常断言为AnalysisError及下列code，且源包未被产品改写（用例自身故障注入后记录比较基线）。无需为了凑数量重复同义断言。

| # | 输入/操作 | 固定预期 |
|---|---|---|
| 1 | 缺正文、额外普通文件、正文替换为子目录，分别测试 | SNAPSHOT_RESOURCES_INVALID |
| 2 | 快照与packages相同；workspace在快照内；workspace在packages内；workspace是现有文件，分别测试 | SNAPSHOT_PATH_INVALID；不得在受保护输入中新建缓存 |
| 3 | 改一个正文的字节但不改manifest | SNAPSHOT_HASH_MISMATCH |
| 4 | manifest.files中把一个合法键替换为../outside、绝对路径、反斜线路径，分别测试 | SNAPSHOT_RESOURCES_INVALID；观测_read_file确认未读取声明的外部路径 |
| 5 | manifest/preparation分别重复JSON键；非法UTF-8；非对象顶层JSON，分别测试 | SNAPSHOT_JSON_INVALID；不得产生raw ValidationError或UnboundLocalError |
| 6 | JSON中的NaN、Infinity、1e999，分别测试（可放额外键，解析应先拒绝） | SNAPSHOT_JSON_INVALID |
| 7 | manifest/report分别未知版本和缺version，分别测试；必要时更新manifest正文哈希以只针对版本 | SNAPSHOT_VERSION_UNSUPPORTED |
| 8 | 改report.preparation_id，并同步manifest ID与正文哈希，但不按算法重算ID | SNAPSHOT_ID_MISMATCH |
| 9 | 将report.status和manifest.status分别同步改为partial/empty并重算report ID及manifest正文哈希 | SNAPSHOT_STATUS_UNSUPPORTED，不能当complete处理 |
| 10 | worksheet.reviewer、decision、reason任一非null，分别在source/candidate/anomaly上覆盖，重算ID/manifest（decision用合法accept） | SNAPSHOT_WORKSHEET_NOT_EMPTY |
| 11 | 从合成源目录移走所选包；packages目录不存在，分别测试 | SNAPSHOT_SOURCE_UNAVAILABLE |
| 12 | 修改源包字节而保留快照（不用修改包内内容）；或在快照coverage地址修改archive_sha256并重算ID/manifest | SNAPSHOT_SOURCE_MISMATCH |
| 13 | 修改候选item_id、source证据raw_text、anomaly载荷reason、coverage来源指纹，各自重算report ID/manifest | SNAPSHOT_SOURCE_MISMATCH；合法类型下自洽哈希也不能通过 |
| 14 | 改任一Markdown并更新manifest对应文件哈希 | SNAPSHOT_PRESENTATION_MISMATCH |
| 15 | prepare正常完成后、返回前在合成源包末尾追加字节（monkeypatch prepare包装器） | SNAPSHOT_CHANGED |
| 16 | prepare正常完成后更改合成快照Markdown字节（不改函数已读取的original） | SNAPSHOT_CHANGED |
| 17 | monkeypatch MAX_FILE_BYTES/MAX_SNAPSHOT_BYTES降低限制，分别触发单文件和总量上限 | SNAPSHOT_LIMIT_EXCEEDED；不创建大文件 |
| 18 | 合成快照目录/正文用symlink或Windows junction替代 | SNAPSHOT_PATH_INVALID；无创建链接权限则明确skip及原因，不改ACL、不升级权限。可用lstat受控桩补充reparse分支，但不能把桩测试写成真实链接验收 |
| 19 | 复制完整合成快照和同名同字节包到新位置，用全新不嵌套workspace读取 | 成功，snapshot_id相同、输入哈希不变、仍unreviewed/release_allowed=false |
| 20 | 完整数据中报告缺必要字段（如sources），更新manifest正文哈希 | SNAPSHOT_SCHEMA_INVALID；格式化traceback不得含注入的自制敏感标记（检验异常输出不泄漏） |

路径权限或系统行为限制可以标not_checked/skip并解释；若错误码、接口或设计有冲突，不改设计或核心，先记录具体失败与复现测试然后停止。不要为了全绿改已有测试或删失败用例。

## 执行与固定命令

先仅运行新的测试文件；通过后再跑既有相关测试；全部通过后跑一次全量。先静态确认测试不会调用真实服务；发现不确定的live用例则停止报告，不自行跳过它后宣称全量通过。

PowerShell中先设`$env:PYTHONDONTWRITEBYTECODE='1'`。以下`<run>`必须替换为本次新目录，不要使用已有路径。

```powershell
.venv/Scripts/python.exe -m pytest tests/test_review_snapshot.py -o addopts='' -q -p no:cacheprovider --basetemp artifacts/b12-d02/<run>/snapshot-tmp --junitxml artifacts/b12-d02/<run>/snapshot.xml
.venv/Scripts/python.exe -m pytest tests/test_review_preparation.py tests/test_reviews.py -o addopts='' -q -p no:cacheprovider --basetemp artifacts/b12-d02/<run>/related-tmp --junitxml artifacts/b12-d02/<run>/related.xml
.venv/Scripts/python.exe -m pytest -o addopts='' -q -p no:cacheprovider --basetemp artifacts/b12-d02/<run>/full-tmp --junitxml artifacts/b12-d02/<run>/full.xml
git diff --check
```

不要手数点；从JUnit读取tests/failures/errors/skipped和终端汇总交叉核对，分别记录命令/退出码/耗时。失败即保留日志、矩阵结果并停止依赖步骤，不重复跑整套；成功不做发行构建、Schema导出或再跑真实脚本。

最后验证28份review/review-preparation Schema索引哈希（只读，不导出），受保护输入、src及设计文件哈希不变；与基线比较新增修改文件是否全在允许范围。初始5项测试必须仍存在且未改写，RESULT附测试文件diff摘要供Codex核验。

## 交回格式

RESULT写：基线、20行矩阵逐项→测试名及结果、各次命令统计、skip/not_checked/失败定位、真实受保护输入及核心哈希前后对照、允许范围差异、运行文件哈希。只输出非敏感摘要，不复制真实正文或本地配置。

成功写`D02 executed_pending_review`，失败写`D02 stopped`，说明实际原因；两者均不得写B12 done、不改NEXT、不创建验收归档、不实现会话。用户通知Codex后，由Codex核验和处理失败。
