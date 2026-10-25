# B18 合成规模与资源开销基线设计

2026-10-25，Codex设计。正式任务仍是CURRENT的B18；D01是它的子步骤，不代表B18整体完成。

## 产品依据与范围

回读原01/04/08/09/16章、overall规则及349份Schema所在集合。产品需要可复现评价和真实测量，不能从小样例宣称大规模容量；数据包结构和来源身份保持兼容。已确认ReviewProgressService、_summarize、ReviewSessionView和现有合成夹具真实存在。

现有tests/test_review_progress.py的view只有4目标；适合正确性回归，不直接当规模构建器。Codex新建内部实验脚本tasks/benchmarks/b18_progress_probe.py，生产src/tests/Schema均不修改。它不是产品API、发行契约或可信快照入口；内部实验JSON仅是本任务证据，不注册新操作契约。

## 两个测量层，不能混写

1. D01先测`_summarize(typed_view)`：包含它实际执行的序列化/类型重验、最新意见映射、两两比较、报告验证和稳定ID计算。构造输入、输入前后哈希及独立正确性检查不计入该段计时。不是单纯循环耗时。
2. D02待Codex核验D01后另行设计真实自制包/准备快照/会话的Service.report端到端计时，单列源包/快照/事件历史重验、缓存与磁盘边界。D01不调用service，也不能证明真实历史合法或正式event ID绑定。

D01的history_rounds表示合成历史意见轮次，每条意见一个合成event ID；这些ID只满足类型格式，并未经内容ID/事件持久化核验。来源绑定、真实历史链、真实跨来源、临床正确性、容量SLO明确not_checked。不能把D01完成写成B18整体完成或性能门passed。

## 固定数据与独立预期

无随机采样：配方modulo-5-v1，静态UTC时间，目标依次循环四个scope，N都是20的倍数。第i个目标按i%5分为：0无意见；1全部accept；2按声明ID序号奇偶accept/reject；3全部unable；4仅r000 accept其余unable。R只取0/2/10，均为合成声明ID，非真实专家。

每轮对非空目标给每名声明ID一条意见。旧轮次按轮次奇偶accept/reject，最新轮用上述模式；expected_previous_id串接自身前序，不增加独立票数。原文理由使用固定合成标记，不输出到统计报告。

令b=N/20。R>0时每scope total=5b、pending=2b、insufficient=b、agreement=b、disagreement=b、unable_votes=(2R-1)b。每人每scope覆盖4b：r000 decisive=3b，其他人2b。每对每scope overlap=4b、comparable=2b、unable=2b，同奇偶matched=2b，不同奇偶matched=b。R=0时全部pending且无声明ID/对。意见/event ID数=4N/5×R×H。这些闭式公式由采集器独立断言，不从生产结果反推预期。

## 固定矩阵

| case | N目标 | R声明ID | H历史轮 |
|---|---:|---:|---:|
| blank20 | 20 | 0 | 1 |
| blank5000 | 5000 | 0 | 1 |
| n20-r2-h1 | 20 | 2 | 1 |
| n200-r2-h1 | 200 | 2 | 1 |
| n1000-r2-h1 | 1000 | 2 | 1 |
| n5000-r2-h1 | 5000 | 2 | 1 |
| n200-r10-h1 | 200 | 10 | 1 |
| n1000-r10-h1 | 1000 | 10 | 1 |
| n200-r10-h3 | 200 | 10 | 3 |
| n1000-r2-h3 | 1000 | 2 | 3 |
| n1000-r10-h3 | 1000 | 10 | 3 |
| n1000-r2-h10 | 1000 | 2 | 10 |

每组1次丢弃样本+3次计入样本，共48个独立子进程/36条正式采集；所谓warmup是独立丢弃进程，不是同进程热缓存。每子进程120秒，启动新样本总预算600秒；已启动者最多再运行120秒。首次失败/超时/保护哈希变化即停止，不改点位、不重试挑最好结果。

perf_counter_ns是段内墙钟，process_time_ns是段内CPU；另记输入构造墙钟。每次用新进程避免前测点峰值污染。Windows GetProcessMemoryInfo的PeakWorkingSetSize记录进程生命周期峰值，包含导入/构造/输入指纹，不能相减当成某阶段独占内存，也不是Python堆或private committed bytes。不支持/不可采时null+not_evaluated，不推算。记录导入后、构造与输入指纹后、统计后峰值。

每个正式样本检查闭式计数、分母、固定医学/发布/训练门、输入前后指纹、报告无理由标记；组内input_sha256/report_id须一致。中位数取3样本中位；p95取nearest-rank第ceil(.95×3)项，即最大值，仅探索性描述，不能推论总体尾延迟/置信区间。ns转ms除1e6，bytes转MiB除1048576。

## 本次设计核验与交接

Codex只跑3组smoke（blank20、n20-r2-h1、n200-r10-h3，每组1丢弃+1正式），全部通过；最大smoke4800条意见，Windows峰值采集实际可用，输入/受保护材料未变。证据artifacts/b18-d01/codex-design-smoke-20261025/。相关原有回归21 passed（7.86秒），JUnit artifacts/b18-d01/codex-design-tests-20261025.xml。

12组正式矩阵尚未执行，留给DeepSeek按D01执行单机械运行。执行后停在executed_pending_review，Codex核验脚本/原始数据/统计及原产品符合性，再决定D02。实际资料/包/349Schema/语义不变，不联网、不读LLM配置、不调用模型/OCR/蒸馏/训练，不改任何医学门。
