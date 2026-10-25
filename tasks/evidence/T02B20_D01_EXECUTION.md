# T02-B20-D01：固定五类最小闭环执行单

> ready_for_execution；2026-10-25。Codex设计和核验，DeepSeek重复运行/机械整理。不自行研究医学、扩预期或改实现。

## 启动与冻结

工作区D:/test/tongyongzhengliu，按AGENTS读STATE/CURRENT/HANDOFF/NEXT/ROADMAP及当前稳定设计/Schema，再读[T02B20_DESIGN.md](T02B20_DESIGN.md)。B19已归档，不重复其矩阵。当前只本D01，不执行NEXT。

- tasks/benchmarks/b20_five_types_check.py SHA256 `24ca762f6a07e44d865c9ac62cf405fda3d189071c2f8b34b925c6d5e0fd1eb8`。
- 复用tasks/benchmarks/b19_library_check.py SHA256 `0cd549f6b9a775216ff95d22d16c4ce99138125b6a03adde795669cd96c3f092`。
- 保护函数依赖tasks/benchmarks/b18_progress_probe.py SHA256 `baa8a61ffbc5151bb9e97bdd14fc02fef2bd88da88504383d7d96b90168e729c`。
- Codex已做5条类型检查及foundation/case两端实际smoke，不等于完整五类生产矩阵。

## 允许与禁止

只新建tasks/evidence/T02B20_D01_RESULT.md、新artifacts/b20-d01/deepseek-唯一目录及同名前缀.driver.log/.exit-code.txt；三个状态文件仅同步事实/路径，停executed_pending_review。

不改三脚本/设计/执行单、src/tests、349Schema/语义字典、md/overall、NEXT/ROADMAP、archive、docs/log/config/pdfs或旧artifacts，不清理旧未提交文件。不联网/装依赖/外部LLM/真实资料OCR/蒸馏/训练，不读config/llm.local.toml，无commit/push。不得自行换字段/类别/组、补临床事实、手改包封hash或降低预期；发现失败直接交Codex。

## 固定执行

1. 只读保存HEAD/status --short/diff --stat及脚本/设计/执行单SHA；核对.venv/Scripts/python.exe为3.13、349Schema和原真实包/7准备文件存在/哈希（见STATE）。B19归档更新了能力表，本轮独立保护基线以新采集为准，不用旧baseline覆盖。
2. 在仓库根执行一次，不带--smoke，不逐类重跑：

```powershell
$b20Run = 'artifacts/b20-d01/deepseek-' + [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ')
if ((Test-Path -LiteralPath $b20Run) -or (Test-Path -LiteralPath ($b20Run + '.driver.log'))) { throw 'Use a fresh path' }
& .venv/Scripts/python.exe -B tasks/benchmarks/b20_five_types_check.py --output $b20Run 2>&1 | Tee-Object -FilePath ($b20Run + '.driver.log')
$b20Exit = $LASTEXITCODE
Set-Content -LiteralPath ($b20Run + '.exit-code.txt') -Value $b20Exit
```

脚本创建新目录并直接顺序执行；无内部硬超时，总命令超过15分钟停止留证。首次非零/失败/保护变化即停，不修脚本、改数据/字段或重跑挑结果。summary不在也保留目录与driver日志，不补造结果。

3. 独立机械核对（不重新构建/测量）：

- exit0，summary.status=executed_pending_review、smoke=false、contract_rows=5、produced_categories与设计五行顺序一致、completed_checks=8、failure=null、protected_unchanged=true。
- contract-checks.json恰5行category/group/field，逐行对设计映射，全部passed；corpus.json恰5行，字段类别/组对应同表，各source_id/source_sha256/component_id/bundle_id不同，每源原生TXT SHA等于corpus、每归档SHA等于corpus。
- checks.json恰8行：joint-query 1行matched_nodes=5；category-query 5行各1命中且类别不重不漏；blank-review-preparation 1行targets=15；verified-blank-session 1行targets=15/opinions=0。全部passed。脚本已对每类节点全文SHA、证据源/引文、类过滤、组/字段做断言，不从类型检查推断实际矩阵通过。
- preparation-summary.json须source_evidence=5、nodes=5、facts=5、candidate_targets=10、gaps=0、rejected_candidates=0、issues=0、facts_stated=5，medical_review=unreviewed、release_allowed=false、review_records=0。原始preparation/与session/preparation均存在，7资源字节相同、manifest正文哈希自洽；空白worksheet无提交人/理由/决定。
- blank-progress.json须target_count=15、reviewer_count=0、event_ids=[]，四组source_annotation/candidate_node/candidate_fact/anomaly数量5/5/5/0、全部pending，medical_gate=blocked、release_allowed/training_allowed/phase02_complete=false；session/events/下0事件，不提交任何意见。
- 不变性：protected-before/after完全相同并复核当前保护集合；349Schema按索引复核；公开knowledge中5份正常.medpkg与corpus哈希一致，查询/准备未改包。不要把统一package-spec/说明书/发布锁等公开元数据当额外包或独立来源。

4. 在本次新artifact目录保存只读独立校验脚本、校验JSON、证据清单（文件名/大小/SHA，排除自身；私有缓存可单列不作为医学证据），git diff --check与git前后边界核对。源码/测试/Schema/三脚本/设计/执行单/原真实材料均不变，仅允许范围内产物与3状态/RESULT变化。不重跑全量549项、旧B18/B19或Codex smoke。
5. 写RESULT并同步3状态，停executed_pending_review，不归档、不推进NEXT，不写医学/性能/许可门passed。B20最终由Codex核验与产品复查后判定。

## RESULT格式与固定边界

记录环境/命令/退出/唯一路径/冻结SHA/失败或超时；5行表列category/group/field、类型检查、实际产包、分类查询、源/节点/包SHA、对应复核node/fact目标、空白状态。表中“软件闭环通过”与“临床/完整业务not_checked”分列，不能只写五类能力全部完成。

必须保留：每类只有1节点/1字段的自制TXT最小样本，本地确定性函数不是远程模型；结构和运行不等于医学真实。病例history不证明CanonicalCase或多诊次；方剂composition不证明配伍/剂量/安全处方；药材origin不证明鉴别或临床应用；pathomechanism不证明辨证正确。五类全面内容/真实金标准/临床/许可/跨平台/性能SLO均未检。数据包结构与原字段不变，不因失败任意改Schema/重新蒸馏。
