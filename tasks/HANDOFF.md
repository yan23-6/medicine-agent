# AI 接手说明

先读AGENTS、STATE、CURRENT、NEXT、ROADMAP及引用设计，不依赖聊天历史。

## 当前正式任务

T02-B12 复核意见接入与分歧治理，paused，尚未编码。用户于2026-10-18明确暂停推进，未经恢复不得执行B12；本轮仅写署期2026-10-19的log报告并提交/推送，不需要用户补分析文件。

先检查B11实际快照与现有模型，形成tasks/evidence/T02B12_REVIEW_SESSION_DESIGN.md。最早缺失前置是准备快照读入校验：资源/路径/manifest哈希/版本/Report稳定ID/材料和目标指纹，不能只验Pydantic或文件名。再建版本化复核会话；具体范围见CURRENT。

独立意见、无法判断、缺身份和分歧必须保留；声明身份不是已认证专家。准备表不是ReviewRequest，gap/隔离项不是其可写目标。默认不写原包、不代签专家或升级医学状态；真实空表只做安全检查，不填写合成认可。

## 最近完成B11

- 验收tasks/archive/phase-02/T02B11_ACCEPTANCE.md，完成时任务基线同目录T02B11_TASK_BASELINE.md。
- 设计tasks/evidence/T02B11_REVIEW_PREPARATION_DESIGN.md，契约review-preparation/0.1.0，10个模型；既有医学和意见写入版本不变。
- API analysis.review_preparation.ReviewPreparationService.prepare()/export()；CLI analyze review-prepare。管理能力不登记为Agent/Skill。
- 原文188条逐条一致，541目标指纹有效（63节点/478字段）、27gap/1隔离项；新表全部空白，真实意见写入0，unreviewed及源目录哈希不变。
- 定向88 passed（104.93秒）；全量208 passed（271.75秒）；330项Schema哈希、112份范围内Markdown链接与受保护路径通过。
- 独立wheel实际从site-packages执行API/CLI完整报告一致；112项源码/资源一致，敏感产物排除。
- engineering/source通过仅指本次准备过程/包内来源；医学、训练、病例门仍blocked，许可、规模和跨源正例未评估。

## 实际输入与恢复

准备目录artifacts/b11-review-preparation/materials/preparation_718bf6c856acd871970f3eea/，共7文件（preparation.json、5份分步Markdown、manifest.json），均被忽略。先独立标原文再看候选；文件分步不等于权限隔离或专家认证。

包artifacts/b7-real-compat/model-knowledge/bundle_a7c24a2ba66c6200241e87e0.medpkg，153943字节；SHA256 50742f7c32f7178c562ba2927ae070feac1e82696f7f86792157090fe2f7786d。原件指纹及当前未审内容计数见STATE；物理34—38页已有两阶段覆盖，禁止重复OCR/蒸馏。

若准备目录缺失但同哈希包存在，可用B11只读管理接口生成到新目录，不需PDF/模型；包也缺时继续合成工程，实证明确待恢复。不要重复B7任务learning_1bbcfa1a7a4447f38ddb1a4d52ae891d。权限受限走工具流程，不改ACL。

```powershell
.venv/Scripts/python.exe -m medicine_agent.cli analyze review-prepare --packages artifacts/b7-real-compat/model-knowledge --workspace artifacts/b11-review-preparation/handoff-cache --output-dir artifacts/b11-review-preparation/handoff-materials
.venv/Scripts/python.exe -m pytest tests/test_review_preparation.py tests/test_reviews.py
```

输出目录必须全新、在源目录和解包缓存之外；不覆盖旧材料。完整JSON/Markdown含原文，只放忽略的运行目录，勿提交或在聊天大段输出。默认CLI不传output-dir会输出完整报告。

## 固定边界

中医优先、多维分类、地图式多轮辨证；事实与来源不覆盖。B10覆盖管理和B4/B5待补声明仍有效，缺包不等于未处理。B9缓存和完整性校验保留，不重跑旧baseline。

专家缺席阻止医学确认/金标准/发布，不阻止独立工程；不能把用户意见升格专家结论。没有完整问诊、安全处方、正式包v0、数据库、产品服务或后训练/西医专业实现。

保持暂停；用户恢复后才按CURRENT工作，每一步同步STATE/HANDOFF/CURRENT，验收后才重评NEXT。docs只读，log仅按用户明确授权更新；本地配置不读取到报告。原件、密钥、环境、包与运行产物不进Git。本轮已授权报告与commit/push，最终结果以Git和交付答复为准；无新资料外发或训练。
