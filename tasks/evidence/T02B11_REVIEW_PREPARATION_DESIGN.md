# B11 复核准备契约与只读边界

## 实现前决定

新增独立 `review-preparation/0.1.0` 管理契约；Pydantic模型为唯一结构源，导出schemas/review-preparation。不改变ReviewRequest/ReviewRecord、医学注册表、包协议或现有Skill。ReviewPreparationService.prepare()/export()与CLI analyze review-prepare不登记为Agent工具。

输入为可选成品文件名集合，默认扫描目录顶层全部medpkg。先复用B10 CoverageService校验、来源身份与覆盖盘点，再只读载入对应文件；前后哈希必须与盘点相同。仅私有解包缓存可写，禁止prepare/scan/view写源目录。缺包不重蒸馏，坏文件整文件隔离，健康文件继续。

## 产物与身份

1. 原文标注：全部活跃组件EvidenceRecord和SourceDocument，不按被模型引用与否过滤。保存原文、纠正值、原定位、指纹与包/manifest/资源地址。未提供物理页保持未知，非PDF不伪造物理页。模板决定/评审者/理由初始null。
2. 候选对照：提取现有review_queue的确定性构建函数供原接口和本服务复用；沿用ReviewTarget完整身份与目标指纹、事实出现序号、引文、flags、用户意见与expected_previous_id。原意见仅用户声明，不确认医学状态；新模板仍空白。
3. 异常材料：graph_gap/node_gap/rejected_candidate分别保存原AnalysisGap或RejectedAnalysisCandidate、位置/节点/出现序号与来源地址。它们不是ReviewTarget，不可直接传给review-record；没有自动重分析许可。
4. 质量报告：工程/来源/医学/许可/性能/训练/病例/跨来源门分别输出。工程通过只指当前准备过程结构一致，来源通过只指包内证据/身份检查，不能推导OCR正确或理解完整。专家未审核、许可未核实、无规模基准、病例/跨源正例未确认保持blocked或not_evaluated，release_allowed恒false。

完整报告自包含原文、候选、异常和模板，稳定ID由规范化内容计算；每条材料按组件包ID+manifest+原证据/目标/异常地址定位，重复文件合并内容但保留所有成品来源地址。不同修订/来源不混为同一事实；同家族多活版本显示冲突，不自动选择或拼接。历史异常、目标无法解析/指纹变更不得显示最终认可；未知字段分项待核，强制身份失败隔离。

## 分步评审和输出

完整JSON + 全部原文Markdown + 全部候选目标Markdown + 异常Markdown + 质量门与操作说明。先独立标原文再看模型，降低只评价已召回知识的偏差；文件分开仅辅助盲评，不是权限隔离/专家认证。

单个新目录原子导出：拒绝已存在目标、源目录内/祖先、解包缓存内和文件型输出名；先在同父临时目录生成全部文件及哈希清单，再rename提交。失败清理本次新建临时目录，不覆盖任何既有导出；部分/空报告必须显式标记，不冒充完整。输出目录应位于忽略的artifacts或用户指定本地运行目录，正文与真实候选不提交Git。

不写原意见，不预填认可，不把准备表当ReviewRequest，无法判断/缺身份保持待审。原文标注、专家独立意见和仲裁的正式回收协议留B12重新评审，本轮不实现。

## 验收

合成测试覆盖未引用证据、状态、跨页、缺口/隔离、缺可选字段、坏包共存、旧包、历史异常/目标指纹、重复/输入顺序、只读/原子导出/路径与CLI/Schema。真实只读核对188证据、541目标（63节点/478字段，133推断）、27gap/1隔离项及包/目录哈希不变；无专家意见写入。独立wheel API/CLI、全量、Schema和Markdown检查通过才归档。
