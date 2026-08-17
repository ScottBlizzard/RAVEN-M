# GPT_PRO_OPEN_V2_LONG_HORIZON_COORDINATION_DESIGN_2026-08-15.md

## 文档状态

| 项目 | 冻结内容 |
|---|---|
| 仓库分支 | `a2-verified-progress-audit-20260810` |
| 当前设计资料提交 | `1854fd2b7a5b3ca488b45e27953186ba7c447f96` |
| 冻结科研证据边界 | `b5635939acd628156f8c8e36aa8219834a3e6ad8` |
| 研究问题 | 长程目标分解、阶段协调、要求保持与局部导航漂移 |
| 最终推荐系统 | **SYS-SCOPE-R2** |
| 全称 | **Sparse Checkpointed Objective–Phase Envelope** |
| 中文名称 | **稀疏检查点目标—阶段包络** |
| 对显式 planner 的裁决 | **修改，而不是原样保留或完全否定** |
| 当前实施授权 | **NO-GO-AUDIT：在R2全19题原始轨迹完成零生成、哈希绑定审计之前，不得实现或运行live generation** |
| 本轮范围 | 仅设计；不修改仓库、不运行GPU、不改写历史证据 |

设计提交 `1854fd2...` 已核对为当前设计文档提交；开放设计章程明确规定，planner只是问题假设，机制、角色、调用次数和状态结构必须由正式证据决定。冻结边界之后的设计文档不能改变此前A-series正式结果。

---

## 0. 最终裁决摘要

### 0.1 推荐结论

本设计**不推荐开局生成完整层次计划，也不推荐继承A7/A10/A11式的持续workflow、obligation、frontier或route状态机**。

最终冻结一条更窄的假设：

> **当且仅当R2轨迹已经消耗原生动作预算的一半而仍未终止时，调用一次独立阶段协调角色，把剩余目标压缩为“全局不变量、当前阶段、后续阶段、可见交接线索和阶段回退风险”，并仅在随后最多8次executor决策中作为可忽略建议注入；这可能减少长轨迹中的要求丢失和局部漂移，同时使短任务继续保持R2的reactive执行。**

该系统称为：

> **SYS-SCOPE-R2：Sparse Checkpointed Objective–Phase Envelope**

它的关键特征是：

1. **不做初始planning**；
2. **每个episode最多一次辅助调用**；
3. 只在 `executed_action_count = ceil(native_max_steps / 2)` 后的下一次决策前调用；
4. 输出不是动作序列，而是最多三个语义阶段；
5. 输出可以是 `PASS_THROUGH`，此时不向executor注入任何协调文本；
6. 有效包络最多影响随后8次executor调用，之后自动过期；
7. 不replan、不验证结果、不诊断失败、不覆盖动作、不阻止终止；
8. 当前截图和R2 executor始终保留最终行动权；
9. R2 compact verified/pending memory原样保留；
10. 使用同资源、无专业阶段结构的active control，以及同调用但不注入的role-shadow判断因果。

### 0.2 为什么不是完整Hierarchical Milestone Planner

完整开局planner会无差别干预所有任务，而R2六个成功任务中有三个在动作预算一半之前已经结束；另外三个即使跨过中点，也已接近成功终止。R2失败组的动作预算使用率中位数为100%，成功组则为49%，因此“到达预算中点仍未结束”比“episode一开始”更像一个跨任务的长程协调暴露点。该结论目前来自正式聚合数据，而不是原始轨迹语义标签。

### 0.3 当前为什么仍是NO-GO

Git中只有R2的episode ID、episode JSON哈希和聚合结果；完整逐步轨迹、截图树、请求响应和动作转移仍在本地原始run tree中。现有`A1R2_CVP_OFFLINE_REPLAY_REPORT.json`是把R2存储规则投影到旧A1轨迹上，并不是R2 live 19题轨迹：它的来源suite是旧A1的596 actions，甚至把`OsmAndMarker`记录为reward 0，而R2 live中该题成功。因此它不能用于统计R2的requirement loss、phase loss、route cycle或phase relapse。

所以当前结论分成两层：

- **架构选择：条件性GO。** 若原始轨迹审计证实跨任务、跨应用的中后程协调缺陷，SCOPE-R2是最值得实现的一条方案。
- **实现与live运行：NO-GO-AUDIT。** 在第4节的零生成审计完成并通过资格门之前，不得写production implementation，不得冻结live arm，不得发起任何模型调用。

---

# 1. Commit-pinned证据审计

## 1.1 证据等级

| 等级 | 本文如何使用 |
|---|---|
| 正式完整suite结果 | 可用于系统性能、聚合动作成本和成功/失败统计 |
| 正式gate结果 | 只能表示该arm在已运行任务上的结果，不能外推为0/19 |
| 正式offline qualification | 可以决定arm是否有资格进入live，但不能替代live reward |
| Post-hoc diagnostic | 只能说明激活、读取和行为迹象，不能修复正式arm状态 |
| 本文推断 | 必须明确标记为推断，不得写成正式轨迹事实 |
| 缺失证据 | 必须进入零生成补全计划，不能从组件名或task name脑补 |

开放设计章程与完整输出要求明确要求区分正式证据、诊断、推断和未知，并要求缺失原始证据通过零生成、哈希绑定审计补全。

## 1.2 正式系统结果

| 系统 | 正式范围 | Full success | Reward | Calls | Actions | Tokens | 结论 |
|---|---:|---:|---:|---:|---:|---:|---|
| A0 | 19题 | 4/19 | 4.5 | 329 | 316 | 1,273,361 | 冻结官方式base |
| A1 | 19题 | 5/19 | 5.5 | 603 | 596 | 3,464,267 | 一项paired gain，成本显著增加 |
| A1-R2 | 19题 | **6/19** | **6.5** | 603 | 595 | **2,685,730** | 当前最佳正向参考 |
| A2 | 19题 | 0/19 | 0 | 705 | — | 3,170,413 | compound verified-progress负结果 |
| A6 | 19题 | 0/19 | 0 | 628 | 625 | 2,674,422 | always-on action→transition memory完整负结果 |
| A7 | 透明拼接19题 | 4/19 | 4 | 不作pristine cost比较 | 不作pristine cost比较 | 不作pristine cost比较 | 可作透明机制对照，不能作干净prospective cost arm |

A1-R2相对A1是一胜、零负、十八平；它保留A1的五个成功并新增`OsmAndMarker`。其accuracy判据通过，严格cost判据因calls未低于A1而失败，memory causality由于缺少matched read-disabled ablation仍未建立。

## 1.3 A1-R2真正改变了什么

A1-R2并没有加入planner、verifier、guard、action override或额外模型调用。它保留模型原有的`MEMORY[observed; verified; pending]`输出契约，但在存储时：

- 删除`observed`；
- 只保留最新一份`verified + pending`；
- 把`MEMORY[...]`前缀从普通action history中去除，避免同一状态被history与memory block重复注入；
- 保持“当前截图权威”；
- 默认TTL为8次请求；
- 单次render上限为1100字符；
- 没有hidden UI、evaluator或强制终止。

正式R2结果记录了：

- 603次memory read调用；
- 436次非空读取；
- 205次成功写入；
- 130次same-state refresh；
- 389次无效prefix；
- 14次过期；
- 1次显式清空；
- 0次额外模型调用；
- 0次动作覆盖；
- 0次强制终止。

因此，R2是**一个成本仍高、因果尚未隔离，但已有系统级正向结果的reactive executor + compact ledger**。这正是本设计选择它作为父系统，而不选择任何失败arm的原因。

## 1.4 A6：为什么不能把更多action→transition记录直接当作解决方案

A6自动保存短期action→visible transition，并在几乎每步注入：

- 19/19有效；
- 0/19成功；
- 625次写入；
- 609次非空读取；
- A0四个成功任务0/4保持；
- 总token 2,674,422；
- elapsed 19,118.59秒。

它证明了action→transition信息可以机械地记录和读取，但没有证明这些记录改善决策。正式交接材料把其失败归因于记录与普通action history高度重复、低信息转移持续占用注意力。

**本设计只允许复用A6的可见转移记录作为offline audit feature和因果测量材料，不把它作为runtime prompt memory。**

## 1.5 A7：为什么不能直接升级为workflow phase controller

A7使用冻结规则从goal抽取条目，只表示`pending / attempted_visible_change / attempted_no_visible_change`，不声称完成。其最终透明拼接结果为4/19，但：

- 不是一次完整、pristine、同一source closure下的prospective成本比较；
- 部分成功发生在ledger不活跃时；
- parser覆盖不足，多个任务完全没有激活；
- 读取或写入不能等同于成功因果。

因此，A7只能支持一个很弱的结论：**goal item representation可以机械存在，但冻结文本解析不能被视为可靠的长程阶段系统。**

## 1.6 A10、A10-v2、A11：为什么复杂obligation/frontier/route状态不能继承

正式offline qualification结果为：

- A10：`status=fail`，失败项包括`a0_success_silence_gate_failed`与`a1_recipe_sentinel_or_trace_evidence_failed`；
- A10-v2：`status=fail`，失败项包括`a6_timing_or_kind_gate_failed`与`a9_exposure_or_pure_t3_gate_failed`；
- A11：`status=fail`，失败项包括A6 confirmed segment、A8-v2 Expense independent segment和A9 Retro independent segment相关门。

后续六题diagnostic并未修复这些状态：

- A10-v2：2/6，6次read，3个read-active失败episode，0个productive-divergence signal；两个成功均memory-silent；
- A11：2/6，4次read均位于失败episode，0个productive-divergence signal；两个成功均memory-silent；
- A12：1/6，3次read均位于失败episode，0个productive-divergence signal；唯一成功memory-silent。

由此得到的设计约束是：

1. 不继承A10/A11的obligation maturity、frontier score、route graph或multi-support confirmation；
2. 不把“状态机激活”当作长程协调改善；
3. 不把成功但组件silent的episode归因于组件；
4. 新系统必须让专业结构与generic extra reasoning直接对照；
5. 新状态必须足够小，使每个字段都能对应一个跨任务缺陷。

## 1.7 A1-R3至R12的正式含义

R3–R12不是十个0/19，而是十个独立的0/1 gate failure。它们形成依赖性很强的串行patch链：

- R3新生命周期没有激活；
- R4激活writer但形成陈旧状态；
- R5清除跨页陈旧状态，却丢失即时子义务；
- R6持续注入完整goal，仍不能修复错误点击与弱恢复；
- R7/R8的detector触发不足；
- R9触发三次恢复文本，却没有productive行为改变；
- R10/R11增加坐标与self-check文本，仍失败；
- R12减少4.37% token，但reward不变。

这条链最强的结论不是“所有记忆都无效”，而是**在一个已回归的父系统上继续增加状态、提醒和恢复文本，不会自动产生更好的决策，而且容易过拟合单一Expense轨迹**。

---

# 2. R2完整19题聚合审计

## 2.1 逐题正式聚合结果

“中点暴露”列是一个**反事实调度投影**：假定采用本设计的统一触发规则，在R2历史动作数下，该episode是否会在终止前达到`ceil(max_steps/2)`。它不是对未来Full轨迹的预测，也不是原始trace语义证据。

| 分组 | Task | Reward | Actions / Max | 终止 | Reads / Writes / Refresh | 预计到达中点 |
|---|---|---:|---:|---|---:|---|
| 成功 | ExpenseDeleteMultiple2 | 1 | 17 / 34 | 正确terminate | 17 / 10 / 5 | 是 |
| 成功 | RetroSavePlaylist | 1 | 24 / 50 | 正确terminate | 14 / 4 / 0 | 否 |
| 成功 | SimpleCalendarAddOneEvent | 1 | 22 / 34 | 正确terminate | 21 / 5 / 1 | 是 |
| 成功 | SportsTrackerTotalDurationForCategoryThisWeek | 1 | 6 / 16 | 正确answer | 5 / 4 / 1 | 否 |
| 成功 | RecipeDeleteMultipleRecipesWithConstraint | 1 | 17 / 40 | 正确terminate | 16 / 7 / 2 | 否 |
| 成功 | OsmAndMarker | 1 | 11 / 20 | 正确terminate | 11 / 6 / 2 | 是 |
| 失败 | BrowserMultiply | 0 | 22 / 22 | max steps | 19 / 12 / 5 | 是 |
| 失败 | ExpenseAddMultipleFromGallery | 0 | 13 / 60 | 错误terminate | 13 / 5 / 2 | 否 |
| 失败 | ExpenseAddMultipleFromMarkor | 0 | 60 / 60 | max steps | 21 / 9 / 6 | 是 |
| 失败 | MarkorCreateNoteAndSms | 0.5 | 18 / 18 | max steps | 14 / 5 / 1 | 是 |
| 失败 | MarkorMergeNotes | 0 | 78 / 78 | max steps | 73 / 34 / 27 | 是 |
| 失败 | MarkorTranscribeVideo | 0 | 14 / 20 | 错误answer | 11 / 7 / 5 | 是 |
| 失败 | OsmAndTrack | 0 | 120 / 120 | max steps | 119 / 71 / 67 | 是 |
| 失败 | RecipeAddMultipleRecipesFromImage | 0 | 60 / 60 | max steps | 8 / 2 / 1 | 是 |
| 失败 | RecipeAddMultipleRecipesFromMarkor | 0 | 28 / 60 | 错误terminate | 18 / 6 / 1 | 否 |
| 失败 | RecipeAddMultipleRecipesFromMarkor2 | 0 | 60 / 60 | max steps | 33 / 7 / 1 | 是 |
| 失败 | SaveCopyOfReceiptTaskEval | 0 | 10 / 16 | 错误terminate | 10 / 5 / 2 | 是 |
| 失败 | SportsTrackerActivitiesOnDate | 0 | 7 / 20 | 错误answer | 6 / 3 / 1 | 否 |
| 失败 | SportsTrackerTotalDistanceForCategoryOverInterval | 0 | 8 / 22 | 错误answer | 7 / 3 / 0 | 否 |

以上数据来自正式R2 scored-result JSON。

## 2.2 成功组与失败组的可确认统计

| 指标 | 6个成功任务 | 13个失败任务 | 谨慎解释 |
|---|---:|---:|---|
| 总executed actions | 97 | 498 | 失败组承担了大部分轨迹长度 |
| 平均actions | 16.17 | 38.31 | 失败轨迹平均更长 |
| 中位actions | 17 | 22 | 长度分布受数个极长失败影响 |
| 平均预算使用率 | 49.6% | 74.8% | 失败更容易持续消耗预算 |
| 中位预算使用率 | 49.0% | 100% | 7个失败用满预算 |
| max-step termination | 0/6 | 7/13 | 明确存在长时间未解决episode |
| 错误terminal/answer | 0/6 | 6/13 | 这是outcome-judgment信号，不自动属于planner问题 |
| 至少60个actions | 0/6 | 5/13 | 存在明显长程失败子集 |
| 非空reads | 84 | 352 | 更多读取没有自动变成成功 |
| 成功writes | 36 | 169 | 写入量同样不是能力证据 |
| same-state refresh | 11 | 119 | 失败组陈旧或重复状态更多 |
| refresh / writes | 30.6% | 70.4% | 只能作为停滞代理，不是phase-loss证明 |
| 按50%统一检查点预计暴露 | 3/6 | 9/13 | 固定中点比开局planner更偏向长失败episode |
| 按50%检查点预计保持silent | 3/6 | 4/13 | 可让一半成功任务完全不受planner文本影响 |

这些比例由正式逐题JSON聚合推导。它们支持“长失败与反复状态集中存在”，但仍不能直接证明模型发生了requirement loss或phase relapse。

`OsmAndTrack`与`MarkorMergeNotes`合计产生94次same-state refresh，占全部130次refresh的72.3%，但它们的198个actions只占全suite 595个actions的33.3%。这说明重复状态高度集中在少数长episode中，却也意味着不能把这些极端episode当成所有13个失败的共同机制。

## 2.3 当前能够与不能够量化的模式

| 模式 | 成功6题当前可确认 | 失败13题当前可确认 | 当前证据边界 |
|---|---:|---:|---|
| Requirement loss | 只能给出0–6的未知范围 | 只能给出0–13的未知范围 | 必须逐步查看goal clause、model summary与截图 |
| Phase loss | 0–6未知 | 0–13未知 | 聚合action数不能识别阶段切换 |
| 重复局部导航 | 精确值未知；0/6用满预算 | 精确值未知；7/13用满预算 | refresh与max-step只是代理 |
| 长时间停留错误子任务 | 精确值未知；0/6达到60 actions | 精确值未知；5/13达到60 actions | 长轨迹不等于错误phase |
| Premature termination | 0/6错误terminal | 6/13错误terminal或answer | 这是正式可确认的evaluator mismatch |
| 已完成阶段重新进入 | 0–6未知 | 0–13未知 | 需要可见handoff与后续回退标注 |
| 成功是否依赖reactive行为 | 3/6在预算中点前结束 | 不适用 | 只能视为planner-silence风险代理 |
| Planner潜在伤害 | 3/6会在中点前结束；另3题接近终止 | 4/13会在中点前失败 | 真实伤害必须由prospective gate测量 |

因此，当前不能诚实地写出诸如“R2有7个phase-loss失败”或“4个任务重复进入已完成阶段”这样的数字。任何此类精确统计在原始trace审计前都属于脑补。

## 2.4 关键反例

### 反例一：长失败不一定伴随大量R2 memory refresh

`RecipeAddMultipleRecipesFromImage`走满60 actions，但只有8次非空read、2次write和1次refresh。它反驳了“所有长失败都由陈旧pending反复注入导致”的简单解释。

### 反例二：same-state refresh不是失败充分条件

成功的`ExpenseDeleteMultiple2`也有5次same-state refresh。refresh可以与成功共存，因此它只能作为停滞候选信号，不能直接触发phase controller或recovery。

### 反例三：六个失败terminal更接近outcome judgment问题

`ExpenseAddMultipleFromGallery`、`RecipeAddMultipleRecipesFromMarkor`与`SaveCopyOfReceiptTaskEval`错误terminate；三个Sports/Markor任务错误answer。它们可能需要结果验证，而不是阶段规划。SCOPE-R2不得把这六题的所有问题都装进协调组件。

### 反例四：R2成功任务并不都需要显式阶段

`SportsTrackerTotalDurationForCategoryThisWeek`只用了6个actions；`RetroSavePlaylist`与`RecipeDeleteMultipleRecipesWithConstraint`也在中点前结束。对这些任务开局生成计划只会增加调用、延迟和prompt负担。

### 反例五：R2 offline replay不是R2 live trace

offline replay使用旧A1 suite并投影R2渲染规则，不能提供R2真实动作分叉、阶段回退或成功机制证据。尤其`OsmAndMarker`在该replay中为reward 0，而R2 live中为reward 1。

---

# 3. 研究问题的证据化重述

本研究不应再问：

> “给agent加一个更复杂的planner会不会更强？”

而应问：

> **在保留R2当前截图驱动、逐步reactive action selection的前提下，一次稀疏、受限的阶段计算，是否能在真正变成长轨迹的episode中重新突出全局要求和阶段顺序，并使后续动作出现可见、可归因的进展？**

这个问题故意不覆盖：

- 已识别失败后的critic/recovery；
- 对单次动作结果或最终完成状态的独立验证；
- 坐标修正；
- action candidate arbitration；
- workflow donor retrieval；
- 结果终止guard。

这些属于其他问题族。开放设计章程也要求长程协调、失败恢复和结果判断保持独立，不因并行设计而自动组合。

---

# 4. 必须先完成的零生成、哈希绑定R2全19题审计

## 4.1 审计目标

在任何实现前，必须把R2本地19个正式episode materialize为一个只读审计包，并回答：

1. requirement carriage何时消失；
2. 轨迹何时离开尚未完成的phase；
3. 是否存在局部screen/action route复现；
4. 是否在错误子任务上持续消耗actions；
5. terminal claim是否发生在可见要求不足时；
6. 是否重新进入已完成或已交接phase；
7. 六个成功任务中哪些依靠短、单调、reactive路径；
8. 统一50%检查点是否在缺陷发生前、缺陷发生中或已经太晚；
9. 8-decision phase envelope是否有足够剩余runway产生作用；
10. 缺陷是否横跨至少两个task family，而不是只来自Expense或Osm。

## 4.2 哈希闭包

审计程序必须执行以下零生成步骤：

1. 从正式R2 scored-result读取19个`episode_id`与`episode_json_sha256`；
2. 从本地原始run tree逐一找到对应`episode.json`；
3. 对19个episode JSON做byte-level SHA-256验证；
4. 验证episode内引用的每一张before/after screenshot的SHA-256；
5. 验证task seed `20260806`、generation seed `3407`、suite ID、run signature与正式结果一致；
6. 原始图片不得重新编码后再计算hash；
7. 审计脚本的`generation_calls`必须硬编码并最终验证为0；
8. 审计环境不得加载vLLM client、不得访问推理端口；
9. 所有派生JSON、JSONL与Markdown报告都生成content SHA-256；
10. 任一episode、step、截图或响应缺失，则审计状态为`INCOMPLETE`，不得用其余数据估算缺失任务。

正式结果已经为19个episode记录了固定episode JSON哈希与source closure信息，可作为该审计的根。

## 4.3 标注信息边界

语义标注只允许使用：

- 原始goal；
- 当前及过去截图；
- executor原始响应；
- canonical executed action；
- ordinary committed history；
- R2 memory read/write记录；
- 可见pixel transition；
- action index与native action budget。

语义标注不得使用：

- hidden UI tree内容；
- activity/package；
- evaluator中间状态；
- 已知最终答案；
- 未来截图去解释当前决策；
- task-specific人工标准路线；
- donor trajectory；
- task name驱动的不同标注规则。

reward与最终success label应在所有过程标签冻结之后再join，用于计算成功/失败组 prevalence，避免审核者根据结果倒推缺陷。

## 4.4 操作化定义

| 模式 | 主定义 |
|---|---|
| Requirement loss | 某个由goal直接产生、仍无可见解决证据的要求，先前曾在executor summary、R2 pending或行为中被明确携带，随后连续至少4个executed actions完全不再被携带，且动作开始服务于与该要求无关或冲突的局部目标 |
| Phase loss | agent已进入一个目标一致phase，却在没有可见handoff cue的情况下离开，并连续至少3个actions服务于另一phase |
| Repeated local navigation | 同一可见状态簇与action-family转移形成至少两次A→B→A或A→B→A→B复现，期间没有新增goal-relevant visible fact |
| Wrong-subtask dwell | 在存在未完成前置要求时，连续至少4个actions投入到非当前phase、非必要导航或已满足子任务 |
| Premature termination | executor给出terminal/answer，episode最终reward不足；同时单独标注终止前截图是否具备支持该claim的可见证据 |
| Completed-phase reentry | 已观察到phase handoff，且至少一个动作进入后续phase后，agent又用至少2个actions返回旧phase，当前截图没有提供必须回退的可见理由 |
| Reactive success | 成功轨迹在中点前终止，或在中点后两次decision内完成，并且没有requirement/phase loss标签 |
| Planner-interference risk | 统一中点处，R2接下来1–2次决策已经直接推进一个可见要求或正确终止，且没有活跃协调缺陷 |

这些标签是**可观察轨迹代理**，不应被解释为对模型内部记忆状态的直接读取。

## 4.5 标注与一致性

- 使用两个独立审核者；
- episode以匿名ID呈现，隐藏reward与最终success；
- 两名审核者先独立标注；
- binary label主报告要求Cohen’s κ至少0.70；
- first-onset step偏差大于2 actions时必须仲裁；
- 仲裁完成后冻结标注hash，再加入reward；
- 同时报告episode prevalence、事件次数、受影响action比例与first-onset normalized budget；
- 不只报告事件总数，避免极长`OsmAndTrack`支配全suite。

## 4.6 SCOPE-R2的审计资格门

只有同时满足以下条件，SCOPE-R2才可进入实现：

1. 19/19 episode JSON和全部引用截图完成哈希验证；
2. 至少90%的有效executed steps完成一致标注，其余明确列为不可判定；
3. 至少**3/13**个失败任务出现requirement loss、phase loss、phase reentry或repeated local navigation中的至少一项；
4. 这至少3题必须分布于至少两个task family，且任何单一family不得占全部positive cases的一半以上；
5. 对应缺陷在至少2题中于预算中点前或中点附近出现，并在中点后仍有至少8次原生decision的理论runway；
6. 同一复合协调缺陷在成功组中至多出现于1/6；
7. 若主要问题集中为错误terminal、动作结果不确认或单次坐标错误，而不是协调缺陷，则SCOPE-R2判定为`NO-GO_WRONG_TRACK`；
8. 不得在看到审计结果后放宽“3题、2个family、中点、8次TTL”等同一identity下的资格条件。

当前原始trace尚未在Git证据包中，因此本设计的即时状态是：

> **NO-GO-AUDIT**

---

# 5. 候选架构比较

| 候选 | 核心机制 | 可能优势 | 主要问题 | 裁决 |
|---|---|---|---|---|
| 开局完整Hierarchical Milestone Planner | episode开始生成完整phase tree | 可以最早保存全部要求 | 无差别干预短任务；计划可能基于初始空白screen；易锁定错误phase；额外调用覆盖6个成功任务 | 拒绝原样采用 |
| Always-on workflow/phase FSM | 持续更新phase、obligation、frontier、route | 状态显式、可审计 | A7覆盖窄；A10/A11 formal replay失败；状态字段多、prompt持续占用；容易重现失败arm | 拒绝 |
| Deterministic goal parser + scheduler | 零额外调用，按goal文本拆项 | 成本低 | A7说明冻结parser容易silent；无法根据当前可见进度决定phase；人工规则风险高 | 拒绝 |
| Recurrence-triggered adaptive replanner | 检测循环后重规划 | 触发稀疏、面向困难轨迹 | 触发器本身成为主要变量；R9已显示检测+恢复文本可能行为惰性；更接近失败恢复Track A | 延后至recovery研究 |
| Option-like skill library | 把任务组织成可复用技能 | 潜在降低长程搜索 | 需要模板、donor或task-family先验；泄漏与方向不匹配风险高；A4证据不足 | 拒绝当前实现 |
| Executor每步自报phase | 在原action response中增加phase字段 | 不增加模型调用 | R3–R5表明模型每步额外语法脆弱；会改变所有executor outputs | 拒绝 |
| **SCOPE-R2** | 到预算中点仍未结束时，一次生成短期剩余phase envelope | 保护短任务；专业结构与extra reasoning可直接对照；状态小；无动作覆盖 | 可能触发过晚；一次计划可能陈旧；辅助调用带来延迟 | **最终推荐** |

## 5.1 为什么SCOPE最值得先实现

SCOPE-R2不是理论上最强的planner，而是当前证据下**最小、最可证伪、最能保护R2六个成功、最容易做因果对照**的协调组件：

- 它不把A6/A7/A10/A11的失败状态机打包继承；
- 不要求executor每步满足新语法；
- 不把所有失败都解释为planning failure；
- 不需要从task name或app family选择模板；
- 不在开局打断短任务；
- 只增加一个行为相关组件；
- generic active control可以保持同调用、同输入、同长度预算，只移除phase结构；
- role-shadow可以分离辅助调用延迟与文本影响；
- 如果无收益，可以明确否定“中点一次专业phase envelope”这条假设，而不是得到一个难以解释的复合负结果。

---

# 6. 对初步planner假设的明确裁决

## 裁决：**修改**

保留的部分：

- 需要一个独立于executor的专业长程协调计算；
- 输出应把全局goal组织成少量阶段；
- 阶段必须有当前截图可理解的交接线索；
- 阶段文本应影响executor，而不是只写入日志。

删除的部分：

- 不在episode开始规划；
- 不生成完整动作路线；
- 不维护phase completion truth；
- 不维护obligation maturity、frontier score或route graph；
- 不持续replan；
- 不根据detected failure触发；
- 不选择、阻止或覆盖executor动作；
- 不替executor判断最终完成；
- 不在每步注入长期状态。

因此，SCOPE-R2更准确地说是：

> **一个延迟、稀疏、短期有效的phase advisory controller，而不是完整planner-executor hierarchy。**

---

# 7. 最终推荐系统

## 7.1 系统名称

**SYS-SCOPE-R2**

**Sparse Checkpointed Objective–Phase Envelope**

## 7.2 一句话假设

> 在R2 episode消耗到原生动作预算的一半仍未结束时，一次可见证据约束的剩余阶段计算，能比无结构的等资源额外推理更有效地恢复全局要求与阶段顺序，并在最多8次后续决策内减少局部漂移，同时不破坏中点前的reactive行为。

## 7.3 真正被测试的单一新组件

唯一新增的行为组件是：

> **Mid-horizon Phase Coordinator**

它只做一件事：

> 根据原始goal、当前截图、最近可见执行历史和当前R2 ledger，生成一个短期、不可强制、不可验证完成状态的“剩余阶段包络”。

以下内容**不是**本实验的一部分：

- 失败critic；
- action-outcome verifier；
- terminal verifier；
- action candidates；
- action judge；
- recovery route；
- donor retrieval；
- phase completion classifier；
- budget termination guard；
- coordinate calibration。

---

# 8. 父系统、复用原语与新增内容

## 8.1 父系统

父系统必须是正式R2 source closure对应的：

- `a1r2_compact_verified_pending_v1`；
- 同一Qwen3-VL-32B model revision；
- task seed `20260806`；
- generation seed `3407`；
- 同一sampling；
- 同一AndroidWorld instances；
- 同一native action limits；
- 同一official executor system prompt；
- 同一action parser与Android adapter；
- 同一R2 memory TTL、renderer与write/read规则。

R2正式结果记录的implementation commit为`ad7a39b55926408aa4a3c7101c9ff5cd83af4d80`，新系统应把这一source closure作为父证据，而不是从当前分支上任意复制一份“看起来相同”的代码。

## 8.2 从失败arm复用什么

### Runtime行为路径

**不复用任何失败arm的runtime状态或prompt。**

### Offline audit路径

允许复用：

- controller已有的action→visible pixel transition；
- A12 diagnostic所使用的divergence/progress/relapse审计思想；
- screenshot/action-family归一化工具。

这些只用于测量，不进入executor prompt，不决定是否规划，不产生task completion claim。组件证据账本明确把action→visible transition和post-intervention divergence审计列为可复用audit primitive，而不是已证明的决策机制。

## 8.3 真正新增内容

1. 一个独立Phase Coordinator模型角色；
2. 一个统一50% normalized-budget checkpoint；
3. 一个不可变、最多8次decision有效的`PhaseEnvelope`；
4. 一个与Full同资源、无phase结构的Generic Reasoning Advisor；
5. 一个同调用但不注入文本的SCOPE-Shadow；
6. 对辅助调用与注入影响的分角色成本及因果审计。

---

# 9. 端到端工作流

## 9.1 总体流程

```text
Episode开始
    |
    v
完全按R2执行
- 当前截图
- 普通action history
- R2 compact verified/pending
- 由R2 executor选择并执行动作
    |
    | executed_action_count < ceil(max_steps / 2)
    |------------------------------------------> 继续完全按R2执行
    |
    | 首次达到统一中点，episode仍active
    v
冻结当前截图，不重新观察环境
    |
    v
Phase Coordinator最多调用一次
    |
    +--> MODE=PASS_THROUGH / 输出无效
    |        |
    |        v
    |    不注入任何phase文本，继续R2
    |
    +--> MODE=ACTIVE
             |
             v
       生成不可变PhaseEnvelope
             |
             v
       当前及随后最多8次executor决策
       将包络作为可忽略advisory block注入
             |
             v
       TTL耗尽或episode终止
             |
             v
       清除包络，恢复纯R2
```

## 9.2 中点前

中点前必须与R2保持行为等价：

- 没有planner call；
- 没有planner prompt；
- 没有phase state；
- 没有额外截图；
- 没有不同history；
- 没有额外action syntax；
- 没有不同termination policy。

因此，如果Full在中点前已经与prospective R2 Base发生行为差异，该差异不能归因于SCOPE，只能归因于随机性、环境漂移或基础设施差异。

## 9.3 中点调用

触发条件冻结为：

```text
episode_active
AND phase_call_count == 0
AND executed_action_count >= ceil(native_max_steps / 2)
```

调用发生在下一次executor generation之前。

触发器只能读取：

- 当前executed action count；
- 当前task的原生max steps；
- 是否已经调用；
- episode是否仍active。

它不能读取：

- task name；
- app；
- package/activity；
- reward；
- evaluator；
- screen hash模式；
- 已知轨迹；
- “当前是否失败”的语义判断。

## 9.4 Coordinator输入

辅助角色可见：

1. 原始goal；
2. 与该次executor相同的当前截图；
3. 当前`executed_action_count / native_max_steps`；
4. 当前R2 rendered `VERIFIED / PENDING`，若存在；
5. 最近最多8条committed action summaries；
6. 固定角色prompt。

辅助角色不可见：

- task name；
- task params；
- hidden UI tree；
- foreground activity/package；
- evaluator/reward；
- future screenshot；
- 旧成功轨迹；
- app-specific模板；
- executor即将提出的动作；
- 已知最终答案。

## 9.5 Coordinator输出

输出只能是：

- `PASS_THROUGH`；或
- 一个包含2–3个语义phase的`ACTIVE`包络。

它不得输出：

- canonical Android action；
- tap coordinate；
- swipe direction；
- text输入内容；
- action candidates；
- “任务已完成”；
- “上一步成功/失败”的最终判断；
- recovery route；
- terminal建议。

## 9.6 Executor阶段

若包络有效：

- 将同一份不可变包络最多注入8次；
- executor仍按official action protocol只输出一个动作或terminal；
- controller不解析executor是否“遵循phase”；
- controller不根据phase阻止动作；
- executor可以忽略不一致或过时的包络；
- 当前截图继续是最高优先级证据。

## 9.7 Episode结束后

episode结束后才允许：

- evaluator打分；
- 将reward与phase audit join；
- 计算productive intervention；
- 计算phase relapse；
- 判断成功是否component-silent；
- 计算分角色成本。

---

# 10. 角色权限

| 能力或信息 | Phase Coordinator | R2 Executor | Controller | Evaluator |
|---|---:|---:|---:|---:|
| 当前截图 | 是 | 是 | 是 | 依AndroidWorld |
| 原始goal | 是 | 是 | 是 | 是 |
| 最近action summaries | 是，最多8条 | 是，按R2历史策略 | 是 | 否 |
| R2 ledger | 是，标记为self-authored uncertain state | 是 | 是 | 否 |
| hidden UI tree | 否 | 否 | 仅audit记录，不得用于决策 | 可按环境实现 |
| activity/package | 否 | 否 | 仅audit记录，不得用于决策 | — |
| reward/evaluator state | 否 | 否 | episode结束前否 | 是 |
| 生成Android动作 | 否 | 是 | 否 | 否 |
| 覆盖或阻止动作 | 否 | 否 | 否 | 否 |
| 判断任务完成 | 否 | 只能按原协议提出terminal | 否 | 是 |
| 触发recovery | 否 | 可按自身reactive policy行动 | 否 | 否 |
| Replan | 否，v1只有一次调用 | 不适用 | 否 | 否 |
| 增加native steps | 否 | 否 | 否 | 否 |

当前controller已经把UI tree、activity和package保存为audit数据，同时明确标记这些字段对模型不可见；新sidecar必须沿用这一隔离，而不能因为controller内已有字段就把它们传给Coordinator。

---

# 11. PhaseEnvelope主要结构与生命周期

## 11.1 核心字段

`PhaseEnvelope`只需要下列概念字段：

| 字段 | 含义 |
|---|---|
| `mode` | `PASS_THROUGH`或`ACTIVE` |
| `global_invariants` | 最多2条必须持续保持的goal约束 |
| `phase_now` | 当前应优先服务的语义阶段 |
| `phase_next` | 完成当前可见handoff后应进入的下一阶段 |
| `phase_later` | 可选的第三阶段，不允许超过一个 |
| `visible_handoff_cue` | 何种当前可见事实提示可以转向下一phase；不是完成oracle |
| `relapse_guard` | 最容易被局部导航挤掉的全局要求或旧phase回退风险 |
| `source_step` | 生成包络时的executed action count |
| `remaining_injections` | 初始为8，每次真实executor prompt注入后减一 |
| `source_hashes` | goal、截图、history、R2 ledger、prompt、response与render hash |
| `validation_status` | parse、长度、禁用字段与注入commit状态 |

不建立以下字段：

- `completed=true/false`；
- phase confidence score；
- obligation maturity；
- route score；
- branch credit；
- frontier；
- action outcome truth；
- final success probability；
- per-app状态。

## 11.2 生命周期

```text
ABSENT
  |
  | 到达统一中点
  v
CALL_PENDING
  |
  +---- output=PASS / invalid ----> SILENT ----> ABSENT
  |
  +---- valid ACTIVE -------------> ACTIVE
                                      |
                                      | 每次真实注入 remaining_injections -= 1
                                      |
                                      +--> episode结束 --> CLEARED
                                      |
                                      +--> TTL=0 -------> EXPIRED --> CLEARED
```

## 11.3 为什么状态不可变

不在episode中更新phase状态，是有意的科学限制：

1. 动态更新会额外引入phase classifier或verifier；
2. update trigger本身会成为第二个待验证组件；
3. 多次replan会混合“专业结构”与“更多推理次数”；
4. A10/A11已表明复杂状态成熟与route更新不自动改善行为；
5. v1首先只测试一次phase computation是否足以改变后续决策。

若一次、短期phase envelope取得正向结果，后续才有理由注册单独的adaptive replanning factorial，而不能在本arm中临时增加。

---

# 12. 推荐完整Prompt模板

## 12.1 Phase Coordinator system prompt

```text
You are the SCOPE Phase Coordinator for a mobile-use agent.

You are NOT the mobile executor. You must not choose, propose, rank, block,
or rewrite Android UI actions. You must not judge final task success, verify
that an operation succeeded, diagnose a failure, or recommend a recovery route.

You may use only:
1. the original user goal;
2. the single current screenshot;
3. the current executed-action count and native action budget;
4. the executor's recent committed action summaries;
5. the executor's current self-authored VERIFIED/PENDING ledger, if present.

The screenshot is authoritative. The ledger and action summaries may be stale
or mistaken. Never infer hidden UI state, package/activity, evaluator state,
reward, future frames, a known task template, or a known successful trajectory.

At this single mid-horizon checkpoint, decide whether the remaining work
benefits from a compact semantic phase envelope.

Return PASS_THROUGH when:
- the remaining task appears to be one direct reactive operation;
- the current screenshot already directly affords an answer or terminal choice;
- a phase decomposition would be speculative;
- you cannot ground the phases in the goal and current visible evidence.

If a phase envelope is useful:
- preserve exact goal names, values, quantities, dates, and constraints;
- produce only 2 or 3 semantic phases;
- describe objectives, not taps, coordinates, swipes, text-entry commands,
  app-specific routes, or action sequences;
- give a prospective visible handoff cue, not a completion verdict;
- identify one likely phase-relapse risk;
- never state that the task or an operation is complete.

Output exactly one of the following forms.

MODE: PASS_THROUGH
REASON: <brief reason; not shown to the executor>

or

MODE: ACTIVE
INVARIANTS: <at most two compact goal constraints>
NOW: <current semantic phase objective>
NEXT: <next semantic phase objective>
LATER: <optional third phase, or NONE>
HANDOFF_CUE: <visible evidence that would justify moving from NOW to NEXT>
RELAPSE_GUARD: <one requirement or earlier-phase distraction not to lose>
```

## 12.2 Coordinator user prompt

```text
ORIGINAL GOAL:
{goal}

CHECKPOINT:
executed_actions={executed_action_count}
native_max_steps={native_max_steps}

CURRENT SELF-AUTHORED R2 LEDGER:
{r2_ledger_or_none}

RECENT COMMITTED ACTION SUMMARIES, OLDEST TO NEWEST:
{up_to_8_recent_summaries}

Use the attached current screenshot as the only visual observation.
Produce the required SCOPE response.
```

## 12.3 注入给executor的phase block

仅在`MODE: ACTIVE`且validation通过时注入：

```text
ADVISORY SCOPE PHASE ENVELOPE
This is not an action, recovery instruction, or completion judgment.

GLOBAL INVARIANTS:
{invariants}

CURRENT PHASE:
{phase_now}

AFTER A VISIBLE HANDOFF:
{phase_next}

LATER:
{phase_later_or_none}

VISIBLE HANDOFF CUE:
{visible_handoff_cue}

PHASE-RELAPSE RISK:
{relapse_guard}

The current screenshot is authoritative. Choose the next UI action yourself.
Ignore any line above that conflicts with what is currently visible.
```

该block：

- 最大700字符；
- 不写入ordinary history；
- 不复制到R2 ledger；
- 不要求executor输出phase ID；
- 不改变official action schema；
- 最多注入8次。

## 12.4 Resource-matched Generic Reasoning Advisor prompt

Generic control使用相同截图、goal、R2 ledger、最近8条history、调用位置、模型、最大tokens与时间上限，但禁止有序phase结构。

```text
You are a generic context advisor for a mobile-use agent.

You are NOT the executor. Do not propose UI actions, coordinates, routes,
completion judgments, failure diagnoses, or recovery instructions.

Using only the original goal, the current screenshot, the recent committed
action summaries, and the self-authored R2 ledger, produce a compact,
UNORDERED continuation note.

Do not divide the task into phases. Do not use current/next/later ordering.
Do not define milestone handoff conditions or phase-relapse rules.

Return exactly:

MODE: PASS_THROUGH
REASON: <brief reason; not shown to the executor>

or

MODE: ACTIVE
GOAL_FACTS: <compact exact goal facts>
VISIBLE_CONTEXT: <compact current visible context>
RECENT_CONTEXT: <compact recent-history fact>
GENERAL_CONSIDERATION: <one non-action general consideration>
CAUTION: <one general caution>
```

该control与Full具有同样的五行信息容量、700字符render上限和8次TTL，但没有：

- phase ordering；
- 当前/下一阶段；
- handoff cue；
- relapse guard。

因此它直接回答“收益来自专业phase结构，还是仅仅多了一次视觉推理”。

---

# 13. Planning、Replanning、失效与预算

## 13.1 Initial planning

**禁止。**

episode开始时完全按R2执行，避免：

- 在缺少任务上下文时过度规划；
- 对短任务增加延迟；
- 将错误开局计划持续注入；
- 破坏R2已有reactive能力。

## 13.2 Planning trigger

统一触发点：

\[
s_{\text{plan}}=\left\lceil \frac{B_{\text{native}}}{2} \right\rceil
\]

其中：

- \(B_{\text{native}}\) 是该task原生max-step budget；
- trigger只看实际executed action count；
- 不因task name、app或历史结果改变；
- 不改变原生action budget。

选择50%的依据是当前正式聚合数据中成功组预算使用率中位数为49%，失败组为100%；按历史R2轨迹，它会覆盖3/6成功与9/13失败，而不是像开局planner那样覆盖19/19。这个阈值仍必须接受第4节原始trace审计的资格检验。

## 13.3 Replanning

**SCOPE-R2 v1不允许replan。**

理由：

- 保持单一组件；
- 防止把Track A recovery混入；
- 避免多次推理本身成为收益来源；
- 减少对成功任务的prompt占用；
- 使Full与generic control可严格匹配。

## 13.4 调用预算

| 项目 | 上限 |
|---|---:|
| Auxiliary calls / episode | 1 |
| Auxiliary completion tokens | 256 |
| Auxiliary total input + output tokens | 8,192 |
| Auxiliary wall timeout | 60秒 |
| Auxiliary retries | 0 |
| Coordinator current screenshots | 1，与同次executor共用 |
| Recent action summaries | 最多8条 |
| Rendered envelope | 最多700字符 |
| Envelope TTL | 最多8次真实executor prompt注入 |
| Native action budget增加 | 0 |

若输入超过预算，必须按以下顺序确定性截断：

1. 保留完整system prompt；
2. 保留完整goal；
3. 保留当前截图；
4. 保留当前R2 ledger；
5. 从最旧recent summary开始删除；
6. 不用额外模型总结历史；
7. 若仍超限，则辅助调用fail closed，不得删goal或换更低分辨率未来截图。

## 13.5 失效规则

以下情况直接`PASS_THROUGH`，不重试：

- 输出无法解析；
- 超过字段或字符上限；
- 输出包含canonical action、坐标或action sequence；
- 输出声明任务或某操作已完成；
- 输出引用hidden UI、package、reward或已知路线；
- 不是2–3个phase；
- 输入token预算无法满足；
- render超过700字符。

## 13.6 语义冲突处理

controller不尝试自动判断包络是否语义过时，因为这会引入一个隐式verifier。

处理原则是：

1. 当前截图在executor prompt中明确高于包络；
2. executor可以忽略包络；
3. 包络8次后自动过期；
4. 不因冲突触发replan；
5. 冲突及其后果在offline causal audit中标注。

---

# 14. 如何保证当前截图与executor保留最终行动权

当前controller的正式链路是：

1. 获取当前state和截图；
2. 构建goal + history；
3. 读取并附加memory；
4. 调用executor；
5. 解析一个action或terminal；
6. 执行动作；
7. 观察after state；
8. episode结束后才调用evaluator。

SCOPE集成必须满足：

- Coordinator与executor使用同一张已捕获的current screenshot；
- Coordinator调用后不得重新`env.get_state`并把新截图传给executor；
- Coordinator输出只是user prompt中的advisory text；
- `protocol.py`中的official executor system prompt保持不变；
- `parse_official_response`保持不变；
- action adapter保持不变；
- controller不解析phase去修改canonical action；
- Coordinator不能提交terminal；
- Coordinator不能阻止executor terminal；
- evaluator继续只在episode结束后可见；
- phase block结尾明确写出“current screenshot authoritative”和“choose the next UI action yourself”。

这使SCOPE对动作的影响只能通过正常语言条件化发生，而不能通过controller override发生。

---

# 15. 仓库集成方向与实现风险

## 15.1 主要模块方向

### 保持byte-for-byte不变的核心

- `official_qwen_mobile/protocol.py`中的official executor协议；
- `a1r2_compact_verified_pending.py`；
- R2配置；
- Android action adapter；
- evaluator；
- native max steps；
- task order与seed。

### 新增或最小修改方向

| 模块方向 | 责任 |
|---|---|
| `scope_phase_envelope.py` | checkpoint、prompt、parse、validate、TTL、render与audit state |
| 新的SCOPE contract/preflight | source closure、prompt hash、call cap、leakage检查 |
| `controller.py`最小sidecar hook | 在R2 prompt构建前检查checkpoint，调用auxiliary并附加advisory block |
| runner/config | 选择Base、Full、Generic或Shadow arm |
| offline audit脚本 | 19题trace哈希验证、trigger replay、annotation export |
| result finalizer | executor/auxiliary分角色成本与causal chain统计 |

## 15.2 推荐接口

概念接口应类似：

```text
coordination_advisor.maybe_prepare(
    goal,
    current_screenshot,
    executed_action_count,
    native_max_steps,
    recent_committed_history,
    rendered_r2_ledger
) -> PhaseEnvelope | None
```

以及：

```text
coordination_advisor.render_for_executor() -> text
coordination_advisor.commit_injection(prompt_hash)
coordination_advisor.observe_executor_decision(...)
coordination_advisor.expire_or_clear(...)
coordination_advisor.audit_record()
```

`observe_executor_decision`只能做审计和TTL递减，不能改变phase内容或动作。

## 15.3 关键实现风险

### 风险一：辅助调用造成UI时间漂移

辅助调用期间真实Android界面可能随时间变化，但executor仍看到调用前截图。Shadow arm必须保留同样调用和延迟，以区分“planner文本影响”与“额外等待影响”。

### 风险二：与R2 memory重复表达

SCOPE不得重复完整R2 `VERIFIED / PENDING`。Coordinator可以读取ledger，但render只保留global invariants和phase结构。

### 风险三：输出偷偷变成action instruction

prompt与validator都必须禁止坐标、tap/swipe/type命令、路线步骤和terminal建议。

### 风险四：PhaseEnvelope变成completion verifier

`HANDOFF_CUE`只能是prospective visible cue，不能写“已完成”“已保存”“已删除”。runtime不维护completed phase状态。

### 风险五：在controller中误用audit side channels

当前controller拥有UI tree、activity和package审计字段。辅助input必须采用allowlist构建，而不是把完整step record传入Coordinator。

### 风险六：模型输出schema失败

与R3不同，该schema只影响一次auxiliary call；parse失败会silent fallback到R2，不会使executor action protocol失败，也不允许retry。

---

# 16. Base、Full、Active Control与Ablation

## 16.1 四个prospective arm

| Arm | Auxiliary call | 注入executor | 专业phase结构 | 作用 |
|---|---:|---:|---:|---|
| **R2-BASE-PROSPECTIVE** | 0 | 仅R2 memory | 否 | 回答没有新协调组件时会怎样 |
| **SCOPE-FULL** | 中点最多1次 | 最多8次 | 是 | 测试最终推荐机制 |
| **GENERIC-ACTIVE-CONTROL** | 与Full相同 | 最多8次 | 否 | 测试相同额外推理资源但无phase结构 |
| **SCOPE-SHADOW** | 与Full完全相同 | 否 | 生成但不影响executor | 测试调用延迟、环境时间和随机性 |

Generic control同时是最重要的mechanism ablation：它保持调用位置、视觉输入、goal、history、R2 ledger、模型、token上限、输出行数、render容量与TTL，只移除：

- 当前/下一phase；
- 时间顺序；
- visible handoff；
- relapse guard。

## 16.2 为什么还需要prospective R2 Base

历史R2是正式性能参考，但不能自动代表新实验当天的服务状态、环境稳定性与随机性。Prospective Base：

- 使用独立实验ID；
- 不覆盖历史R2；
- 仍从六题门开始；
- 有效科学失败不重跑；
- 结果只作为同期no-component control；
- 无论其结果如何，都不能改写历史R2的6/19。

## 16.3 Arm间可比性

Full与Generic之间：

- 同一auxiliary trigger；
- 同一最大调用数；
- 同一current screenshot政策；
- 同一input token cap；
- 同一completion cap；
- 同一TTL；
- 同一render长度；
- 同一model revision与sampling。

Full与Shadow之间：

- 同一个SCOPE prompt；
- 同一个SCOPE output；
- 同一个辅助调用延迟；
- 唯一区别是是否将output加入executor prompt。

Base与Shadow之间：

- 可估计额外辅助调用和延迟本身是否改变环境或轨迹。

---

# 17. Offline replay、preflight与泄漏检查

## 17.1 Zero-generation trigger replay

使用哈希验证后的R2真实episode replay controller逻辑，但不发起任何模型调用：

1. 对19题逐步回放executed action count；
2. 验证中点trigger每题最多一次；
3. 验证中点前最终executor prompt与R2 byte-equivalent；
4. 验证trigger不读取task name、package、reward或screen hash；
5. 使用固定mock `PASS_THROUGH`与最大长度`ACTIVE`输出测试parse；
6. 验证TTL严格为8；
7. 验证episode终止清空；
8. 验证Shadow最终executor prompt不包含phase文本；
9. 验证Generic不含phase-order字段；
10. 验证任何invalid output都不重试并继续R2；
11. 报告历史R2轨迹下预计trigger episode数和step分布；
12. `generation_calls`必须为0。

## 17.2 行为等价preflight

必须证明：

- Full在trigger前与Base prompt hash一致；
- Full的R2 memory read/write行为未被修改；
- Full不改变history policy；
- Full不增加native action；
- Full不修改terminal parser；
- Full不重新观察future frame；
- Full不把phase block写入ordinary history；
- Full不把phase block写回R2 memory；
- Full不允许Coordinator输出动作；
- Full auxiliary transport failure与科学输出失败有不同状态码。

## 17.3 泄漏静态扫描

行为source closure中必须扫描并禁止：

- `task.name`；
- app whitelist；
- package/activity读取；
- evaluator/reward；
- known final answer；
- known success task list用于runtime；
- screenshot hash条件分支；
- episode ID条件分支；
- task-specific thresholds；
- donor trajectory；
- hidden UI/accessibility；
- future screenshot；
- known action sequence。

六题success list只可存在于实验gate和结果分析代码中，不得进入runtime Coordinator或executor分支。

## 17.4 Runtime taint test

为所有禁止字段注入可识别哨兵值，验证：

- auxiliary request payload中不存在哨兵；
- final executor prompt中不存在哨兵；
- phase outputvalidator不能访问这些字段；
- trigger结果在替换task name、package与reward哨兵后不变；
- trigger结果只随action count、max steps和是否已调用变化。

## 17.5 Prompt与source freeze

首次generation前必须提交并哈希绑定：

- Full Coordinator system/user prompt；
- Generic prompt；
- executor render模板；
- exact parser；
- exact field长度；
- checkpoint off-by-one规则；
- TTL规则；
- task order；
- arm order；
- model revision；
- sampling；
- source files；
- config；
- offline replay；
- zero-generation preflight；
- leakage scan；
- live server receipt。

任何行为相关内容变化均产生新identity，并从六题第一题重新开始。

---

# 18. 六题保持门、后13题释放与停止规则

## 18.1 固定六题顺序

1. `ExpenseDeleteMultiple2`
2. `RetroSavePlaylist`
3. `SimpleCalendarAddOneEvent`
4. `SportsTrackerTotalDurationForCategoryThisWeek`
5. `RecipeDeleteMultipleRecipesWithConstraint`
6. `OsmAndMarker`

该顺序来自R2六个正式成功任务，Full必须6/6才可释放剩余13题。

## 18.2 Gate执行原则

按task-major方式运行四个arm。arm顺序应在preregistration中用固定四阶轮换冻结，避免某个arm总是在同一天或同一服务状态下先运行。例如：

| Task ordinal mod 4 | Arm order |
|---:|---|
| 0 | Full → Generic → Shadow → Base |
| 1 | Generic → Shadow → Base → Full |
| 2 | Shadow → Base → Full → Generic |
| 3 | Base → Full → Generic → Shadow |

该轮换只用于实验调度，不进入runtime行为。

## 18.3 Full停止门

若SCOPE-FULL在六题中任一题出现有效科学失败：

- Full立即终止；
- 不再运行剩余门题；
- 不释放后13题；
- 不修改prompt、TTL或threshold后重跑；
- 该版本记为正式gate failure；
- 已完成的Generic、Shadow和Base结果保留；
- 若要修改设计，必须建立新identity并从第一题重新开始。

## 18.4 组件silent不自动失败

若某个成功任务：

- 在中点前结束；
- Coordinator返回`PASS_THROUGH`；
- 输出invalid后fail closed；
- 或Shadow不注入；

该任务的成功计入system accuracy，但不计入component causality。

与早期Top-3草案不同，本设计**不要求在第一道Expense任务上强迫planner产生productive intervention**。因为SCOPE的核心保护机制就是允许简单或近终止任务保持silent。强迫第一题一定激活会把“保护reactive能力”与“组件必须表演”置于冲突中。

## 18.5 后13题顺序

Full达到6/6后，按正式suite中的固定顺序释放：

1. `BrowserMultiply`
2. `ExpenseAddMultipleFromGallery`
3. `ExpenseAddMultipleFromMarkor`
4. `MarkorCreateNoteAndSms`
5. `MarkorMergeNotes`
6. `MarkorTranscribeVideo`
7. `OsmAndTrack`
8. `RecipeAddMultipleRecipesFromImage`
9. `RecipeAddMultipleRecipesFromMarkor`
10. `RecipeAddMultipleRecipesFromMarkor2`
11. `SaveCopyOfReceiptTaskEval`
12. `SportsTrackerActivitiesOnDate`
13. `SportsTrackerTotalDistanceForCategoryOverInterval`

## 18.6 Infrastructure-invalid规则

允许同题replacement的情况仅包括：

- transport断开；
- ADB/UIAutomator错误；
- environment reset失败；
- screenshot文件损坏；
- lifecycle/evaluator基础设施异常；
- aux call明确的transport failure。

以下均属于科学失败，不得重跑：

- Coordinator输出`PASS_THROUGH`但任务失败；
- Coordinator输出格式错误；
- Full走满预算；
- executor action错误；
- executor错误terminate或answer；
- phase advice无效；
- phase advice导致回归；
- prompt遵循失败；
- 组件激活但无行为改变。

## 18.7 Resume规则

若实验在有效episode之间中断：

- 从下一个尚未运行的`task × arm`单元继续；
- 不重跑已完成episode；
- checkpoint必须记录完整source、prompt、model、server receipt和结果hash；
- 若任何行为source发生变化，不能resume，必须新建identity；
- infrastructure-invalid replacement与原attempt必须同时保留并链接。

---

# 19. Accuracy、Cost与Causality判据

## 19.1 Accuracy

SCOPE-FULL系统accuracy通过必须同时满足：

1. 六个R2成功任务6/6；
2. 完整suite至少7/19 full successes；
3. reward严格大于6.5；
4. 相对R2六题0 loss；
5. 所有19题结果均公开，包括失败和silent episode。

这些结果属于已观察task/seed上的matched prospective diagnostic，不得声称held-out generalization。

## 19.2 Cost

分别报告：

### Executor

- calls；
- prompt tokens；
- completion tokens；
- total tokens；
- GPU inference time；
- request latency；
- wall time；
- executed native actions。

### Phase Coordinator

- call count；
- input tokens；
- output tokens；
- image tokens；
- GPU inference time；
- request latency；
- timeout或transport failures；
- valid/invalid/PASS/ACTIVE数量。

### 合计

\[
C_{\text{total}}=C_{\text{executor}}+C_{\text{auxiliary}}
\]

还要报告：

- 注入phase字符与token；
- active episode数；
- 每个active episode的注入次数；
- 因SCOPE导致的executor call/action变化；
- 相对R2的success增量 / extra auxiliary call；
- 相对Generic的success增量 / extra specialized token。

由于SCOPE显式增加辅助调用，除非总executor成本显著下降，否则不得声称相对R2是cost improvement。允许出现：

- accuracy PASS；
- causality PASS；
- cost FAIL。

三个结论必须独立。

## 19.3 Component causality

专业phase结构的强因果判据：

1. Full六题无loss；
2. Full相对Generic至少多1个full success；
3. Full相对Shadow至少多1个full success，或在最终成功episode中展示Shadow没有的productive intervention；
4. 至少2个trace-grounded productive interventions；
5. 至少2个productive interventions分布在至少两个task family；
6. 成功不能全部发生在SCOPE silent episode；
7. Full与Generic若持平，则只能说额外推理可能有用，不能说phase结构有效；
8. Full与Shadow若持平，则不能排除随机性、延迟或无文本影响；
9. Full取得新成功但该episode未触发或返回PASS，则该成功不得归因于SCOPE。

## 19.4 Productive intervention定义

一次`productive intervention`必须同时具备：

1. checkpoint真实触发；
2. Coordinator调用成功；
3. `MODE=ACTIVE`；
4. exact output和render hash已记录；
5. exact phase block确实进入executor prompt；
6. phase内容对应goal中的一个真实要求；
7. 随后1–3个executed actions产生新的goal-relevant visible progress；
8. progress不能仅由任意pixel change定义；
9. 随后至少4个actions内没有phase relapse，若episode更早成功则到成功为止；
10. 行为与同checkpoint的Base、Generic或Shadow存在可解释分叉，或在无法精确配对时明确降低因果等级。

若Full与control在checkpoint前的截图、history和R2 ledger hash完全一致，可形成最强matched fork。若不一致，必须标注为非同状态比较。

## 19.5 Visible milestone progress

可见milestone progress定义为：

> 当前截图新增了一个与phase objective和goal clause直接对应的、可被独立审核者识别的事实，使下一phase在语义上合理。

不计为milestone progress：

- 任意页面切换；
- pixel变化；
- 点击动画；
- Coordinator声称“已完成”；
- R2 ledger自报verified；
- action summary声称成功；
- action数量减少。

## 19.6 Phase relapse

phase relapse是一个审计结果，而不是runtime trigger：

> 在出现可见handoff并进入下一phase后，agent又连续至少2个actions回到旧phase，且当前截图没有提供必要回退的可见理由。

报告：

- relapse episode数；
- relapse次数；
- first relapse step；
- relapse前后phase；
- relapse是否发生在包络TTL内；
- relapse是否导致最终失败。

---

# 20. R2六个成功任务逐题preservation与风险分析

## 20.1 ExpenseDeleteMultiple2

**R2聚合：**17/34 actions，正好达到50%阈值，下一次模型调用是正确terminal decision；17次read、10次write、5次refresh。

**主要风险：**

- SCOPE会在一个已经接近正确终止的状态触发；
- 任何错误phase都可能让模型继续操作而不是terminate；
- 过度强调“下一phase”可能重新进入已完成删除流程；
- 辅助调用延迟可能改变UI。

**保护策略：**

- Coordinator在当前截图直接支持终止或只剩单一操作时必须`PASS_THROUGH`；
- 不允许completion claim，也不允许要求重复删除；
- 这是固定gate第一题；
- 任一Full失败立即终止整个设计；
- 若Full成功但PASS，则记为preservation success，不记planner causality。

## 20.2 RetroSavePlaylist

**R2聚合：**24/50 actions，在25-action中点前终止；14次read、4次write、0次refresh。

**主要风险：**

- 历史R2路径下SCOPE应完全silent；
- 若Full在中点前与Base不同，只能来自随机性或环境差异，不能归因于SCOPE；
- 若实际轨迹变长后触发，说明该次run已经偏离历史成功路径。

**保护策略：**

- 中点前byte-equivalent；
- 不提前调用planner；
- 实际未到中点则aux calls必须为0；
- 若触发，完整记录触发前与Base/Shadow是否同状态。

## 20.3 SimpleCalendarAddOneEvent

**R2聚合：**22/34 actions，在17-action中点后还有5个executed actions；21次read、5次write、1次refresh。

**主要风险：**

- Calendar任务通常含精确字段，Coordinator可能错误改写日期、时间或事件名；
- phase decomposition可能把一个已经单调推进的表单流程过度复杂化；
- handoff cue可能被误写成completion claim。

**保护策略：**

- `INVARIANTS`必须逐字保持goal中的名称、日期、时间和约束；
- 不得生成具体点击或字段值之外的新要求；
- envelope最多8次，足以覆盖历史剩余轨迹但不会全程常驻；
- 任何字段变形都应触发validator或在审计中判为requirement corruption。

## 20.4 SportsTrackerTotalDurationForCategoryThisWeek

**R2聚合：**6/16 actions，正确answer；历史路径明显早于中点。

**主要风险：**

- 这是查询并回答型成功；
- 显式planner可能诱导无必要导航或不必要验证；
- planner容易与outcome-judgment track混淆。

**保护策略：**

- 中点前无SCOPE调用；
- 若实际run到达中点，Coordinator只有在确有多阶段剩余工作时才ACTIVE；
- 不允许Coordinator建议answer内容或判断数值正确。

## 20.5 RecipeDeleteMultipleRecipesWithConstraint

**R2聚合：**17/40 actions，在20-action中点前终止；16次read、7次write、2次refresh。

**主要风险：**

- 这是A1/R2中与pending repeated operation最相关的已有成功；
- 新phase文本可能覆盖R2 compact ledger的有效pending bookkeeping；
- 重新组织阶段可能让模型漏掉约束或重复删除。

**保护策略：**

- R2 memory保持原样；
- 历史路径下SCOPE完全silent；
- SCOPE不得复制或重写R2 ledger中的逐项pending；
- Full该题成功若未触发，仅计系统保持，不计组件收益。

## 20.6 OsmAndMarker

**R2聚合：**11/20 actions，在10-action中点后只剩1个executed action及终止；11次read、6次write、2次refresh。

**主要风险：**

- 这是R2相对A1新增的唯一full success；
- planner触发点极接近成功；
- 错误phase可能破坏目前最重要的paired gain；
- R2 causality本身尚未由matched ablation证明，更不能假设planner可以替代其行为。

**保护策略：**

- 保留完整R2；
- 当前截图若已直接支持最后操作或终止，Coordinator应PASS；
- 任何Full loss都会使整个系统accuracy verdict失败；
- 即使其他13题有新增成功，也不能用它抵消`OsmAndMarker` loss。

---

# 21. 预期收益、已知失败模式与设计否定条件

## 21.1 预期收益

若原始trace审计通过，SCOPE最可能带来的不是“更聪明的单步点击”，而是：

1. 在长episode中重新突出容易被局部导航覆盖的全局约束；
2. 把当前局部操作放回一个明确的剩余phase顺序；
3. 提供一个可见handoff cue，减少在两个subtask之间无目的往返；
4. 通过短期TTL让phase结构产生行为影响，而不成为always-on第二份memory；
5. 对已在中点前成功的任务保持完全silent；
6. 将“专业阶段结构”与“多一次通用视觉推理”直接区分。

## 21.2 主要失败模式

### 失败模式一：调用太晚

若requirement loss主要发生在前25%的预算，中点plan无法恢复已经丢失的精确要求。此时SCOPE应在audit gate被拒绝，而不是live后临时把threshold提前。

### 失败模式二：一次phase计划很快陈旧

由于v1不replan，当前截图变化后包络可能不再合适。executor必须能忽略，TTL必须限制损害。

### 失败模式三：Coordinator把当前状态误判为未完成phase

这可能导致已完成阶段重入，尤其危及Expense与Osm成功题。

### 失败模式四：phase输出实际变成动作提示

这会把研究问题从协调变成action arbitration，破坏边界和归因。

### 失败模式五：Generic extra reasoning同样有效

若Full和Generic取得相同新增成功，说明收益可能来自额外视觉推理、goal重述或延迟，而不是phase结构。

### 失败模式六：组件激活但行为惰性

A9、A10-v2、A11和A12已经出现“有read、无productive divergence”。SCOPE必须接受同样的负结论：有phase output不等于phase coordination有效。

### 失败模式七：成功全部silent

如果Full达到7/19，但新增成功episode没有Coordinator调用或返回PASS，则这是系统级随机gain，不能归因于SCOPE。

### 失败模式八：成本过高

一个新成功若需要大量额外GPU与wall time，可能通过accuracy但不能通过cost或Pareto审查。

## 21.3 能够否定SCOPE的结果

### 实现前否定

出现任一情况即维持NO-GO：

- 原始R2 trace无法完成19/19哈希闭包；
- 少于3个失败任务存在跨任务协调缺陷；
- 缺陷只集中于一个task family；
- 成功组同样频繁发生该缺陷；
- 缺陷普遍发生在中点之后，留下不足8次action runway；
- 失败主要由错误结果判断、单步视觉误识别或坐标错误构成；
- 审核者无法达到冻结的一致性门。

### Live gate否定

- Full六题任一loss；
- Full输出频繁格式失败或越权；
- phase文本导致已成功phase reentry；
- Full没有任何active exposure且不能测试组件；
- 组件调用导致不可接受的基础设施不稳定。

### Full-suite accuracy否定

- Full少于7/19；
- reward不大于6.5；
- 六题有任何loss。

### Planner因果否定

- Full不优于Generic；
- Full不优于Shadow；
- 没有至少2个productive interventions；
- 所有成功均component-silent；
- 输出激活但next action与后续可见进展无关联。

如果Full相对R2有系统gain，但与Generic持平，应给出：

> **System accuracy可能改善；专业phase结构因果不成立。**

如果Full与Shadow持平，应给出：

> **SCOPE文本影响未建立；结果可能由随机性、延迟或环境差异解释。**

---

# 22. 分阶段实施、独立审查、offline验证与live路线图

## 阶段0：证据闭包

- Materialize R2正式19题raw tree；
- 验证episode和截图hash；
- 产出只读manifest；
- generation calls固定为0。

**输出门：**19/19完整，否则停止。

## 阶段1：R2协调缺陷审计

- 冻结标注手册；
- 双人blind annotation；
- 统计成功6题与失败13题；
- 计算first-onset、duration、budget位置；
- 评估50% checkpoint和8-decision runway。

**输出门：**通过第4.6节资格条件，否则`NO-GO_WRONG_TRACK`。

## 阶段2：独立设计审查

独立审核者检查：

- SCOPE是否仍只包含一个新组件；
- 是否与TRC/VOV边界混合；
- 50% checkpoint是否被trace支持；
- 成功任务风险是否可接受；
- Generic与Shadow是否公平；
- prompt是否含动作、验证或恢复；
- 是否存在task-specific条件。

**输出门：**审核意见关闭并生成design-freeze hash。

## 阶段3：最小实现

只实现：

- checkpoint；
- auxiliary call；
- PASS/ACTIVE parse；
- immutable envelope；
- TTL；
- Full/Generic/Shadow；
- 分角色audit与成本。

不得顺手加入：

- replan；
- phase completion；
- recurrence detector；
- verifier；
- action guard；
- task parser；
- app rules。

## 阶段4：Zero-generation preflight

- trigger replay；
- mock output；
- prompt equivalence；
- leakage taint；
- source closure；
- cost cap；
- no-generation assertion；
- resume与invalid handling。

**输出门：**所有preflight PASS。

## 阶段5：Live source freeze

冻结：

- implementation commit；
- prompt hashes；
- config；
- model manifest；
- server receipt；
- arm order；
- task order；
- result schemas；
- stop/resume contract。

首次generation发生后不得修改行为source。

## 阶段6：六题能力保持门

按固定顺序运行Full、Generic、Shadow与prospective Base。

- Full任一科学失败立即停止；
- 不重跑；
- 不修改；
- 不释放后13题。

**输出门：**Full 6/6。

## 阶段7：释放后13题

- 按固定顺序与冻结arm rotation运行；
- 记录所有失败；
- 不中途根据结果调整checkpoint、TTL或prompt；
- valid failure不重跑。

## 阶段8：三层结果审计

分别发布：

1. System accuracy；
2. Component causality；
3. Cost。

同时发布：

- component-silent successes；
- active failures；
- productive interventions；
- phase relapses；
- Full/Generic/Shadow matched checkpoints；
- 所有infrastructure-invalid attempts及replacement。

## 阶段9：后续决策

只有当SCOPE-FULL同时满足accuracy与causality时，才可讨论：

- 第二次adaptive replan；
- 更早或event-based checkpoint；
- 动态phase expiry；
- 与recovery或verifier的factorial combination。

这些都必须是新arm，不能回填进SCOPE-R2 v1。

---

# 23. 实现团队仍需在首次生成前冻结的关键决策

## 23.1 本蓝图已经冻结

- 父系统为正式R2；
- 不继承A6/A7/A10/A11完整状态机；
- 不做initial planning；
- 每episode最多一次auxiliary call；
- 触发为50% native action budget；
- Coordinator不生成动作、不验证、不恢复、不终止；
- 输出最多3个phase；
- 允许PASS；
- max completion 256 tokens；
- input+output不超过8192 tokens；
- 60秒timeout；
- render最多700字符；
- TTL为8次真实executor injection；
- 不replan；
- invalid output不重试；
- 当前截图权威；
- executor最终行动；
- Base、Full、Generic和Shadow四arm；
- 六题6/6后才释放13题；
- full-suite正向目标≥7/19、reward>6.5、六题0 loss；
- accuracy、cost、causality分开；
- raw trace audit未完成前NO-GO。

## 23.2 仍需写入最终preregistration的实现细节

1. exact Coordinator prompt字节与SHA-256；
2. exact Generic prompt字节与SHA-256；
3. exact executor advisory render模板；
4. parser允许的换行、Unicode和缺失字段行为；
5. 坐标、canonical action与completion claim的validator词法规则；
6. `executed_action_count`的精确off-by-one测试；
7. 最近8条history的逐条字符上限与截断函数；
8. input token计数是否包含image token及超限处理；
9. auxiliary transport failure的基础设施分类；
10. request timeout后是否终止episode或标为invalid；
11. GPU time测量方法；
12. task-major arm rotation的最终顺序；
13. prospective Base的独立experiment ID；
14. raw trace annotation手册版本与审核者；
15. visible progress与phase relapse仲裁格式；
16. productive intervention的matched-state等级；
17. source closure文件清单；
18. checkpoint、result finalizer与resume schema；
19. live server receipt与model manifest；
20. independent pre-generation audit签字或hash。

这些内容必须在第一次model generation之前一次性冻结。第一次generation之后，任何修改都意味着新设计identity和新的六题gate。

---

# 24. 最终冻结决定

## 24.1 推荐系统

> **SYS-SCOPE-R2：Sparse Checkpointed Objective–Phase Envelope**

## 24.2 Planner裁决

> **修改显式planner。**  
> 保留一次专业phase computation，但删除开局完整计划、持续phase FSM、动态obligation状态和多次replanning。

## 24.3 父系统

> **正式A1-R2 compact verified/pending系统。**

## 24.4 唯一新增行为组件

> **在统一预算中点调用一次Phase Coordinator，并把有效的短期剩余phase envelope最多注入8次。**

## 24.5 当前科学状态

> **NO-GO-AUDIT。**

原因不是SCOPE已被否定，而是当前Git证据不足以完成用户要求的R2全19题requirement loss、phase loss、局部导航、错误子任务停留和phase reentry统计。现有聚合数据只支持“失败组更长、更多用满预算、same-state refresh更集中、错误terminal更多”，不能替代原始trace语义审计。

## 24.6 最小下一步

> 先完成第4节定义的R2全19题零生成、哈希绑定轨迹审计。  
> 审计通过资格门后，才允许把本蓝图转换为正式preregistration和implementation contract；审计不通过则直接否定SCOPE-R2，不在同一identity下移动checkpoint、添加replan或改造为恢复/验证系统。