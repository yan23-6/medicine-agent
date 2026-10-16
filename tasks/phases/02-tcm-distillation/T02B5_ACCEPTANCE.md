# T02-B5 真实新页增量核验记录（2026-10-16）

> 状态：done（真实增量核验任务完成，非全部关联能力达标）；继承、真实分析、原文核验及独立迁移通过。自动关联缺口已明确，下一步先修。

## 范围、授权与运行

用户授权继续推进，并要求每推进一个可核验步骤同步STATE/HANDOFF，已写入根AGENTS、稳定md入口和总体变更规则。B4原CURRENT归档为T02B4_TASK_BASELINE.md，B5启动前重评并建立正式任务。103份维护Markdown读取/本地引用检查通过；未改docs参考文本、log周报及不受影响的未来技术草案。

基础为B4单文件包，以独立贡献者身份从同教材物理37—38页（书内19—20页）学习。用户明确允许这两页OCR及必要36页上下文发送至原配置模型服务；实际请求仅units=[37,38]，第38页用第37页作为既有逐单元上下文，没有发送整本PDF或重分析34—36页。原PDF只由产品本地读取/快照，不进入Git、测试夹具或发行物；配置只由运行时读取，未打印密钥、请求头或错误响应正文。

任务 `learning_acbd6754ab5c46ea9bbada807d2c70f8`，工作区 `artifacts/b5-incremental/work/`。第37页完成后真实paused、next_unit=38，再用另一进程执行rest，最终completed、extracted=2、analyzed=2、errors为空。共2次真实OCR、3次模型返回（第37页包含工具的一次纠正）；没有手改检查点或以假模型替代真实运行。第37页初稿并未直接被当作合格结果。

## 数据与完整性

| 项目 | 实际结果 |
| --- | --- |
| 新成品 | `artifacts/b5-incremental/knowledge/bundle_2c58e2c337aab6daa6da31cb.medpkg` |
| 文件大小/SHA256 | 143,145字节；`e5fe7dd925a8d7de1213ab86f349506f981c72375c146e189437bedab6760a76` |
| 来源组件 | 2个，旧34—36页组件与新37—38页组件，各自完整保留 |
| 节点 | 53＝旧28＋新25；均unreviewed |
| 原文证据 | 188＝旧113＋新75 |
| 分组字段 | 265＝旧166＋新99；stated214、inferred47、ambiguous4 |
| 旧资源继承 | 除重新生成的顶层bundle外，基础包13项资源逐文件SHA256/字节一致；旧节点/字段/分类/原文/位置未重写 |
| 新原文 | 75条完整EvidenceRecord逐项对比产品抽取记录，含原文、全部定位、置信度等字段完全相同 |
| 包血缘 | 原B4 bundle快照随history完整保留；基础文件和原PDF指纹未变 |
| 校验与查询 | 所有组件通过包校验和原文规则；节点/字段引文回查；分类查询返回全部53节点，未隔离为坏包 |

新75条原文中的“未覆盖证据”派生计数为0，不证明分析完整。新组件7条原始提示仍保留（版面候选1、模型报告6）；旧组件16条原提示未丢（仍未覆盖证据3等）。新页边界截断及未知归属没有静默补齐；总4条歧义包含旧3条和新1条。第38页太极图的节点来自教材文字说明，没有视觉语义分析，不能声称图像内容已全部理解。

## 发现的实际缺口：异名内容没有自动关联

成品跨组件候选概念组为 **0**，新增跨组件链接为 **0**。现有`analysis/concepts.py`只按规范化标题/别名相等匹配，模型此次生成的命题式长标题没有共同别名。旧“阐释人体生命活动”与新“气是生命活动的体现，气的运动变化停止意味着生命终止”等可以联合检索，但没有自动建立可沿用的关联。

这是关联召回的实际不足，不是原文丢失或旧节点被覆盖；两个主张的关系也不能仅凭主题都含“气”就断言相同。没有为使数字好看而手工改标题/别名、强合并或伪造同义。B2自制同名气/热例子的通过不能证明真实异名关联已足够。下一步应先补可审计、带证据且区分“同一概念/相关知识/不确定”的候选关联，再同范围回验，不继续扩页掩盖问题。

## 软件与交付检查

本轮无产品Python/Schema/字段语义变更，不需要借机重写旧包或冒称新跑完整133项。三来源气/热、未涉及旧知识保留及单文件迁移的既有专项再跑1项通过；历史B4回归仍是此前记录。

运行命令与脚本（本地产物目录，不是新的正式Skill）：

```powershell
.venv/Scripts/python.exe artifacts/b5-incremental/preflight.py
.venv/Scripts/python.exe artifacts/b5-incremental/run_trial.py submit
.venv/Scripts/python.exe artifacts/b5-incremental/run_trial.py one
.venv/Scripts/python.exe artifacts/b5-incremental/run_trial.py rest
.venv/Scripts/python.exe artifacts/b5-incremental/inspect_trial.py
artifacts/tcm-isolated-env/Scripts/python.exe -I artifacts/b5-incremental/migration_check.py
.venv/Scripts/python.exe artifacts/b5-incremental/check_delivery.py
```

`submit`已经执行，不得无意重复；恢复先读trial.json与产品status。原始草稿/调用计时、inspection.json、quality-view.json、query.json和迁移证明位于`artifacts/b5-incremental/`，Git忽略，普通clone不会带走。

## 边界与下一步

本任务是小范围真实增量能力核验，不是医学验收、正式包v0发布或所有自动关联问题已解决。T02-A仍review；临床B、完整问诊、数据库、规模评测、后训练原阶段门不变。用户不需补文件。下一任务从上述真实关联缺口开始评审，继续同步STATE/HANDOFF；任何新的外发范围仍按实际许可执行。


## 最终迁移结果

安装环境使用B4最终wheel（本轮产品代码未改，资源一致性已检查），python -I从site-packages执行。只复制143,145字节的新.medpkg，禁止访问项目src/config/pdfs、B3/B4结果、B5原工作区及原成品目录，成功回查全部53节点（旧28＋新25）、物理34—38页和来源字段；统一人读/机器说明书生成，文件未被隔离。查询命中证据数见migration-result.json，不用命中数替代源包188条完整证据。此为同台Windows/Python隔离环境，不冒称已在真实第二台电脑或全部系统验证。

整个核验已完成；结论包括“内容继承/原文/单文件迁移成立”和“真实异名自动关联不足”两部分。后者未解决，不能据done字样宣称用户最终关联要求已实现。状态与接手说明继续明确记录该下一步，暂不增加真实资料范围。

最终文档/交付检查通过：104份维护Markdown读取、本地引用0错误；既有wheel与全部src资源逐文件一致、统一生成说明书一致，发行物排除原件及本地配置，PDF Git边界检查通过；git diff --check通过。最后一步亦已同步STATE/HANDOFF。
