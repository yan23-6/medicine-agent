# T02-B7 真实材料兼容与代表性复验

> 验收日期：2026-10-18
>
> 状态：done（限定五页的软件生产消费闭环；不是医学验收）

## 范围与路径选择

真实旧 B4/B5 包未恢复。远程 fetch 已成功，Git 当前分支和全部已获取历史未发现 `.medpkg`；历史报告明确这些包只在被忽略的 artifacts 中，详见 `tasks/evidence/B7_REMOTE_PACKAGE_AUDIT.md`。

本任务采用预先允许的另一验收路径：用户恢复本地配置，并明确授权仅将教材物理页34—38的 OCR 文本发送到该配置对应的模型服务，重建当前格式语义包。未外发 PDF 或页面图像，未扩大到其他页。没有声称已完成真实旧包兼容核验。

## 实际产物

| 项目 | 实际结果 |
|---|---|
| 任务 | `learning_1bbcfa1a7a4447f38ddb1a4d52ae891d` |
| 子任务 | `analysis_e46f9710baa74384b55739d5e78f45eb` |
| 成品 | `artifacts/b7-real-compat/model-knowledge/bundle_a7c24a2ba66c6200241e87e0.medpkg` |
| 大小 | 153,943 字节 |
| SHA256 | `50742f7c32f7178c562ba2927ae070feac1e82696f7f86792157090fe2f7786d` |
| 来源包身份 | `pkg_9c8e2f1d789fc5fdadabfc9c` |
| 协议 | 实验 `.medpkg@0.1.0`，`tcm-knowledge@0.2.0`，语义0.3.2 |
| 原始证据 | 188条，与先前 extractive 包逐条完全一致，包括身份、原文和位置 |
| 节点 | 63个，五页分别14/11/13/13/12个，全部 unreviewed |
| 医学字段候选 | 478项：stated 345、inferred 133；这些状态是候选声明，不是专家判断 |
| 隔离审计 | 1条 NODE_REJECTED，保留原候选及证据引用，未阻断其他有效内容 |
| 缺口 | 27条图级及节点级 gap，不等于27个遗漏知识点 |

真实包、OCR、任务数据库、构建发行物与验证明细留在被忽略的 `artifacts/b7-real-compat/`；此文只记录非敏感摘要。原件指纹及 OCR 过程见 `tasks/evidence/B7_LOCAL_EXTRACTION.md`。

## 生产与恢复

1. 一次性验收脚本核对原件/快照SHA256、适配器版本、文档格式、页码、DocumentUnit结构和检查点哈希，将五页真实 OCR 转入独立模型任务。未复用旧 extractive 分析；此脚本不等于产品已有公开的跨模式检查点导入 API。
2. 原五次真实 OCR 调用记录经核验作为 inherited_runs 保存，不伪造新的 OCR 调用。
3. 最初沙箱连接失败，沙箱外长请求超时；不含教材的短请求成功。随后仅在本次运行中设置600秒请求超时参数，未修改本地配置。
4. 第34页成功后实际暂停（analyzed=1、next_unit=35），再用另一进程完成35—38页。五次成功分析工具调用耗时约174/138/260/151/223秒，包含工具内部可能发生的结构纠正；不能据此推算HTTP请求次数。
5. 五页分析完成后最终封装曾失败，半成品未发布。修复后只恢复构建，未重新OCR或重新请求模型，最终 completed、errors=[]。

## 发现并修复的缺陷

`packages/owned.py` 的缓存校验重建了节点和缺口，却没有汇总 `rejected_candidates`，导致含真实隔离项的包被误报为“Packaged graph differs from committed analysis”。

修复为按单元汇总隔离记录，并参与完整图比对，不放松来源或完整性校验。新增匿名/具名贡献者的两项回归，覆盖多单元隔离记录保留及删改记录后拒绝：修复前两项复现失败，修复后通过。未修改已提交医学分析值。

## 消费与迁移验收

- 当前包完整性、图身份、逐字引文与来源校验通过；188条证据与提取基线全量一致。
- 来源类型、医学体系、知识类型、证据/审核状态和主题组合筛选通过；错误来源类型无命中。
- 本材料没有声明 tcm_layer；未知层次过滤返回空，未为通过验收强填分类。
- 真实节点多种子查询、max_hops=0、max_nodes=1截断和缺失种子审计通过。
- 当前只有一个真实来源，无显式跨源关系、异名候选或概念合并。空候选不自动产生关系；真实跨来源正例仍未覆盖，软件正例由回归测试承担。
- 仅复制同一个 `.medpkg` 到 `model-isolated/`，使用独立 wheel 安装环境和 `python -I` 完成相同查询与追溯；模块实际来自 site-packages，不复制 PDF、配置或分析工作区。
- 两次验证中包哈希均不变；返回 medical_review=unreviewed、consultation_available=false。
- 隔离验证为同台Windows/Python 3.13，未冒称第二台实体电脑或跨操作系统验收。

本地及隔离摘要分别保存在 `verification.json`、`isolated-verification.json`。多轮校验/查询耗时数分钟，未逐查询计时；不得把这次功能通过写成性能达标。B8须评估完整校验、注册表重复加载、索引重建及热查询的开销。

## 软件验证与构建

- 定向回归：70 passed，121.48秒。
- 修复后全量：141 passed，266.99秒。
- 修复后重新构建 wheel/sdist，并重装独立环境；最终逐文件核对108个源码/资源文件与源码完全一致，发行物无原PDF、密钥、知识包或运行缓存。
- 公共契约未变化，不为本次校验器修复升级Schema或混用分析策略。
- 没有修改 docs、log、原始PDF或本地密钥；没有提交或上传真实运行包。

## 接手与复查

不要再次 submit 或重新请求模型。恢复的包先核对上述SHA256，再用已有产品接口只读检查，例如：

```powershell
.\.venv\Scripts\medicine-agent.exe analyze status learning_1bbcfa1a7a4447f38ddb1a4d52ae891d --workspace artifacts/b7-real-compat/model-work
.\.venv\Scripts\medicine-agent.exe analyze query --packages artifacts/b7-real-compat/model-knowledge --workspace artifacts/b7-real-compat/recheck-work --text 阴阳 --max-hops 0 --max-nodes 5
```

新克隆不会携带这些运行产物。应恢复校验过的包或授权备份，而不是从历史“done”推断文件存在。Git代码备份与知识包备份分开；异地备份目的地尚未授权，不擅自上传。

下一任务仅允许重评B8质量门：人工金标准、推断字段、缺口与隔离项复核、病例基线、代表范围和查询性能；不直接开始整书蒸馏或地图式问诊。
