# B12-D05 自主执行结果

2026-10-25；Codex自主执行并核验，done（D05子步骤）。依据用户最新单独连续推进授权，不等待DeepSeek。

- 3项submit发布前限额补测：3 passed/69 deselected（11.50秒）。既有历史可读，过限请求未触及_publish，事件/源包/副本未变。
- 发现旧构建声明0.12系列与本地uv0.13.1不匹配；旧严格PEP517离线失败，日志保留。已将pyproject构建后端固定uv_build==0.13.1；不改运行依赖、数据结构或医学Schema。对齐后的uv离线构建成功。
- 干净依赖解析缺pydantic2.13.5缓存，未联网。将现有38个依赖分发的3495文件物理复制到新环境，再离线--no-deps安装本项目wheel；不使用system-site-packages/editable/PYTHONPATH。此为依赖快照隔离，不是空缓存安装全通过。
- python -I独立闭环通过（13.148秒）：自制TXT+本地SyntheticModel产包、准备、两名声明评审者分歧/幂等/过时拒绝、复制迁移后继续、三条CLI及默认/完整输出边界；加载的项目子模块全部来自新site-packages。自制意见不是医学评审，未触及真实资料。
- wheel/sdist各115项源码/资源双向逐字节一致，禁止路径命中0；wheel207845字节/SHA256 bff10d07c4b9c31b64478e1bd259ccb960b027608baa67b874a7af008f51c002；sdist163522字节/SHA256 2ee44645daab4b1b1d06d2227149da75e956d3443a71992fbde6eebd059a145a。
- 审计341份Schema、74份当前范围Markdown本地链接（错误0）、受保护输入/路径和忽略规则通过。原.medpkg及准备目录全部字节未变；真实意见仍0。
- 不重复D04已通过的435 passed/2 skipped全量；本轮生产变化仅构建元数据，项目src和Schema与D05启动基线相同。现有Windows实链权限skip、跨平台/依赖版本范围/医学/整体回滚边界保留。

运行目录：D:/test/tongyongzhengliu/artifacts/solo-20261025/20261025T065319605463Z。所有尝试独立log/JSON保留；正式发行物在dist-aligned，旧探测产物不是最终发行依据。evidence-manifest.json不含自身，SHA256 59a420e1f4b7bcfdf5bb8f752ff7c6084ac792dac0edf1d71052c0266cdf4d96。

最终工程归档由B12验收及产品符合性复查给出，不以本文件宣布阶段02完成。
