# T02-B18-D02：生产Service固定操作基线采集

> ready_for_execution；2026-10-25。DeepSeek机械执行，Codex负责设计/核验。只执行本单，不优化、不推进NEXT。

## 启动与冻结

在D:/test/tongyongzhengliu按AGENTS读取STATE/CURRENT/HANDOFF/NEXT/ROADMAP，再读[T02B18_D02_DESIGN.md](T02B18_D02_DESIGN.md)、[D01 Codex核验](T02B18_D01_CODEX_REVIEW.md)与设计引用原产品/规则。旧D01执行单已完成，不重复执行。

- D02脚本tasks/benchmarks/b18_service_probe.py，SHA256 `211d4f5138cc2b3521f1afd6b2657a865c93308a0137d28de1ddb6fe97e40937`。
- 依赖冻结D01脚本tasks/benchmarks/b18_progress_probe.py，SHA256 `baa8a61ffbc5151bb9e97bdd14fc02fef2bd88da88504383d7d96b90168e729c`。
- 生成器复用tests/test_review_preparation.py的PreparationModel；只读，绝不可改测试/生产验证器。解释器必须.venv/Scripts/python.exe（3.13）。
- Codex已验证4格小样/2缓存后损坏负例和U40构造边界；7profile正式矩阵未执行，留给你。

## 允许写入与禁止项

只新建tasks/evidence/T02B18_D02_RESULT.md、新artifacts/b18-d02/deepseek-唯一目录及同名前缀.driver.log/.exit-code.txt；STATE/CURRENT/HANDOFF仅更新事实状态和路径。运行目录可包含本次自制包、准备材料、实际事件、私有缓存、故意损坏副本、独立只读重算脚本和证据。

不改两采集器、设计/执行单、src/tests、349Schema/语义注册表、md/overall、NEXT/ROADMAP、archive、既有artifacts、docs/log/config/pdfs。不清理旧改动，不联网/装依赖/LLM/真实资料OCR/蒸馏/训练，不读config/llm.local.toml，无commit/push。别手写正常事件文件、跳过submit/绑定/历史校验，别因结果慢改测点或缓存。双方不并发修改。

## 固定步骤

1. 只读保存HEAD、status --short、diff --stat及两脚本/设计/执行单SHA；核对349Schema、原真实包153943字节/50742f7c…f7786d和7准备文件（见STATE）。缺前置/哈希不符即停，不自行修正。
2. 只运行一次正式矩阵，不带--smoke，不逐格重跑。仓库根PowerShell：

```powershell
$b18d02Run = 'artifacts/b18-d02/deepseek-' + [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ')
if ((Test-Path -LiteralPath $b18d02Run) -or (Test-Path -LiteralPath ($b18d02Run + '.driver.log'))) { throw 'Use a fresh path' }
& .venv/Scripts/python.exe -B tasks/benchmarks/b18_service_probe.py --output $b18d02Run 2>&1 | Tee-Object -FilePath ($b18d02Run + '.driver.log')
$b18d02Exit = $LASTEXITCODE
Set-Content -LiteralPath ($b18d02Run + '.exit-code.txt') -Value $b18d02Exit
```

不要提前创建同名目录。脚本会构建7profile的自制fixture、运行两项负例，再启动112采集进程。构造阶段写入仅在本次artifact目录，计时不包含构造；构造仅模拟适配器/本地确定性生成函数，不是外部模型/OCR。

采集子进程120秒；启动预算1800秒，总命令超过45分钟则停止并留证。首次非零/异常/超时/保护变化停止交Codex，不修脚本/断言、不装依赖、不改点、不补造样本。若summary未生成也按失败保留当前目录和driver日志，不能为了补齐汇总而重跑。

3. 独立机械核对（不要只信summary自报）：

- summary.status=executed_pending_review，smoke=false、profiles=7、cells=28、measured_samples=84、failure=null、protected_unchanged=true。
- 顶层112份样本JSON（28 discard+84 rep-1/2/3）及224份stdout/stderr存在；build/fixture.json不是样本，不混算。每个sample与stdout一致（除父进程加的exit_code/discard），stderr应空。discard不参与统计。
- 28格分别按设计表7profile×inspect/report×fresh/reused核对，不能漏一格。样本status passed、exit0、oracle_passed/fixture_unchanged true；内存非measured时列partial/not_evaluated，不编数。
- 每profile U/N/K/E/O与设计表一致；7份build JSON与fixtures内fixture.json内容相同。E=R*H，O=K*R*H；不沿用D01的event=opinion。正常event必须来自生产submit，不能伪造payload封包。
- 每profile/operation的6份正式样本（跨fresh/reused）logical_result_sha256和fixture_identity一致，不能跨不同profile要求同ID。
- 每格独立重算3次wall_ns中位和nearest-rank p95=max，对照summary逐字段，包括峰值数组；ns/1e6=ms，bytes/1048576=MiB，原始数保留。
- negative-checks.json必须source passed且SESSION_SNAPSHOT_INVALID、event passed且actual_codes含SESSION_EVENT_INVALID，两者after_workspace_warmup=true。损坏只在negative-*副本，不能影响正常fixtures。
- 比较protected-before/after相同，并独立复核当前受保护文件；每正常fixture按fixture.json.files核对最终文件集合/字节哈希。两负例副本故意不同，不作为正常fixture比较。

4. 在本次新artifact目录写独立重算脚本/校验JSON，349Schema按索引哈希核对，git diff --check；确认脚本/设计/执行单未改、源/测试/Schema/md/overall和真实输入未变。记录git前后变化边界，保留校验失败，不改原始测量值。不运行旧全量549项、不重复Codex smoke或U40构造检查。
5. 生成RESULT和排除自身的证据清单（文件名/大小/SHA256），同步3状态文件，停executed_pending_review等Codex。不得归档B18、改NEXT、写性能/医学/阶段门passed。

## RESULT口径

必须含：环境、命令、退出码、唯一目录、冻结SHA、7profile/28格/112进程/84正式完整性；28行表（case/N/R/H/E/O、operation、workspace_mode、median/p95 ms、三次生命周期峰值MiB）；全部失败/超时/未评估；独立重算、fixture/349Schema/原输入不变性、两缓存后损坏负例、git边界、证据清单。

边界必须保留：这是Service操作，不包括进程启动/fixture构建/服务实例化/正确性校验或业务CLI；构造数据全自制、适配器模拟，无临床真实性。fresh/reused仅指私有工作区，不是OS冷/热缓存；哈希读取会影响OS缓存。reused同进程预调用不计入墙钟但会进入生命周期峰值；不能相减峰值或inspect/report中位数来声称阶段开销。3点p95=max仅探索性；同N/O/E对照仍有链长/最新意见/输出行数等差异，不断言单因果瓶颈。来源绑定/实际提交历史只对这些自制fixture经生产API验证，不等于真实跨源/临床/跨平台/容量SLO或整包抗恶意回滚。

观察只报告，不优化。结果通过也只是D02待核验；B18是否整体完成由Codex回到原产品目标后判断。
