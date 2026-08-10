# A1 动作工作记忆：正式结果与配对分析

日期：2026-08-10  
任务集合：AndroidWorld Hard，19 个任务  
任务 seed：`20260806`  
模型：`Qwen/Qwen3-VL-32B-Instruct`，revision `0cfaf48183f594c314753d30a4c4974bc75f3ccb`  
A1 正式套件：`official_qwen_20260810T122419_26573d7c`

## 1. 这次只改变了什么

A1 保留官方 Qwen 基线的模型、采样参数、当前截图输入、动作空间、任务实例、任务 seed 和原生步数预算。唯一有意改变的是：模型每一步把当前观察整理为

`observed / verified / pending`

三部分动作记忆；系统在同一个 episode 内保存最近 6 条不重复记忆，并把它们放入下一步提示。记忆不跨任务，不读取隐藏 UI、数据库或 evaluator，也不增加额外模型调用。

因此，A1 检验的是一个很窄的问题：**让模型持续看见自己刚才观察到什么、确认了什么、还欠什么，是否比官方 A0 更适合 Hard 长程任务。**

## 2. 主要结果

| 指标 | A0 官方基线 | A1 动作工作记忆 | 差异 |
|---|---:|---:|---:|
| 满分任务 | 4/19（21.1%） | 5/19（26.3%） | +1 个，+5.3 个百分点 |
| 部分得分任务 | 1 | 1 | 0 |
| reward 总和 | 4.5 | 5.5 | +1.0 |
| 平均 reward | 0.237 | 0.289 | +0.053 |
| 模型步骤/调用 | 329 | 603 | +274（+83.3%） |
| 总 token | 1,273,361 | 3,464,267 | +2,190,906（+172.1%） |
| 实际运行时间 | 约 1.82 小时 | 约 4.06 小时 | 约 +123% |
| 基础设施无效任务 | 0 | 0 | 0 |

A1 在全部 19 个任务中真实激活，共发生 515 次有效新记忆写入和 580 次非空读取。严格配对结果是 1 个提升、0 个退化、18 个相同；新增满分任务为 `RecipeDeleteMultipleRecipesWithConstraint`。A0 原有的 4 个满分任务和 1 个半分任务在 A1 中均保留。

这个结果是正向信号，但不是普遍性证明：目前只有一个 task seed，而且只有一个不一致配对。因此不能把它写成“已经证明工作记忆普遍有效”，只能写成“在冻结的 19 个 Hard 任务上观察到一个净增益，同时成本显著上升”。

## 3. 逐任务配对

| 任务 | A0 reward | A1 reward | 配对结果 | A0 步数 | A1 步数 | A1 新写入 | A1 非空读取 |
|---|---:|---:|---|---:|---:|---:|---:|
| BrowserMultiply | 0 | 0 | 相同 | 13 | 22 | 22 | 21 |
| ExpenseAddMultipleFromGallery | 0 | 0 | 相同 | 16 | 20 | 19 | 19 |
| ExpenseAddMultipleFromMarkor | 0 | 0 | 相同 | 13 | 18 | 17 | 17 |
| ExpenseDeleteMultiple2 | 1 | 1 | 相同 | 18 | 19 | 18 | 18 |
| MarkorCreateNoteAndSms | 0.5 | 0.5 | 相同 | 17 | 18 | 18 | 17 |
| MarkorMergeNotes | 0 | 0 | 相同 | 32 | 78 | 78 | 77 |
| MarkorTranscribeVideo | 0 | 0 | 相同 | 20 | 20 | 18 | 17 |
| OsmAndMarker | 0 | 0 | 相同 | 11 | 17 | 16 | 16 |
| OsmAndTrack | 0 | 0 | 相同 | 19 | 120 | 115 | 119 |
| RecipeAddMultipleRecipesFromImage | 0 | 0 | 相同 | 60 | 60 | 26 | 59 |
| RecipeAddMultipleRecipesFromMarkor | 0 | 0 | 相同 | 13 | 60 | 22 | 59 |
| RecipeAddMultipleRecipesFromMarkor2 | 0 | 0 | 相同 | 14 | 10 | 9 | 9 |
| RecipeDeleteMultipleRecipesWithConstraint | 0 | 1 | **A1 提升** | 15 | 26 | 25 | 25 |
| RetroSavePlaylist | 1 | 1 | 相同 | 32 | 28 | 25 | 25 |
| SaveCopyOfReceiptTaskEval | 0 | 0 | 相同 | 10 | 16 | 16 | 15 |
| SimpleCalendarAddOneEvent | 1 | 1 | 相同 | 17 | 34 | 34 | 33 |
| SportsTrackerActivitiesOnDate | 0 | 0 | 相同 | 3 | 20 | 20 | 19 |
| SportsTrackerTotalDistanceForCategoryOverInterval | 0 | 0 | 相同 | 3 | 9 | 9 | 8 |
| SportsTrackerTotalDurationForCategoryThisWeek | 1 | 1 | 相同 | 3 | 8 | 8 | 7 |

## 4. 记忆为什么在一个任务上有用

在 `RecipeDeleteMultipleRecipesWithConstraint` 中，A0 删除前两个匹配条目后，对最后一个条目执行了一次点击，就直接声称“已经删除全部配方”并结束；底层 evaluator 给出 0。轨迹显示，它把“已经发起删除”误当成“删除已经确认完成”。

A1 则不断保留三类状态：当前还剩几个匹配条目、当前条目是否已验证符合条件、下一步是否仍需确认删除。例如它明确写下“出现删除确认框；该配方已验证符合条件；待确认删除”。在最后一个条目真正完成确认之后才结束，evaluator 给出 1。

这说明简单工作记忆可能帮助的不是视觉识别本身，而是**多次重复操作中的完成数量与未完成动作记账**。这是目前最可信的正向机制解释。

## 5. 为什么多数任务仍然失败，而且成本很高

### 5.1 记住待办，不等于知道动作有没有生效

`OsmAndTrack` 跑满 120 步仍为 0。在末段，模型连续多次写下几乎相同的记忆：“主界面有加号；尚未验证；待添加三个途经点”，然后反复点击同一个加号。记忆成功保存了目标，却没有回答“刚才点击是否产生了预期页面变化”。

### 5.2 原始记忆会稳定错误循环

`MarkorMergeNotes` 从 A0 的 32 步增加到 A1 的 78 步，仍为 0。末段多次重复“已复制第一个文件；待返回列表打开第二个文件”，随后反复执行返回。这里不是遗忘，而是定位/状态转换失败；持续提醒同一个待办反而让模型更坚定地重复同一动作。

### 5.3 记忆增加了提示长度，也延长了失败轨迹

A1 的步骤数增加 83.3%，总 token 增加 172.1%。token 增幅大于步骤增幅，是因为每一步都重新注入记忆文本。换句话说，这个版本用显著更多时间和上下文换来了一个新增满分任务；从效率看，它还不是一个理想方法。

## 6. 当前结论

1. A1 的记忆机制确实运行了，不是名义上的模块：19/19 episode 激活，且有完整的逐步读写证据。
2. 它在冻结配对中产生了一个净新增满分任务，并没有损失 A0 原有成功项。
3. 它最可能帮助“重复操作的完成记账与确认闭环”。
4. 它没有解决动作落空、页面定位、进度验证和重复循环，反而会把错误待办持续强化。
5. 因此下一步不应简单增加记忆容量，而应改变记忆的内容与更新规则。

## 7. 下一种记忆机制应该检验什么

建议 A2 仍以 A0 为底座，只把 A1 的原始动作记忆替换为**可验证的进度记忆**：

- `verified_completed`：只有观察到预期页面/数据变化后，才把子目标记为完成；
- `current_subgoal`：当前唯一子目标，而不是不断重复整段总任务；
- `last_action_outcome`：上一步是成功转换、无变化还是不确定；
- `stall_count`：同一状态和同类动作连续重复时累积；
- 达到冻结阈值后禁止重复原动作并强制换路线。

这样 A2 检验的是：**记忆的价值是否来自“保存更多历史”，还是来自“保存经过验证的任务进度并识别停滞”。** 这比继续扩大 A1 的上下文更有针对性，也直接回应了本次最主要的失败证据。

## 8. 证据位置

- A1 汇总：`runs/a1_working_memory/official_qwen_20260810T122419_26573d7c/aggregate.json`
- A1 检查点：`runs/a1_working_memory/official_qwen_20260810T122419_26573d7c/checkpoint.json`
- A1 每步截图、UI、模型调用、动作、记忆读写和 evaluator：同一套件的 `episodes/` 目录
- A0 配对来源：`D:/ZJU/Summer_Camp/RAVEN-M-Research/runs/official_qwen_mobile/official_qwen_20260808T012646_c8281b8f/`
- A1 预注册：`protocols/A1_ACTION_WORKING_MEMORY_PREREG_2026-08-10.md`

