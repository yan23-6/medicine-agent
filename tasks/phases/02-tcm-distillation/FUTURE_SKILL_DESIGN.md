# 后续 Skill 能力设计与进入顺序

> 状态：设计储备，不可调用，不加入 Skill Registry
> 原则：先作为现有 Skill 的内部能力验证；只有需要独立版本、权限、复用、吞吐或评价时才提升为顶层 Skill

## 1. T02-B 前后优先能力

### TerminologyNormalizationCapability

- 归属：CaseDistillationSkill、KnowledgeDistillationSkill 的内部能力；
- 输入：原始术语、上下文、医学体系、语言、可用术语集及版本；
- 输出：零个或多个 CodeableConcept 候选、映射依据、冲突、状态和未映射原文；
- 硬规则：不能仅凭显示名合并；不能猜测代码；中医与西医编码并存但不强行等价；
- 提升条件：需要独立术语服务、授权隔离或跨多个 Skill 共享缓存时。

### ClinicalFieldMappingCapability

- 归属：CaseDistillationSkill 内部能力；
- 输入：每次出现的 raw key/value、结构路径、上下文和资料类型；
- 输出：规范字段候选、歧义、未映射状态、规则版本和原值保留结果；
- 用途：解决重复 key、同 key 异义、不同 key 同义和未知字段；
- 提升条件：映射规则需要独立发布或由人工团队维护时。

### TimelineReconstructionCapability

- 归属：CaseDistillationSkill 内部能力；
- 输入：绝对时间、相对时间、诊次顺序和不确定时间表达；
- 输出：TemporalExtent、事件先后约束、冲突和待核项；
- 硬规则：不把“近日”“两年前”等自动伪造成精确日期；
- 提升条件：复诊病例、跨来源记录和时间冲突达到可独立评价规模时。

### EvidenceAssessmentCapability

- 归属：TCMReasoningSkill、WesternReasoningSkill 与 EvidenceReviewAgent 共用的内部能力；
- 输入：候选结论、证据、反证、适用条件和缺失信息；
- 输出：EvidenceLink、证据角色、直接性、冲突和复核要求；
- 硬规则：同一模型产生的解释不能回灌为独立来源证据；
- 提升条件：需要独立盲审、独立模型或独立权限时。

## 2. 后续顶层 Skill 家族

### SafetyGateSkill

优先于任何治疗建议能力实现。输入 CanonicalCase、当前推理候选、策略版本和运行授权；输出安全状态、红旗证据、阻断/限制、转诊或复核要求。它不负责中医或西医诊断，也不能被专业推理 Skill 覆盖。

### WesternReasoningSkill

用于验证通用主干没有被中医样例写死。输入同一 CanonicalCase 与医学证据包；输出表型、病理生理、诊断与鉴别候选、检查缺口、风险和证据图。和 TCMReasoningSkill 共享事实，不共享专业结论。

### FormulaSkill

输入已审核的机制/证候、治疗目标、安全上下文和方剂知识；输出方义、药物角色、配伍、剂量与炮制上下文、加减、停调和状态变化候选。必须先实现 SafetyGate 与正式知识包读取，不能从证型直接跳方药。

## 3. 暂不设为顶层 Skill 的能力

- ReviewAdjudication：先作为 QualityEvaluationSkill 的人工复核协议；
- StateTrajectory：先作为 CaseDistillationSkill 和两个推理 Skill 的共享模块；
- CrossSystemAlignment：先作为 KnowledgeDistillationSkill 的受控映射能力，只允许“相关、互补、共同指向”，不输出天然等价；
- TCM 四诊、病机、冲突、证候和经典方法：先作为 TCMReasoningSkill 内部模块；
- OCR、表格、版面和图片恢复：属于 MaterialIngestionSkill 内部适配器；
- 单味药：进入 HerbKnowledge，不为每味药创建顶层 Skill。

## 4. 推荐实施顺序

```text
T02-A 通用病例契约
  → T02-B 术语候选 + 教材证据 + 人工金标准
  → SafetyGateSkill
  → WesternReasoningSkill 小样本验证
  → 状态轨迹与证据评审模块
  → FormulaSkill
  → 真实负载证明需要后，再拆独立子 Skill 或 Agent
```

该顺序是能力依赖，不是固定工期。资料不可用时保持设计状态，不创建空壳 Skill，也不登记为 `available`。
