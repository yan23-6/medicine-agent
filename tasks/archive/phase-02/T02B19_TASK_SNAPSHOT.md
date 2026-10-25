# T02-B19 单文件多包发现与联合查询兼容验收

> in_progress；D01 executed_pending_review，待Codex核验；2026-10-25。

## 原产品与分工

B18两层有限合成基线已独立核验、回读原产品并归档，不启动未经SLO/调用归因支持的优化。B19回到原01/04/08/16及overall的数据消费目标：兼容.medpkg复制发现、联合查询、来源/owner边界、坏包隔离与移出/恢复/迁移。只CURRENT正式，NEXT不执行。

Codex负责方向、设计、固定采集器、小样与核验；DeepSeek只跑已经固定的重复构造/机械检查/证据，双方不并发修改，不允许执行方选择算法或调预期。

## 已完成设计检查点

- 设计evidence/T02B19_DESIGN.md；固定脚本tasks/benchmarks/b19_library_check.py（SHA见执行单）。
- Codex S=2小样全部9阶段通过：原生TXT/本地确定性生成函数，经生产API构建单文件；跨owner共同查询、精确副本去重、坏文件隔离、最后副本移出无缓存复活、恢复身份相同，旧输入/生成/公共根/查询缓存路径不可用后复制目录与新工作区可查询。
- 555保护文件/349Schema不变，生产src/tests/医学结构未改。证据artifacts/b19-d01/codex-design-smoke-20261025/与codex-design-verification.json。

## D01执行结果：executed_pending_review

DeepSeek已按D01执行单执行完毕，停在executed_pending_review，结果见[evidence/T02B19_D01_RESULT.md](evidence/T02B19_D01_RESULT.md)。

- 运行目录artifacts/b19-d01/deepseek-20261025T135227499Z/（新建，未覆盖Codex小样）；退出码0、整次100.61秒、failure=null、completed_profiles=3、protected_unchanged=true。
- S=1/5/20三profile × 9阶段=27阶段全部按设计表通过：公共查询匹配S节点/S独立来源，S>1共同返回两owner；精确副本只增物理文件（S+1）不翻倍命中；broken.medpkg恒quarantined/PACKAGE_FILE_INVALID；最后副本移出后为S-1（S=1为0）且无缓存复活；恢复后身份集与初始一致；迁移只复制公开目录、原四路径不可用、新工作区查询通过。
- 独立校验117项检查全通过；555文件保护映射/349Schema前后未变；两脚本/设计/执行单哈希未变；git status/diff --stat前后逐行相同，git diff --check通过。
- 本单未归档B19、未推进NEXT、未写性能/医学/许可门passed；B19是否整体验收由Codex回读原产品要求判断。

不改脚本/设计/执行单、生产代码/测试、349Schema/语义、md/overall或旧真实包；不手写重封包/减来源/调查询逻辑让结果通过。遇到失败留证交回Codex，不优化、不归档、不推进NEXT。

只覆盖原生TXT/theory自制数据和现有实验单文件入口；不冒称临床、五类资料全覆盖、真实跨源、权限认证、异机/跨平台、性能SLO、正式包v0或LadybugDB。迁移只移动本次自制profile目录且先验证绝对路径边界，不触及用户数据。

无新资料外发/依赖安装/LLM/真实OCR/蒸馏/训练，不读模型配置，不commit/push；不改数据包结构或来源身份。下一步无需新文件或权限，等Codex核验结论。
