# T02-B11 复核准备与质量门复验

> 日期：2026-10-18；状态：done（软件、真实只读和独立安装通过；不是医学确认）。

## 交付

- [实现前设计](../../evidence/T02B11_REVIEW_PREPARATION_DESIGN.md)，稳定设计第09/12/18章、运行说明同步。
- domain/review_preparation.py：独立review-preparation/0.1.0的10个模型，schemas/review-preparation快照；不改医学注册表、包协议或ReviewRequest/Record。
- ReviewPreparationService.prepare()/export()及analyze review-prepare；复用B10盘点和现有ReviewTarget/队列构建，不新增Agent或Skill。
- 全部独立原文、全部节点/字段目标、graph/node gaps、原隔离审计、空白表、八项质量门；完整JSON与分步Markdown，自包含迁移。
- 新目录原子导出及逐文件哈希，不写源目录，不覆盖已有导出；坏文件隔离、健康文件继续，partial/empty显式标识。

复用的队列构建函数不再依赖目录写入；原清单中“已获暂时认可”“先看前三条”“聊天中按编号”等历史绑定文案已移除。旧用户意见与新模板分开，同一目标的可追溯历史链保留最新意见，冲突/分支/失效指纹不选择最终认可；均不升级医学状态。

## 软件验证

新增25项准备回归，联合既有reviews/coverage/file-learning共88 passed，104.93秒。包括未引用证据、stated/inferred、跨页、低识字置信、graph/node gaps和隔离项、缺页/旧revision、坏包、重复/输入顺序、历史链/分支/坏记录/指纹失效、扫描变化、导出失败/竞态/路径、CLI和Schema。全部为自制适配器与模型软件夹具，不是实际OCR或医学准确率。

最终完整回归208 passed，271.75秒；不同批次不相加。准备专项25项是新增用例数，联合定向88项包含既有回归。

## 真实只读与独立安装

包bundle_a7c24a2ba66c6200241e87e0.medpkg，153943字节，SHA256 50742f7c32f7178c562ba2927ae070feac1e82696f7f86792157090fe2f7786d。原件指纹031007fc2caa796ed6b72f8b6ea4a512a861660e84349c936a5160782b0dded9，登记246物理页；本轮不重新读取/解析PDF。

实际准备ID：preparation_718bf6c856acd871970f3eea。

| 材料/检查 | 实际结果 |
|---|---|
| 全部来源证据 | 188条，与源包EvidenceRecord逐条完全一致 |
| 节点/字段目标 | 541＝63节点＋478字段，每个ReviewTarget指纹经原target_value校验 |
| 字段状态 | 345 stated、133 inferred；未改为医学真值 |
| 异常材料 | 27条graph/node gap、1条原隔离候选；不是可写ReviewTarget |
| 新评审表 | 全部决定/身份/理由null，submitted=false，意见写入0 |
| 医学状态 | 63节点全部unreviewed；release_allowed=false |
| 包与源目录 | 所有文件哈希前后不变；相同输入重复报告完全一致 |
| 独立wheel | python -I实际从site-packages执行API及CLI，完整报告与源码一致 |
| 产物 | 1完整JSON＋5分步Markdown＋1哈希manifest，共7文件 |

本地材料在artifacts/b11-review-preparation/materials/preparation_718bf6c856acd871970f3eea/；验证脚本verify_real.py、real-verification.json、isolated-verification.json与独立环境在同b11目录，均被忽略。不在Git内保存原文/实际候选，不声称真实第二台电脑或全部系统验证。

## 质量门解释

本次engineering/source为passed，仅证明准备过程结构与包内来源检查，不保证识字准确、语义充分或医学正确。medical/training/case_baseline为blocked；license/performance/cross_source为not_evaluated。尚无独立专家审核、T02-A医学确认、真实跨来源正例、规模SLO或训练发布许可；准备完成不解除这些门。

分步文件只辅助先标原文再看模型，不构成访问隔离或专家认证。准备表不是ReviewRequest，本版不回收或自动提交任何意见；无法判断/身份缺失保持待审。

## 发行与保护

离线构建wheel并独立安装；112项源码/资源逐字节相同，发行物无PDF、密钥、知识包、运行缓存或测试夹具。构建器提示本地缓存位于源码根，实际归档检查无缓存泄漏。

语义仍0.3.2/197字段；330项Schema索引哈希正确。112份范围内Markdown本地链接错误0（根目录、md/tasks/src/config/tests，排除docs/log/早期archive），git diff --check通过，现行任务入口已统一B12。docs、log、原件、本地配置未改，无新OCR/模型外发/蒸馏/训练，未提交或推送。

## 下一步

B12重新评审复核意见接入与分歧治理，先明确准备表、独立意见、仲裁与现有用户意见的版本/身份边界。工程可用合成意见验证；不能替真实材料预填专家意见、把准备状态当医学确认或直接发布金标准。
