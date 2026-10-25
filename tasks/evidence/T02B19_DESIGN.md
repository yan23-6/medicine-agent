# B19单文件多包发现与联合消费兼容设计

2026-10-25；B18验收归档并完成[原产品复查](T02B18_PRODUCT_REVIEW.md)后，CURRENT启用B19。Codex设计/小样/核验，DeepSeek固定执行。不是另起数据库或改包协议。

## 目标与前置

原01/04/08/16及overall要求普通兼容单文件复制发现、共同查询、保留来源、不因owner分割查询、坏包隔离及完成产物独立迁移。已检查生产PackageLibrary.scan/view/query、FileLearningService、compose去重与PackageCatalog.query实际返回。既有目录接口/三源测试不等于20个独立单文件的同一路径已验证。

只做现有实验.medpkg-0.1.0入口的合成兼容验收，不冻结正式包v0、不接LadybugDB、不改变349Schema/来源身份/生产代码。任务不设性能SLO，也不继续针对B18推测瓶颈优化。

## 固定采集器与数据

tasks/benchmarks/b19_library_check.py是内部开发验收脚本，不是新产品API或公开数据契约。使用原生TXT适配器（不模拟OCR/文件识别）和本地确定性SyntheticModel，经FileLearningService真实构建、发布每个单文件。无外部模型调用、无真实资料。

正式profile S=1/5/20，每个来源一行自制文本、1节点/1字段；共同标题Shared synthetic concept，正文含公共token LIBJOIN_SOFTWARE_ONLY及唯一SOURCE0000等编号，SHA因自制文本不同而不同。owner依次author-a/b，S>1应共同返回两个owner来源；不是认证/修改权限。

构造后从实际归档读取源SHA、source_id、component package_id、node_id、bundle_id、节点内容SHA、归档字节SHA，核对独立原生输入SHA和文本；每profile内S份SHA/source_id/component/bundle身份各独立。跨profile重复使用同一配方，不相加宣称26个独立来源。没有临床真实性，只覆盖TXT/theory实验Profile。

## 固定9阶段（每profile）

| stage | 查询 | 匹配节点 | 可读物理文件 | 隔离文件 |
|---|---|---:|---:|---:|
| initial-common | 公共token | S | S | 0 |
| unique-source-0 | SOURCE0000 | 1 | S | 0 |
| exact-copy-deduplicated | 公共token，加精确副本 | S | S+1 | 0 |
| bad-file-isolated | 公共token，加broken.medpkg | S | S+1 | 1 |
| primary-removed-copy-retains-source | 原文件移出、副本尚在 | S | S | 1 |
| last-copy-removed-no-stale-content | 副本也移出 | S-1 | S-1 | 1 |
| removed-unique-token-absent | SOURCE0000 | 0 | S-1 | 1 |
| restored-same-identities | 恢复原文件、公共token | S | S | 1 |
| migrated-copy-only-new-workspace | 只复制公开交付目录，新工作区 | S | S | 1 |

物理文件清单允许同时列出两个同bundle_id的精确文件，逻辑节点/来源不能翻倍。只移出一份而副本仍在时来源继续可用；最后一份移出才撤销，不把副本当独立来源。S=1时必须覆盖0个可用包的空目录结果，不能由缓存复活内容。

## 输出与独立oracle

公开查询是PackageLibrary.query(create_facade(),text=...,max_hops=0,max_nodes=50)。最多20节点未触发50节点截断；本单不验多跳关联/索引/向量。注意现有query.packages会含匹配为空的包条目，不能用len(packages)代替命中数；应展平medical_nodes。

每个命中严格核对(component_id,node_id)集合、完整节点内容SHA（仅剔除运行时retrieval_facets）、node.source_id、source.sha256、owner归属、证据source_id及自制原句。结果必须unreviewed、consultation_available=false，无用户意见/复核错误。不以同名概念覆盖源节点，也不把owner作为消费分区。保存的是哈希/身份/计数，不输出查询正文。

每阶段单独核对package_files可读/隔离数量、bundle身份集合，broken.medpkg必须PACKAGE_FILE_INVALID；所有正常归档字节始终与构建值相同，精确副本与原件SHA相等。查询前后公开目录全文件字节映射相同；prepare生成的统一package-spec和说明书已在构造/发布时存在，允许创建临时文件但完成后字节不变。私有缓存按现有代码写入，不当作医学事实。

迁移只复制公开knowledge目录（含统一说明/源包/隔离坏文件），不带输入/生成工作区/查询缓存。随后将原knowledge/inputs/generation/query-cache四目录改名到本profile的retired目录，使所有原路径不可用，再用新PackageLibrary和全新migration-fresh-cache查询。同进程开发测试，不宣称异机/跨平台认证。每次移动前代码验证源/目标的绝对解析路径都在本profile且在工作区内，目标不存在，不删除或移动任何用户文件。

## 执行与停止边界

正式只跑S=1/5/20三profile，各1次；27个阶段断言，非随机性能实验，不报p95/SLO。每profile独立子进程900秒，首失败停止，保留部分产物。只写新artifacts/b19-d01目录，保护现有源码/测试/Schema/设计/真实包不变，不改核心、不降预期、不以修数据绕过失败。

Codex已跑S=2设计smoke（9阶段）全部通过，包含跨owner、精确副本、坏文件、两步移出/恢复与原路径不可用后的迁移；保护映射不变。证据artifacts/b19-d01/codex-design-smoke-20261025/。正式1/5/20尚未执行，留给DeepSeek；不重复全量549项/发行构建。完成后Codex核验并回到原产品要求，再判断B19是否验收及后续。

无新真实PDF/LLM服务/依赖安装/训练或资料外发，不读模型配置；真实757复核目标仍0意见，医学/许可/病例/真实跨源/大容量SLO门不由这些合成包通过。当前无需用户新增资料或权限。
