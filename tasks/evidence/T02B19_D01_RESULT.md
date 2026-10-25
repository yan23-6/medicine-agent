# T02-B19-D01 执行结果（非敏感）

> 2026-10-25；状态：**executed_pending_review，待 Codex 核验**。
> 执行单：tasks/evidence/T02B19_D01_EXECUTION.md（未改动）。只含计数、哈希、身份与阶段名，不含查询正文或真实材料。
> 运行目录：`artifacts/b19-d01/deepseek-20261025T135227499Z/`（脚本新建，未覆盖 Codex 小样目录）。

## 1. 环境、命令与冻结输入

- Python `3.13.15 (MSC v.1944 64 bit AMD64)`；Windows-10-10.0.19045-SP0；pydantic 2.13.5；解释器 `.venv/Scripts/python.exe`。
- 冻结哈希：`b19_library_check.py` `0cd549f6…96c3f092`；依赖的 `b18_progress_probe.py` `baa8a61f…168e729c`；设计 `58830a65…5c99ac1`；执行单 `acdebe3a…ed9a681c`。执行前后均未变。
- 源包 153943 字节 / `50742f7c…2f7786d`；准备目录 7 文件；349 份 Schema 存在且执行前后逐文件哈希相同。
- 命令（仓库根，`PYTHONDONTWRITEBYTECODE=1`）：

```
.venv/Scripts/python.exe -B tasks/benchmarks/b19_library_check.py --output artifacts/b19-d01/deepseek-20261025T135227499Z
```

退出码 **0**（`.exit-code.txt` = 0），整次 **100.61 秒**。未带 `--smoke`，未逐 profile 重跑。

## 2. 完整性

- `summary.json`：`status=executed_pending_review`、`smoke=false`、`expected_profiles=[1,5,20]`、`completed_profiles=3`、`failure=null`、`protected_unchanged=true`。
- 三份 `sources-1/5/20.json` 均 `status=passed`、`exit_code=0`、`stages=9`；与各自 stdout 一致（仅多 `exit_code`）；三份 stderr 全为空。
- 每 profile `corpus.json` 有 S 行，`source_id/source_sha256/component_id/bundle_id` 各 S 个互不相同；owner 按 index 奇偶 `author-a`/`author-b`；S>1 的公共查询同时返回两 owner。
- 每 profile 9 条 `stages.json`，合计 **27 条**，名称/顺序/匹配数/可读文件/隔离数与设计表逐行相符。
- 独立校验脚本 **117 项检查全部通过**（`verify-result.json.passed=true`，`failed_checks=[]`）。
- 无失败、无超时、无未评估项；本单不是计时实验，不报中位/p95。

## 3. 27 行阶段结果

`owner` 列 a=`author-a`、b=`author-b`；身份检查 = `(component_id,node_id)` 集合与独立 oracle 相等且节点/来源/证据哈希通过。

| profile | stage | 匹配节点 | 独立来源 | owner | 可读文件 | 隔离 | 身份检查 |
|---|---|---:|---:|---|---:|---:|---|
| 1 | initial-common | 1 | 1 | a | 1 | 0 | pass |
| 1 | unique-source-0 | 1 | 1 | a | 1 | 0 | pass |
| 1 | exact-copy-deduplicated | 1 | 1 | a | 2 | 0 | pass |
| 1 | bad-file-isolated | 1 | 1 | a | 2 | 1 | pass |
| 1 | primary-removed-copy-retains-source | 1 | 1 | a | 1 | 1 | pass |
| 1 | last-copy-removed-no-stale-content | 0 | 0 | — | 0 | 1 | pass |
| 1 | removed-unique-token-absent | 0 | 0 | — | 0 | 1 | pass |
| 1 | restored-same-identities | 1 | 1 | a | 1 | 1 | pass |
| 1 | migrated-copy-only-new-workspace | 1 | 1 | a | 1 | 1 | pass |
| 5 | initial-common | 5 | 5 | a,b | 5 | 0 | pass |
| 5 | unique-source-0 | 1 | 1 | a | 5 | 0 | pass |
| 5 | exact-copy-deduplicated | 5 | 5 | a,b | 6 | 0 | pass |
| 5 | bad-file-isolated | 5 | 5 | a,b | 6 | 1 | pass |
| 5 | primary-removed-copy-retains-source | 5 | 5 | a,b | 5 | 1 | pass |
| 5 | last-copy-removed-no-stale-content | 4 | 4 | a,b | 4 | 1 | pass |
| 5 | removed-unique-token-absent | 0 | 0 | — | 4 | 1 | pass |
| 5 | restored-same-identities | 5 | 5 | a,b | 5 | 1 | pass |
| 5 | migrated-copy-only-new-workspace | 5 | 5 | a,b | 5 | 1 | pass |
| 20 | initial-common | 20 | 20 | a,b | 20 | 0 | pass |
| 20 | unique-source-0 | 1 | 1 | a | 20 | 0 | pass |
| 20 | exact-copy-deduplicated | 20 | 20 | a,b | 21 | 0 | pass |
| 20 | bad-file-isolated | 20 | 20 | a,b | 21 | 1 | pass |
| 20 | primary-removed-copy-retains-source | 20 | 20 | a,b | 20 | 1 | pass |
| 20 | last-copy-removed-no-stale-content | 19 | 19 | a,b | 19 | 1 | pass |
| 20 | removed-unique-token-absent | 0 | 0 | — | 19 | 1 | pass |
| 20 | restored-same-identities | 20 | 20 | a,b | 20 | 1 | pass |
| 20 | migrated-copy-only-new-workspace | 20 | 20 | a,b | 20 | 1 | pass |

三 profile 复用同一配方（S=1/5/20），**不相加宣称 26 个独立来源**。

## 4. 独立核对要点

- `initial / duplicate / bad-file / primary-removed / restore / migration` 六阶段 `identity_set` 完全一致；`last-copy-removed` 恰为初始集合去掉第 0 来源 `(component_id,node_id)`；`unique-source-0` 初始只含第 0 来源；`removed-unique-token-absent` 为 0 匹配且身份集为空（S=1 时最后副本移出后为 0，未从缓存复活）。
- 精确副本只增加物理可读文件数（S+1），命中节点/独立来源不翻倍（20 来源仍 20 节点/20 源）。
- `broken.medpkg` 从 `bad-file-isolated` 起始终 `quarantined` 且 `PACKAGE_FILE_INVALID`，正常包含法与身份不受影响。
- 所有阶段 `public_bytes_unchanged=true`；正常归档字节与构建值相同，`exact-copy.medpkg`/`holding/copy.medpkg` 与源 0 SHA 相同，`broken.medpkg` 恒为固定 20 字节 `not a medpkg archive`。
- 迁移：原 `knowledge/inputs/generation/query-cache` 四路径均不存在；`retired/` 保留四目录；`migrated-knowledge` 仅公开交付内容（S 份正常归档 + broken + `package-spec.json` + `数据包说明书.md` + `.package-publish.lock`）；`migration-fresh-cache` 独立存在；`retired/knowledge` 与 `migrated-knowledge` 逐字节相同；`retired/inputs/*.txt` 的 SHA 与 `corpus.source_sha256` 逐一相等且保留终止换行。
- 结果恒为 `medical_review=unreviewed`、`consultation_available=false`、无用户意见/复核错误；`query.packages` 未被当作命中数（按 `medical_nodes` 展平）。

## 5. 保护与不变性

- 受保护映射 **555 个文件**（src/tests/schemas/md/tasks/overall、pyproject/uv.lock/AGENTS、真实源包、7 份准备文件）独立重算与采集器 `protected-before` 相同，且 `protected-before == protected-after`（`44965e9c…201525`）。
- 349/349 份 Schema 哈希相符，执行前后两份核对文件字节相同（`f539dedf…`）。
- `git status --short` 前后均 105 行且逐行相同；`git diff --stat` 未变；`git diff --check` 通过。src/tests/Schema/md/overall/两采集器/设计/执行单均未改，未改 NEXT。

## 6. 证据清单

| 文件 | 字节 | SHA256 |
|---|---:|---|
| `…135227499Z/summary.json` | 1573 | `460d95b5e61baa03acb99f228b05dd74f02df51f5d0ca8095671b00c2fdaff53` |
| `…135227499Z/environment.json` | 410 | `ae115122488012aa6e9323643e28df57869218edaeaef711c6711c7b4089b35a` |
| `…135227499Z/sources-1.json` / `-5.json` / `-20.json` | 412 / 412 / 414 | `84835e96…9db73` / `96cfb4f4…24797b` / `3f96f2cc…ddd968` |
| `…135227499Z/protected-before.json` / `-after.json` | 69848 | `44965e9c8a2cd17f105cf85f8cd5d57f55fc795ba30eb9691f784ec6fc201525`（相同） |
| `…135227499Z.driver.log` | 328 | `6d72914255fdb33a77d0d7905f5b7ba16fa212aa1186b3922b8d3c8a8fe7f8a0` |
| `…135227499Z.exit-code.txt` | 3 | `13bf7b3039c63bf5a50491fa3cfd8eb4e699d1ba1436315aef9cbe5711530354` |
| `…-verify…/verify_b19.py` | 12817 | `25d4ba02f23b66cfdbc8d0b28f29f5564c9d2038b2dd12ee955d415298b3fa17` |
| `…-verify…/verify-result.json` | 13892 | `61e76b227a780ec389d730a342441b15e578a1d42460115e1d3a0a70547ea8a5` |
| `…-verify…/schemas-before.json` / `-after.json` | 58 | `f539dedfe3cef46a0ca4a507c6e899263c9f6b30a42a287ba7292352936a8ad8`（相同） |
| `…-verify…/baseline.txt` | 577 | `75a5d4f152653e0ccc9f82390550ceec910bfa58fd8268ac930efce5bc9f4ed1` |
| `…-verify…/evidence-manifest.json` | — | `4b38db82aca6617f586d2bfb4d1bf6704c218e3d8d1b399f454f48ea4fb323fa`（1543 条） |

清单覆盖运行目录全部非缓存文件（自制输入、包、holding、retired、migrated-knowledge、corpus/stages）与校验目录，共 1543 条且排除自身；`query-cache`/`migration-fresh-cache`（2659 个文件、2197906 字节）是私有可重建缓存，单列而不当测量证据。

## 7. 固定边界（原样保留）

- 只验证现有实验单文件 `.medpkg-0.1.0`、原生 TXT / `theory` 自制数据；**不代表真实跨源医学正确性、五类资料全面覆盖、权限认证、正式包 v0、LadybugDB、多跳/向量/并发或异机跨平台认证**。
- 无临床输出：`medical_review=unreviewed`、`consultation_available=false`；无性能 SLO、无医学/许可/性能门升级。
- 三个 profile 同配方重复，不是 26 个独立来源；同进程同机执行，不是跨机器/跨平台认证。
- 任何产品缺陷由 Codex 判断与修复；本单只记录，不改预期、不改采集器、不改 src/tests/Schema。

## 8. 结论

`D01 executed_pending_review`：1/5/20 三 profile、27 阶段、9 阶段模板全部按固定预期通过；副本去重、坏包隔离、移出/恢复身份稳定、只复制公开目录的迁移与全新工作区查询均有独立身份与字节证据；349 份 Schema 与 555 文件保护映射未变。**B19 是否整体验收由 Codex 回读原产品要求判断**；本单未归档、未推进 NEXT、未写任何门 passed。
