# 中医知识蒸馏与智能体平台

一个以中医为当前主线、为西医保留未来扩展口的独立智能体项目。项目包含资料摄取、证据定位、中医知识候选、可迁移知识包、多包查询和未来地图式多轮辨证能力。

## 先看哪里

- 当前真实状态：[tasks/STATE.md](tasks/STATE.md)
- 当前唯一任务：[tasks/CURRENT.md](tasks/CURRENT.md)
- 下一任务预告：[tasks/NEXT.md](tasks/NEXT.md)
- 项目路线图：[tasks/ROADMAP.md](tasks/ROADMAP.md)
- 稳定设计总览：[md/README.md](md/README.md)
- 开发运行说明：[DEVELOPMENT.md](DEVELOPMENT.md)

历史验收位于 `tasks/archive/`，早期长篇设计位于 `archive/legacy-design/`。它们只用于追溯，不代表当前状态。

## 当前能力摘要

- Python 3.13 项目、CLI、Facade、Skill Registry 和版本化 Schema；
- PDF、DOCX、TXT/Markdown、PNG/JPEG 摄取及本地 OCR；
- SQLite 检查点、暂停、失败恢复和跨进程续跑；
- 来源、原文证据、候选知识、关系、复核、更正和包组合；
- 单文件 `.medpkg` 交付、安装、迁移和查询；
- 中医五类知识、多维分类、受限局部知识图、候选关联和字段级失败隔离。
- 来源覆盖只读盘点与最小增量计划，区分已校验、历史待补与待核，不自动派发蒸馏。
- 自动生成可追溯的复核准备材料，分开原文、候选、缺口与质量门；不自动确认医学结论。

尚未完成医学金标准、完整地图式问诊、安全处方、正式包 v0、LadybugDB、MCP/REST/Web、规模评测和后训练。详细边界以 `tasks/STATE.md` 为准。

## 快速开发

```powershell
.tools\bin\uv.exe sync --group dev
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m medicine_agent.cli list-skills
```

导出 Schema 示例：

```powershell
.venv\Scripts\python.exe -m medicine_agent.cli export-schemas --contract-set tcm --output-dir schemas/tcm
```

真实模型配置只放 `config/llm.local.toml`，格式见 [config/README.md](config/README.md)。该文件不得提交、打印或写入报告。

## 数据保护

- `pdfs/`：用户本地原始资料，Git 只保留占位；
- `artifacts/`：运行产物和实验包，默认忽略；
- `docs/`：导师原始参考资料，默认只读；
- `log/`：仅用户明确要求时更新；
- `config/llm.local.toml`：仅运行时读取。

本项目产生的是研究候选数据和推理支持能力，不替代医生诊断，也不把软件验证等同于医学正确性。
