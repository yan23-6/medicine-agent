"""Generate a human-readable view, never maintain a second semantic dictionary."""
from pathlib import Path
from medicine_agent.semantics import load_semantic_registry


def export_tcm_field_guide(path: Path):
    registry = load_semantic_registry()
    rows = ['# 中医数据包字段说明书（自动生成）', '',
        f'> 唯一来源：`src/medicine_agent/semantics/registry.json`，版本 {registry.version}。',
        '> 请修改注册表后重新生成，不在本文件手工增加医学字段。', '',
        '每个知识节点保留自己的来源，相关节点通过包 ID 和节点 ID 关联，不做覆盖式合并。',
        '医学字段放在 `groups[].facts[]`，`field_id` 取下表标识。每项包括 value、state、quotes、reason。',
        'quotes 保存 evidence_id 和逐字原文；证据对象另存完整原文/OCR、位置、来源和纠正候选。',
        'state 区分 stated、inferred、missing、ambiguous、not_applicable；后三种 value 必须为空并说明原因。',
        '同一药味、剂量、诊次或结局分别用 group_id 分组，about_group_id 指向所属分组，不能混合多次测量。',
        '所有输出是未审核候选，字段多不代表资料已提供或模型已正确理解全部内容。', '',
        '理论命题原话值须按引文原阅读顺序逐字保留，只忽略排版空白；概括和解释另存，不能替换完整OCR。',
        '模型纠正后仍不吻合的原话建议完整保存在reason中并标ambiguous/null，加gap；不自动补成事实，原引文和OCR不变。',
        '当前材料转引文献用 tcm.theory_cited_work，观点归属人物/角色/时代用 tcm.theory_attribution；不是新建已核验的一手来源。',
        '查询 analysis_quality 区分版面候选、其他位置已引用、仍未覆盖和模型报告，原始gap和quotes全部保留，提示条数不是遗漏知识点数。','',
        '五类：tcm_foundation（基础）、chinese_materia_medica（药材）、tcm_pattern_differentiation（辨证）、tcm_formula（方剂）、tcm_clinical_case（病例）；节点可多选。', '',
        '## 分组专用字段', '', '| 分组 | 字段标识 | 中文名称 | 意义 |', '| --- | --- | --- | --- |']
    count = 0
    for f in registry.fields:
        grouped = [x.split(':', 1)[1] for x in f.allowed_on if x.startswith('tcm_group:')]
        if grouped:
            count += 1
            rows.append(f"| {', '.join(grouped)} | `{f.field_id}` | {f.label_zh} | {f.definition.replace('|', '/')} |")
    rows += ['', '## 已有可复用语义', '',
        '辨证仍复用已有 tcm.etiology、tcm.disease_location、tcm.disease_nature、tcm.pathomechanism、tcm.syndrome、tcm.treatment_principle、tcm.treatment_method、tcm.transformation 等字段。',
        '方中角色、配伍等仍可引用已有 formula.*，通用适用条件、否定、确定性和时间复用 common.*。当前中医分析接口不输出西医字段，西医扩展保留独立接口。', '',
        '## 物理结构与关联', '',
        '`tcm.json` 保存节点、分组、事实和分析缺口；`extensions.json` 声明版本；两者受包 manifest 校验。',
        '`links/*.json` 是包根目录内独立的关联记录，source/target 各有 package_id、node_id；relation 为 same_definition、related、expands、contradicts，当前均为候选。',
        '关联双向可发现；expands 等语义方向仍保留。查询的分类并集是视图，不写回来源节点。',
        '移走目标包后引用保留并显示 target_unavailable；放回相同标识包后自动恢复 resolved。',
        '最终成品为单个 .medpkg 文件，放入固定知识目录发现；原文、来源、关联和更正历史保存在文件内。',
        'tcm.json、links 等是内部封装资源；用户不需要手动管理解包目录。内部目录实验接口不代表最终交付形式。',
        '派生包继承完整基础知识和必要来源，移走基础文件后仍可查继承内容。说明书为平台统一规范，不随每包另造。', '',
        '完整结构由 `medicine-agent export-schemas --contract-set tcm --output-dir schemas/tcm` 导出。',
        f'本表由注册表导出 {count} 个分组字段；注册表全部字段共 {len(registry.fields)} 个。', '']
    from medicine_agent.domain.learning import DerivedBundle
    rows += ['## 数据包文件操作字段（从封装契约生成）','','| 字段 | 意义 |','| --- | --- |']
    for name,field in DerivedBundle.model_fields.items():
        if field.description:rows.append(f'| `{name}` | {field.description} |')
    rows += ['','贡献者不构成更新权限。成品包放在固定 knowledge 目录；构建、解包、检查点和索引留在内部工作区。','']
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(rows), encoding='utf-8')
    return {'path': str(path), 'registry_version': registry.version, 'group_fields': count}
