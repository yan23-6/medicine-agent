# B12复核会话设计与分步契约

2026-10-24。实现前设计；只有明确标为已验证的步骤才构成当前能力。B11的review-preparation/0.1.0、review/0.1.0、医学注册表及包协议保持兼容。

## 一、分步与版本

1. D01现状核查已核验，只是证据收集。
2. Codex实现准备快照读入核心；D02由DeepSeek按本设计扩充合成坏输入矩阵并执行固定验证，Codex核验。
3. 快照核心检查点通过后，Codex冻结review-session/0.1.0的11个Pydantic模型（第五节）；D03交DeepSeek接入Schema导出和固定契约测试。模型已有初始实现，Schema尚未生成或验收，持久化/API/CLI仍未实现。
4. 完整会话与发行验收通过后归档B12，才重评B13。

## 二、快照核心：当前实施契约

内部类型化Python管理入口：`analysis.review_snapshot.load_preparation_snapshot(snapshot_dir, *, packages, workspace)`，返回`ValidatedPreparationSnapshot`（snapshot_id、manifest_sha256、export、report）。不登记Agent/Skill，不新增CLI、Schema、医学字段或模型调用。返回对象是本次验证结果，不是签名或永久授权令牌；后续持久化/写入前必须重验绑定，不能信任调用者修改后的Python对象。

只接受review-preparation/0.1.0的完整、空白准备快照。partial/empty显式拒绝为`SNAPSHOT_STATUS_UNSUPPORTED`，不称损坏；以后支持时另加契约，不静默将partial变complete。历史用户意见允许存在于review_records，所有新worksheet仍必须为空且submitted=false。当前版本要求原包可用；缺包给明确错误，不能仅凭自报指纹认定可信。迁移验证需复制相同字节的包并保留成品文件名；改名需重新导出准备材料。

验证顺序固定：

1. 路径：快照/源包目录已存在，workspace可新建；三者互不嵌套。路径从已有祖先至目标不得含symlink/reparse point；快照恰好7个普通文件（与B11一致）。拒绝异常后立即返回，不能再按未知manifest路径读取。
2. 每个快照文件最大64MiB，总量最大128MiB，超限拒绝`SNAPSHOT_LIMIT_EXCEEDED`，不截断或部分接受。读前后lstat并比较身份/大小/时间，结束重新读取完整快照比较哈希，观测到变化即失败。此为本地协作一致性检查，不声称能对抗具有操作系统写权限的恶意进程。
3. JSON拒绝重复键、非有限数及非法UTF-8，manifest和report必须对象。先检查显式version=0.1.0，再做既有Pydantic类型校验，防止缺版本被默认值填充。manifest.files必须恰为固定6个正文文件且SHA256均为小写64位十六进制；拒绝路径或额外资源。所有哈希根据已读取的原始字节计算。
4. manifest/report准备ID、status一致，重新按B11稳定ID算法比较Report；全部新worksheet为空。类型校验不能替代来源校验。快照身份为`stable_id('snapshot', {'manifest_sha256': <manifest原始字节哈希>, 'preparation_id': <报告ID>})`，格式变化也视为新快照；保留6文件的字节哈希绑定。
5. 源包绑定：从report.coverage.records中的address取得非空、纯文件名.medpkg集合，使用既有ReviewPreparationRequest先验证。读取所选包原始字节哈希，与每条address.archive_sha256比较。只读调用现有prepare(archives=该集合)，在指定独立workspace重建报告；完整model_dump必须与快照report相同。这同时重验来源/证据、材料ID、目标指纹、计数、异常、历史和质量门，避免另写一套医学或材料定位规则。源包或内容变更不得继承认可。重建无需PDF/OCR/模型；缓存可写，源包/快照不可写。坏包等导致重建partial也不能通过。
6. 渲染完整report的5份Markdown，与快照对应文件的UTF-8字节逐一比较，拒绝只改展示材料后重算manifest的伪造。JSON空格/键序可以不同，只要结构与绑定相符；不自动改写文件。
7. 再读取所选包哈希和快照全部字节；任何变化拒绝，不返回验证对象。失败不创建会话、不写意见或部分正式产物；只可能留下可重建私有缓存。

错误均为AnalysisError，固定非敏感消息，不带原文、候选、服务地址或底层异常正文。分类：SNAPSHOT_PATH_INVALID、SNAPSHOT_RESOURCES_INVALID、SNAPSHOT_LIMIT_EXCEEDED、SNAPSHOT_JSON_INVALID、SNAPSHOT_VERSION_UNSUPPORTED、SNAPSHOT_SCHEMA_INVALID、SNAPSHOT_HASH_MISMATCH、SNAPSHOT_ID_MISMATCH、SNAPSHOT_STATUS_UNSUPPORTED、SNAPSHOT_WORKSHEET_NOT_EMPTY、SNAPSHOT_SOURCE_UNAVAILABLE、SNAPSHOT_SOURCE_MISMATCH、SNAPSHOT_PRESENTATION_MISMATCH、SNAPSHOT_CHANGED。错误优先级按上述阶段，不承诺同阶段多个坏项的顺序。

## 三、会话持久化与意见（后续实现）

会话与源快照、源包分目录；新会话绑定快照身份、全部文件哈希与源包身份，保存可迁移的只读准备副本。创建采用同父临时目录、全部校验后原子改名，拒绝覆盖。迁移/恢复时先检查副本清单与会话身份；需要确认来源时仍须提供同字节源包。不保存开发对话或本地配置。

意见独立输入，不导入已填写准备表。目标分source_annotation/candidate/anomaly三类，绑定snapshot_id与对应稳定材料ID；candidate额外绑定完整ReviewTarget。source纠错只存候选；anomaly意见只审计，永不转成ReviewRequest。意见决定为accept/revise/reject/unable_to_judge，理由和声明评审者ID必填且去首尾空白，展示名/专业角色为声明，不认证专家。未填不创建意见；unable_to_judge保留明确记录，仍待审。

独立意见按评审者ID+材料地址分历史链，修改由同一声明ID追加，不把同一人的新记录算独立第二人。明确expected_previous_id；服务端UTC时间、内容哈希、稳定ID、前序均校验。最初版本逐条提交为事务：持进程锁，验证会话、全历史和前序后，原子写一条完整事件。批导入先全量校验、整批提交单个不可覆盖事件文件，不逐条写半批；事件保存有序意见列表并在持锁状态验证各链。不在检查点外隐式修改头指针，视图从有效历史重建。相同内容/客户端submission_id重复返回同一记录；同submission_id不同内容拒绝。分支、缺历史、环或篡改阻断相关会话写入，不擅选最新分支；读取仍返回异常和健康内容。具体文件模型、批事件Schema及CLI参数在第3步冻结，不交给执行助手自行设计。

一致性只比较不同声明评审者的最新有效决定，unable_to_judge单列、不能补足独立意见。pending/insufficient_opinions/agreement/disagreement/awaiting_adjudication分别展示；agreement仅意见一致，不能映射为医学confirmed。存在分歧时保留每人理由，不按时间、票数或模型偏好决断。当前不实现认证仲裁或已裁决状态，分歧标awaiting_adjudication。

不自动写ReviewRequest或.medpkg。未来显式转换只允许candidate且accept→confirmed、revise→needs_revision、reject→rejected；unable_to_judge无转换，仍满足既有reviewer/reason/proposed_value/expected_previous_id约束。转换本身也不是提交、医学认证或知识值修订。

## 四、验收与范围

D02重点覆盖坏哈希、未知/缺版本、重复键、路径/链接、报告ID、目标及来源篡改（包括同时重算报告ID和manifest）、空白模板、状态、展示材料、坏包/缺包、读取中变化及私有缓存边界。健康源包和准备目录前后哈希不变；真实材料只由本地脚本读取并输出摘要，真实意见写入0。

完整B12还必须覆盖独立意见、无法判断、重复/过时/分支/并发、迁移恢复、类型化API/CLI、Schema、独立发行及受保护路径。医学、许可、规模和跨源门仍独立；本设计不授予资料外发、训练或发布许可。

## 五、review-session/0.1.0冻结的结构与算法

Pydantic唯一结构源：`src/medicine_agent/domain/review_session.py`；`REVIEW_SESSION_MODELS`固定11项。独立操作契约不新增医学字段、不修改旧review/准备/包协议、不登记Agent/Skill。Schema仅表达模型可导出的约束；跨字段validator、原包绑定、内容ID和历史校验仍需Python运行时，不能只靠JSON Schema宣称可信。

| 模型 | 固定职责 |
|---|---|
| SessionSnapshotBinding | snapshot_id、preparation_id、manifest_sha256、7文件哈希snapshot_files、非空源包文件名→哈希source_archives |
| SessionReviewer | reviewer_id、display_name、declared_role；identity_status只能self_declared |
| SessionTarget | snapshot_id、kind、material_id；只有candidate必须且允许携带ReviewTarget |
| SessionOpinion | target、decision、非空reason、可选proposed_value、expected_previous_id |
| SessionSubmission | version、session_id、submission_id、一名reviewer、1—1000项opinions；一批同材料仅一项且同一snapshot |
| ReviewSessionManifest | version、session_id、UTC created_at、binding；声明身份/未审/禁止发布固定值 |
| SessionEvent | version、event_id、UTC created_at、submission；一次原子批事件 |
| SessionOpinionRecord | event_id、opinion_index、派生opinion_id、同事件时间/评审者及原opinion；只读投影，不单独落盘 |
| SessionIssue | 非敏感code及可选event_file，不带真实正文或底层异常 |
| TargetReviewSummary | target、agreement_state、adjudication_state、latest_opinion_ids、unable_to_judge_count、history_invalid |
| ReviewSessionView | manifest、全部有效opinions、targets、issues、writable及固定医学边界；有issue/异常历史禁止writable |

reviewer_id去首尾空白并casefold，规范化后为最长128字符的ASCII字母数字/点/下划线/短横线标识，以字母数字起始；大小写变化不能产生第二票。别名及冒名无法自动认证，两个声明ID也不证明两名真实专家。display_name与declared_role去首尾空白且非空。submission_id最长128字符，ASCII同类安全字符，区分大小写，在会话内唯一；重试比较规范化后完整提交内容，同ID不同内容拒绝。

材料ID前缀固定annotation_/reviewitem_/anomaly_，后缀24位小写十六进制，分别对应source_annotation/candidate/anomaly。snapshot_/reviewsession_/sessionevent_/sessionopinion_后缀均为24位小写十六进制，SHA256为64位。结构类型符合不等于已在快照中存在，运行时必须逐项精确匹配。意见reason去首尾空白、最长8000字符；所有决定均要求理由。修正候选仅revise允许；source_annotation只允许非空字符串纠正候选，anomaly不允许proposed_value，candidate沿用JsonValue但不得自动发布。

会话目录布局固定为session.json、preparation/（7文件副本）、events/、.session-write.lock；工作缓存和原包在外部互不嵌套目录。session.json包装为`{"manifest":<ReviewSessionManifest>,"sha256":<content_hash(manifest)>}`；事件文件events/<event_id>.json包装为`{"event":<SessionEvent>,"sha256":<content_hash(event)>}`；包装键集合严格，未知版本、重复JSON键与路径异常拒绝。SHA256只保证完整性，不构成可信签名。

session_id=stable_id('reviewsession', manifest.model_dump(mode='json',exclude={'session_id'}))；event_id同法以sessionevent为前缀排除event_id。单条opinion_id=stable_id('sessionopinion', {'event_id':event_id,'opinion_index':从0开始序号})，不依赖时间排序，意见时间取事件UTC时间。运行时负责重算ID/外层完整哈希和文件名一致性；模型不自行生成这些标识。导入事件不得重写旧文件或重分配ID。event里的submission.session_id必须与当前会话相同，目标snapshot_id和全部material/ReviewTarget必须与绑定副本相同。

expected_previous_id寻址同一规范化reviewer_id、同一材料的派生opinion_id；其他评审者的意见不能当此前序。整批在锁内预验证全部链、所有目标、submission_id幂等及无健康历史污染后，仅提交一个不可覆盖完整事件文件；失败无部分意见。未知/损坏/分支历史令会话writable=false，视图保留可审计健康事件，异常目标不选择最终意见；不能按时间裁分支。临时文件不作为已提交事件，恢复不删除不属于本次操作的文件。

agreement_state固定pending/insufficient_opinions/agreement/disagreement。仅统计不同规范化声明ID各自最新有效意见：无明确决定为pending（包括全部unable）；一名为insufficient；两名及以上比较decision和规范化JSON proposed_value，完全相同为agreement，否则disagreement。理由始终保留但不以理由文字差异自动制造或消除分歧。unable单列计数，不计入明确决定人数。disagreement必须对应awaiting_adjudication，其他为not_required；无已裁决状态。history_invalid时不得展示已确认结论，即使agreement也不能升级medical_review。

后续运行时入口固定为`ReviewSessionService(packages, workspace).create(preparation_dir, output_dir)`、`.inspect(session_dir)`、`.submit(session_dir, SessionSubmission|dict)`；创建返回manifest，读取返回view，提交返回event（含幂等同一结果）。这些签名在D03不实现，CLI映射在运行时实现后再交接。D03只接入现有export-schemas命令的新契约选项。

## 六、运行时实施细节（包外，Schema不变）

所有会话操作重验preparation副本与同字节源包，session.json、事件包装只接受规范化model_dump的完整字段、显式0.1.0及固定包装键。创建在目标同父临时目录复制并重验快照，最终改名；同父`.session-create-<目标路径稳定哈希>.lock`串行化协作创建者，目标已存在一律拒绝，不能覆盖。锁由OS持有，文件残留不是锁仍被占用，不删除他人锁。当前验收平台Windows，跨平台原子目录发布仍需独立验收，不声称能对抗拥有OS写权限的非协作进程。

创建锁哈希使用`stable_id('path', os.path.normcase(str(已resolve的目标目录)))[5:]`的24位后缀，避免Windows同路径大小写写法创建两把锁。

提交持会话内.session-write.lock；inspect不创建锁，检查前后manifest/副本/选定源包与事件目录观测状态一致，否则SESSION_CHANGED。事件先写本次临时文件并fsync，再以同目录hard link原子发布不可覆盖目标，最后只清理本次临时文件；文件系统不支持该操作时明确失败，不降级为可见半文件或覆盖写。遗留`.pending-session-event-*.tmp`只作未提交临时资源，安全普通文件可忽略且不自动清理，链接/其他未知资源报告异常。

每事件最大64MiB、一次历史扫描累计128MiB、已提交事件最多10000；超限SESSION_LIMIT_EXCEEDED，不截断视图或提交。每个事件全量验证类型、显式版本、完整哈希、稳定ID、文件名、session_id、全部目标；一项非法则整事件隔离，其他健康事件保留审计。按规范化reviewer_id+kind+material_id建独立链，检查单根、单头、前序存在、无重复后继和遍历无环。坏链标history_invalid，不选该链最新；其他健康链可展示，但有任何issue/坏链就writable=false。损坏会话manifest/绑定副本则整体拒绝，不伪造健康视图。

幂等检查在健康历史成立后执行；相同submission_id与规范化完整提交内容相同返回旧事件，即使其前序后来已更新也不产生新票；同ID不同内容SESSION_SUBMISSION_CONFLICT。正常新提交要求session匹配、精确目标相同、每条expected_previous_id等于本评审者本材料当前头；任一失败整批拒绝，不追加部分记录。

错误固定非敏感AnalysisError：SESSION_PATH_INVALID、SESSION_EXISTS、SESSION_MANIFEST_INVALID、SESSION_SNAPSHOT_INVALID、SESSION_EVENT_INVALID、SESSION_HISTORY_INVALID、SESSION_SUBMISSION_CONFLICT、SESSION_REQUEST_INVALID、SESSION_TARGET_INVALID、SESSION_STALE_WRITE、SESSION_BUSY、SESSION_CHANGED、SESSION_LIMIT_EXCEEDED、SESSION_COMMIT_FAILED、SESSION_IO_ERROR。inspect中的坏事件转为SessionIssue（含安全文件名），submit有任何历史issue拒绝；绑定和资源根错误不以issue掩盖。所有底层异常上下文抑制，避免正文泄漏。事件hard-link提交需要本地文件系统能力，验证时明确平台边界。

无法解码的坏事件或重复submission_id不能可靠定位受影响链，故所有目标标history_invalid、agreement_state=pending；仍返回健康事件原意见供审计，不把可能过时的健康头当最终结论。已定位的单链分支仅标该材料异常，但整个会话阻止写入。哈希和前序可发现引用缺失、篡改、分支；没有外部可信锚点/签名时，不能证明完整一致目录未被整体回滚，此威胁边界不得冒称已解决。

业务CLI映射固定：`analyze review-session-create --preparation-dir --output-dir --packages --workspace`、`analyze review-session-inspect --session-dir --packages --workspace [--include-opinions]`、`analyze review-session-submit --session-dir --input-file --packages --workspace`。路径参数均显式必填，无默认HOME、模型配置或服务调用。创建只输出manifest；提交只输出version/event_id/session_id/submission_id/opinion_count和固定医学边界，不输出意见正文。inspect默认输出version/session_id/snapshot_id/writable/opinion_count/target_count/state_counts/issues及固定医学边界；--include-opinions才输出完整ReviewSessionView，含用户意见/纠正候选，真实内容不得送入执行助手上下文。CLI提交文件限64MiB，严格JSON对象/重复键/非有限数/显式version=0.1.0，非法统一SESSION_REQUEST_INVALID；不能传准备表。CLI错误沿用既有非敏感PlatformError出口，不增加包内写接口或新Skill。
