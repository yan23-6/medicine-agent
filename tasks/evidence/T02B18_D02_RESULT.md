# T02-B18-D02 执行结果（非敏感）

> 2026-10-25；状态：**executed_pending_review，待 Codex 核验**。
> 执行单：tasks/evidence/T02B18_D02_EXECUTION.md（未改动）。本文件只含计数、耗时、内存、哈希与错误码。
> 运行目录：`artifacts/b18-d02/deepseek-20261025T131045099Z/`（脚本新建，未覆盖 Codex smoke/边界目录）。

## 1. 环境、命令与冻结输入

- Python `3.13.15 (MSC v.1944 64 bit AMD64)`；Windows-10-10.0.19045-SP0；AMD64；12 逻辑核；pydantic 2.13.5；project 0.1.0；解释器 `.venv/Scripts/python.exe`。
- 冻结哈希：`b18_service_probe.py` `211d4f51…7e40937`；依赖的 `b18_progress_probe.py` `baa8a61f…168e729c`；设计 `1aecdba4…e1da3c8`；执行单 `8af24e36…0053631`。执行前后均未变。
- 源包 153943 字节 / `50742f7c…2f7786d`；准备目录 7 文件；349 份 Schema 存在（执行前后逐文件哈希相同）。
- 命令（仓库根，`PYTHONDONTWRITEBYTECODE=1`）：

```
.venv/Scripts/python.exe -B tasks/benchmarks/b18_service_probe.py --output artifacts/b18-d02/deepseek-20261025T131045099Z
```

退出码 **0**（`.exit-code.txt` = 0），整次 **305.96 秒**。未带 `--smoke`，未逐格重跑，未重试挑结果。

## 2. 完整性（7 profile / 28 格 / 112 进程 / 84 正式样本）

- 顶层 348 个文件 = 112 份样本 JSON（28 discard + 84 rep-1/2/3）+ 224 份 stdout/stderr + 7 份 `<case>-build.json` + `summary.json`、`environment.json`、`protected-before/after.json`、`negative-checks.json`。`build/fixture.json` 不混算为样本。
- `summary.json`：`status=executed_pending_review`、`smoke=false`、`profiles=7`、`cells=28`、`measured_samples=84`、`failure=null`、`protected_unchanged=true`。
- 每份样本 JSON 与自身 stdout 一致（除父进程追加的 `exit_code`/`discard`）；112 份 stderr 全为空；discard 不参与统计。
- 84 份正式样本全部 `status=passed`、`exit_code=0`、`discard=false`、`oracle_passed=true`、`fixture_unchanged=true`、`memory_status=measured`；`targets/reviewers/history_rounds/events/opinions` 逐份与设计表相符。
- 7 份 build JSON 与 `fixtures/<case>/fixture.json` 内容完全相同；`E=R×H`、`O=K×R×H` 逐 profile 成立（E≠O，未沿用 D01 一条意见一 event 的口径）；正常事件全部来自生产 `submit`。
- 每 profile/operation 的 6 份正式样本（跨 fresh/reused × 3 次）`logical_result_sha256` 与 `fixture_identity` 各自唯一一致；未跨 profile 比较身份。
- 独立校验脚本 **123 项检查全部通过**（`verify-result.json.passed=true`，`failed_checks=[]`）。
- 失败/超时：**无**。`memory_status` 无 `partial`/`not_evaluated`。

## 3. 28 格结果（中位/p95 ms，三次生命周期峰值 MiB）

计时段 = 生产 `ReviewSessionService.inspect` 或 `ReviewProgressService.report` 调用；不含进程启动、fixture 构建、服务实例化、oracle。`fresh` = 本进程开始时 workspace 不存在；`reused` = 同进程先做一次同操作验证后丢弃，再用同一 workspace 计时。

| case | N/R/H | E/O | 操作 | 模式 | 中位 ms | p95 ms | 三次峰值 MiB |
|---|---|---:|---|---|---:|---:|---|
| u2-r0-h1 | 24/0/1 | 0/0 | inspect | fresh | 662.227 | 665.156 | 100.79 / 100.73 / 100.72 |
| u2-r0-h1 | 24/0/1 | 0/0 | inspect | reused | 639.224 | 657.110 | 102.02 / 100.84 / 100.79 |
| u2-r0-h1 | 24/0/1 | 0/0 | report | fresh | 662.709 | 668.856 | 101.14 / 100.70 / 100.84 |
| u2-r0-h1 | 24/0/1 | 0/0 | report | reused | 623.519 | 716.469 | 101.01 / 101.00 / 100.80 |
| u2-r2-h1 | 24/2/1 | 2/38 | inspect | fresh | 707.669 | 726.266 | 101.09 / 101.05 / 100.98 |
| u2-r2-h1 | 24/2/1 | 2/38 | inspect | reused | 650.747 | 653.919 | 100.92 / 100.89 / 101.07 |
| u2-r2-h1 | 24/2/1 | 2/38 | report | fresh | 706.209 | 764.402 | 100.91 / 101.01 / 100.93 |
| u2-r2-h1 | 24/2/1 | 2/38 | report | reused | 645.601 | 674.077 | 101.96 / 101.21 / 101.01 |
| u10-r2-h1 | 120/2/1 | 2/192 | inspect | fresh | 802.998 | 807.032 | 104.25 / 103.86 / 103.79 |
| u10-r2-h1 | 120/2/1 | 2/192 | inspect | reused | 763.268 | 778.311 | 104.19 / 104.15 / 104.17 |
| u10-r2-h1 | 120/2/1 | 2/192 | report | fresh | 810.523 | 813.889 | 104.85 / 104.18 / 103.95 |
| u10-r2-h1 | 120/2/1 | 2/192 | report | reused | 722.740 | 724.872 | 104.59 / 104.28 / 104.50 |
| u40-r2-h1 | 480/2/1 | 2/768 | inspect | fresh | 1131.808 | 1214.548 | 115.00 / 115.21 / 115.03 |
| u40-r2-h1 | 480/2/1 | 2/768 | inspect | reused | 1035.656 | 1077.886 | 115.34 / 115.32 / 115.27 |
| u40-r2-h1 | 480/2/1 | 2/768 | report | fresh | 1161.151 | 1168.390 | 115.21 / 115.12 / 114.95 |
| u40-r2-h1 | 480/2/1 | 2/768 | report | reused | 1018.863 | 1020.765 | 115.32 / 115.26 / 115.70 |
| u10-r10-h1 | 120/10/1 | 10/960 | inspect | fresh | 942.723 | 967.111 | 104.63 / 104.91 / 104.48 |
| u10-r10-h1 | 120/10/1 | 10/960 | inspect | reused | 883.627 | 893.561 | 105.85 / 105.45 / 105.60 |
| u10-r10-h1 | 120/10/1 | 10/960 | report | fresh | 1017.544 | 1070.437 | 104.55 / 104.68 / 104.56 |
| u10-r10-h1 | 120/10/1 | 10/960 | report | reused | 1018.335 | 1020.185 | 109.46 / 109.18 / 109.35 |
| u10-r2-h5 | 120/2/5 | 10/960 | inspect | fresh | 1024.833 | 1038.250 | 104.74 / 104.71 / 104.76 |
| u10-r2-h5 | 120/2/5 | 10/960 | inspect | reused | 1118.423 | 1168.176 | 105.96 / 105.71 / 105.93 |
| u10-r2-h5 | 120/2/5 | 10/960 | report | fresh | 1158.137 | 1199.786 | 104.73 / 104.79 / 104.79 |
| u10-r2-h5 | 120/2/5 | 10/960 | report | reused | 947.732 | 980.434 | 109.19 / 109.38 / 109.50 |
| u10-r10-h3 | 120/10/3 | 30/2880 | inspect | fresh | 1434.733 | 1487.346 | 111.34 / 111.29 / 111.21 |
| u10-r10-h3 | 120/10/3 | 30/2880 | inspect | reused | 1336.148 | 1500.688 | 112.15 / 111.88 / 112.40 |
| u10-r10-h3 | 120/10/3 | 30/2880 | report | fresh | 1684.162 | 1707.650 | 111.41 / 111.23 / 111.20 |
| u10-r10-h3 | 120/10/3 | 30/2880 | report | reused | 1374.246 | 1385.905 | 122.38 / 122.66 / 121.11 |

原始 `wall_ns`、`cpu_ns`、`lifetime_peak_before/after_bytes`、`logical_result_sha256`、`fixture_identity` 保留在 112 份样本 JSON 与 28 组 summary 中；换算为 ns/1e6、bytes/1048576，未做任何峰值相减。

## 4. 负例与非计时检查

`negative-checks.json`（在两个独立副本上、**先预热 workspace** 后注入）：

- `source`：翻转源包一字节后 `SESSION_SNAPSHOT_INVALID`，`status=passed`，`after_workspace_warmup=true`。
- `event`：改事件理由但不重封 hash → `metrics_available=false`、`engineering_gate=blocked`、`diagnostic_codes` 含 `SESSION_EVENT_INVALID`、无 coverage/pairwise，`status=passed`，`after_workspace_warmup=true`。
- 损坏只发生在 `negative-source/`、`negative-event/` 副本；7 个正常 fixture 的 `fixture.json.files`（packages/session/preparation 全字节）在本轮结束后逐文件复核仍相同。

## 5. 独立重算与不变性

- 从 84 份正式样本独立重算 28 格的 `median` 与 nearest-rank p95（=最大值），**逐格与 `summary.json` 相等**（含三次峰值数组）。
- 123 项机械检查含：样本/stdout/stderr 完整性、7 份 build≡fixture、U/N/K/E/O 与设计表逐行、E=R×H、O=K×R×H、6 份样本身份一致、28 格统计、两负例、protected 前后、脚本/设计/执行单哈希。
- 受保护映射 **555 个文件**（src/tests/schemas/md/tasks/overall、pyproject/uv.lock/AGENTS、源包、7 份准备文件）独立重算与采集器 `protected-before` 相同，且 `protected-before == protected-after`（`cea30791…`）。
- 349/349 份 Schema 哈希相符，执行前后两份核对文件字节相同（`f539dedf…`）。
- `git status --short` 前后均 98 行且逐行相同；`git diff --stat` 未变；`git diff --check` 通过。src/tests/Schema/md/overall/两采集器/设计/执行单均未改。

## 6. 证据清单

| 文件 | 字节 | SHA256 |
|---|---:|---|
| `…131045099Z/summary.json` | 9149 | `ffaa1f9097f35c225c3ccd861d9dee71d815fc7216d10c731ca39b8634c3cedd` |
| `…131045099Z/environment.json` | 774 | `0477b3c0d631f8ad1c5825238409734dc554b39e2a5d755cab18e0a413e2e1b4` |
| `…131045099Z/negative-checks.json` | 278 | `83c02778e8c56bb88d34f2def907e69b329204610e6a0b8cfcdc253cec2f3887` |
| `…131045099Z/protected-before.json` / `-after.json` | 69848 | `cea307917e16aee54179fef2d50ebab41167270a92c5f7fa39fd9539a4bd71f1`（相同） |
| `…131045099Z.driver.log` | 326 | `a35636ac107dfdab2b6bc14f82f455a5cc471cec34849db925bddb1fcb69364f` |
| `…131045099Z.exit-code.txt` | 3 | `13bf7b3039c63bf5a50491fa3cfd8eb4e699d1ba1436315aef9cbe5711530354` |
| `…-verify…/verify_b18_d02.py` | 14378 | `f1f899b75fac52a34d702944d8ef03f02a01432e326b71b0bd695575cd0add5e` |
| `…-verify…/verify-result.json` | 55980 | `5df3c674020fc469bb19b18e6175d60146a589fef52ddefb380b467391cbea38` |
| `…-verify…/schemas-before.json` / `-after.json` | 58 | `f539dedfe3cef46a0ca4a507c6e899263c9f6b30a42a287ba7292352936a8ad8`（相同） |
| `…-verify…/baseline.txt` | 580 | `1f42cf284dcb1c8e7ec336f3197c83b10171703cc203bde954c9d4ceec0c2992` |
| `…-verify…/evidence-manifest.json` | — | `f17c5f0a804f2b5d370d9607cd5398d80a9f563ad56ae052b0c2345995d948de`（1369 条） |

证据清单覆盖运行目录全部非缓存文件、`.driver.log`/`.exit-code.txt` 与校验目录（共 1369 条，排除自身）；`workspaces/`（2912 个文件、20655632 字节）是私有可重建缓存，不列为测量证据。清单内含全部 112 份样本 JSON 与 7 份 fixture 记录。

## 7. 观察（只报告，不优化）

- 全部 28 格落在约 **0.62–1.71 秒**；最小 N 的 `u2-r0-h1`（24 目标、0 意见）已需 623–663 ms，说明该段以源包/快照重建与事件历史重验为基线成本，不是目标数独大。
- `u10-r10-h1`（E=10,O=960）与 `u10-r2-h5`（E=10,O=960）N/O/E 相同但耗时不同（report fresh 1017.5 vs 1158.1 ms），声明人数、链长、最新意见数与输出 pair 行数仍在变，**不能归因单一因素或断言 R² 是瓶颈**。
- `reused` 在多数格低于 `fresh`（如 `u10-r2-h1` report 810.5→722.7 ms、`u10-r2-h5` report 1158.1→947.7 ms），但并非全部（`u10-r2-h5` inspect reused 反而更高、`u10-r10-h3` inspect reused p95 1500.7 > fresh 1487.3），离散度与 3 点样本不足以推断因果。
- 生命周期峰值约 **100.7–122.7 MiB**；`reused` 峰值含同进程预调用，个别格偏高（如 `u10-r10-h3` report reused 122.4 vs fresh 111.4），**不能相减当缓存增量**。

## 8. 固定边界（原样保留）

- 这是 **Service 操作**测量：不含进程启动、fixture 构建、服务实例化、正确性校验或业务 CLI。
- 构造数据全自制、适配器模拟（本地确定性函数），**无临床真实性**，不是外部模型/OCR。
- `fresh`/`reused` **仅指私有工作区**，不是 OS 冷/热缓存；未清系统缓存；哈希读取本身会影响 OS 缓存。
- `reused` 的同进程预调用不计入墙钟，但进入生命周期峰值；**不可相减峰值**，也不可把 inspect 与 report 中位数相减当作阶段开销。
- 3 点 p95 = 最大值，**仅探索性**，不能推论总体尾延迟/置信区间。
- 同 N/O/E 对照仍有链长、最新意见数、输出行数等差异，**不断言单因果瓶颈**。
- 来源绑定/实际提交历史只对这些**自制 fixture**经生产 API 验证，不等于真实跨源、临床、跨平台、容量 SLO 或整包抗恶意回滚。

## 9. 结论

`D02 executed_pending_review`：7 profile × 2 操作 × 2 工作区模式的 28 格、112 个采集进程、84 份正式样本全部完成且通过机械核对；两负例正确阻断；349 份 Schema、555 文件受保护映射与源输入未变。**结果仅待 Codex 核验，B18 是否整体完成由 Codex 回到原产品目标判断**；本单未归档、未改 NEXT、未写性能/医学/阶段门 passed。
