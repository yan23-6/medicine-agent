# T02-B12-D05：提交限额补测与离线发行验收

> 2026-10-25；ready，尚未执行。CURRENT子步骤，DeepSeek执行、Codex核验。

## 目的与边界

D01—D04已经Codex核验；最后全量435 passed/2 skipped，341份Schema哈希有效。剩余范围见`T02B12_FINAL_GATE_REVIEW.md`。本单补3项submit容量分支、离线构建wheel/sdist、新独立安装API/CLI闭环与文档/发行审计。不改生产代码、Schema、包结构或原真实会话，不重蒸馏。成功也只写executed_pending_review，完整归档/下一任务重评由Codex处理。

按AGENTS启动顺序读任务入口，再读第04/09/18章、D-14、B12设计第5/6节、D04核验段、最终门审查、本单和pyproject.toml（不读取config/llm.local.toml）。执行期间双方不并发修改。

## 允许修改/创建

- `tests/test_review_sessions.py`：仅追加下面3项补测及必要import；不改原D04用例/辅助函数。
- `tasks/evidence/T02B12_D05_RESULT.md`、STATE/CURRENT/HANDOFF中的本单事实。
- `artifacts/b12-d05/<唯一新目录>/`：编辑前副本/基线、补测日志/XML、构建与安装日志、dist、独立环境、完全自制合成包/会话、验证脚本及非敏感摘要/独立文件清单。
- `.uv-cache/`仅允许离线工具正常缓存访问/写入，不能清理旧缓存、改工具或扩大到其他用户目录。

禁止改src、pyproject/锁文件、任何Schema/注册表、md/docs/log/config/pdfs、设计/旧执行单/旧RESULT/既有运行目录或Git设置。不commit/push、不联网、不装新在线依赖、不下载Python、不OCR/真实蒸馏/模型调用/训练、不读本地模型配置或外发正文。真实输入只做本地哈希；不重跑D04真实会话、不给该会话写意见，不复制真实PDF/包/准备材料进测试、发行物或独立环境。

先记录HEAD/status/diff、工具版本与所有src/Schema/设计、真实包目录/原7文件的相对名/大小/SHA256。保存测试编辑前副本。当前有大量既有未提交成果，不清理、不回滚。独立环境和dist必须新建，不复用/改写B11或D04环境。

## 一、3项固定提交限额补测

使用现有session/exported/batch夹具；每项从新合成会话开始。先记录事件目录字节基线，操作后必须完全相同，且源包/准备副本未被产品修改。都要求AnalysisError.code=SESSION_LIMIT_EXCEEDED，不把在_context/inspect阶段失败冒充submit发布前限制通过。

1. `test_submit_event_byte_limit`：无已有事件；将MAX_EVENT_BYTES临时设为session.json字节数+1024，使manifest仍可读；candidate revise带64KiB的自制字符串proposed_value。提交应在事件序列化后、_publish前拒绝，不能调用_publish。不要把阈值设为1；不造真实大文件。
2. `test_submit_history_byte_limit`：先提交1条合法小事件；MAX_HISTORY_BYTES临时设为现有事件总字节数+1，使既有历史仍可读；再提交另一声明ID的新意见，累计大小拒绝；不能调用_publish。
3. `test_submit_event_count_limit`：先提交1条合法事件；MAX_EVENTS临时设为1，现有历史可读；再次新提交因数量上限拒绝；不能调用_publish。

可通过monkeypatch把_publish替换为“被调用就令测试失败”的观察桩，其余读取/模型/历史照常运行，不能直接patch_history返回伪成功。只跑这3项：

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
.venv/Scripts/python.exe -m pytest tests/test_review_sessions.py -k "test_submit_event_byte_limit or test_submit_history_byte_limit or test_submit_event_count_limit" -o addopts='' -q -p no:cacheprovider --basetemp artifacts/b12-d05/<run>/capacity-tmp --junitxml artifacts/b12-d05/<run>/attempt-01-capacity.xml
```

记录JUnit与终端通过/失败/跳过/耗时。只改新增测试中的明确笔误可重试，每轮独立log/XML/basetemp；产品错误、需改模型/设计或不确定则停止交Codex。不要重复435项全量；生产代码若需变化，不在本单自行扩大验证。

## 二、本地离线构建与独立安装

可用工具已核对：`.tools/bin/uv.exe`，本地Python `.venv/Scripts/python.exe`（3.13），已有缓存`.uv-cache/`。build/pip/uv_build未装在当前venv，不要求安装到主环境；由uv离线缓存/构建机制处理。所有uv命令必须带--offline、--no-python-downloads、显式--cache-dir .uv-cache及目标路径。不要--clear、不改依赖、不用--system-site-packages、不做editable安装。

用主venv的importlib.metadata记录已安装分发的名称/版本，生成本次运行目录constraints.txt（排除名称规范化后为medicine-agent的项目本体；其他分发仅约束、不主动安装）。独立安装使用该约束文件，保持D04已测试的依赖版本，避免缓存中另一版本的Pydantic等改变Schema。约束只写运行目录，不修改pyproject/锁文件或主环境；最终说明仅验证这个Windows/Python/依赖基线，不宣称覆盖整个允许版本区间。

参考命令（先按本地--help核对，纯路径/受支持选项调整可记录，不能去掉offline）：

```powershell
.tools/bin/uv.exe build --offline --no-python-downloads --python .venv/Scripts/python.exe --cache-dir .uv-cache --no-create-gitignore --out-dir artifacts/b12-d05/<run>/dist
.tools/bin/uv.exe venv --offline --no-python-downloads --python .venv/Scripts/python.exe --cache-dir .uv-cache artifacts/b12-d05/<run>/isolated-env
.tools/bin/uv.exe pip install --offline --no-python-downloads --python artifacts/b12-d05/<run>/isolated-env/Scripts/python.exe --cache-dir .uv-cache --constraint artifacts/b12-d05/<run>/constraints.txt artifacts/b12-d05/<run>/dist/medicine_agent-0.1.0-py3-none-any.whl
```

每个命令单独日志，记录退出码/耗时。离线缓存/依赖不足或权限失败时记录具体缺失和停止，不联网下载、不改ACL、不改pyproject或换成伪隔离。权限按harness正规工具流程处理，不能绕过拒绝。

构建本身不等于发布，版本仍按当前pyproject的实验0.1.0，不改包协议或软件版本。dist中wheel/sdist各1个，不能混入旧产物。

## 三、发行物审计（只读）

1. wheel与sdist（去掉tar顶层包目录前缀后）不得含pdfs、artifacts、config、docs、log、tasks、tests、md、.venv、.tools、.uv-cache、.git、.agents、.codex或原始资料/知识包/缓存。不得有.medpkg/.pdf/.pyc或__pycache__。只检查路径/类型，不为搜索密钥去读取本地配置；若发现敏感路径，记录文件名并停止，不打开其中正文。
2. wheel的medicine_agent/资源与`src/medicine_agent/`所有范围内非pyc/非缓存文件逐字节比较，包含新3模块、registry、SKILL说明和analysis/README；双向核对文件集合，不只抽样。sdist亦核对其src/medicine_agent资源集合/字节。正常发行元数据(dist-info、PKG-INFO、pyproject、README/许可证等)另列，不冒充源码。
3. 记录两个归档大小/SHA256、实际源码/资源数量、禁止路径命中数。341份开发Schema不需塞进wheel；安装后export-schemas可由Pydantic生成。

## 四、独立环境自制小闭环（必须python -I）

所有脚本写本次运行目录，使用新环境`Scripts/python.exe -I <绝对脚本路径>`或`-I -m medicine_agent.cli ...`，cwd选新环境旁的空目录。不得PYTHONPATH注入仓库src、不从tests导入夹具、不读取真实材料/配置。检查medicine_agent及本次相关子模块__file__全部来自新site-packages，不能只检查顶层模块名。

自包含脚本按下列固定路线：

1. 写一行完全自制UTF-8 TXT，例如“Synthetic theory statement for software acceptance.”。实现仅本地的SyntheticModel（provider='synthetic-software-only'，model='offline-release-check'，generate_json只解析所给evidence，不发网络请求）。可参照既有PreparationModel的有效输出结构，但不能import它：取当前evidence末条，以其source_id/evidence_id/raw_text生成一个tcm_foundation节点、一个theory分组、一项tcm.theory_proposition_text事实，所有quotes逐字对应自制文本；没有医学认可或虚构原件。用FileLearningService(..., model_client=SyntheticModel())提交并run到completed，mode=model只是调用自制stub，不是外部LLM或OCR。
2. 用已安装ReviewPreparationService导出到全新准备目录，必须complete；用已安装ReviewSessionService创建/读取会话，状态未审/禁止发布，初始意见0。
3. 取真实生成的一个candidate完整target；提交两名声明评审者的自制accept/reject，检查disagreement/awaiting_adjudication；同submission_id同内容重试返回原event且不新增；错误前序拒绝、批失败不改事件目录；保存非敏感计数/身份/哈希摘要，不把这些意见当医学评审。
4. 复制这个合成会话和同名同字节合成包到新目录、用新workspace读取，检查旧session/event/opinion ID及原自制理由一致，可继续一条unable_to_judge；旧会话与包未变。
5. 用新环境python -I -m CLI运行三命令小闭环（可创建第二个合成会话）：create→API复制其target构造自制提交文件→submit→inspect默认摘要与--include-opinions对照。默认无理由/纠正值，完整view保留自制理由；医疗状态不变。所有子进程明确同一新环境python与-I，检查退出码。
6. 新环境CLI export-schemas --contract-set review-session --output-dir <run>/isolated-schema，11文件+索引与仓库快照字节相同。只给脚本提供仓库目标文件的期望哈希/路径作比对，不通过sys.path导入源码；安装后报告与源码测试语义一致。

如自制模型输出结构不合法，记录并停，不能放松来源/Schema校验、改核心或换extractive伪装语义分析成功。所有自制包/会话只留artifacts，不能混进发行物。

## 五、最终静态与受保护审计

- 全部341份schema-index资源哈希有效，新旧索引本身亦与执行基线相同。源代码/资源、pyproject、锁文件、设计、注册表哈希与基线相同；测试只新增3项，原函数源码不变。
- 检查当前范围Markdown本地链接：根*.md、md/**/*.md、tasks（不含archive）/**/*.md、src/**/*.md；跳过代码围栏、远程URL和纯锚点，处理URL解码和相对路径。docs/log/archive不改。坏链接只报告，不自行越界修文档。
- git diff --check；git diff/status与基线对比，无新生产改动，无docs/log/pdf/config.local变动；确认artifacts/、原PDF、config/llm.local.toml仍被忽略。仅检查这些敏感路径的存在/忽略状态，不读配置内容。
- 真实包目录4文件和原准备目录7文件集合/大小/哈希不变，原.medpkg仍153943字节/50742f7c32f7178c562ba2927ae070feac1e82696f7f86792157090fe2f7786d；不重新解析原PDF或改变既有真实会话。

## 六、交回与校验清单

先写所有日志/JSON摘要，再生成独立`evidence-manifest.json`，覆盖脚本、补测JUnit/日志、构建/安装日志、dist归档、独立smoke摘要和审计摘要等确定证据；不递归收录整个依赖环境，不包括清单自身。清单SHA256写进RESULT；RESULT不纳入该清单，避免循环依赖。不要覆盖D04 summary或自报“自身哈希匹配”。

RESULT列每步命令/退出码/耗时、3项补测、归档资源比对、新site-packages路径证明与API/CLI/迁移结果、341份Schema/Markdown/保护审计、实际缺口和skip/平台边界、完整manifest哈希及允许范围差异。

成功D05 executed_pending_review，失败stopped。不得创建完整B12验收归档、标B12 done、推进NEXT或提交推送。用户通知Codex后，由Codex核验实际发行物/日志，决定归档和下一任务重评。
