# T02-B2 单文件多基础包学习验收

> 日期：2026-10-16
> 状态：done（软件验收完成；不代表医学正确性验收）

## 已交付

总智能体文件入口生成 `learning_…` 持久化任务，调用数据分析Agent及已有登记工具。`paths` 接新资料，`base_packages` 接多个成品文件，`owner_id` 可选且仅记录贡献。没有新增未验收的Agent角色或Skill。任何用户都能基于其他人的包继续学习；原同用户限制已撤销。

每个最终包是单个 `.medpkg` 文件，默认从 `<用户目录>/MedicineAgent/knowledge/` 发现；同目录自动生成 `数据包说明书.md` 和 `package-spec.json`。包内有完整来源资源、原文/OCR与位置、字段/分类、关联、复核、更正和基础包血缘快照。检查点、源文件快照、解包与索引另存私有工作区；用户不需要管理components目录。

新资料同名概念仍完整分析。用户1/2的两个“气”节点和A的第三个“气”来源各自保留；候选概念视图关联其地址，不合并覆盖原解释。新“热”新增，A未涉及的阴阳/津液旧知识继续继承。旧包字节不变；包3不依赖基础文件或开发缓存。

封装采用声明资源集合及校验和，拒绝缺协议头、路径越界、重复/额外资源和无效内容。坏包单独隔离，健康文件可查询；移走文件后不从缓存继续使用其贡献。原子交付失败不留下半包，可复用已完成分析重试。复核、关联和更正在私有快照构建，失败不污染可读历史；更正重试复用同一私有操作及创建元数据。

操作契约见 `schemas/learning`、`schemas/owned-analysis`；医学字典仍0.3.1（195字段、62绑定、109分组字段）。中文说明从唯一注册表和封装契约生成，无第二套医学字段字典。旧目录API和job_仅保留兼容。

## 检查记录

- 本轮最初完整回归：118 passed，1 failed，971.82秒。失败为200页测试外层180秒超时，当时检查点已完成180页；没有产品结构或证据断言失败。短命令时限不变，仅长书两次运行各允许600秒；全部页数和无重复调用断言保留。
- 200页独立复查：1 passed，233.13秒。第100页暂停、next_unit=101，第二进程完成200页，提取调用总计200次，旧调用记录全部保留。
- 最终新增更正失败重试测试曾发现：新建私有快照会改变创建时间，导致相同更正输出冲突。已用基础视图及请求指纹固定私有操作，保留首次元数据；修复后1 passed，25.17秒。
- 文件专项覆盖CLI/API、多用户气/热、多次继承、原文及旧知识、无基础文件恢复、仅文件迁移、坏包隔离、越界/未声明资源、发布失败重试、更正包继续学习、历史不污染、损坏基础在调用模型前拒绝、并发首次读取。
- wheel/sdist离线构建；独立环境仅安装wheel和声明依赖。隔离脚本禁止读取项目src/config/pdfs、原资料、基础文件及旧工作区，验证单包3迁移、三个气来源、热和旧知识、血缘、说明书、损坏隔离及移除。最终源码逐文件一致性和文档链接检查同时复核。
- 最终wheel隔离复验已通过，结果在被忽略的 `artifacts/b2-delivery-isolation/result.json`；使用安装环境的 `python -I`，模块实际来自site-packages。最终发行物全部源码及数据资源与src逐字一致；97份项目Markdown全量读取、Markdown本地链接零断链，生成说明书与唯一来源一致，发行物不含原PDF、本地配置或开发缓存，见 `artifacts/b2-delivery-check.json`。

### 最终回归结果

最终代码常规完整回归 **119 passed、1 deselected，489.61秒**；被排除的唯一用例是长书专项，最终单独运行 **1 passed，325.69秒**。两批覆盖共120个不同用例，无遗留失败，不把前面的复查批次重复相加。命令：

```powershell
.venv/Scripts/python.exe -m pytest --basetemp artifacts/pytest-b2-final-complete -p no:cacheprovider -k 'not test_200_page_book_cross_process_resume'
.venv/Scripts/python.exe -m pytest tests/test_document_analysis.py::test_200_page_book_cross_process_resume --basetemp artifacts/pytest-b2-200-final-budget -p no:cacheprovider
```

发行物为被忽略的 `artifacts/b2-final-release/medicine_agent-0.1.0-py3-none-any.whl` 和同目录sdist。最终检查后更新STATE及CURRENT_TASK为done，不自动执行下一任务。NEXT_TASK保留为小范围真实教材分析质量核验草案；不重复建设本轮已通过的软件流程。

## 实际边界

软件检查用自制文件和明确的合成模型响应，不能当成真实医学正确性验收。本轮未调用真实模型、未分析用户原书；历史真实OCR/模型试用见T02P_ACCEPTANCE.md。200页测试是自制可选中文本PDF，真实扫描页OCR及崩溃恢复另由既有测试覆盖，不夸称200页扫描书都已医学分析。

概念匹配基于规范化标题/别名，只提供候选关联，不能自动判断医学同义或抹平争论。产物仍research_candidate/candidate_partial，复杂理论完整性、转引识别、医学质量、正式包v0、LadybugDB、完整问诊及MCP/REST/Web未验收或未实现。测试平台为Windows x64/Python3.13，隔离安装不能冒称真实第二台电脑或全部操作系统验证。

T02-A仍review，临床B原进入门保留；未修改docs/log，未读取本地密钥，未提交或复制PDF原件到测试/发行物。已有教材足够下一步小范围真实质量核验，不需新增文件。本轮未自动开始后续任务。
