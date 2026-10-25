# T02-B12-D03：会话契约Schema接入与固定验证

> 2026-10-24；ready，尚未执行。CURRENT子步骤，DeepSeek执行、Codex核验。

## 目标和基线

D02已由Codex核验，快照核心工程检查点通过，真实建链权限skip仍保留。Codex已冻结设计第五节、实现`src/medicine_agent/domain/review_session.py`的11个操作模型及`tests/test_review_session_contract.py`的初始7项边界测试（7 passed，0.18秒）。会话持久化、意见写入/历史、视图运行时和CLI尚未实现。

你的任务是按固定接入点增加review-session/0.1.0 Schema导出，并补参数化契约检查。不改模型、不设计会话、不实现运行时。Schema通过也不能声称会话功能或医学门通过。

## 启动和可写范围

工作区D:/test/tongyongzhengliu；按AGENTS顺序读取任务入口，再读md第09/18章、`T02B12_REVIEW_SESSION_DESIGN.md`（重点第五节）、D02核验段、本单、会话模型、初始测试、contracts.py和cli.py。执行时其他助手不并发修改。

只允许修改/创建：

1. `src/medicine_agent/contracts.py`：仅下节规定的review-session导出分支；
2. `src/medicine_agent/cli.py`：仅export-schemas的--contract-set choices追加review-session；
3. `schemas/review-session/`：通过现有导出器生成，不手改JSON；
4. `tests/test_review_session_contract.py`：仅追加测试/辅助函数与必要import，保持原7项及既有辅助函数不变；
5. `tasks/evidence/T02B12_D03_RESULT.md`、STATE/CURRENT/HANDOFF的D03状态事实；
6. `artifacts/b12-d03/<唯一新目录>/`：基线、执行脚本、每次命令日志/JUnit、哈希与统计、合成临时目录。

禁止修改会话模型、快照核心、旧tests/Schema/设计/执行单/既有RESULT/进展报告、md/docs/log/config/pdfs/注册表、真实产物或Git设置。不commit/push，不联网、不装依赖、不OCR/蒸馏/模型调用、不读取本地模型配置、不运行真实快照、不解包真实材料。真实输入只由本地脚本做哈希对照，不进入模型上下文。

先记录HEAD、git status、git diff --stat。保存两个允许改源码文件及测试的编辑前副本；记录11模型文件、快照核心、设计、已有Schema所有文件和受保护真实目录（同D02输入）的名称/大小/SHA256。当前已有未提交工作，不清理、不回滚。新Schema目录若已存在则停止报告，不覆盖。

## 固定实现接入点

`contracts.export_schemas`做且只做以下四项：

- 接受的contract_set集合增加'review-session'。
- 为'review-session'从`medicine_agent.domain.review_session`导入`REVIEW_SESSION_MODELS`，将common_models直接设为此元组；不能加COMMON_MODELS、旧review模型或其他独立文件。嵌套依赖由Pydantic的$defs保留。
- 在跳过Skill导出的管理契约集合中增加'review-session'。
- contract_version映射增加'review-session':'0.1.0'。

cli.py只在已有export-schemas的choices增加'review-session'；不新增命令或动默认值、错误处理/模型配置。

实现接入后，用现有CLI生成一次新目录：

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
.venv/Scripts/python.exe -m medicine_agent.cli export-schemas --contract-set review-session --output-dir schemas/review-session
```

预期：11份common/<模型名>.schema.json + schema-index.json共12文件，无skills/。index的contract_set/version正确、files恰为REVIEW_SESSION_MODELS的11项且哈希相符；CRLF沿用既有_write_json，不另写导出器。不能改旧契约版本或Schema。

## 固定模型验证矩阵

复用已有测试的reviewer/target/opinion/binding辅助函数；只造自制数据。每行至少一项，明确要求分别时参数化。预期结构非法抛Pydantic ValidationError（不是新的AnalysisError）；模型不负责来源存在性、内容ID生成或历史链，不能以本单测试冒称这些运行时能力。

| # | 测试范围 | 固定预期 |
|---|---|---|
| 1 | reviewer_id空白、非法路径字符、超128字符；display_name/declared_role空白分别测试 | 拒绝；规范化同大小写/首尾空白ID相同，identity_status不能为authenticated |
| 2 | source/candidate/anomaly的材料前缀错、后缀不合24位小写hex；candidate缺ReviewTarget；其他kind带ReviewTarget | 拒绝；三个合法kind正常往返 |
| 3 | 四种decision合法且reason非空；未知decision、reason空白/超8000字符分别测试 | 合法保留，非法拒绝；unable_to_judge不变为accept |
| 4 | accept/reject/unable携proposed_value；anomaly revise携proposed_value；source revise携空字符串/对象分别测试 | 拒绝；source合法字符串保留原值，candidate revise的JsonValue保留，revise允许无建议值 |
| 5 | expected_previous_id格式错；opinion_index负数/布尔/字符串；合法ID/索引0 | 非法拒绝，合法保留 |
| 6 | submission_id非法字符/空/超128；opinions空、超过1000、重复同材料、混两个snapshot分别测试 | 拒绝；同快照不同材料批提交结构合法（不写盘） |
| 7 | binding缺一个/多一个/错一个资源名；manifest资源哈希与manifest_sha256不一致；source_archives空、含目录或非medpkg分别测试 | 拒绝；正确7项与源包文件名可往返，不访问文件 |
| 8 | manifest、event、opinion record的时间无时区/非UTC分别测试 | 拒绝；UTC支持JSON往返；Record仍只是事件的只读投影类型 |
| 9 | manifest/view的medical_review=confirmed或release_allowed=true；reviewer_identity认证值 | 拒绝，缺省固定未审/false/声明身份 |
| 10 | summary的disagreement配not_required、agreement配awaiting_adjudication、latest_opinion_ids重复、unable计数负/布尔分别测试 | 拒绝；合法分歧必须待仲裁 |
| 11 | view有issues或target.history_invalid=true却writable=true | 拒绝；同内容writable=false允许，用于异常只读视图 |
| 12 | 11个模型各自在合法自制样本上添加未知字段；四个version顶层模型manifest/event/submission/view显式未知版本 | 拒绝未知字段/版本；Python构造允许缺version取0.1.0（磁盘显式版本验证是未来运行时职责） |
| 13 | API导出到tmp_path并与schemas/review-session逐字节比较 | 恰11项，无Skill资源；索引及文件哈希一致 |
| 14 | subprocess调用现有CLI导出到tmp_path；对所有10个旧contract_set通过API导出到各自新临时目录 | 新CLI成功，生成结果与API一致；旧索引及其列出文件逐字节等于仓库旧快照，不能因新增契约变动 |

测试基于已冻结模型实际字段，生成ID用固定格式自制值，不将结构测试伪装成运行时内容ID校验。若模型/设计/接入存在冲突，记录复现后停，不改模型或降低期望。测试夹具/断言自身有明确笔误可以仅修新增部分，但每次失败日志/XML须独立保留，说明具体修正；不可覆盖失败证据。

## 固定检查与日志要求

每次尝试独立命名，例如attempt-01-contract.log/xml，记录命令、退出码、开始结束/耗时；禁止复用输出路径覆盖失败记录。若harness只返回终端输出，先设计好重定向/保存方式再运行；JUnit从命令第一次就保存。不要手数点。

先仅跑契约文件，通过后再跑既有导出/CLI相关回归。本单不重跑7分钟全量；D02已有全量基线，本次只改导出分派且通过旧契约全部字节对照，完整会话实现后另做全量与发行验收。

```powershell
.venv/Scripts/python.exe -m pytest tests/test_review_session_contract.py -o addopts='' -q -p no:cacheprovider --basetemp artifacts/b12-d03/<run>/contract-tmp --junitxml artifacts/b12-d03/<run>/attempt-01-contract.xml
.venv/Scripts/python.exe -m pytest tests/test_contracts_and_runs.py tests/test_reviews.py tests/test_review_preparation.py -o addopts='' -q -p no:cacheprovider --basetemp artifacts/b12-d03/<run>/related-tmp --junitxml artifacts/b12-d03/<run>/attempt-01-related.xml
git diff --check
```

如需要重试，用全新attempt名称和新basetemp，不重复成功检查；产品错误或不确定冲突时停止，不继续依赖步骤。核对JUnit与终端，记录每轮而非只最终成功。

最后对全部既有schema-index列出文件做哈希验证，新review-session单独报告11项；真实包/准备目录、模型/快照核心/设计/既有Schema哈希不变；源码变化严格仅contracts/cli规定接入点，初始7项测试和原辅助函数源码不变。

## 交回

RESULT写基线、四处接入及cli差异、14行矩阵到测试名/结果、每次运行命令/退出码/耗时/JUnit、12项新文件清单、旧Schema字节对照及哈希、受保护输入对比、未检查项/异常/skip、运行证据哈希。

成功写D03 executed_pending_review，异常写stopped，均不得写B12 done、不推进NEXT、不实现会话或写意见。用户通知Codex后，Codex核验再继续运行时核心。
