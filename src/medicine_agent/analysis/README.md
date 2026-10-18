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
medicine-agent analyze query --text "气" --knowledge-type theory --evidence-state stated --max-hops 1 --max-nodes 30
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

查询还可用 `--knowledge-type`、`--evidence-state`、`--topic`、`--tcm-layer` 组合筛选。返回的 `retrieval_facets` 由来源节点、字段、包分类和审核状态确定性派生，不是第二份医学事实。`local_graph` 以命中节点为种子，按 `--max-hops` 和 `--max-nodes` 受限扩展显式关联，并返回缺失种子、截断和过滤审计。`--seed-file` 接收地址数组，可从上一轮候选继续局部查询。

```powershell
medicine-agent analyze review-queue --scope all --output-file "D:/复核/queue.json" --markdown-file "D:/复核/核对.md"
medicine-agent analyze review-record --input-file "D:/复核/opinion.json"
medicine-agent analyze reviews
medicine-agent analyze revise --input-file "D:/复核/change.json"
medicine-agent analyze links
medicine-agent analyze link --input-file "D:/复核/link.json"
```

复核输入从清单复制完整 target、expected_previous_id，填写 decision/reviewer/reason，可附 proposed_value。修订输入 `parent_path` 为成品文件名，`review_ids` 为明确最新 needs_revision 意见。字段改法与第18章一致。文件接口的复核、关联、更正发布新不可覆盖文件并保留旧内容和历史，不就地篡改缓存；review/revise 返回实际新文件路径。`select` 的选择对象是返回的内部来源版本地址，选择保存在私有工作区，可切回旧来源版本。

关联 source/target 各含 package_id/node_id；relation 支持 same_definition、related、expands、contradicts，均为候选。概念同名/别名只作候选线索，分歧并存。`concept_link_candidates` 还提供“精确名称、主题加词形、较高词形重叠”的可审计候选类型、分数和依据；它不自动写关系或合并节点。依赖缺失保留不可解析引用，不冒称拥有其原文。复核是用户意见，不自动升级医学状态。

## 契约与边界

### 只读覆盖盘点与最小增量计划

```powershell
medicine-agent analyze coverage --packages "D:/知识包" --workspace "D:/覆盖缓存"
medicine-agent analyze coverage --packages "D:/知识包" --workspace "D:/覆盖缓存" --input-file "D:/规划/request.json"
medicine-agent export-schemas --contract-set coverage --output-dir "D:/契约/coverage"
```

不传input-file只盘点；传入独立 `coverage/0.1.0` 的 CoverageRequest 则生成计划，JSON仅打印到标准输出。请求例（指纹须替换成实际原件SHA256，不按名称匹配）：

```json
{
  "version": "0.1.0",
  "source_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "unit_kind": "physical_page",
  "document_unit_count": 246,
  "units": [34, 35, 36, 37, 38, 39],
  "history": []
}
```

`units` 排序去重、取值1至document_unit_count，总数上限100000；PDF物理页、文本行、DOCX结构单元和图片不可混用。可选policy包含analysis_policy/context_policy/semantic_version，默认source-faithfulness-v3/previous-unit-plus-current-v1/0.3.2；策略不同或版本缺失只提示待核，不自动重做。提取记录另带方法和适配器版本，不输出模型地址或密钥。

history每项包含source_sha256（可null）、unit_kind、units、stage（extraction或semantic_candidate）、reference。已知指纹历史待补为held，不冒充verified；未知身份保留在unresolved_record_indexes，不按书名绑定其他来源。旧包缺revision/逐单元语义提交记录时标unknown，而非要求全部重蒸馏。无revision的未知范围保守待核。

结果inventory含逐来源/阶段记录、资源地址、父修订与哈希依据；decisions逐单元给出covered/held/needs_check/proposed及record_indexes。proposed仅指最早缺失阶段；只有原文包时建议semantic_candidate而不重复OCR。语义候选覆盖仍是unreviewed，不是医学完整性、识字准确或训练金标准。停用组件只提供暂避依据；同一家族多活修订（包括同ID不同manifest）必须明确选择，不自动拼接。

文件坏包/来源身份/范围错误整文件隔离，健康文件继续盘点。无法辨认来源的坏文件使尚未覆盖部分降级needs_check，但不抹掉健康包已证明的覆盖；目录缺失不自动创建或误报空库。源目录只读，缓存与包目录必须互不嵌套。管理API为 `analysis.coverage.CoverageService.inventory()/plan(CoverageRequest)`，不是Agent可直接调用的新Skill；不会OCR、调用模型、派发任务、改包或训练。

本工具不读取查询工作区的select选择，也不自动切换版本；多活冲突可先将明确选定的成品文件集合放在独立扫描目录再盘点。它只读取所给目录顶层的.medpkg，不递归扫描内部目录型实验产物。

### 复核准备与分步评审

```powershell
medicine-agent analyze review-prepare --packages "D:/知识包" --workspace "D:/复核缓存" --output-dir "D:/复核材料/本次新目录"
medicine-agent analyze review-prepare --packages "D:/知识包" --workspace "D:/复核缓存" --input-file "D:/复核材料/request.json"
medicine-agent export-schemas --contract-set review-preparation --output-dir "D:/契约/review-preparation"
```

请求是 `{"version":"0.1.0","archives":["某包.medpkg"]}`；archives为空或不传请求时盘点顶层所有成品文件，文件名不能是路径。新管理接口复用coverage校验，不调用会写源目录的prepare/scan/view；缓存与源目录互不嵌套，不读本地模型配置，不OCR、不调用模型。

不传output-dir时完整Report输出到标准输出，可能很长且含原文；传output-dir仅打印版本化导出清单，正文保存在新目录。API为 `ReviewPreparationService.prepare(ReviewPreparationRequest)` 和 `export(output_dir, request)`，不是新Agent/Skill。契约源为domain/review_preparation.py，快照为schemas/review-preparation/，与既有ReviewRequest/Record版本分开。

目录包含preparation.json（完整类型化报告/引用/历史/空白表）、source-annotations.md（全部活跃来源证据）、candidates.md（全部节点/字段目标，可读引文节选，完整内容见JSON）、anomalies.md、quality-gates.md、README.md及manifest.json哈希清单。先标原文，再看候选；文件分步只是盲评辅助，不是权限隔离。不同manifest/修订独立，不按标题合并；重复文件保留所有地址。同一目标的可追溯历史链可沿用最新用户意见，分支/异常/失效指纹不选择最终意见。

准备状态complete/partial/empty必须与医学状态unreviewed分开读；engineering passed仅指本次准备过程，source passed仅指包内证据完整性，不代表识字正确、内容充分或医学正确。医学、许可、性能、训练、病例与跨源正例分别列门，release_allowed恒false。旧用户意见单独保留，新模板决定/评审者/理由为空；gap/隔离项不是ReviewTarget，准备表不能直接当review-record输入。后续正式回收/仲裁另经评审。

目录导出拒绝已存在目标、源目录/祖先、解包缓存和.json/.md等文件型名称；先生成全部文件及哈希再原子提交，失败不发布半个目录，不覆盖旧结果。坏文件隔离、健康文件继续；缺可选定位/旧revision显示待核，不自动重蒸馏。真实材料输出放被忽略的artifacts或用户本地目录，不能把完整原文清单提交代码库。

### 原有学习与意见契约

`export-schemas --contract-set learning` 导出文件学习与内部组合契约；`t02p`、`tcm`、`review`、`correction` 分别描述处理、知识、复核和更正。文件协议验证归档资源集合、校验和、来源身份与血缘，拒绝路径越界/未声明资源。目录型 `DataAnalysisAgent` / `PackageCatalog` 及旧 job_ 仅保留内部兼容，不是最终交付接口。

本版为研究候选文件协议首版，不是冻结正式包 v0。未实现完整问诊、LadybugDB、MCP/REST 或自动医学审核。所选页处理完不代表全部知识理解充分；模型输出保留缺口与质量警告。当前实现状态见仓库 `tasks/STATE.md`。


当前分析工具 `tcm-knowledge-analysis@0.3.0/source-faithfulness-v3` 强制理论原话逐字保真、文献转引与人物归属分开、独立主命题分节点，并提供字段/分组/节点级失败隔离。不合法候选进入 `rejected_candidates`，保留错误码、路径、原候选值和证据 ID，并汇总进最终包；无依赖的有效内容继续，但不自动修医学值。旧未完成任务不静默混用新策略；只有其他运行版本完全一致且尚无分析结果的子任务才能显式升级。`analysis_quality` 保留全部原提示并区分布局、已有引用、当前未覆盖和模型报告，不自动升级医学状态。
