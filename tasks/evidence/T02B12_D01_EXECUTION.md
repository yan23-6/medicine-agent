# T02-B12-D01：前置核查与契约清单（DeepSeek执行单）

> 2026-10-24；ready，尚未执行。属于CURRENT的子步骤，不是另一个正式任务。
> 用户安排：Codex设计任务，DeepSeek在同一工作区执行，用户通知后Codex核验。

## 目标和边界

收集B12设计需要的机械核查证据，不作新设计、不实现B12、不修复失败。本单完成后停止，等待Codex核验；不得直接执行NEXT或编写会话实现。本单不是医学评审，也不是生产级快照校验器验收。

工作目录：`D:/test/tongyongzhengliu`。禁止同时由两个助手修改本工作区。

先按AGENTS顺序读取STATE、CURRENT、HANDOFF、NEXT、ROADMAP，再读本单及以下文件：

- `md/09-评审评价与临床验证.md`、`md/18-候选复核与更正记录.md`；
- `tasks/evidence/T02B11_REVIEW_PREPARATION_DESIGN.md`；
- `src/medicine_agent/domain/review_preparation.py`、`domain/reviews.py`、`domain/ids.py`（后两项相对src/medicine_agent）；
- `src/medicine_agent/analysis/review_preparation.py`、`analysis/reviews.py`、`packages/tcm.py`；
- `schemas/review-preparation/schema-index.json`、`schemas/review/schema-index.json`。

## 可写范围与交付

只允许新建：

1. `tasks/evidence/T02B12_D01_RESULT.md`：非敏感结果摘要；
2. `artifacts/b12-d01/<本次唯一目录>/`：本次核查脚本、汇总JSON、命令日志、测试临时目录；禁止覆盖既有运行目录；
3. 按仓库规则更新STATE、HANDOFF、CURRENT中本单的进度，保留B12其余范围暂停和待Codex核验的边界。

本执行单保持不改。禁止修改src、tests、schemas、md、docs、log、config、pdfs、归档、原包、原准备目录、Git配置及忽略规则。禁止commit/push、安装依赖、联网、OCR、蒸馏、模型API调用、生成意见或读取本地模型配置。不重新导出已有B11材料。

DeepSeek作为执行助手只能查看本单指定的代码及非敏感摘要；不要向其聊天、工具输出或服务发送真实PDF、OCR原文、候选正文、密钥或完整preparation.json。真实材料只能由本地脚本读取并输出下述计数/哈希/布尔结果。若harness自动向模型上传文件正文，禁止用该功能读取真实材料。

## 步骤1：记录基线

记录`git rev-parse HEAD`、`git status --short`、Python版本、`git diff --stat`。本单交付时已有任务文档改动，不要求工作区干净；记录实际基线，不能清理、回滚或覆盖他人改动。

记录源包目录顶层文件及准备目录全部文件的相对文件名、字节数、SHA256，作为结束时的对照；不记录正文。

输入固定为：

- 包：`artifacts/b7-real-compat/model-knowledge/bundle_a7c24a2ba66c6200241e87e0.medpkg`；153943字节；SHA256 `50742f7c32f7178c562ba2927ae070feac1e82696f7f86792157090fe2f7786d`。
- 快照：`artifacts/b11-review-preparation/materials/preparation_718bf6c856acd871970f3eea/`。
- 准备ID：`preparation_718bf6c856acd871970f3eea`。

缺失、权限不足、哈希不同、出现并发改动时，记录具体事实并停止依赖步骤；不重建、不重蒸馏、不修改权限。

## 步骤2：本地只读核查

用`.venv/Scripts/python.exe`运行本次新建的短核查脚本。仅使用标准库及已有项目依赖，设置`PYTHONDONTWRITEBYTECODE=1`避免写源码缓存。不得载入完整原文到模型上下文。

逐项输出expected、actual、passed/failed（无法验证时not_checked及原因）：

1. 目录恰为7个普通文件：`manifest.json`、`preparation.json`、`README.md`、`source-annotations.md`、`candidates.md`、`anomalies.md`、`quality-gates.md`；无额外目录、链接或reparse point。先检查清单及路径边界，再按清单读文件，禁止跟随未知路径。
2. manifest.files恰好列出上述6份正文；无绝对路径、父路径或重复JSON键；逐文件实际SHA256等于manifest声明。JSON重复键应用标准库object_pairs_hook显式拒绝，不能由默认解析静默覆盖。
3. 用既有ReviewPreparationExport、ReviewPreparationReport验证类型，分别核对version=0.1.0、status=complete、准备ID一致、medical_review=unreviewed、release_allowed=false。类型通过只代表这一项通过。
4. 按现有prepare实现，用`stable_id('preparation', report.model_dump(mode='json', exclude={'preparation_id'}))`重新计算并比较ID；不另造规范化规则。
5. 实际数组及分类计数与report.counts分别核对：sources=188、candidates=541、node=63、fact=478、stated=345、inferred=133、gap=27、rejected_candidate=1、issues=0。不要仅打印report.counts就算通过。
6. 所有source/candidate/anomaly的worksheet.reviewer/decision/reason均为null、submitted=false；review_records长度0；所有候选user_review_state=unreviewed；异常writable_review_target=false。只输出异常数量和字段名，不输出原文、值或理由。
7. 对两个指定Schema目录，逐一核对schema-index.files列出的文件存在及其SHA256；分别报告实际核对数量。不重新导出或改写Schema。
8. 再核对步骤1的源包目录与准备目录文件集合、大小、哈希全部不变。

本单不要求从真实包重算每个目标指纹，也不调用PackageCatalog写接口。明确把“材料来源身份与目标指纹相对源包重验”标成not_checked，不能宣称完成B12快照可信校验。

## 步骤3：整理代码位置表

只记录现状，每行给出仓库相对路径、符号和经核实的行号；未找到写“未找到”，不猜测、不编码。表格固定为以下8行：

| 检查项 | 现有生成/校验符号及位置 | 是否已有准备目录读入入口 | 后续设计待定点 |
|---|---|---|---|
| manifest资源集合与路径边界 | 待填 | 待填 | 待填 |
| 导出文件哈希 | 待填 | 待填 | 待填 |
| Report稳定ID | 待填 | 待填 | 待填 |
| 来源/材料身份 | 待填 | 待填 | 待填 |
| ReviewTarget定位和fingerprint | 待填 | 待填 | 待填 |
| expected_previous_id与意见历史 | 待填 | 待填 | 待填 |
| worksheet与ReviewRequest决定差异 | 待填 | 待填 | 待填 |
| gap/隔离项的不可写边界 | 待填 | 待填 | 待填 |

“后续设计待定点”只摘录CURRENT已有要求或写待Codex设计，不自行决定新版本、事务粒度、独立评审者认证或仲裁规则。不得把导出时检查当作已有导入校验。

## 步骤4：固定合成回归

步骤1—2通过后只跑一次下列范围，不跑全量、真实验收脚本或任何live测试。先确认这两个测试文件及实际存在且会被加载的conftest不调用真实服务；不存在conftest本身不是阻塞，不确定是否调用真实服务则停止报告。

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
.venv/Scripts/python.exe -m pytest tests/test_review_preparation.py tests/test_reviews.py -q -p no:cacheprovider --basetemp artifacts/b12-d01/<本次唯一目录>/pytest-tmp
git diff --check
```

将占位目录替换成本次实际目录。记录命令、退出码、通过/失败/跳过数量和耗时；不照抄历史88/208等数字。测试失败保存简短错误定位后停止，不重试、不删测试、不修代码。日志意外含真实材料时不复制进结果摘要或聊天。

## 步骤5：交回

RESULT包括：基线、逐项结果、8行代码位置表、测试统计、产物相对路径及哈希、开始/结束的受保护输入哈希对比、与基线相比的新增修改文件、失败或not_checked列表。

每完成一个步骤，在STATE/HANDOFF/CURRENT的D01进度中同步事实。顺利完成写“D01 executed_pending_review，待Codex核验”，不能写B12 done，也不创建B12验收归档、不推进NEXT。若中途异常，写“D01 stopped”与具体阻塞，不把未跑步骤写通过。

最终只向用户报告摘要与RESULT路径，然后停止。由用户通知Codex，再由Codex检查实际脚本、文件和必要复验。
