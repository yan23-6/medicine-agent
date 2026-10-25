# B19 Codex核验

2026-10-25，verified（限定工程范围）。独立核验脚本artifacts/b19-d01/codex_review_b19.py，最终摘要artifacts/b19-d01/codex-review-20261025T140125896970Z/review.json。

1543项清单逐文件大小/SHA及清单本体4b38db82…fb323fa相符；冻结两脚本/设计/执行单未变。三个case/stdout相同、stderr空；逐行独立核对1/5/20×9阶段的命中/来源/owner/物理可读与隔离文件/身份集合，555保护文件、349Schema、git前后快照通过。

每profile原生输入SHA、正常.medpkg字节、精确副本、移出/恢复身份均相符。原knowledge/inputs/generation/query-cache路径不可用；retired/knowledge与migrated-knowledge字节映射相同，隔离坏文件保持原字节。公开目录除包还含统一spec/说明书/发布锁，执行方第一次校验误把它们算作意外文件，范围修正合理；不影响原始采集/产品，未重跑。

Codex额外用新私有工作区调用未修改生产查询，迁移后的20来源各自节点/原文/源SHA/owner身份全部通过，命中20，owner-a/b共同可见；未重跑27阶段。

初次核验受沙箱限制无法读取构造缓存.selected.json；获准只读访问后使用新审计目录完成，未改ACL/原始证据/代码。核验只在新的Codex目录写查询缓存/摘要，没有用户数据移动。

结论：B19规定的实验单文件、TXT/theory合成消费闭环已通过，符合任务范围；不是五类资料全覆盖、医学正确性、跨平台、权限认证、正式包v0、LadybugDB或性能SLO。原真实包、349Schema、生产代码/测试不变。下一步先回到原产品要求复查再归档，不仅凭执行方passed直接推进。
