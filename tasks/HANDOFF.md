# 接手说明（2026-10-16，持续更新）

> 版本保存（2026-10-16）：代码已本地提交f7e7f14（317个文件，详细中文说明）。向origin/master正常推送3次，分别SSL连接重置/443连接超时/443连接超时，尚未推送成功；不是权限审批拒绝。网络恢复后执行git push origin master，代码及本次状态同步提交均待推送。用户PDF、密钥和运行产物未提交。


## 当前正在做什么

- 当前唯一正式任务：**T02-B5 小范围真实新页增量验证**，状态 **done**。
- 当前步骤：B5核验和最终交付检查完成；关联缺口待修。
- 实际结果：53节点=旧28+新25，188原文=旧113+新75；旧13资源与新75条OCR完整记录一致；暂停跨进程继续/独立安装仅新文件回查通过；104份维护Markdown引用0错误，wheel与源码资源及字段说明书一致；异名自动关联0，未解决。
- 接手后的下一动作：先恢复网络并推送当前本地提交（git push origin master），核对远程一致；再重评并建立B6异名知识可审计关联任务，利用已有B4/B5结果和反例优先修复关联，不新增页；无需补文件；验收见T02B5_ACCEPTANCE.md。
- 用户已要求继续推进；此前“停在B4收尾”的指令已被本轮继续取代。每推进一个可核验步骤，立即同步本文件和STATE，保留历史验收时点。

先读 [STATE.md](STATE.md)、[任务规则](README.md)、overall目录、[当前阶段](phases/02-tcm-distillation/README.md)、[正式任务](phases/02-tcm-distillation/CURRENT_TASK.md)。[下一任务](phases/02-tcm-distillation/NEXT_TASK.md)仍是草案，不自动整书或进入临床。

## 范围和已获授权

已有教材 `pdfs/15086322中医基础理论.pdf` 足够，不需用户补文件。B5以B4文件为完整基础，只分析PDF物理37—38页（书内19—20页），在独立 `artifacts/b5-incremental/` 工作区生成新.medpkg，旧文件不覆盖。

用户本轮明确答复“允许这两页及必要上下文联网分析”：允许上述37—38页OCR及必要第36页上下文发送到原配置模型服务；此前34—36页许可仍保留。不发送整本PDF，不扩大目的地或其他页。新任务使用units=[37,38]，按现有接口处理，不为假造上下文重分析旧页。模型/密钥仅由运行时读取本地配置，不输出内容、请求头或响应错误正文。

## 已完成基线及限制

B4 done：133个不同软件用例通过（132常规+1个200页专项），后续语义绑定检查23 passed；同3页真实分析及仅单文件安装环境迁移通过。28候选节点、166字段、113条OCR及全部位置保留；3条建议显式歧义保留草稿及引文。全部节点仍unreviewed，用户“还可以吧”不等于医学逐项确认。T02-A仍review，阶段02及整体项目未完成。

当前语义0.3.2（197字段、111分组字段、64绑定），分析工具0.2.0，策略source-faithfulness-v2。总智能体/数据分析Agent已支持PDF、DOCX、TXT/Markdown、PNG/JPEG、本地OCR及跨进程继续。成品每包一个.medpkg，默认发现目录 `<用户目录>/MedicineAgent/knowledge/`；实验文件保存在artifacts而非冒称已经安装到默认目录。

任何用户可基于他人的多个包继续分析；作者不是权限。完整旧来源/节点/字段/分类/关系/复核历史保留，新资料同概念仍分析并保留原文，关联不覆盖。B4是同范围重分析，不是继承旧B3所有202项解释；旧解释仍在B3文件。B5必须实际核验完整继承，不能仅看数量。

完整问诊、正式医学金标准、正式v0冻结、LadybugDB、MCP/REST/Web、规模评价和后训练尚未完成；临床B原阶段门不变。既有软件测试不证明医学正确或理论覆盖完整。图像结构（本次第38页有太极图）不能用文本OCR成功冒称已完成视觉语义理解。

## 产物和恢复位置（相对仓库根）

- B5运行记录和新结果：`artifacts/b5-incremental/`；执行前/后查 `trial.json` 与 `status-result.json`（若尚未形成，不能假定已存在）。实时任务ID及进度随步骤更新于本页顶部。
- B4基础包：`artifacts/b4-quality/knowledge/bundle_bd668c695f761309551e81c4.medpkg`，82,709字节，SHA256 `def707c3a3886c00e9aacdbfd8013c85ecebeaae3310ef50e8f12a4ac7b2c760`。
- B3历史包：`artifacts/b3-real-book/knowledge/bundle_f74f29f88ebdcd5cf8ebc833.medpkg`，SHA256 `4a73218ef0eb3e4fc35841a2fcdb95445ef7a62b93b036a1090bbc02edea9c3b`。
- B4证据/迁移：`artifacts/b4-quality/inspection.json`、`migration-result.json`、`quality-view.json`、`nodes.json`；源包113条，查询命中101条不等于丢失12条。
- B4发行文件：`artifacts/b4-release/medicine_agent-0.1.0-py3-none-any.whl`，未正式发布；验收见 [T02B4_ACCEPTANCE.md](phases/02-tcm-distillation/T02B4_ACCEPTANCE.md)。
- B4旧模型任务已completed，无需恢复。B5不要重复submit；先查看trial和检查点，再用已有任务ID执行。失败如实记录，不手改检查点或用假模型冒充真实成功。

## 代码和运行提示

正式入口：`analysis/orchestrator.py`、`analysis/file_learning.py`；合成：`analysis/composition.py`；候选概念按标题/别名匹配：`analysis/concepts.py`，不冒称语义推理匹配。原文质量：`analysis/quality.py` 与 `skills/tcm_knowledge_analysis/handler.py`。字段唯一来源 `semantics/registry.json`，生成说明书从其维护。

本机PowerShell、`.venv/Scripts/python.exe`。复验优先针对本次实际改动和前置；原有完整测试记录见B4验收，不重复声称新跑133项。新任务的真实验证必须使用真实模型；自制测试只证明软件行为。

## 工作区保护

用户已授权提交并推送；代码/Schema/测试/文档已保存到本地f7e7f14，推送因三次远程连接故障未成功，本次状态同步另作本地文档提交。网络恢复后执行git push origin master；接手先看git status/log，不清理/reset或重复重建代码提交。尚未正式发布产品。artifacts为Git忽略目录，clone不带真实包和运行记录；换机器需另存需要的结果，供产品读取仅迁移单个.medpkg即可。缺失产物须如实补前置，不能依据文字假定存在。

PDF可本地读取但不提交原件或复制改名绕过，Git只留pdfs/.gitkeep；不复制进测试夹具或发行物。config/llm.local.toml只由运行时读取，不查看/复述/提交/写入报告。docs默认只读，log仅用户明确要求时更新。
