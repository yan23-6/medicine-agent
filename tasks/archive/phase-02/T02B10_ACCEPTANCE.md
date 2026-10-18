# T02-B10 来源覆盖盘点与增量规划验收

> 日期：2026-10-18；状态：done（软件、真实只读与独立安装验收通过；不是医学确认）。

## 交付

- [实现前设计](../../evidence/T02B10_COVERAGE_DESIGN.md)，同步稳定设计第04/12/16章及运行说明。
- `domain/coverage.py`：独立coverage/0.1.0的9个管理模型；`schemas/coverage/`快照及哈希。
- `analysis/coverage.py`：CoverageService.inventory()/plan()；`analyze coverage [--input-file …]`；无新Agent或Skill。
- [可迁移的当前来源规划请求](../../evidence/T02B10_COVERAGE_REQUEST.json)：保存原件指纹、物理范围和B4/B5历史待补声明，不含正文或密钥。不将历史声明伪装成已恢复包。

源目录只读，仅在互不嵌套的独立工作区写解包缓存。不调用prepare/scan/view，不改包，不OCR、不调用外部模型、不训练或派发任务。

## 规则与容错

按来源SHA256、明确单位和阶段组织覆盖。physical_page不混印刷页/文本行/结构单元。extraction只证明已提交定位原文；semantic_candidate需逐单元提交及合法节点，仍为unreviewed，不代表理解完整或医学正确。

缺可选字段为unknown；历史为historical_pending；没有合法节点为partial_failed；策略缺失/不同分别返回POLICY_UNKNOWN/INCOMPATIBLE_POLICY并待核。包完整性、来源身份、资源或范围错误隔离整个文件，健康包继续；无法绑定来源的坏文件只阻止未知范围新增建议，不抹掉健康覆盖。定位缺页仅影响可定位的对应单元；无法定位单元时保守待核整个声明范围。

计划逐单元给出covered/held/needs_check/proposed及记录索引和证据地址。只建议最早缺失阶段；历史待补暂避，缺包不是重做许可。停用组件不计当前覆盖，同家族多活修订（含相同ID不同manifest）不得拼接。当前工具不读取查询select；可扫描明确选定的成品文件集合。无指纹历史独立待核，不凭名称绑定或阻断其他来源。

## 软件验证

`python -m pytest tests/test_coverage.py`：33 passed，24.56秒。覆盖重叠、乱序、重复包/声明、原文包、无revision/缺元数据、历史待补/未知身份、错误指纹、非物理单元、越界、坏包与健康包、策略不同/缺失、停用、多活冲突、扫描中途变化、缓存路径、单页定位缺失、CLI和Schema确定性。夹具仅模拟文档适配器和模型，真实校验器未替换；不产生或复制真实PDF，不作为医学证据。

首轮全量182 passed，244.54秒；补齐单页定位隔离用例后重新完整执行，最终183 passed，245.40秒。不同批次不相加作为用例数。

## 真实只读验证

复用B7单文件 `bundle_a7c24a2ba66c6200241e87e0.medpkg`，153943字节，SHA256 `50742f7c32f7178c562ba2927ae070feac1e82696f7f86792157090fe2f7786d`。原件SHA256为请求中记录的 `031007fc2caa796ed6b72f8b6ea4a512a861660e84349c936a5160782b0dded9`，登记246物理页，本轮不重新读取/解析原PDF。

- 实际盘点10条逐页/阶段记录，物理34—38两阶段覆盖；请求34—40时，仅39—40建议extraction，没有执行。
- 188证据、63未审节点、478字段、27gap及1隔离项保持；扫描前后公共目录全部文件哈希一致。
- 相同输入重复规划完全一致。带真实历史声明时34—38仍由当前包证明；仅在空目录放入这些历史声明时34—38为held，不升级verified。
- 独立wheel安装后使用python -I，从site-packages执行同一真实包管理API及CLI，完整计划一致；未借助源码导入，不声称第二台电脑/全部系统验收。

本地非提交明细：`artifacts/b10-coverage/verify_real.py`、real-verification.json、isolated-verification.json、plan.json及独立环境。新克隆可能没有这些文件，不能仅凭历史done冒称重新做过实证。

## 发行、文档与边界检查

离线构建及安装wheel；110项源码/资源逐字节一致，发行物没有PDF、密钥、知识包、运行缓存或测试夹具。构建器提示本地缓存位于源码根，但实际归档资源检查未发现缓存泄漏。

语义注册表仍为0.3.2/197字段，医学JSON未变。320项Schema索引哈希正确；109份检查范围内Markdown本地链接错误0（根目录、md/tasks/src/config/tests，排除docs/log/早期archive），git diff --check通过。docs、log、原件、本地密钥配置未改，未提交或推送。

## 下一步重评

B11可构建代表复核材料准备与质量门报告：复用review-queue/ReviewTarget和覆盖，先独立原文标注，再对照候选；补gap及隔离项的准备材料，不把它们冒充可写的ReviewTarget。工程不依赖专家先到场；医学审核、T02-A确认、真实跨来源正例和正式金标准仍缺，不启动新蒸馏或训练。
