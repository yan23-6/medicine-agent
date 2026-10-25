# T02-B18-D01：固定复核统计微基准采集

> ready_for_execution；2026-10-25。DeepSeek执行，Codex核验。B18子步骤；不是整体验收。

## 启动

工作区D:/test/tongyongzhengliu。按AGENTS顺序读STATE/CURRENT/HANDOFF/NEXT/ROADMAP，再读[T02B18_BENCHMARK_DESIGN.md](T02B18_BENCHMARK_DESIGN.md)、原md01/04/08/09/16和overall规则。不要从旧聊天补规则。当前只执行本单，不执行NEXT/D02。

Codex已完成脚本与独立预期设计，并通过3点smoke/21项相关回归。你的工作是运行固定12点矩阵、机械核对完整性、整理原始结果。不实现代码、不优化性能、不改任何预期、不自行补模型资料。

冻结脚本：tasks/benchmarks/b18_progress_probe.py。
SHA256：`baa8a61ffbc5151bb9e97bdd14fc02fef2bd88da88504383d7d96b90168e729c`。
不符先停，记录实际值交回Codex，不能自行更新这行。

## 允许改动

- 新建tasks/evidence/T02B18_D01_RESULT.md。
- 仅向STATE/CURRENT/HANDOFF同步本D01的事实状态、运行路径和问题；保留B18整体in_progress，不写done/验收通过。
- 新建artifacts/b18-d01/deepseek-唯一时间目录及同名.driver.log/.exit-code.txt（均忽略、不提交）。所有证据只能写新位置，不覆盖Codex smoke或旧目录。

除此之外不改任何文件，包括采集脚本、设计、执行单、生产src、tests、Schema、md、overall、NEXT/ROADMAP、archive、docs/log/config/pdfs及既有artifacts。不清理/还原/格式化当前未提交工作；无commit/push、联网、安装、真实资料读取/OCR/蒸馏、模型API、训练。不读config/llm.local.toml。双方不并发修改；发现源文件变化直接停交回。

## 执行步骤

1. 只读记录git HEAD、git status --short、git diff --stat，不打印全部diff/正文。核对.venv/Scripts/python.exe为3.13，脚本SHA相符；确认源包/7准备文件、349份Schema存在。源包路径和哈希见STATE。只做大小/哈希，不解包或显示内容。缺前置即停。
2. 用新时间目录运行一次正式矩阵，不带--smoke，不逐点重跑。PowerShell示例（在仓库根）：

```powershell
$b18Run = 'artifacts/b18-d01/deepseek-' + [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ')
if ((Test-Path -LiteralPath $b18Run) -or (Test-Path -LiteralPath ($b18Run + '.driver.log'))) { throw 'Use a fresh path' }
& .venv/Scripts/python.exe -B tasks/benchmarks/b18_progress_probe.py --output $b18Run 2>&1 | Tee-Object -FilePath ($b18Run + '.driver.log')
$b18Exit = $LASTEXITCODE
Set-Content -LiteralPath ($b18Run + '.exit-code.txt') -Value $b18Exit
```

脚本自行创建目录；不要先创建同名目录。缺内存计数/超时/非零退出/断言失败都保留日志，停止交回，不改脚本、不提权、不装依赖、不缩小测点、不挑结果重跑。

3. 机械核对：退出0；summary.status=executed_pending_review、smoke=false、profiles=12、measured_samples=36、repeats=3、failure=null、protected_unchanged=true。48份样本JSON（12 warmup+36正式）及各自stdout/stderr存在；before/after保护映射相同。每正式样本oracle_passed/input_unchanged=true，组内report_id/input_sha256一致；memory_status如非measured须明确列partial，不编数字。检查每样本targets/declared_reviewers/history_rounds与设计表逐行相符，意见和合成event数满足4N/5×R×H。
4. 独立重算12组的median和nearest-rank p95，对照summary；允许在本次新artifact目录写一个只读结果校验脚本，但不得替换采集器或重新执行测量。换算ms/MiB须保留原ns/bytes，不把峰值相减。保留重算脚本与校验JSON；失败照报，不修采集值。
5. 对当前349份Schema按各schema-index.json复核逐文件SHA，保存核对结果；git diff --check。比较执行前后git状态，新增变化仅限允许清单；执行单/采集脚本哈希必须不变。无需跑全量549项或再次跑21项/3点smoke，除非Codex明确安排。
6. 生成RESULT并同步3状态文件，停在executed_pending_review，等待Codex。不得归档B18、推进NEXT、写性能门/医学门passed，或自行执行D02。

## RESULT必含

- 执行环境、唯一运行目录、命令/退出码/脚本SHA，48样本/36正式与12点矩阵完整性；所有失败/跳过/未评估项。
- 12行结果表：case、N/R/H、意见/event数量、中位墙钟ms、p95 ms、三次进程峰值MiB、正确性和只读核对。原始数据保留链接，不只报平均值。
- 独立重算、349Schema/受保护输入前后哈希、git边界和证据清单（文件名/大小/SHA256；清单排除自身避免循环）。
- 固定边界原样保留：typed-view重验+投影微基准；来源绑定/真实事件历史/service端到端/医学/容量SLO均not_checked。H是合成历史轮次，ID不是经内容重验的真实事件；声明ID不是专家数；3点p95=max仅探索性。峰值是进程生命周期Working Set，不能当阶段增量/私有提交量。
- 如果慢，只报告测量和观察，不改实现；若全通过，也只是本D01待Codex核验，B18仍未整体验收。
