# B14复核覆盖与声明意见统计设计

2026-10-25，实施前设计。依据原产品第09章与B13门重评，不新增医学正确性判断。

## 契约与调用

新增review-progress/0.1.0独立管理契约，4模型：MaterialReviewCoverage、ReviewerCoverage、ReviewerAgreementPair、ReviewProgressReport。Pydantic位于domain/review_progress.py，为唯一结构源；export-schemas独立导出，不拼COMMON_MODELS/Skill，旧341份Schema不变，不改.medpkg/语义注册表/已有会话事件。

`ReviewProgressService(packages, workspace).report(session_dir)`先调用已验收ReviewSessionService.inspect，重验原包/快照/历史，只写私有缓存；返回类型化报告。内部纯计算函数只处理该可信视图，不当作身份认证入口。新CLI `analyze review-session-progress --session-dir --packages --workspace`均显式必填，输出报告JSON，不读配置、不调用模型、不写会话/源包。不注册Agent/Skill。

## 统计定义

- 四个互斥分组：source_annotation、candidate_node、candidate_fact、anomaly；节点和字段不继承认可，不能按字段数量把全部原文视为已审。
- 只使用每目标latest_opinion_ids对应的各规范化声明ID最新有效意见，更新不增加独立票数。reason、原文、纠正候选正文不进入报告；比较内部只看decision与canonical_json(proposed_value)，保留精确值区别。
- 每组coverage：total、pending、insufficient_opinions、agreement、disagreement（四状态和=total），unable_votes为最新unable意见数，不能当已明确审核。
- 每声明ID/每组coverage：targets、decisive、unable（三者满足targets=decisive+unable）；IDs只是self_declared，不证明独立专家。
- 每对不同规范化ID、每组：overlap（双方均给最新意见的材料数）、comparable（双方都非unable）、matched、conflicting、unable（至少一方unable）。overlap=comparable+unable；comparable=matched+conflicting。agreement_fraction=matched/comparable，分母0必须null，绝不能为100%。即使overlap0也保留该行，零评审时pairwise为空。
- 最新IDs必须存在、归属正确目标，每目标同一规范化ID最多一个最新意见；还核对其派生状态/unable计数与视图相符，不把结构类型通过当作可比较性。坏历史/不可写视图只给diagnostics、目标总数及有效事件引用；coverage/reviewers/pairwise为空、reviewer_count=null、metrics_available=false，不拿健康子集当全部最终头。

报告含version、report_id、session_id、snapshot_id、有效event_ids、target_count、reviewer_count、coverage、reviewers、pairwise、diagnostic_codes、metrics_available、declared_agreement_complete及固定门。report_id=stable_id('reviewprogress', report.model_dump(mode='json', exclude={'report_id'}))，相同会话状态排序后确定性相同，不嵌入运行日期、路径或原文。

declared_agreement_complete仅健康、非空且所有目标均达到agreement时为true；它不是医学质量门。engineering_gate仅报告计算/历史健康passed或blocked；medical_gate恒blocked、license_gate/performance_gate恒not_evaluated、reviewer_identity=self_declared、phase02_complete/release_allowed/training_allowed恒false。不可用工程相同意见宣称阶段02或训练已通过。

## 边界/错误

最多100名声明评审者、100000目标；超限REVIEW_PROGRESS_LIMIT_EXCEEDED，拒绝而不截断、不给部分比率。边界为计算资源保护，不是性能SLO。最多四行×4950对，输出有界。视图内引用/计数不一致或类型不合法为REVIEW_PROGRESS_INPUT_INVALID，固定非敏感AnalysisError，抑制底层异常正文；源快照/会话失败沿用已验收SESSION/SNAPSHOT错误，不掩盖。

空白但健康会话metrics_available=true，reviewer_count=0，各组pending=total，pairs为空、declared_agreement_complete=false；表示能计算空状态，不代表已完成任何人工审核。异常会话metrics_available=false，不用0票计算假一致。

## 验收

纯计算与实际合成会话覆盖：0/1/2人、相同ID更新、unable、不同修正值、缺引用/错目标/重复最新ID、空组/无重叠、坏历史诊断、资源上限、确定性/不输出正文、版本/Schema/CLI和源包/会话不变。真实空白只读0意见、757目标分组188/63/478/28；不填意见。定向后必要全量、旧Schema哈希、独立wheel与资源/文档检查。完成后回读原产品设计并记录PRODUCT_REVIEW，才归档B14和重评下一项（不执行第4任务）。
