# Qwen3-VL-32B 完整 Hard：最早失败层标注规范

日期：2026-08-08（Asia/Hong_Kong）

本文件为 `official_qwen_20260808T012646_c8281b8f` 的人工分层标注规范。统计单位是**每个 episode 中最早能够由截图、动作 JSON、前台 activity 或 evaluator 数据证明的任务相关失败**，不是最后出现的所有症状。这样做是为了避免把上游选错对象造成的后续记忆丢失、循环和虚假完成重复计数成多个独立根因。

## 1. 层级的操作性定义

| 层 | 本轮如何判定 | 不应误归入该层的情况 |
|---|---|---|
| L0 运行时 | 模型服务未返回、超时、权重/显存/传输故障 | 模型正常返回但内容错误 |
| L1 感知与目标绑定 | 截图中存在关键信息，但模型读错、漏掉，或把相关候选绑定为错误的文件、日期、字段、地点、对象类型、app 别名 | 坐标映射或 Android 没执行 |
| L2 协议与坐标 | 官方输出格式无法解析，或归一化坐标映射错误 | 合法点击落在模型自己选错的控件上 |
| L3 动作执行与前置条件 | 工具动作没有被 Android 完成，或模型在焦点/页面/资源前置条件不满足时执行输入、粘贴等动作 | 动作成功执行但任务策略本身错误 |
| L4 状态转换与进度闭环 | 动作后页面没有预期变化，模型却把意图写成已完成事实；同一状态重复而不换策略 | 一开始就选错目标对象时，应优先标 L1 |
| L5 完成与 evaluator | 模型在缺少结果证据时声明成功，或可见结果类型与任务不符却终止 | evaluator 为 0 本身不是 L5 根因，必须先找更早失败 |
| WM 跨步任务状态 | 正确观察过的瞬时变量、字段集合、顺序或资源状态没有在后续需要时保留 | 从一开始就看错/选错来源，不算“记住了又忘” |

## 2. 标注顺序

1. 先确认 L0--L3 是否有客观异常；若无，再看任务语义。
2. 从 step 0 顺序找到第一个使正确完成路径失效的动作或遗漏。
3. 若同一步既有目标选择错误又有后状态未确认，优先记录更上游、可干预的目标选择错误，并把未确认写作放大因素。
4. 模型自然语言 Action 只算自述，不算执行证据；以工具 JSON、动作后截图、foreground、UI audit 和数据库 evaluator 为准。
5. `terminate(success)` 与 evaluator=0 只说明虚假完成；不能覆盖更早的来源、状态或执行错误。

## 3. seed 20260806 的 19 个科学有效实例初标

| 实例 | reward | 最早层 | 简要证据 |
|---|---:|---|---|
| BrowserMultiply | 0 | L4 | 网页尚为空白时，一次 click 被叙述为点击五次，并继续虚构结果 |
| ExpenseAddMultipleFromGallery | 0 | L1 | 自动打开的 `old_expenses` 噪声图被当成指定 `expenses.jpg` |
| ExpenseAddMultipleFromMarkor | 0 | L1 | 未搜索/定位 `Reimbursable` 行就离开源文件 |
| ExpenseDeleteMultiple2 | 1 | 成功 | 三个删除均有局部可见闭环，evaluator 验证成功 |
| MarkorCreateNoteAndSms | 0.5 | L3 | 未先取得正文焦点就输入，正文保持为空；短信子任务成功 |
| MarkorMergeNotes | 0 | WM/L4 | 在第二份源文件中把 Paste/Copy 资源角色记成“已写入尚未创建的目标文件”，后续无法形成三段按序内容 |
| MarkorTranscribeVideo | 0 | L1 | 没核对精确视频文件名就播放噪声视频 |
| OsmAndMarker | 0 | L1 | 同屏 `Add` 与 `Marker` 中选了前者，建立 Favorite |
| OsmAndTrack | 0 | L4 | 普通地图定位被动作历史记成“已加入 waypoint”，从未进入轨迹编辑器 |
| RecipeAddMultipleRecipesFromImage | 0 | L1 | 未将 `Simple Gallery Pro` 与启动器标签 `Gallery` 绑定，随后 58 步停滞循环 |
| RecipeAddMultipleRecipesFromMarkor | 0 | WM→L2 | 整篇文本未拆成目标字段，随后生成不存在的 `paste` 动作而被拒绝 |
| RecipeAddMultipleRecipesFromMarkor2 | 0 | L1/WM | 只检查并带走第一条 2 小时食谱，未形成三条符合项的完整集合 |
| RecipeDeleteMultipleRecipesWithConstraint | 0 | L4 | 前两条正确删除；第三条只打开就被记成已删除并直接终止 |
| RetroSavePlaylist | 1 | 成功 | 32 步中从错误设置分支恢复，按序加歌并导出到 Downloads |
| SaveCopyOfReceiptTaskEval | 0 | L1 | 把 `Internal/DCIM/Download` 当成根目录 `Internal/Download`，叶子名相同但父路径错误 |
| SimpleCalendarAddOneEvent | 1 | 成功 | 单对象显式字段在同一表单核验后保存，evaluator 验证通过 |
| SportsTrackerActivitiesOnDate | 0 | L1 | 未到 October 02，并把 October 08 的活动标题当成 activity type |
| SportsTrackerTotalDistanceForCategoryOverInterval | 0 | L1/推理 | 候选基本正确，但把 miles 求和后给出错误的米制答案 |
| SportsTrackerTotalDurationForCategoryThisWeek | 1 | 成功 | 正确识别两条 mountain biking 记录并求和为 180 分钟 |

seed 20260806 的最早失败分布（成功项不计）为：L1/目标约束类 9，L3 1，L4 3，WM 2，L0 0；另有 1 例在更早的 WM/计划问题之后触发 L2 协议错误。4 个完整成功任务分别是 ExpenseDeleteMultiple2、RetroSavePlaylist、SimpleCalendarAddOneEvent、SportsTrackerTotalDurationForCategoryThisWeek，总成功率为 4/19=21.05%。这个单 seed 分布已经说明三点：第一，官方链路能够获得稳定非零结果，不能再把全 0 归因于模型服务、坐标或 evaluator 的统一低级错误；第二，“所有失败都是记忆不足”与证据不符，目标/来源/字段/单位绑定比纯跨步遗忘更常见；第三，任务长短不是充分根因，32 步任务可以成功，3 步问答也能因一个约束槽位不对而失败。最终干预选择仍须等待另外两个 seed 的科学有效重跑结束后重算。

## 4. 后续干预选择门

完整集结束后，只对满足以下条件的机制做下一轮最小因果实验：

1. 同一最早失败类型跨至少两个任务类重复出现；
2. 干预能在动作发生前改变决策，而不是事后解释失败；
3. 干预不向模型泄露 evaluator、隐藏 UI 树或具体测试答案；
4. 在任何生成调用前冻结提示词/控制器、模型 revision、采样、预算、停止规则和污染边界；
5. 先运行独立 pilot，失败后调整的版本不得冒充 held-out。

当前最值得继续观察的候选不是“加更多通用记忆”，而是两个更窄的问题：

- **目标身份约束**：文件名、日期、字段、地点粒度、对象类型或 app 标签至少一个硬条件不匹配时，不允许把候选写入已完成进度；
- **证据化进度提交**：只有动作后截图出现相应目标页面、目标实体或列表变化，才把“尝试了”提升为“完成了”。

二者是否实施、先实施哪一个，必须由 57 个实例的最终频率和同类三 seed 一致性决定。

## 5. 57-key 完成后的资格判断

最终集合为 57/57 个唯一有效键，完整成功 7 条。自动可复核的横向信号为：21 条虚假成功声明、39 条重复状态、14 条连续停滞；执行失败为 0，说明这些轨迹不能继续统一归因于 Android 没有执行动作。

“精确目标/来源约束”覆盖面更广，但它同时包含文件名、父路径、日期、图标类别、字段角色和地点粒度等多种规则，直接一次实现容易变成任务特定硬编码。相比之下，“无可观察转移时不得提交语义效果”更窄：它不判断正确答案，也不读取 evaluator，只约束模型历史不能把尝试升级成事实。该机制至少在两个不同任务类中重复出现：

- `ExpenseDeleteMultiple2/20260808` 在误入详情页后连续约 27 步无进展 swipe，动作历史仍写成继续搜索；
- `OsmAndTrack/20260808` 在轨迹编辑器 `points: 0` 后连续约 72 次无进展操作，历史仍写成 waypoint 已添加/保存。

因此首个最小 matched diagnostic 选择 L4 状态转移证明，而不是立即实现覆盖更广的 Destination-First Binding Gate。干预只在页面像素与 UI 哈希均未变化时，把下一轮历史改写为“动作已执行，但所描述的语义效果未验证；不可在同一状态重复同一动作”，其余模型、采样、提示主干、任务实例、预算、动作执行和 evaluator 全部保持不变。由于 57 个基线实例均已被观察，这一轮只能报告同实例因果诊断，不能声称 pristine held-out 泛化。
