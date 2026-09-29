# 统一医学语义契约验收

> 验收日期：2026-09-29
> 状态：自动验收通过，作为 T02-A 用户评审输入
> 规范版本：`medicine-agent.semantic-registry` `0.1.0`（review）

## 1. 目标与唯一位置

项目的医学字段定义、值类型、关系、术语体系元数据、权威来源、专业 Profile 和物理 Schema 绑定只在 `src/medicine_agent/semantics/registry.json` 维护。

- `registry.py` 只定义注册表自身的校验结构和加载方法；
- `schemas/t02/common/SemanticRegistry.schema.json` 是可再生快照，不是编辑源；
- `md` 和任务文档只解释设计或记录状态，不复制完整字段字典；
- 数据包和 Skill 只能声明采用的注册表版本及 Profile，不能局部改写字段含义。

## 2. 字段与专业分流

| Profile | 用途 | 边界 |
| --- | --- | --- |
| `common` | 身份、来源、原始值、规范值、时间、诊次、证据、血缘、审核、适用范围和医学体系声明 | 所有路径共有；专业 Profile 只能引用，不能重定义 |
| `tcm` | 四诊、病因、病位、病性、病机、证候、治则治法和转化 | 不用于伪装西医诊断或病理生理机制 |
| `western` | 表型、危险因素、病理生理、诊断、鉴别、检查、风险、干预和预后 | 不把中医病机强译为西医概念 |
| `safety` | 红旗、安全门、策略、限制和升级处置 | 独立并行，优先于专业推理和方剂路径 |
| `formula` | 方剂、药物引用、方中角色、剂量、炮制、配伍、加减与停调 | 药物固有知识与方中特定角色分开 |

无法确定专业归属的内容保留在 `common` 原始层，标记未映射或使用受治理的命名空间扩展，不丢失、不猜测。

## 3. 权威来源吸收原则

本轮联网核验并登记 15 个权威来源。FHIR 用于观察、诊次、临床评估、值类型和血缘维度；OMOP 用于原始值与标准概念并存、临床域和测量值表达；openEHR 用于观察、评价、指令与行动分离；W3C PROV-O 用于实体、活动与责任主体；UCUM 用于计量单位；WHO ICD-11 传统医学与中国国家标准用于中医专业术语范围。

外部标准仅作为完整性检查、映射目标和来源依据。本仓库没有复制受许可约束的完整术语内容，也没有宣称项目模型等同于 FHIR、OMOP、openEHR、ICD-11 或国家标准。

## 4. 自动验收结果

| 检查 | 结果 |
| --- | --- |
| 注册表结构与引用 | 通过：15 个值类型、67 个字段、10 类关系、10 个术语体系元数据、15 个来源、5 个 Profile |
| 重复语义 | 通过：`field_id` 与 `semantic_key` 唯一；重复定义会被拒绝 |
| Profile 隔离 | 通过：专业字段必须使用所有者命名空间，不能由另一 Profile 占有 |
| Schema 连接 | 通过：43 条绑定全部指向真实 Pydantic 字段和已登记语义字段 |
| Skill 运行时 | 通过：两个 T02 Skill 校验注册表身份、版本、启用 Profile 和术语体系声明 |
| 版本化 Schema | 通过：T02 `0.4.0` 已导出 `SemanticContext` 与 `SemanticRegistry` 快照 |
| 回归测试 | 通过：`uv run pytest -q` 为 `29 passed` |
| 构建 | 通过：sdist 与 wheel 均包含注册表、校验器与使用说明，不含本地密钥或 `.uv-cache` |
| 保护目录 | 通过：`docs` 未修改；`log` 本次未更新 |

## 5. 验收命令

```powershell
uv run medicine-agent validate-semantics
uv run medicine-agent export-schemas --contract-set t02 --output-dir schemas/t02
uv run pytest -q
uv build
```

## 6. 当前边界

本次通过的是语义结构、单一来源、字段分流和运行时约束验收，不是医学内容正确性验收。外部术语内容尚未导入，西医、方剂和完整安全 Skill 尚未实现；后续新增真实字段时必须先判断能否复用 `common`，只有确属专业语义时才进入相应 Profile，并同步版本、迁移说明、绑定和测试。
