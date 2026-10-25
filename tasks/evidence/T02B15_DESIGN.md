# B15 环境预检与可复现清单设计

实施前回读原产品01/04/08/09章与最终需求。独立运行不依赖开发智能体；预检不能反过来依赖全部医学运行库。

交付stdlib-only模块`medicine_agent.preflight`，API `inspect_environment()`和独立`medicine-agent-preflight`入口/`python -m medicine_agent.preflight`，不经现有主CLI的Pydantic导入。输出environment-preflight/0.1.0 JSON：Python/OS/架构、项目版本/安装方式、活动运行依赖闭包的实际版本、要求及状态、可复现版本清单、诊断码。默认不输出安装绝对路径、direct_url URL或异常正文。不导入OCR/医学库、不读模型配置、不写目录、不联网/安装。

依赖规范使用可选packaging解析，缺解析器则not_evaluated，不能猜测PEP440/508。元数据缺失/损坏、依赖缺失/版本不符/Python不符明确blocked；未评估状态阻止ready。遍历活动传递依赖，正确传播extras、求值markers，至多500分发/5000要求防异常元数据。循环去重。版本快照不是锁文件，不包含平台wheel/下载哈希，不保证缓存和原生库/OCR资源可用；offline_cache/runtime_imports/model_resources恒not_evaluated。项目来自editable须明示，不冒充已安装wheel。解析器缺失不妨碍诊断入口启动。

新操作清单不属于.medpkg，不改任何旧Schema或医学门。合成元数据覆盖缺失/不兼容/marker/extras/循环/非法要求/解析器缺失/来源、并在当前环境及隔离安装环境只读对照。完成后回读产品目标和08/09章，归档后再重评NEXT。
