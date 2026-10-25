# B16 离线发行依赖材料核验设计

实施前设计，2026-10-25。已核对B15预检和发行wheel真实存在。B15完成后回读原产品01/04/08/09章确定：版本元数据通过仍不能证明本机具备离线安装文件。

新包外模块`medicine_agent.wheelhouse`提供`inspect_wheelhouse(directory, snapshot)`、独立console `medicine-agent-wheelhouse --wheel-dir --snapshot`，只读无执行/解压/安装/联网。不经Pydantic/医学主CLI。输入是显式B15 environment-preflight/0.1.0通过报告，冻结当前Python/OS/架构与全部活动依赖版本；其他平台报告明确拒绝，不猜测交叉安装。packaging缺失not_evaluated。

只检查目录顶层wheel，目录和候选文件拒绝symlink/reparse。最多500wheel，单文件512MiB、展开总2GiB、20000成员、元数据/RECORD各4MiB；不读取其他文件/嵌套目录。安全打开文件、同句柄SHA256/ZIP，检测读期间元数据改变。拒绝重复ZIP成员、越界路径、链接、损坏/缺失WHEEL/METADATA/RECORD、非法包名版本、文件名/元数据/标签不符。按RECORD对每个文件的sha256与大小复核；这是内容自洽检查，不是签名或可信供应链认证。

按快照选精确版本且当前平台兼容的唯一wheel；缺件/歧义/不兼容保持blocked。对选中的wheel元数据重新运行B15依赖闭包：markers/extras、Requires-Python、全部活动传递要求都必须符合冻结版本；快照不能多带或漏掉分发。结果wheelhouse-readiness/0.1.0含精确wheel大小/SHA256、缺件、诊断与metadata_resolution状态；即使通过，也只表示当前环境标签/元数据闭包与文件自洽，installation/native_runtime/model_resources仍not_evaluated。输入清单没有受信签名，不能证明版本来自可信供应商。

合成wheel覆盖完整正例、空目录/缺件、版本/标签/RECORD/元数据/路径/重复/限制、依赖闭包及CLI只读；本地真实目录只含项目wheel应报告缺依赖，不联网补齐。旧345份Schema/真实包/准备材料不改。完成后产品复查再归档，第三项由结果重评。
