# B18-D02：实际提交事件的Service操作基线设计

2026-10-25，Codex设计；D01已独立核验，见[T02B18_D01_CODEX_REVIEW.md](T02B18_D01_CODEX_REVIEW.md)。D02仍是CURRENT/B18内的子步骤，不推进NEXT。

## 原产品依据与决策

回读01/04/08/09/16章与overall规则：基线要可复现、来源可核验，不能改变旧包/来源身份，不把软件结果升级成医学或规模SLO。D01只测typed-view；D02补现有Service操作的源包/快照/事件完整性路径。暂不优化生产实现，也不根据D01断言R²是瓶颈：R增加同时增加意见总量，存在混杂。

Codex固定脚本tasks/benchmarks/b18_service_probe.py；DeepSeek只运行矩阵与机械核对，不设计数据、改预期或实现优化。脚本是内部开发实验，不是新产品API/公开数据契约，不改变349份Schema。

## 数据构造与受信范围

- 独立自制输入，沿用已测tests/test_review_preparation.py的PreparationModel（本地确定性函数，不是远程LLM）。仅在构造时模拟inspect_document/extract_unit两个适配边界，生成每单元4条自制文本证据；未生成/识别真实PDF，没有OCR。
- FileLearningService实际构建.medpkg，退出适配器patch后，未修改的ReviewPreparationService导出、ReviewSessionService.create/inspect/submit生成并校验准备材料、绑定及真正提交的事件。不得手写正常事件文件或伪造ID来省略submit。
- 单元数U生成4U原文、U节点、2U字段、5U异常，总目标N=12U，正常组均需断言该数量。异常来自自制夹具刻意的gap/隔离字段，不是医学错误率。
- 目标按(kind,material_id)排序后，以i%5沿用D01的0空白/1全accept/2奇偶accept-reject/3全unable/4仅r000 accept。R为0/2/10合成声明ID，非专家。
- 每轮每声明ID一批，涵盖全部非0桶目标，K=N-ceil(N/5)，K<=1000。event数E=R×H，意见数O=K×R×H。每次submit用返回event ID及生产stable_id公式记录前序，后续轮次必须串联自己前序。D02的E不等于O，不能沿用D01一条意见一event的口径。
- 正常fixture构建完后实际inspect须健康，字节哈希固定。只测这些自制绑定/历史，不代表真实资料、第三方包或恶意完整目录回滚的验收。

## 固定矩阵与可比性

| case | U | N目标 | R | H | K | E事件 | O意见 |
|---|---:|---:|---:|---:|---:|---:|---:|
| u2-r0-h1 | 2 | 24 | 0 | 1 | 19 | 0 | 0 |
| u2-r2-h1 | 2 | 24 | 2 | 1 | 19 | 2 | 38 |
| u10-r2-h1 | 10 | 120 | 2 | 1 | 96 | 2 | 192 |
| u40-r2-h1 | 40 | 480 | 2 | 1 | 384 | 2 | 768 |
| u10-r10-h1 | 10 | 120 | 10 | 1 | 96 | 10 | 960 |
| u10-r2-h5 | 10 | 120 | 2 | 5 | 96 | 10 | 960 |
| u10-r10-h3 | 10 | 120 | 10 | 3 | 96 | 30 | 2880 |

u10-r10-h1和u10-r2-h5拥有相同N/O/E，但声明数、最新意见数、链长和输出pair行数不同。这是更有用的对照，仍不能归结为单一因素因果或直接证明R²。

每profile分别测两项操作×两种工作区模式，共28格，每格1丢弃+3正式，共112独立采集进程、84正式样本。建fixture不计入采集进程数；不把负例检查算作测点。固定顺序，不随机化，不挑更快重跑。

## 测量边界

- inspect：未修改的ReviewSessionService.inspect，含源包/准备重建绑定、真实事件wrapper/内容ID/前序历史与不变性检查。
- report：未修改的ReviewProgressService.report，包含上述完整检查和统计投影。是Service操作端到端，不包括解释器启动、fixture构造、服务对象创建或业务CLI。
- 两项操作是不同进程的独立实验，不能用中位数相减当作“统计阶段耗时”，也不能把D01时间从D02扣除。
- fresh：本进程开始时workspace不存在；计时内API自行建缓存。reused：本进程先执行同操作一次、验证并丢弃结果，再用同一workspace计时。两者都在测前读取fixture哈希，因此不叫操作系统冷/热缓存；不清系统缓存、不提权。
- 每个样本新进程，fixture共享只读、工作区独立。丢弃样本也是独立进程，不是同进程预热。reused内的预调用才是同进程缓存准备；其耗时不在计时段，但生命周期峰值包含它。
- wall_ns=perf_counter_ns，cpu_ns=process_time_ns；内存为Windows进程生命周期PeakWorkingSetSize，含导入/哈希/预调用，不能相减当增量、private bytes或Python堆。不可采则null/not_evaluated，如实报告。
- 每样本120秒；采集阶段新样本启动预算1800秒，已开始者最多再120秒。构造阶段未设置内部硬超时，若总命令超过45分钟，停止并记录，不提权或自行改数据。失败首次停止，保留部分结果，不按慢快设通过阈值。

## 正确性与不变性

每scope根据预存target顺序产生的五桶数量b0…b4作为独立oracle：R>0时pending=b0+b3、insufficient=b4、agreement=b1、disagreement=b2、unable_votes=R*b3+(R-1)*b4；R=0全pending。每人覆盖Kscope，r000 decisive=b1+b2+b4，其他人b1+b2。每对overlap=b1+b2+b3+b4、comparable=b1+b2、unable=b3+b4、matched=b1+（同奇偶时b2），0分母null。

inspect逐目标核对状态、最新意见数量、unable、无issues/坏历史及总意见；report核对上述统计、event总数、完整pair矩阵及固定医学/训练/发布门。相同profile/operation在fresh/reused和重复之间logical_result_sha256必须一致；不跨profile比较身份。每次计时前后源包/原准备目录/会话全字节哈希一致，只有本次私有workspace可写。

另在两个新副本中做非计时负例：先report预热缓存，再翻转源包一字节→SESSION_SNAPSHOT_INVALID；或改事件理由但不重封hash→diagnostic含SESSION_EVENT_INVALID、metrics不可用、无覆盖/一致率。这些副本不用于正式采集，不能改原fixture/旧真实包。

## Codex设计验证与交付

已跑1 profile的4格smoke（每格1丢弃+1正式），全部通过，源包/事件两负例正确阻断、保护哈希不变；证据artifacts/b18-d02/codex-design-smoke-final-20261025/。另仅做最大U40构造边界的功能检查：480目标/768意见/2实际事件，生产report/oracle通过，未运行该点正式矩阵。未跑7profile正式采集，不重复旧全量549项。

DeepSeek按D02单运行/重算并停executed_pending_review；Codex核验后回到原产品要求判断是否足以关闭B18或还需补项。医学/病例/许可/真实跨源/新机离线安装/跨平台/容量SLO都不因本单通过。结构与来源身份继续稳定，无新资料或外部服务授权需求。
