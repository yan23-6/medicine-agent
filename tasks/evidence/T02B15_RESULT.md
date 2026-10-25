# B15 验收结果

2026-10-25，done。实施前设计见[T02B15_DESIGN.md](T02B15_DESIGN.md)。18 passed，0.44秒；源文件/资源118项在wheel和sdist逐字节一致；新隔离环境python -I/API与独立console入口输出相同，项目来源archive，34个活动分发元数据满足要求。原有345份Schema及真实包/7份准备材料哈希不变。

预检只读、stdlib可启动，缺Pydantic/packaging仍可诊断；缺失/版本冲突/Python不符/marker/extras/闭包循环/异常元数据/URL隐藏/限额均覆盖。版本清单不是安装锁；未宣称原生库、OCR模型或空缓存离线安装成功。本轮不联网、不安装新第三方版本、不读模型配置、不生成医学意见。

首次隔离验证uv误用全局缓存被沙箱拒绝，改为已授权工作区缓存后通过，两个尝试日志分开保留。依赖是前轮已安装快照的物理复制，未冒称新机依赖解析成功。

证据：artifacts/solo-next/20261025T110558Z/b15-target-final.log、b15-release.log（失败）、b15-release-02.log（通过）、b15-release-audit.json、b15-installed-report.json。本阶段尚不需要全量重跑；新增入口独立于旧业务分派，三任务最终统一全量。


后续整合核验：B17整合时新增非法版本/非字符串Requires-Python防御用例，当前本文件20项；整体全量通过。历史B15的18项结果不改写。


## 最终公开契约补充验收（2026-10-25）

初次完成检查遗漏了overall“新公开结构必须生成Schema”；已暂停最终完成、回B17整合补齐runtime-readiness/0.1.0四Schema。原历史档案不改写，以[补充验收](../archive/phase-02/T02B15_B17_SCHEMA_FINAL_ACCEPTANCE.md)共同说明最终完成。最终全量549 passed/2 skipped（JUnit 621.50秒），95项定向、122源资源发行、新安装四Schema字节一致及同进程无下载OCR正负例通过。旧345Schema及12索引不变，新增4份包外操作Schema+索引，总349；数据包与来源身份不变。B18仅登记ready，本轮停止。
