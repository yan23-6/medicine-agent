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

### 复核会话（包外，review-session/0.1.0）

会话不写 `.medpkg`、不改准备目录和既有意见：只在独立的被忽略目录保存只读准备副本与追加事件。三个命令的路径参数都必填，不使用 HOME 默认值，不读本地模型配置，也不通过 PackageCatalog/FileLearningService 写包；会话目录、知识包目录和缓存目录三者必须互不嵌套，输出目录已存在则拒绝，不覆盖。

```powershell
python -m medicine_agent.cli analyze review-session-create --preparation-dir <新准备目录> --output-dir <新会话目录> --packages <知识包目录> --workspace <私有缓存目录>
python -m medicine_agent.cli analyze review-session-inspect --session-dir <会话目录> --packages <知识包目录> --workspace <私有缓存目录> [--include-opinions]
python -m medicine_agent.cli analyze review-session-submit --session-dir <会话目录> --input-file <意见批JSON> --packages <知识包目录> --workspace <私有缓存目录>
```

`inspect` 默认只返回摘要（会话身份、writable、目标数、各目标状态计数、issues），不含理由或纠正值；`--include-opinions` 才返回完整意见正文。提交输入示例（自制占位材料，仅示意字段；`target` 必须从同一会话的完整视图复制，不能只写显示序号）：

```json
{"version":"0.1.0","session_id":"reviewsession_000000000000000000000000",
 "submission_id":"submission-1",
 "reviewer":{"reviewer_id":"reviewer-a","display_name":"占位评审者","declared_role":"占位角色"},
 "opinions":[{"target":{"snapshot_id":"snapshot_000000000000000000000000",
   "kind":"candidate","material_id":"reviewitem_000000000000000000000000",
   "review_target":{"address":{"package_id":"占位包","node_id":"占位节点"},"scope":"node",
     "fingerprint":"0000000000000000000000000000000000000000000000000000000000000000"}},
   "decision":"accept","reason":"占位理由","expected_previous_id":null}]}
```

- `submission_id` 在会话内幂等：同 ID 同内容重试返回原事件、不改历史；同 ID 不同内容按 `SESSION_SUBMISSION_CONFLICT` 拒绝。
- `reviewer_id` 去首尾空白并 casefold，大小写变化不产生第二票；`reviewer_identity` 恒为 `self_declared`，不认证专家。
- `expected_previous_id` 只能引用“本评审者、本材料”的最新意见；旧值、他人意见或不存在 ID 均按 `SESSION_STALE_WRITE` 拒绝。
- `unable_to_judge` 与分歧不改医学状态：`medical_review` 恒 `unreviewed`，`release_allowed` 恒 `false`，分歧保持 `awaiting_adjudication`。
- 历史出现坏事件、分支、缺前序或重复 `submission_id` 时整体 `writable=false`，`inspect` 仍成功并展示 issue，`submit` 按 `SESSION_HISTORY_INVALID` 拒绝。
- `--include-opinions` 含理由与纠正值正文，只供本地人工查看；不要把真实输出交给模型或写入提交物。

### 复核覆盖与声明意见统计

```powershell
python -m medicine_agent.cli analyze review-session-progress --session-dir <会话目录> --packages <知识包目录> --workspace <私有缓存目录>
python -m medicine_agent.cli export-schemas --contract-set review-progress --output-dir <新契约目录>
```

只读API为`ReviewProgressService(packages, workspace).report(session_dir)`。先复用会话inspect重验源包/快照和历史，再按原文标注、候选节点、候选字段、异常分别统计覆盖与每声明ID的最新意见；同人更新不增加一票。成对比较显式列overlap/comparable/matched/conflicting/unable，双方都有明确决定才入comparable；分母0时agreement_fraction=null，不报100%。即使两人没有任何重叠材料，也保留该组0分母行。

报告不包含原文、理由或纠正值，仅保存计数/声明ID与session/snapshot/事件身份。坏历史输出diagnostics且metrics_available=false、比较列表为空；健康空白会话为0评审/无可比较对，不等于审核完成。最多100名声明评审者和100000目标，超限明确拒绝、不截断统计；该上限不是性能SLO。

`declared_agreement_complete`只表示所有非空目标在声明意见层面一致，不证明真实专家资格或医学正确性。medical_gate恒blocked，许可/性能not_evaluated，phase02_complete/release_allowed/training_allowed恒false。数据包、会话和原意见不因统计而改变。
# 只读环境预检

三个诊断报告与OCR资源描述共用包外`runtime-readiness/0.1.0` Schema集合，单一来源为
`medicine_agent.runtime_readiness_schemas`，不修改医学Schema。导出：
`python -m medicine_agent.runtime_readiness_schemas --output-dir <新目录>`（标准库可启动），
或`medicine-agent export-schemas --contract-set runtime-readiness --output-dir <新目录>`。
仓库快照位于`schemas/runtime-readiness/`，索引记录四份Schema的SHA256。

本地OCR资源：`medicine-agent-ocr-resources [--model-root <目录>]`或
`python -m medicine_agent.ocr_resources`只读核验受测RapidOCR版本/配置及det/cls/rec三份模型。
当前受测基线是RapidOCR3.10.0；其他版本为not_evaluated，不能只按版本元数据声称可用。
通过退出0，缺失/变化/未评估退出1；不下载/复制/创建资源目录，不输出绝对路径。
显式model-root仅供核验，不改变业务配置。`analyze capabilities`追加资源状态和判断依据；
TXT/MD仍保留支持。实际OCR缺资源返回OCR_RESOURCES_UNAVAILABLE，需受控准备资源后重试。
运行时显式传入已核验模型路径，不走后端默认下载分支；资源就绪不等于识字质量或再分发许可。

离线材料核验：`medicine-agent-wheelhouse --wheel-dir <目录> --snapshot <预检报告.json>`
（或`python -m medicine_agent.wheelhouse`）只读核对当前平台冻结依赖的wheel集合、
兼容标签、METADATA和逐文件RECORD及SHA256。不解包、不导入或安装wheel。
目录缺件/版本不兼容/内容损坏/依赖闭包不符返回blocked、退出1；通过退出0。
仅接受当前Python/OS/架构的通过预检报告，最多500wheel，总压缩/展开各2GiB。
通过只证明显式材料自洽，不能证明供应链可信、实际安装、原生库或OCR模型可用。
普通版本清单和依赖物理复制都不能替代完整wheel集合。

离线材料核验：`medicine-agent-wheelhouse --wheel-dir <目录> --snapshot <预检报告.json>`
（或`python -m medicine_agent.wheelhouse`）只读核对当前平台冻结依赖的wheel集合、
兼容标签、METADATA和逐文件RECORD及SHA256。不解包、不导入或安装wheel。
目录缺件/版本不兼容/内容损坏/依赖闭包不符返回blocked、退出1；通过退出0。
仅接受当前Python/OS/架构的通过预检报告，最多500wheel，总压缩/展开各2GiB。
通过只证明显式材料自洽，不能证明供应链可信、实际安装、原生库或OCR模型可用。
普通版本清单和依赖物理复制都不能替代完整wheel集合。

`medicine-agent-preflight`或`python -m medicine_agent.preflight`直接输出
`environment-preflight/0.1.0`清单，独立于主业务CLI启动，仅使用标准库和可选packaging。
不导入OCR/模型库，不读配置，不联网或安装。退出0只表示活动依赖闭包的元数据满足要求；
退出1表示阻塞或未评估。解析器缺失会明确标记，不能猜测版本规范。
清单列出安装版本和editable/归档来源类别，不输出本地安装路径或下载URL。
版本快照不是哈希锁或离线wheel集合；原生库可加载性、OCR模型资源、离线缓存仍未评估。

# 只读环境预检

`medicine-agent-preflight`或`python -m medicine_agent.preflight`直接输出
`environment-preflight/0.1.0`清单，独立于主业务CLI启动，仅使用标准库和可选packaging。
不导入OCR/模型库，不读配置，不联网或安装。退出0只表示活动依赖闭包的元数据满足要求；
退出1表示阻塞或未评估。解析器缺失会明确标记，不能猜测版本规范。
清单列出安装版本和editable/归档来源类别，不输出本地安装路径或下载URL。
版本快照不是哈希锁或离线wheel集合；原生库可加载性、OCR模型资源、离线缓存仍未评估。
