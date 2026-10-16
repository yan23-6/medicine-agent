# 数据分析 Agent 使用说明

总智能体 `OrchestratorAgent` 接收文件，由数据分析 Agent 调用已登记工具完成识别、候选分析、校验和产包。安装 wheel 后可独立运行，不依赖 Codex。当前支持 PDF、DOCX、UTF-8 TXT/Markdown、PNG/JPEG；其他格式尚未支持。Windows x64 / Python 3.13 已检查，其他系统需另验收。

## 包文件和工作区

默认成品目录为 `<用户目录>/MedicineAgent/knowledge/`，不随当前运行目录变化；其中只需管理 `.medpkg` 文件，统一 `数据包说明书.md` 和 `package-spec.json` 自动生成。复制文件即可发现，移走停止其贡献；坏包隔离，不阻断健康包。派生文件自含继承来源和历史，不需要另外携带基础文件。原页视觉复核仍需原件，包内保留原文/OCR及位置。

默认内部工作区为 `<用户目录>/MedicineAgent/workspace/`，存输入快照、检查点、解包和可重建缓存。可用 `--workspace` / `--packages` 配置其他互不嵌套的目录。完成结果迁移只复制包文件；未完成任务迁移需整个工作区及输入快照并校验运行版本。

## 提交与继续

```powershell
medicine-agent analyze capabilities
medicine-agent analyze submit "D:/资料/教材.pdf" --allowed-use "本地研究" --mode extractive
medicine-agent analyze run learning_返回ID --max-units 100
medicine-agent analyze status learning_返回ID
medicine-agent analyze run learning_返回ID
medicine-agent analyze query --text "气"
```

`extractive` 真实读取/OCR并保存原文候选，不调用语言模型，不冒称医学语义分析。`model` 调用用户配置的模型；submit 用 `--mode model --config ...`，run 用同一配置 `--config ...`。密钥只由运行时读取。模型输出经结构与逐字证据校验后才保存；仍为候选。

提交返回 `learning_…`，结果含 `package_path` 单文件名。`--max-units` 限制每个子任务本次新增单元数；PDF为物理页，文本为行，DOCX为可定位单元，图片为整图。`--units 1-100,105` 可限定范围。另一进程可 `analyze pause learning_…`，提交边界暂停；再 run 继续，不重复已提交阶段。失败状态带错误，修复原因后再 run；产包失败可复用已完成分析，不发布半个包。外部模型调用崩溃前未提交时可能重试，不承诺计费恰好一次。

## 基于多个包继续学习

```powershell
medicine-agent analyze submit "D:/资料/新书A.pdf" --allowed-use "本地研究" --mode model --config "D:/配置/llm.local.toml" --base-package "包1.medpkg" --base-package "包2.medpkg" --owner-id "用户3"
medicine-agent analyze run learning_返回ID --config "D:/配置/llm.local.toml"
medicine-agent analyze packages
```

`--base-package` 可重复，接受成品文件路径（相对路径在包目录解析）；`paths` 只放新资料。`owner_id` 可不填，仅为贡献记录，任何人都可基于他人包学习。基础文件先校验并内部快照，暂停后移走基础原文件仍能继续。新资料全部按所选范围分析，不能因为旧包已有“气”就跳过A的原文。包3完整继承未涉及旧知识；同概念的三个来源节点和字段并存，候选概念视图关联；新“热”新增。旧文件不覆盖。

## 分类、关联与复核

`--subjects` 科目/专题、`--material-types` 来源内容类型、`--profiles` 专业、`--knowledge-layers` 知识层、`--knowledge-categories` 中医五类均支持逗号分隔多值；查询支持对应过滤。中医五类为基础理论、药材、辨证、方剂、病例，基础理论不强制填症状/证候。分类和字段意义以唯一语义注册表0.3.2为准（197字段、64绑定、111分组医学字段）；中文说明用 `export-field-guide` 导出。

```powershell
medicine-agent analyze review-queue --scope all --output-file "D:/复核/queue.json" --markdown-file "D:/复核/核对.md"
medicine-agent analyze review-record --input-file "D:/复核/opinion.json"
medicine-agent analyze reviews
medicine-agent analyze revise --input-file "D:/复核/change.json"
medicine-agent analyze links
medicine-agent analyze link --input-file "D:/复核/link.json"
```

复核输入从清单复制完整 target、expected_previous_id，填写 decision/reviewer/reason，可附 proposed_value。修订输入 `parent_path` 为成品文件名，`review_ids` 为明确最新 needs_revision 意见。字段改法与第18章一致。文件接口的复核、关联、更正发布新不可覆盖文件并保留旧内容和历史，不就地篡改缓存；review/revise 返回实际新文件路径。`select` 的选择对象是返回的内部来源版本地址，选择保存在私有工作区，可切回旧来源版本。

关联 source/target 各含 package_id/node_id；relation 支持 same_definition、related、expands、contradicts，均为候选。概念同名/别名只作候选线索，分歧并存。依赖缺失保留不可解析引用，不冒称拥有其原文。复核是用户意见，不自动升级医学状态。

## 契约与边界

`export-schemas --contract-set learning` 导出文件学习与内部组合契约；`t02p`、`tcm`、`review`、`correction` 分别描述处理、知识、复核和更正。文件协议验证归档资源集合、校验和、来源身份与血缘，拒绝路径越界/未声明资源。目录型 `DataAnalysisAgent` / `PackageCatalog` 及旧 job_ 仅保留内部兼容，不是最终交付接口。

本版为研究候选文件协议首版，不是冻结正式包v0。未实现完整问诊、LadybugDB、MCP/REST或自动医学审核。所选页处理完不代表全部知识理解充分；模型输出保留缺口与质量警告。软件验收见项目当前阶段 T02B2_ACCEPTANCE.md。


B4新分析使用tcm-knowledge-analysis@0.2.0/source-faithfulness-v2：理论原话逐字保真、文献转引与人物归属分开、独立主命题分节点；新旧包和完整原文保留。旧未完成任务不静默混用新策略，新建任务；只有其他运行版本完全一致且尚无分析结果的子任务才能显式升级。查询analysis_quality保留全部原提示并区分布局、已有引用、当前未覆盖和模型报告，不自动升级医学状态。
