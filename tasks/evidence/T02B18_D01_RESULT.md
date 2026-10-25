# T02-B18-D01 执行结果（非敏感）

> 2026-10-25；状态：**executed_pending_review，待 Codex 核验**。
> 执行单：tasks/evidence/T02B18_D01_EXECUTION.md（未改动）。本文件只含计数、耗时、内存、哈希与测试名，不含原文或配置。
> 运行目录：`artifacts/b18-d01/deepseek-20261025T124354767Z/`（脚本自行新建，未覆盖 Codex 的 smoke/设计目录）。

## 1. 执行环境与冻结输入

- Python `3.13.15 (MSC v.1944 64 bit AMD64)`；Windows-10-10.0.19045-SP0；AMD64；CPU 12 逻辑核；pydantic 2.13.5；project 0.1.0；解释器 `.venv/Scripts/python.exe`。
- 脚本 `tasks/benchmarks/b18_progress_probe.py` SHA256 `baa8a61f…168e729c`，与执行单一致；`environment.json` 内记录的 `source_sha256` 与运行后实测相等。
- 执行单 SHA256 `364c2cdf…4d44f652`、设计 `552dfe21…49a19d9`，执行前后均未变。
- 源包 `bundle_a7c24a2b…medpkg` 153943 字节 / `50742f7c…2f7786d`；准备目录 7 文件；349 份 Schema 存在。
- 命令（PowerShell，仓库根，`PYTHONDONTWRITEBYTECODE=1`）：

```
.venv/Scripts/python.exe -B tasks/benchmarks/b18_progress_probe.py --output artifacts/b18-d01/deepseek-20261025T124354767Z
```

退出码 **0**（`.exit-code.txt` = 0），整次 45.06 秒。未带 `--smoke`，未逐点重跑，未重试挑结果。

## 2. 完整性（48 子进程 / 36 正式 / 12 组）

- 目录内 148 个文件：`summary.json`、`environment.json`、`protected-before/after.json`、48 份样本 JSON（12 `-warmup` 丢弃 + 36 `-rep-{1,2,3}` 正式）、96 份 stdout/stderr 日志。
- `summary.json`：`status=executed_pending_review`、`smoke=false`、`profiles=12`、`measured_samples=36`、`warmup_per_profile=1`、`repeats=3`、`failure=null`、`protected_unchanged=true`。
- 36 份正式样本全部 `status=passed`、`exit_code=0`、`warmup=false`、`oracle_passed=true`、`input_unchanged=true`、`memory_status=measured`；每样本 `targets/declared_reviewers/history_rounds` 与设计表逐行相符，`opinion_records = synthetic_event_ids = 4N/5×R×H`。
- 每组 3 份的 `report_id` 与 `input_sha256` 各唯一；12 个 warmup 样本同样 passed 且被排除在统计外。
- 独立校验脚本共 **66 项检查全部通过**（`verify-result.json.passed=true`，`failed_checks=[]`）。
- 失败/跳过：**无**。`memory_status` 无 `partial`；Windows 峰值采集可用，无 `not_evaluated`。

## 3. 12 行结果（毫秒/次、MiB）

统计段 = `_summarize(typed_view)` 段内墙钟（含序列化/类型重验、最新意见映射、两两比较、报告验证与稳定 ID）；中位取 3 份中位数，p95 取 nearest-rank 第 3 项（= 最大值，仅探索性）。峰值是进程生命周期 Working Set 的 3 次观测，不可相减。

| case | N | R | H | 意见/合成 event | 中位 ms | p95 ms | 三次峰值 MiB | 正确性/只读 |
|---|---:|---:|---:|---:|---:|---:|---|---|
| blank20 | 20 | 0 | 1 | 0 | 0.444 | 0.509 | 33.44 / 33.81 / 33.50 | passed |
| blank5000 | 5000 | 0 | 1 | 0 | 52.371 | 53.157 | 61.19 / 61.02 / 61.07 | passed |
| n20-r2-h1 | 20 | 2 | 1 | 32 | 1.497 | 2.183 | 34.09 / 33.91 / 34.09 | passed |
| n200-r2-h1 | 200 | 2 | 1 | 320 | 13.610 | 14.032 | 37.92 / 38.02 / 37.93 | passed |
| n1000-r2-h1 | 1000 | 2 | 1 | 1600 | 54.265 | 76.275 | 53.30 / 52.81 / 53.20 | passed |
| n5000-r2-h1 | 5000 | 2 | 1 | 8000 | 265.856 | 269.424 | 128.63 / 128.84 / 128.60 | passed |
| n200-r10-h1 | 200 | 10 | 1 | 1600 | 40.608 | 42.155 | 49.14 / 48.80 / 49.06 | passed |
| n1000-r10-h1 | 1000 | 10 | 1 | 8000 | 254.433 | 268.036 | 107.21 / 107.09 / 107.24 | passed |
| n200-r10-h3 | 200 | 10 | 3 | 4800 | 104.328 | 108.141 | 75.27 / 75.45 / 75.36 | passed |
| n1000-r2-h3 | 1000 | 2 | 3 | 4800 | 168.178 | 168.890 | 79.67 / 79.68 / 79.70 | passed |
| n1000-r10-h3 | 1000 | 10 | 3 | 24000 | 963.620 | 964.194 | 236.95 / 237.06 / 237.09 | passed |
| n1000-r2-h10 | 1000 | 2 | 10 | 16000 | 441.525 | 452.764 | 172.49 / 172.55 / 173.28 | passed |

原始 `projection_wall_ns`、`projection_cpu_ns`、`build_wall_ns`、`peak_*_bytes` 全部保留在各样本 JSON；上表换算是 ns/1e6、bytes/1048576，未做峰值相减。

## 4. 独立重算与核对

只读校验脚本 `verify_b18.py`（不重新执行测量、不替换采集器）：

- 从 36 份样本 JSON 独立重算 12 组的 median 与 nearest-rank p95，**逐组与 `summary.json` 相等**（含 3 个峰值数组）。
- 复算 `4N/5×R×H` 意见/合成 event 数、每组 `report_id`/`input_sha256` 唯一性、warmup 已丢弃。
- 独立按 `schema-index.json` 复核 **349/349** 份 Schema 哈希，执行前后两份结果文件字节相同（`43e09c8f…`）。
- 独立重算受保护映射（src/tests/schemas/md/tasks/overall、pyproject/uv.lock/AGENTS、源包、7 份准备文件，共 **555** 个文件）与采集器的 `protected-before.json` 相等（`cea30791…`），`protected-before == protected-after`。
- `git status --short` 执行前后均为 94 行且逐行相同；`git diff --stat` 未变。源码/测试/Schema/md/overall/采集脚本/执行单/设计均无改动。

## 5. 证据清单（关键项；全量见 `evidence-manifest.json`，163 条，自身排除）

| 文件 | 字节 | SHA256 |
|---|---:|---|
| `…124354767Z/summary.json` | 4041 | `31f87ee513b6adeb9cc7a3be57445664af0100b15beecae63e37fc6350aef90a` |
| `…124354767Z/environment.json` | 650 | `7979737b2c8e4d5767aedb7ddb8397e09cfa74c017603fbd1ff4e430d2dc5acc` |
| `…124354767Z/protected-before.json` / `-after.json` | 69848 | `cea307917e16aee54179fef2d50ebab41167270a92c5f7fa39fd9539a4bd71f1`（两者相同） |
| `…124354767Z/blank20-warmup.json` | 679 | `0e937d5dd4a7d20b18b1e7c6552c962467f9a2e60d452576b5ff63ce59d260ea` |
| `…124354767Z/blank20-rep-1.json` | 680 | `422ea209bac1e086b82ed632274cdd5309d7315b5c80692ed5b8a45364ab9e7b` |
| `…124354767Z/n1000-r10-h3-rep-3.json` | 712 | `0fc863d5332ae2fb61a9f6bcc85d4ea39751b9965dd89506118cb48aa6d5606e` |
| `…124354767Z.driver.log` | 326 | `f4934ada1d601c589ca895078035e4a12864eeaa0d9cbaabb547e129f884ee8c` |
| `…124354767Z.exit-code.txt` | 3 | `13bf7b3039c63bf5a50491fa3cfd8eb4e699d1ba1436315aef9cbe5711530354` |
| `…-verify…/verify_b18.py` | 10462 | `cb0e3663f04654e2b26abea5d395cb58824188d684f4574bbca604ef2755d363` |
| `…-verify…/verify-result.json` | 26962 | `159f6b30cf0fbe9cff825edd61def5383646dc6c5dafbc682bc1d33a8f685a33` |
| `…-verify…/schemas-before.json` / `-after.json` | 368 | `43e09c8f28509c7d88511f1ecd593ddd460fd1e302c96ff26ab4132df6fadd62`（两者相同） |
| `…-verify…/baseline.txt` | 409 | `d17103a1b34c18fd785a18b37e77c3265fbc333d71b82e20637516a0f4407aa3` |
| `…-verify…/evidence-manifest.json` | — | `971928be792228bd6ebd44c0c7848847810d35ca769207c83ddcdf1045c57183`（163 条清单） |

校验目录 `artifacts/b18-d01/deepseek-verify-20261025T124300Z-bootstrap/` 另含 `git-status-before/after.txt`、`git-diffstat-before/after.txt`、`build_manifest.py`、`list_key.py`（均为只读记录脚本/输出）。

## 6. 观察（只报告，不改实现）

- 最大点位 `n1000-r10-h3`（24000 条合成意见）中位 963.6 ms、峰值约 237 MiB；`n5000-r2-h1`（8000 条）中位 265.9 ms。
- 同 N 下 R 从 2 增到 10 显著抬升耗时（n1000-h1：54.3 → 254.4 ms）；H 从 1 增到 3/10 主要增加意见基数（n1000-r2：54.3 → 168.2 → 441.5 ms）。
- 各点数区间的三次离散度小（p95/中位多在 1.0–1.4 倍以内，`n1000-r2-h1` 为 1.41 倍）；3 点样本不足以推断总体尾延迟或置信区间。

## 7. 固定边界（原样保留）

- 本 D01 是 **typed-view 重验 + 投影微基准**；**来源绑定、真实事件历史、service 端到端、医学正确性、容量 SLO 均 not_checked**。
- `H` 是**合成历史意见轮次**，每条意见一个合成 `event_id`；这些 ID 只满足类型格式，未经内容 ID 或事件持久化核验，不是真实事件。
- `R` 是**声明的合成评审 ID 数量**，不是真实专家人数，也不是专家认证。
- 3 点 p95 = 最大值，**仅探索性**；不能推论总体尾延迟或置信区间。
- 峰值是**进程生命周期 Working Set**（含导入、构造、输入指纹），不能当阶段增量、Python 堆或私有提交量；不推算、不相减。
- 不联网、未安装、未读本地模型配置、未调用模型/OCR/蒸馏/训练、未读真实资料正文、无 commit/push。

## 8. 结论

`D01 executed_pending_review`：固定 12 组 × 3 次正式采集完成，48 个子进程与 36 份正式样本齐全，闭式预期、分组一致性、独立重算、349 份 Schema 与受保护输入前后哈希全部通过。**B18 整体仍未验收**，等 Codex 核验脚本、原始数据与统计后决定 D02；本单不归档、不推进 NEXT、不写性能门或医学门 passed。
