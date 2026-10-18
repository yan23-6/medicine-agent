# T02 数据契约通用性审计

> 审计日期：2026-09-29
> 范围：现有 Pydantic/JSON Schema、病例与推理模型、稳定设计和未来 Skill 边界
> 结论：逻辑设计基本通用，但 T02-A 初版物理契约被单个胸痹文本样例压窄；已完成第一轮整改和统一语义注册表落地

## 1. 判断标准

“通用”不等于字段无限多，也不等于复制某个医疗标准。项目采用以下判断：

1. 同一结构可以表达中医、西医、安全和研究语境中的共同事实；
2. 新资料出现不同值类型、时间、术语或来源时，不需要把信息塞进不可计算的自由文本；
3. 原文、规范值、推断、审核和行动保持分离；
4. 专业分支通过编码、类型和扩展增加语义，不覆盖共同事实；
5. 当前没有标准承载的内容仍能保真保存，并能在以后迁移。

参考的权威基线：

- [HL7 FHIR R5 Observation](https://hl7.org/fhir/R5/observation.html)：区分观察状态、编码、值类型、有效时间、诊次、部位、方法、解释和缺失原因；
- [HL7 FHIR R5 Encounter](https://hl7.org/fhir/R5/encounter.html)：区分诊次状态、类型、主体、参与者、机构、地点和实际期间；
- [HL7 FHIR R5 ClinicalImpression](https://hl7.org/fhir/R5/clinicalimpression.html)：临床评估可以连接诊次、发现、支持信息和连续复评；
- [HL7 FHIR R5 Provenance](https://hl7.org/fhir/R5/provenance.html) 与 [W3C PROV-O](https://www.w3.org/TR/prov-o/)：用实体、活动和责任主体表达生成与修订血缘；
- [OMOP CDM 5.4](https://ohdsi.github.io/CommonDataModel/cdm54.html)：保留 source value，同时映射标准概念，并按 Observation、Measurement、Condition 等临床域区分事件；
- [openEHR EHR Information Model](https://specifications.openehr.org/releases/RM/latest/ehr.html)：区分观察、评价、指令和实际行动；
- [国家中医药管理局《中医病证分类与代码》和《中医临床诊疗术语》通知](https://www.gov.cn/zhengce/zhengceku/2020-11/24/content_5563703.htm)、[GB/T 16751.2—2021 解读](https://www.samr.gov.cn/bzjss/bzjd/art/2022/art_ae386988ba3a44f387bb5634b5f2aa08.html) 与 [WHO ICD-11 传统医学说明](https://www.who.int/standards/classifications/frequently-asked-questions/traditional-medicine)：证明中医疾病、证候和治法需要版本化术语编码，但不能把分类编码当作病机推理本身。

这些标准只作为字段完整性和映射能力检查表，不整套复制为项目模型。项目内部唯一机器可读语义源是 `src/medicine_agent/semantics/registry.json`。

## 2. 发现的问题

| 对象 | 初版问题 | 风险 | 本轮处理 |
| --- | --- | --- | --- |
| PatientProfile | 只有年龄和性别字符串 | 无法表达去标识外部 ID、出生性别、性别、其他人口学属性和隐私标签 | 已增加通用标识、编码概念、属性与隐私标签 |
| RawCase | 只允许一个来源 | 病历、检验、影像或复诊来自多文件时丢失来源集合 | 已支持主来源和相关来源，CanonicalCase 去重汇总 |
| Encounter | 只有顺序和原始日期 | 无法表达门诊、住院、急诊、远程、期间、参与者、机构与父子诊次 | 已增加状态、类型、场景、期间、参与者、机构、地点与父诊次 |
| Observation | 规范值只有文本 | 数值、单位、范围、编码、布尔、时间、引用和缺失原因不可计算 | 已增加带判别符的通用值联合类型 |
| Observation | 否定与确定性混在一起 | “无乏力”可能被关键词规则当成气虚支持 | 已拆分 polarity 与 certainty，并增加负向观察回归测试 |
| Observation | 缺少部位、方法、来源角色和状态 | 检验、设备观察、影像与问诊无法共用 | 已增加 body site、method、origin、performer、status、interpretation |
| 字段映射 | 只有一个 category | 同 key 异义与多术语映射难以审核 | 已接入映射状态、候选、规则版本和多编码概念 |
| HistoricalRecord | 只有文本与 kind | 无法表达历史事件时间、主体、状态和结构化值 | 已增加事件概念、结构化值、时间、来源主体和状态 |
| 推理节点 | 默认只能表达少量中医节点 | 西医诊断、鉴别、风险、操作与结局无法复用 | 已扩展通用节点类型并显式标记 medical_system |
| 推理证据 | 只有 ID 列表 | 支持、弱支持、反证、歧义和强度无法结构化 | 已增加 EvidenceLink，保留兼容 ID 列表 |
| 推理图 | 没有协议和诊次范围 | 多次推理、跨诊次状态和迁移不可判断 | 已增加 graph type、protocol version、诊次与医学体系范围 |
| 安全上下文 | 只记录一个状态 | 不能表达政策版本、适用范围、限制和安全事件 | 已增加策略、警报、范围、时间与限制引用 |

## 3. 当前仍未达到正式通用协议的部分

以下对象来自已验收 T01 的最小实验闭环，本轮不直接破坏其 0.1 契约：

- `SourceMetadata` 缺少贡献者、机构、语言、地域、许可、权利、发布日期与版本关系；
- `DocumentFragment` 仍偏向 Markdown 行号，不能完整表达页码、区域、表格、图片、音视频和结构路径；
- `EvidenceRecord.location` 仍是松散字典，纠正历史、陈述主体和抽取活动尚未类型化；
- `KnowledgeCandidate` 与 `RelationCandidate` 仍是最小字符串候选，缺少术语、作用域、条件、时间、极性、证据角色和完整血缘；
- `ExperimentalPackageManifest` 仍是实验格式，缺少资料配置、依赖、许可、安全、能力和构建活动声明。

这些问题不妨碍 T02-A 的病例契约验证，但会阻止“正式知识包 v0”冻结。它们应在阶段 03 之前通过新版本迁移完成，不能直接修改已验收 T01 快照后假装兼容。

## 4. 本轮软件变化

- T02 契约版本最终升为 `0.4.0`，两个 T02 Skill 最终升为 `0.3.0`；
- 新增 Identifier、Coding、CodeableConcept、TemporalExtent、Quantity 与多种 ClinicalValue；
- 扩展 RawCase、CanonicalCase、Encounter、ClinicalObservation、HistoricalRecord、SafetyContext 和推理图；
- CaseDistillationSkill 逐项传递新增字段，不用示例特定规则覆盖它们；
- TCMReasoningSkill 忽略明确否定、取消或录入错误的观察，不再把它们作为正向病机证据；
- 增加“多来源 + 编码 + 数值单位 + 时间 + 设备来源”跨分支夹具测试。
- 增加统一语义注册表、Profile 分流、Schema 绑定、版本声明和运行时语义上下文校验。

## 5. 结论与边界

整改后的病例主干不再依赖“胸痹、文本值、单来源”三个假设，可作为中西医共同 CanonicalCase 的候选契约。它仍不是 FHIR、OMOP 或电子病历交换实现，也不代表外部术语已经获得授权、导入或验证。

T02-A 只验证通用结构和边界。教材证据、医学正确性、正式术语映射、外部互操作与完整知识包协议仍分别留给后续里程碑。
