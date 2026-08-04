# AndroidWorld Hard 失败的信息链审计

**日期：** 2026-08-04

**性质：** 仅使用既有证据的事后诊断；不是新实验、不是新方法评测、不是新颖性结论

**审计基线：** `6d8f7a9737aeadd30a5626f026173eccb2fe990f`

**运行边界：** 本审计未调用模型、未启动模拟器任务、未修改方法代码或正式 LaTeX 报告

## 1. 结论先行

现有 AndroidWorld Hard 结果不能被概括为“记忆模块失效”。更准确的结论是：大多数轨迹在到达可检验的记忆环节之前，就已经因来源页面未进入、感知/落点错误、动作循环、动作接口缺失或完成验证错误而断链。

- `[D]` 冻结的 95 个 Hard cells 中只有 1 个成功；15 个问答 cells 因冻结动作接口没有 `answer`，在结构上无法得分。剩余 80 个受支持 cells 中，1 个成功、50 个耗尽预算、14 个模型声明不可行、14 个过早完成、1 个修复后输出仍非法。
- `[D]` 在这 80 个受支持 cells 中，59 个出现至少 3 次连续相同动作，32 个至少 10 次；共有 477 个已执行动作没有产生截图变化。这里已经存在共享控制器 floor。
- `[D]` M0 并非“没有用上记忆”：19 个 M0 episodes 中有 758 次带 memory bundle 的决策、457 次引用记忆和 270 次辅助调用，但成功为 0/19，并相对 B3 增加约 33% calls、53% tokens、52% wall time。因此现有证据只说明复杂记忆没有跨过共享 floor，不能说明记忆本身是主瓶颈。
- `[D]` 最清楚的自然“记住值但做错对象”信号来自已污染的 EEST-P1：普通摘要与结构化 ledger 都保留了正确地址；B3/B3-MATCH 把它发到来源会话，M-SLOTS/M-RISK 的 4 条记录均正确绑定来源，却没有导航到目标联系人。第一处关键断链是 **destination-role retention / destination grounding → action**，不是 value capture。
- `[D+I]` “任务步数 = 记忆难度”作为等价关系不成立：同为 20-step 的 H07、H08、H17 分别是跨应用时序转录、无需运行时取值的坐标操作、同应用日期检索并回答；120-step 的 H09 不需要从界面获取待迁移值，却因 98 次相同输入动作失败。**但当前样本不足以证明依赖拓扑比步数更能预测成功**：只有一个 Hard 成功、一个 seed、15 个接口不支持 cells，且多数任务被控制器 floor 截断。

因此，本审计支持把后续问题缩小为“信息链的哪一条边最容易断”，而不支持宣称结构化记忆有效、无效或具有新颖性。

## 2. 证据口径与分析单位

### 2.1 标记

- `[D] Direct`：可由冻结 task goal、episode JSON、step action、截图哈希、evaluator 或既有汇总直接复核。
- `[I] Inference`：根据 task goal 和可见动作序列作出的结构编码或因果解释；不是 evaluator 给出的标签。
- `[U] Unknown`：现有轨迹没有到达该环节，或没有足够观测判定。

### 2.2 信息链

本审计按以下顺序定位**第一处**断链：

`获取证据 → 绑定 source/entity/field/value → 跨状态保留 → 决策时取回 → 定位 destination/field → 执行动作 → 观察结果 → 验证全局后置条件`

“信息依赖距离”不等同于最大步数。这里使用四个结构等级，并同时记录应用、页面状态与实际动作间隔：

- `R0`：不需要从运行时界面取得新值，所需值已在 task literal 中；仍可能有很长的控制链。
- `R1`：在当前页/同一局部状态取得值并在该局部使用。
- `R2`：同一应用内跨多个页面、记录或子目标后使用。
- `R3`：从来源应用取得值，在目标应用使用。

页面数是可见 UI state 的保守下界，不是 Android activity 的严格计数；动作间隔只在代表轨迹确实同时到达 source 和 use 时报告。没有到达 use 的记为 `NR`。

### 2.3 证据集合与污染边界

主要直接证据来自：

- `runs/frozen_hard_v1/hard_v1_breadth/suite_summary.json`
- `reports/breadth_forensic_analysis_2026-07-26.md`
- `runs/frozen_hard_v1/hard_v1_breadth/episodes/*/attempt_*/episode.json`
- `reports/eest_ac/eest_ac_smoke_v0_1_1_analysis.md` 及对应 8-cell 原始产物
- `reports/eest_ac/eest_ac_v0_2_blind_smoke_analysis.md` 及对应 9-cell 原始产物

Hard 表以 19 个 task instances 为单位，五个 arms 是同一 task 的重复实现证据；“第一处断链”使用表中注明的代表 episode。EEST v0.1.1、v0.2 及后续 qualification 已被开发污染，只用于说明机制和排除混杂，绝不计为新的 held-out 效能证据。H17/rXX 仅作历史失败审计，不作新实验结论。

## 3. 19 个 Hard 任务的逐任务断链分类

| Task（原生 max steps） | 信息依赖距离 `[I]` | 干扰 / role 风险 `[I]` | 结果可观测性 `[I]` | 可复核的失败事实 `[D]` | 第一处断链 verdict |
|---|---|---|---|---|---|
| H01 `BrowserMultiply` (22) | `R1`；同一网页连续取得 5 个数后使用；代表轨迹未到输入积的 use (`NR`) | 5 个时序值、点击计数和乘积 | 最终表单可见，数值正确性由 evaluator 判定 | B1 在 step 11–21 连续点击同一 `Click Me` 位置 11 次，未进入乘积输入 | `[D]` 动作计数/进度控制先断；是否还存在保留或计算错误为 `[U]` |
| H02 `ExpenseAddMultipleFromGallery` (60) | `R3`；Gallery 图像 → Pro Expense；use `NR` | 多条 expense、多字段、图像 OCR | 目标记录可在列表复查 | B3 打开 Gallery 后从 step 2 起连续 58 次同一 swipe，未打开 `expenses.jpg` | `[D]` source grounding / evidence acquisition 先断，不是 retention |
| H03 `ExpenseAddMultipleFromMarkor` (60) | `R3`；Markor 文本 → Pro Expense；use `NR` | 多交易 + reimbursable 条件 + 多字段 | 目标记录可复查 | B3 打开文本后连续 55 次同一 swipe，未进入目标应用 | `[D]` source parsing / progress control 先断 |
| H04 `ExpenseDeleteMultiple2` (34) | `R0`；三个名称来自 task literal；单应用 | 三个相似目标，需维护剩余集合 | 每次删除有详情和确认；最终列表可复查 | B1 成功进入并确认删除 `Video Games`、`Groceries`，随后连续 19 次 swipe 寻找剩余项并声明不可行 | `[D]` remaining-goal navigation/search 先断；不是运行时取值记忆 |
| H05 `MarkorCreateNoteAndSms` (18) | `R0`；正文和号码均在 literal；执行跨 Markor→SMS，两应用 | note 内容、文件名、收件号码、source/destination 阶段 | 正确 SMS 会话及 send 状态可见 | B2 创建并保存 note、触发 Share，step 17 即 done，未完成 SMS 目标选择和发送 | `[D]` destination/action phase 与 completion verification 先断 |
| H06 `MarkorMergeNotes` (78) | `R2`；同一应用至少 4 个页面状态；第一来源到新 note 输入约 22 个决策 | 三个来源、严格顺序、换行和目标文件名 | 新文件内容可直接重开检查 | B3 多次把“要复制”的意图映射成 `Paste`；step 23 只输入第三份内容，step 24 输出修复后仍非法 | `[D]` 终止于 action-format；`[I]` 更早已在 selection/copy semantics 与 ordered retention 处断链 |
| H07 `MarkorTranscribeVideo` (20) | `R3`；VLC 时序帧 → Markor；看见 `Juan` 后未到 use (`NR`) | 多个短字符串、严格帧序 | 最终文本文件可见；视频帧短暂 | B3 反复重开 VLC、选择同一视频/等待；step 14 summary 记录 `Juan`，但从未进入 Markor | `[D]` temporal acquisition / playback control 先断；保留能力 `[U]` |
| H08 `OsmAndMarker` (20) | `R0`；坐标来自 literal；单应用 | 低；一对坐标需正确映射到地图操作 | marker 可在地图看到 | M0 step 2 在地图中心 tap，随后 17 次 wait，耗尽 20 步 | `[D]` action strategy / progress recovery 先断 |
| H09 `OsmAndTrack` (120) | `R0`；两个 waypoint 名称来自 literal；单应用长控制链 | 两地点、顺序和 track 状态 | waypoint/track 可在应用内复查 | B1 step 22–119 连续 98 次重新输入 `Planken, Liechtenstein`；B2 同类连续 100 次 | `[D]` grounding + repeated-action recovery 先断，非 value-memory 距离 |
| H10 `RecipeAddMultipleRecipesFromImage` (60) | `R3`；Gallery 图像 → Broccoli；use `NR` | 多 recipe、多字段、图像 OCR | 保存后 recipe 列表/详情可见 | B2 打开 Gallery 后连续 58 次 wait，最终声明图像不可读/不可操作 | `[D]` perception/readiness/evidence acquisition 先断 |
| H11 `RecipeAddMultipleRecipesFromMarkor` (60) | `R3`；Markor → Broccoli；source copy step 14，首次目标输入 step 17（约 3 actions） | 多 recipe、多字段、来源文本与目标表单角色 | 每条 recipe 可在详情复查 | B3 把整段 recipe 文本输入 Broccoli 搜索框，之后创建若干内容不一致的记录，并在 48 actions 后 done/reward 0 | `[D]` destination-field grounding 先断；后续 requirement closure 也失败 |
| H12 `RecipeAddMultipleRecipesFromMarkor2` (60) | `R3`；Markor → Broccoli，并需按 30 min 过滤；B3 source 可见至首次 title 输入约 13 actions | 多 recipe、时长条件、多字段 | 每条 recipe 可复查 | B3 只创建一个候选后 step 19 done/reward 0；M0 在 source 页连续 57 次 swipe | `[D]` B3 首个可定位错误是 incomplete goal closure；M0 则在 acquisition/progress 先断；无法归因给单一 memory 机制 |
| H13 `RecipeDeleteMultipleRecipesWithConstraint` (40) | `R2`；需逐条读取 directions，再决定是否删除 | 多 recipe、directions 中的语义条件、删除集合 | “没有遗漏”需要遍历与最终列表复核 | B0 仅搜索字符串 `vegetables`，无结果后在 3 actions 声明不可行 | `[D]` task-semantic strategy / evidence acquisition 先断 |
| H14 `RetroSavePlaylist` (50) | `R0`；歌名和顺序来自 literal；单应用 + 导出阶段 | 两首歌顺序、playlist 与 export destination | playlist 内容可见；导出文件需跨界复核 | B3 建立空 playlist 后，在打开 playlist 与 back 之间循环 23 轮，未添加歌曲 | `[D]` navigation/planning loop 先断 |
| H15 `SaveCopyOfReceiptTaskEval` (16) | `R0`；源文件与目标目录来自 literal；Gallery/系统目录选择器 | source file 与 destination folder 角色相近 | copy 的持久结果主要在文件系统/evaluator 可见 | B3 进入 `Copy to` 后新建名为 `Download` 的目录，而非选择既有 Download；9 actions 后 done/reward 0 | `[D]` destination-role grounding 先断；随后 completion verification 假阳性 |
| H16 `SimpleCalendarAddOneEvent` (34) | `R0`；全部字段来自 literal；单应用 | title/description/start/end/duration 多字段角色 | 保存后 calendar entry 可见；可能有 disclaimer | B3 连续 18 次点 save/checkmark 后 done/reward 0；同任务 B2 在修正时间并处理 disclaimer 后 21 actions 成功 | `[D]` post-action observation/recovery 先断；同任务差异不支持 memory 归因 |
| H17 `SportsTrackerActivitiesOnDate` (20) | `R2`；OpenTracks 日期列表/记录 → answer | 多日期行、活动类型 | benchmark 依赖 `interaction_cache` 中的 `answer` | 五 arms 均失败；冻结 schema/prompt/adapter 没有 `answer`，因此 evaluator 结构上不可得分 | `[D]` final action-interface compatibility 先断；该 task 不可用于 memory efficacy |
| H18 `SportsTrackerTotalDistanceForCategoryOverInterval` (22) | `R2`；多个详情页 → 聚合 → answer；B3 详情到 done 约 2–5 actions | 日期区间、类别、多单位和数值 | 只有 `answer` 通道能被 evaluator 读取 | B3 summary 计算出 `1706` meters 后直接 done/reward 0；所有 arms 均受缺失 `answer` 约束 | `[D]` execute-answer interface 先断；聚合是否正确不足以改变结构性零分 |
| H19 `SportsTrackerTotalDurationForCategoryThisWeek` (16) | `R2`；多个详情页 → 聚合 → answer；B3 详情到 done 约 2–12 actions | 周界、类别、多个时长和单位 | 只有 `answer` 通道能被 evaluator 读取 | B3 summary 得出 `210` minutes 后直接 done/reward 0；所有 arms 结构性不支持 | `[D]` execute-answer interface 先断 |

### 3.1 跨任务汇总：第一断链不在同一层

按上述代表轨迹，至少可以直接区分以下类别：

1. **获取前失败：** H02、H03、H07、H10、H13 在目标值被可靠取得前就失败。
2. **控制/grounding 循环：** H01、H08、H09、H14，以及 H04 的后半段；这些任务中多项所需值本就在 literal 中。
3. **destination/field/action role 错误：** H05、H11、H15；EEST-P1 是更干净的自然实例。
4. **完成与结果验证错误：** H12-B3、H15、H16-B3；局部画面变化并不等于全局 requirement closure。
5. **接口导致的结构性失败：** H17–H19；H06-B3 另有一次 decision output invalid。

这些类别可以在同一个 episode 中叠加，但因果审计应以第一处断链为主，不能把后续未发生的 memory use 也记成 memory failure。

## 4. 最干净的三层绑定证据：EEST-P1（开发污染）

EEST-P1 的 task literal 是：把 Petar Muller 刚发来的活动地址转发给 Gabriel Fernandez。冻结实例的值是 `968 Spruce St, Hartford, CT, 06103`。

| 层 | 直接证据 | Verdict |
|---|---|---|
| source → field → value capture | M-SLOTS 与 M-RISK 共存入 4 条记录，4/4 都是 `Petar Muller → event_address → 968 Spruce…`，且带当前页 source hash | `[D]` 实现机制存在；只有两个 M episodes、每个两条记录，不是四个任务成功 |
| destination-role retention | ledger 没有把 Gabriel 作为独立、可关闭的目标义务暴露给执行；两种 M arms 都未进入 Gabriel 会话 | `[D]` end-to-end destination role 未被保持到行动 |
| value → destination action | B3 在来源会话输入并发送正确地址后看到 checkmark，随后 false done；B3-MATCH 同样输入来源会话并连续重复 Send；M arms 改为在消息输入区附近 long-press | `[D]` 四个 arms 都没有完成正确 destination action；不能说 M-SLOTS 优于摘要 |

这个例子说明“值正确”与“任务绑定正确”不是同一个指标。B3 的局部发送结果甚至是可见的，但**对错误 entity 的可见成功仍是全局失败**。因此 outcome observability 必须包含 destination identity，而不能只检查按钮或 checkmark 是否变化。

同批次的 EEST-N1 是负对照：Clock 在第一个 `open_app` 后已满足任务，但 B3 又 wait 4 次才 done，M-SLOTS/M-RISK 均耗尽 10-action budget。这里没有跨页值依赖，仍出现 completion floor，直接反驳“多余动作必然来自记忆困难”。

## 5. 非记忆混杂的边界证据

### 5.1 v0.2 的 action contract floor

`eest_ac_v0_2_blind_smoke_20260803` 的 9/9 cells 在第一项环境动作前失败：模型给出 `recent_app` press、`dx/dy` swipe 或 `direction/distance` swipe，而冻结 schema 要求另一套 canonical 形式；一次 repair 仍重复非法形式。18 个 raw calls、0 environment actions、9 个 evaluator 结果。

这批结果只能证明 prompt→schema→adapter 契约不一致，不能把三层绑定记为 0 后声称 memory 无效。后续 v0.2.1–v0.2.4 又分别暴露 decision metadata、outcome measurement、trace collection 和 Android service readiness 问题；它们均不是 task efficacy 证据。

### 5.2 M0 的“活跃但无净收益”

Hard M0 的 cited items 中 84.0% 是 `HYPOTHESIS`；所有 16 个引用记忆的 `type_text` 决策都引用了 `HYPOTHESIS`。另一方面，五个 M0 episodes 共 13 次 finish 尝试全部被 completion validation 拒绝。现有架构呈现“中间动作授权偏松、结束授权偏严”的迹象，但这是 `[I]` 的架构诊断：没有匹配任务证明改变权限分配会提高成功。

## 6. 对“步数是记忆难度代理”的显式检验

### 6.1 结构编码结果

按 task goal 独立编码，19 个任务中：

- `R0`（无运行时取值）7 个，max-step 范围 16–120，中位数 34；
- `R1` 仅 H01，22 steps；
- `R2` 5 个，范围 16–78，中位数 22；
- `R3` 6 个，范围 20–60，中位数 60。

`[I]` R3 的较高中位数说明 benchmark 设计者可能已给跨应用任务更多预算，不能说两者毫无关系；但范围严重重叠，而且同一 step budget 内的依赖结构不同：

- 20 steps：H07 是跨应用、时序多值转录；H08 只使用 literal 坐标；H17 是同应用记录检索并通过 `answer` 返回。
- 16 steps：H15 无需取得新值，主要难点是目标目录与复制验证；H19 要读取并聚合多个时长，却受 answer 接口阻断。
- 34 steps：H04 与 H16 都是 `R0`，但 H04 五 arms 全失败，H16-B2 成功；差异首先出现在导航与 post-action handling。
- 120-step H09 是 `R0`，98–100 次相同输入动作说明长轨迹可以只是控制循环；20-step H07 则在理论上需要真正的跨应用时序记忆。

### 6.2 Verdict

- **支持：** `[D+I]` step count 不是 memory difficulty 的定义，也不能单独区分是否需要 runtime-acquired information、跨应用 transfer、entity interference 或 postcondition verification。
- **不支持：** 现有数据不能估计 step count 与 memory difficulty 的可靠相关系数，也不能证明 dependency distance 对 success 的预测优于 step count。原因是 task-level `n=19`、仅一个 seed、success 只有 1、15 cells 接口结构性不支持，且大部分轨迹在 acquisition/use 前被 controller floor 截断。
- **应有的下一步：** 用总动作数匹配、只操纵 source→use 页面/应用距离和干扰实体数的任务，才能检验依赖拓扑的因果作用。

## 7. Claim–evidence verdict

| Claim | Verdict | 证据边界 |
|---|---|---|
| Hard 结果主要测到了共享 controller/interface floor | **SUPPORTED** | 1/80 supported success、重复动作/no-change、15 个 answer-incompatible cells |
| 自然任务中存在“正确值 → 错误 destination”的 role-permutation failure | **MECHANISM SIGNAL** | EEST-P1 四 arms 的单个 positive instance；频率无法估计，且任务已污染 |
| M-SLOTS 比普通摘要更能完成跨页任务 | **NOT SUPPORTED** | 记录 binding 正确，但无 destination-action paired win、无 task success 增益 |
| 任务步数等同于记忆难度 | **REJECTED AS A DEFINITION** | 同预算任务结构不同，长 `R0` 与短 `R3` 并存 |
| dependency distance 比 step count 更能预测成功 | **UNTESTED** | 当前 floor、样本量和接口缺陷阻止比较 |
| outcome observability 是独立失败轴 | **SUPPORTED AS DIAGNOSIS; EFFICACY UNTESTED** | H15/H16、EEST-P1/N1 和后续 measurement qualification；尚无 matched intervention |
| RAVEN-M/M0 或 EEST memory 本身有效或无效 | **UNRESOLVED** | 方法没有在无 floor、接口完整、匹配预算的任务集上被隔离评估 |

## 8. 排名后的可证伪假设与最小匹配实验

以下是从现有失败提出的可检验问题，**不是新颖性声明**；本审计没有做文献检索。

### 1. Destination-role binding 比 raw value retention 更接近跨页失败的直接原因

**假设：** 当 value capture 保持不变时，增加相似 source/destination entities 会显著提高“值正确但目标动作错误”的比例；显式 role obligation 只应降低这一比例，而非只提高 record accuracy。

**最小实验：** 12 个配对 instances；相同 UI、相同 6–8 actions、相同地址长度。每对只改变 `(a)` 单一会话 vs 两个相似会话，`(b)` source/destination 是否交换。比较 shared-summary 与最小 role slots，匹配 model/calls/tokens。逐层报告 capture、destination retention、最终 action；primary metric 是 destination-action accuracy。若 slots 只提高 record binding 而没有 paired destination-action win，则假设被否证。

### 2. 信息依赖拓扑而非总步数决定显式记忆的收益阈值

**假设：** 在总动作数固定时，从“值在 use 页面可见”变为“隔一页”再变为“跨一应用”，会出现可重复的成功下降；显式绑定的收益只在较远距离或高干扰条件出现。

**最小实验：** `3 distances × 2 interference levels × 4 seeds × 2 arms = 48 cells` 前先做 12-cell gate。所有任务固定 8 个必要动作；距离为当前页/同应用一页/跨应用，干扰为 1 或 3 个同类型 entities。负对照是值在目标表单旁持续可见。若在匹配动作数后距离与错误率无单调关系，或 slots 在远距离没有 net paired win，则停止该方向。

### 3. 全局后置条件的 entity-aware observability 决定 completion precision

**假设：** 仅验证局部 UI effect（输入框清空、checkmark、页面变化）会在错误 destination 上产生高 false-completion；把 destination identity 与 requirement closure 纳入 outcome oracle 可降低 FP，而不显著增加多余操作。

**最小实验：** 对同一发送/保存动作构造三种匹配后置条件：正确 entity 明确可见、错误 entity 但局部 effect 相同、正确 effect 延迟出现。基础 completion 与 entity-aware oracle 各跑配对 seeds。primary metrics 为 completion precision/recall 与 wrong-entity FP；成本上限为 actions/calls +15%。若 FP 不降或成本超限，则否证。

### 4. 有界稳定观察与“禁止原样重复”能独立于记忆降低控制器 floor

**假设：** 对 delayed-effect/no-effect 状态，先做固定窗口稳定观察，并在确认 no-effect 后要求不同动作类别，会显著减少长重复动作串，而不会损伤立即生效的负对照。

**最小实验：** 只用不需要跨页取值的可逆任务；匹配制造 immediate effect、1–2 s delayed effect、true no-op 三类，每类至少 4 对。比较相同 controller 的 recovery off/on，报告 ≥3/≥10 repeated runs、recovery success、task success、wall time。若重复率不降或负对照成本上升超过 15%，则否证。

### 5. 动作/评测接口完整性是任何 memory efficacy 实验的前置可证伪条件

**假设：** 当信息获取轨迹完全相同时，仅 final response adapter 是否支持 evaluator 所需动作，就足以解释问答任务的零分；在接口未通过资格测试前扩大 memory 对照只会产生不可解释 ties。

**最小实验：** 离线 conformance + 6 个非计分 paired qualifications：同一已冻结观察结果分别通过受支持 final action 与 evaluator-required final action 提交，要求 6/6 schema→adapter→interaction cache→evaluator 闭环。任何一格失败即停止 task-level memory 试验。该假设若通过，只解除接口 floor，不构成 memory 效能结论。

## 9. 限制与最终边界

1. Hard breadth 是 19 tasks × 5 variants，但只有一个 task seed；cells 不是 95 个独立任务分布样本。
2. 第一断链表使用每个 task 的一个代表 episode 加五臂汇总；未逐帧人工标注全部 95 条轨迹。未达到 source/use 的 episode 不能评价 retention。
3. 信息距离等级是本审计的结构编码 `[I]`，尚未验证 inter-rater reliability，也没有文献新颖性审计。
4. EEST-P1/N1、H17/rXX 和 v0.2+ qualification 均已开发污染；它们可定位机制，不能提供新 held-out 泛化证据。
5. 当前最稳妥的研究结论不是“需要更复杂的记忆”，而是先用匹配任务将 acquisition、role binding、destination grounding 和 outcome verification 分层测量；任何一层没有可执行证据时，不应让 record-level accuracy 代替 task-level success。

## 10. 受保护工作树审计

本报告只读引用旧产物。审计开始时三份 legacy H17/r79 WIP 的 SHA-256 为：

- `episode_controller.py`: `fc0e82e0fde90119365d4f685f080eb4519bf2f602e4bda58de5d4809a40fe33`
- `protocol_v2_guard.py`: `ff89d6b70be4b4738646d262beb67d7b7e932e9eb95956d940b1c5000a999d10`
- `test_protocol_v2_2_r79_r78_trace_replay.py`: `5bb1f1e3de673a1072cfee62938b761a62fd69c187d5eadf54bc46b115a3fd0a`

它们以及既有冻结报告、tags、runs 和污染边界均未被本审计修改或重新解释。
