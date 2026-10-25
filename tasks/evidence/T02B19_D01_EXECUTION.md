# T02-B19-D01：多包联合消费固定兼容验收

> ready_for_execution；2026-10-25。DeepSeek仅重复运行/机械校验；Codex设计并核验。

## 启动与冻结

工作区D:/test/tongyongzhengliu，按AGENTS读STATE/CURRENT/HANDOFF/NEXT/ROADMAP和当前设计/Schema，再读[T02B19_DESIGN.md](T02B19_DESIGN.md)及原01/04/08/16、overall规则。B18已完成，不重复其采集/全量或重建发行。

固定脚本tasks/benchmarks/b19_library_check.py，SHA256 `0cd549f6b9a775216ff95d22d16c4ce99138125b6a03adde795669cd96c3f092`。
依赖D01保护清单函数来自tasks/benchmarks/b18_progress_probe.py，SHA256 `baa8a61ffbc5151bb9e97bdd14fc02fef2bd88da88504383d7d96b90168e729c`。
必须用.venv/Scripts/python.exe（3.13），不要默认系统python。两脚本/设计/执行单不符或前置缺失即停，不自行更新预期或哈希。

## 允许写入

- tasks/evidence/T02B19_D01_RESULT.md。
- STATE/CURRENT/HANDOFF仅同步事实状态、路径与失败，不写B19 done。
- artifacts/b19-d01/deepseek-唯一新目录及同名前缀.driver.log/.exit-code.txt，含本次自制输入/包/工作区、移出与retired目录、只读独立校验脚本、证据。

禁止改采集器、设计/执行单、src/tests、349Schema/语义、md/overall、NEXT/ROADMAP、archive、docs/log/config/pdfs或既有artifacts。不清理旧改动、不联网/装依赖/LLM/真实资料OCR/蒸馏/训练，不读config/llm.local.toml，无commit/push。不得手改包/重新封hash、调查询逻辑、减少来源、跳过移动或降低断言。双方不并发修改。

## 固定步骤

1. 只读记录HEAD/status --short/diff --stat、两脚本/设计/执行单哈希；核对349Schema与STATE中的真实包/7准备文件存在且原哈希相同。只记哈希/大小，不解包/显示真实材料。注意B18验收已按规则更新overall能力表，B19以本轮新保护基线为准，不拿旧任务baseline替换。
2. 运行一次正式矩阵，不带--smoke，不逐profile重跑：

```powershell
$b19Run = 'artifacts/b19-d01/deepseek-' + [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ')
if ((Test-Path -LiteralPath $b19Run) -or (Test-Path -LiteralPath ($b19Run + '.driver.log'))) { throw 'Use a fresh path' }
& .venv/Scripts/python.exe -B tasks/benchmarks/b19_library_check.py --output $b19Run 2>&1 | Tee-Object -FilePath ($b19Run + '.driver.log')
$b19Exit = $LASTEXITCODE
Set-Content -LiteralPath ($b19Run + '.exit-code.txt') -Value $b19Exit
```

脚本自行建目录；先后构造并核验1/5/20来源，3个子进程（每个900秒）各完成9阶段。它使用原生TXT与本地确定性生成函数，不是远程模型/OCR。移动只涉及本次自制profile目录，代码先核对绝对源/目标路径均在profile内；不要手工扩大移动范围。整个命令超过50分钟停止留证。

3. 首次超时/非零/断言失败/哈希变化即停止、保留所有日志，交回Codex，不修包/源码/脚本，不为了全绿重跑挑结果。即使summary缺失也保留当前产物，不能补造数据。
4. 独立机械核对（不重跑测量/构造）：

- exit0；summary.status=executed_pending_review，smoke=false、expected_profiles=[1,5,20]、completed_profiles=3、failure=null、protected_unchanged=true。
- 三份sources-1/5/20.json各passed、exit0、stages=9；与stdout一致（仅多exit_code），stderr为空。样本不是B18计时样本，不报中位/p95。
- 每profile corpus.json有S条，profile内source_id/source_sha256/component_id/bundle_id各S个；两owner按index奇偶，S>1公共查询包含两owner。每profile9条stages.json，合计27条，名称/顺序/匹配数/可读物理文件/隔离数按设计表逐行核对。不能把三个profile来源数相加当26个独立来源。
- initial、duplicate、bad-file、primary-removed、restore、migration的identity_set一致；last-copy-removed恰好少第0来源的(component_id,node_id)；unique初始只有第0来源，removed-unique为空。S=1时最后副本移出后必须0匹配，不能从缓存复活。
- 物理package_files的精确副本允许同bundle_id两行，命中节点/独立来源不能翻倍。bad-file开始及之后broken.medpkg始终quarantined/PACKAGE_FILE_INVALID，正常包不被拖垮。不要用len(query.packages)当命中数；采集器展平medical_nodes，理由见设计。
- 结果中所有public_bytes_unchanged=true，节点/来源/证据哈希oracle通过；普通包字节与corpus一致，精确副本与源0一致，坏文件固定字节not a medpkg archive。迁移结束后原knowledge/inputs/generation/query-cache四路径均不存在，retired中保留；migrated-knowledge仅公开目录副本，migration-fresh-cache独立存在。
- 独立复核最终migrated-knowledge里S份正常归档SHA与corpus一致、broken仍原字节；holding/copy.medpkg与源0 SHA一致；retired/knowledge的公开文件字节与migrated-knowledge相同。源输入在retired/inputs（含终止换行），逐一SHA与corpus.source_sha256一致。
- protected-before/after文件集合和SHA相同，并复核当前保护文件；349Schema按各索引复核。确认两脚本/设计/执行单/原真实输入未改；git diff --check和git前后变化边界相符。仅3状态文件/RESULT/新artifact在允许范围，不修改NEXT或overall。

5. 在本次新artifact目录保存独立只读校验脚本、校验JSON、全量证据清单（文件名/大小/SHA，排除清单自身；私有缓存可单独计数不当测量证据）。不把旧路径移到retired误判为输入丢失或采集器破坏真实资料。
6. 写RESULT，同步3状态，停executed_pending_review，等Codex核验；不归档、不推进NEXT、不写临床/性能/许可门passed。

## RESULT必含

环境/命令/退出/运行路径/冻结SHA，1/5/20三个profile与27阶段完整性；27行表（profile/stage/匹配节点/独立来源/owner集合/可读物理文件/隔离数/身份检查）；所有异常/超时/未评估；独立重算、迁移和包字节/来源SHA证据、349Schema/原包保护、git边界与清单。

保持边界：只验证现有实验单文件、原生TXT/theory自制数据，不代表真实跨源医学正确性、五类资料全面覆盖、权限认证、正式包v0、LadybugDB、多跳/向量/并发或异机跨平台认证。无临床输出，medical unreviewed/consultation=false。没有性能SLO或医学门升级。任何产品缺陷由Codex判断与设计修复，DeepSeek只记录，不自行改预期。
