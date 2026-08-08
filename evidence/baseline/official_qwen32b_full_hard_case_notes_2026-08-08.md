# Qwen3-VL-32B 完整 Hard：逐例分层注释

本文件只记录 `official_qwen_20260808T012646_c8281b8f` 中已经结束、并经人工检查过截图与动作的实例。自动统计见同目录下持续更新的 `layer_suite_summary.partial.json`。尚未检查的实例不提前归因。

## 1. BrowserMultiply / seed 20260806

- episode：`BrowserMultiply_20260806_3e2fd311`
- 结果：0；13 次模型调用；以 `answer` 结束
- 模型答案：120
- 基础链路：模型服务、解析、坐标和动作执行无报错
- 最早任务相关失败：Chrome 的本地页面仍是空白加载态时，模型在文字 Action 中声称已经点击按钮五次，但该步工具 JSON 只有一次 click，且页面上没有可点击的 `Click Me`
- 后续：模型没有等待/确认页面内容，返回文件管理器，再凭空声称已算出乘积并用 `answer` 结束；它既未真实观察五个数，也未在网页输入与提交
- 分层判断：首先是 L1/L4 的后状态确认失败，并伴随“自然语言动作计数 ≠ 单次工具动作”；此例尚未到达跨步记忆是否足够的可检验阶段

## 2. ExpenseAddMultipleFromGallery / seed 20260806

- episode：`ExpenseAddMultipleFromGallery_20260806_5a3bfad4`
- 结果：0；16 次模型调用；模型自报 success
- 真值：应从 `expenses.jpg` 读取 Bike Repairs、Tuition Fees、Public Transit 三条完整记录并写入 Pro Expense
- 最早任务相关失败：Gallery 启动后自动显示的是 `old_expenses_*.jpg` 噪声图，页面上出现 Landscaping、Shoes、Bakery Items 等噪声；模型没有选择并核对文件名 `expenses.jpg`，直接把自动展示内容当成目标图
- 第二个失败：返回应用抽屉后，模型声称打开了 Pro Expense，实际前台包始终是 `com.simplemobiletools.gallery.pro`。它先点空白/边缘位置，再点回 Gallery，却没有用新截图纠正 app 身份
- 后续：模型在 Gallery 的搜索/图像界面连续调用 `type`，把 `156.98`、`301.67`、`181.53`、`$26.42` 当作四笔费用依次输入；它从未进入 Pro Expense、从未建立费用记录，后三次输入几乎不产生页面变化，最后仍自报成功
- 分层判断：最早是文件身份绑定错误，随后是 app 身份/前台状态确认错误；跨 app 记忆也丢失目标字段，但在此之前任务已经因选错源图和目标 app 而失败

## 3. ExpenseAddMultipleFromMarkor / seed 20260806

- episode：`ExpenseAddMultipleFromMarkor_20260806_705f23ab`
- 结果：0；13 次模型调用；模型自报 success
- 任务约束：只录入 `my_expenses.txt` 中备注带 `Reimbursable` 的交易；初始化文件含大量干扰交易，目标行不保证在首屏
- 最早任务相关失败：模型打开文件后只查看首屏，没有搜索 `Reimbursable`、没有向下定位目标行，也没有在 Action 历史中保存任何真实交易字段，就离开 Markor
- 后续：它正确打开 Pro Expense 和新增页，却凭空生成 `Lunch with client / 50`，保存一条任务中不存在的交易后自报全部完成
- 分层判断：首先是条件过滤与信息检索未执行，其次才是跨 app 字段记忆缺失；目标 app 定位和 `+` 按钮执行在本例是正常的，因此能够和上一例的 app 身份错误区分

## 4. ExpenseDeleteMultiple2 / seed 20260806

- episode：`ExpenseDeleteMultiple2_20260806_0eeb0637`
- 结果：**1**；18 次模型调用；模型自报 success，evaluator 同意
- 完成路径：打开正确的 Pro Expense → Expense Logs → 依次打开并删除 Public Transit、Tuition Fees → 向下滚动定位 Bike Repairs → 删除并确认
- 基础链路：每次详情页、删除按钮、确认框和返回列表的页面转换都与 Action 对齐；没有解析或执行失败
- 为什么这一例能成功：三个目标名称从任务开始就明确给出，不需要从另一 app/图片中提取字段；删除一个目标后，数据库和列表都立即留下可见反馈；任务可以拆成三个局部闭环，每次只需绑定“当前指定名称—当前列表项—删除确认”，不需要保存会消失的长字段集合
- 对照价值：同一个模型、同一官方控制器、同一模拟器与 evaluator 已取得非零结果，直接排除了“整个链路配置错误所以所有 Hard 都必然为 0”。前面三例的失败应归因于各自的目标绑定、信息检索和跨步状态机制，而不能再笼统归因于服务器或坐标

## 5. MarkorCreateNoteAndSms / seed 20260806

- episode：`MarkorCreateNoteAndSms_20260806_91f6e017`
- 结果：总 reward=0.5，按完整任务计 0；17 次模型调用；模型自报 success
- 成功的半项：Simple SMS Messenger 中收件人 `+14678402526` 和消息 `Ignorance is bliss.` 均正确，最终截图可见消息气泡与发送状态
- 失败的半项：Markor 文件名创建路径完成，但模型没有先点击正文获得编辑焦点就调用 `type`；离开 Markor 前的截图显示正文仍为空。它没有检查输入后页面是否出现目标文本，也没有显式保存/返回列表验证文件内容
- 分层判断：任务参数始终在用户指令中，因此不是跨 app 记忆丢失；最早失败是“输入动作的前置条件（正文焦点）未满足”，随后是后状态验证缺失。SMS 半项成功说明它具备跨 app 执行和保留显式任务参数的能力
- 研究价值：部分 reward 将“整条任务失败”拆成可定位的单组件失败；若只看最终 0，会错误地把已成功的短信链路也当作问题

## 6. MarkorMergeNotes / seed 20260806

- episode：`MarkorMergeNotes_20260806_4b24e296`
- 结果：0；32 次模型调用；模型自报 success
- 真实目标内容顺序：`nlEji0iw4OTEexN8ZNlf`、`Xm588oF4xHREnYU3lTRq`、`lGOTn20sYP7OPg233v3c`
- 最早任务相关失败：模型选中第二份源文件正文后，Action 声称已把第一份内容粘贴到“新文件”，但目标新文件直到第 24 步才创建；该步实际点击的是选择工具条上的 `Paste`，因而是在第二份源文件里操作，而不是在目标文件中
- 资源状态错误：随后模型重新打开第二份源文件并继续 Copy/粘贴流程，但自然语言历史已经把“源文件被改动/仍在源页面”记成“目标文件已收到内容”。普通活动剪贴板、Gboard 历史、当前正在编辑的文件三种资源角色没有被区分
- 最终证据：目标文件 `2zo4n6Ho` 确实创建，但没有三段按序内容与空行；最后只尝试从 Gboard Clipboard 点击当前可见条目，无法补回先前未正确提交的三段结构。最终截图与 evaluator=0 一致
- 分层判断：最早是资源角色与页面状态错误（WM/L4）：`Copy/Paste` 的对象和目的文件被自然语言提前改写。后续的剪贴板选择与空内容完成判断是放大因素，而不是一次简单的“记忆容量不够”

## 7. MarkorTranscribeVideo / seed 20260806

- episode：`MarkorTranscribeVideo_20260806_f19368f3`
- 结果：0；20 次模型调用，达到原生步数上限
- 冻结目标：视频 `edited_clip_92_export.mp4`，真实帧序列 `Henry, Louis, Juan`，写入 `edited_clip_92_export_transcription.txt`
- 最早任务相关失败：进入 VLC 的 Download 后没有核对精确文件名，就播放了一个噪声视频；看到的字符串是 `cDck298Ptq`、`7OPg233v3c`，与目标真值完全不符
- 后续：模型用 Action 历史保存了第一段噪声字符串，第二次识别后却在 VLC 中直接调用 `type`；随后反复点击播放/暂停，未进入 Markor、未创建目标转写文件，最终耗尽 20 步
- 分层判断：最早仍是源文件身份绑定错误，而不是纯粹的“视频记忆容量不足”。在错误视频上，它还暴露出时序观察、结构化累积和目标 app 写入三个阶段没有分离
- 横向复现：H02 自动打开旧图片、H07 打开噪声视频，都说明“进入正确目录”后模型容易把第一个可见媒体当成指定文件；这是跨媒体任务共享的可检验失败模式

## 8. OsmAndMarker / seed 20260806

- episode：`OsmAndMarker_20260806_2f730163`
- 结果：0；11 次模型调用；模型自报 success
- 已完成部分：模型搜索了任务指定的精确坐标 `47.1858882, 9.5452201`，进入地图并在该位置调出详情面板；因此坐标输入、搜索跳转和地图定位链路均正常
- 最早任务相关失败：详情面板底部同时存在 `Add`（星形图标，加入收藏）与 `Marker`（旗形图标，建立地图标记）。模型点击了 `Add`；下一页标题已经明确显示 `Add Favorite`，但模型仍输入 `Location Marker` 并保存
- 最终证据：保存后详情面板显示 `Location Marker`，其下方类别明确写着 `Favorites`，且操作项变成 `Edit Favorite`。它建立的是一个命名为 Location Marker 的收藏点，而不是任务要求的 map marker；evaluator 从 `map_markers` 数据库检查目标，自然得到 0
- 分层判断：坐标和页面导航正确，失败发生在目标对象类型绑定；“名字叫 Marker”不能把 Favorite 变成 Marker。这不是长程参数遗忘，而是两个语义相近、同屏可选的合法操作之间的目的地歧义，属于 L1 语义/目标绑定错误，并由缺少 L5 结果类型核验放大
- 研究价值：这是 `Correct location, wrong object type` 的直接实例，比笼统说“视觉没看清”更精确；若后续做最小救援，应在动作前要求核对将要创建的实体类型，并在保存后核对 `Favorites`/`Marker` 这样的结果类型证据，而不是增加泛化的长文本记忆

## 9. OsmAndTrack / seed 20260806

- episode：`OsmAndTrack_20260806_d883cd01`
- 结果：0；19 次模型调用；模型主动报告 failure，而非虚假 success
- 任务要求：依次把 Oberplanken、Rotenboden、Planken 三个精确地点加入并保存为一条轨迹；evaluator 实际读取 OsmAnd 导出的 GPX 轨迹点，要求三个目标坐标按顺序出现
- 最早任务相关失败：搜索 `Oberplanken, Liechtenstein` 后，页面只有 `SHOW ON MAP`，没有精确地点候选。模型点击该入口后只把地图定位到附近，但其 Action 历史把这次普通定位写成“selected ... as the first waypoint”；界面从未进入轨迹规划/编辑状态，GPX 中也不可能已有第一个 waypoint
- 后续失败：搜索 `Rotenboden, Liechtenstein` 时页面明确只返回 `Liechtenstein — Country`。模型没有返回并探索真正的轨迹创建入口，而是连续点击 `INCREASE SEARCH RADIUS`，其中多次点击后的像素变化接近或等于 0；同一 UI 状态最多出现 5 次
- 终止：模型最终点开国家级 Liechtenstein，截图仍是国家详情页，底部只有 Add、Marker、Share、Actions，随后诚实地 `terminate(failure)`；本例没有协议或动作执行异常
- 分层判断：最早错误与 Hard Pulse H09 一致，是把“搜索/地图定位”错误记账为“已加入 waypoint”，即自然语言进度超前于可观察状态；之后才出现精确地点检索失败和无效循环。仅增加记忆不会修复，因为记忆会忠实保存错误的进度陈述
- 独立复现价值：H09 与完整集 H09 使用不同冻结参数，但都在 OsmAnd 精确地点候选与轨迹入口处失败，说明该模式不是单次随机误点。更合适的救援对象是“只有出现轨迹编辑器/waypoint 列表证据时才允许提交 waypoint 进度”，并在重复状态后转向轨迹创建入口，而不是继续扩大搜索半径

## 10. RecipeAddMultipleRecipesFromImage / seed 20260806

- episode：`RecipeAddMultipleRecipesFromImage_20260806_a68f8831`
- 结果：0；60 次模型调用；达到原生步数上限；耗时 908.1 秒
- 任务入口：任务文本要求从 `Simple Gallery Pro` 的 `recipes.jpg` 读取三份食谱，再写入 Broccoli；设备启动器把该 app 显示为短标签 `Gallery`
- 最早任务相关失败：打开 app drawer 后，截图中 `Gallery` 图标从一开始就清晰可见，但模型没有把产品全名 `Simple Gallery Pro` 与启动器短标签 `Gallery` 绑定起来；它选择继续向上滚动寻找字面全名
- 循环证据：滚动到列表底部后，模型仍连续执行同一方向 swipe。60 步中有 58 步的有效像素变化低于 0.1%，同一 UI 哈希出现 58 次，最长连续停滞也是 58 步；模型从未点击任何 app，因而尚未接触图片识别、字段记忆或 Broccoli 写入
- 基础设施排除：全部 60 次模型生成、协议解析和 swipe 执行均成功；页面不动是因为已经位于抽屉边界，而不是 Android 拒绝动作。任务初始化时目标 `recipes.jpg`、Broccoli 数据与 evaluator 均已正常建立/清理
- 分层判断：最早是 app 实体别名绑定错误（L1），随后由缺少重复状态/动作无效检测（L4）把一次入口错误放大为 58 次无效调用。这个 0 不能归因于跨 app 记忆，因为控制器根本没有进入源 app
- 研究价值：精确身份约束不能简单理解为“字符串必须完全相同”；文件名、日期、坐标等任务约束通常要求精确匹配，而产品全名与系统短标签需要允许受控别名。更合理的目标绑定应区分哪些槽位必须 exact match、哪些槽位允许 alias match，并要求别名由当前 app 图标/包身份或先验映射支持

## 11. RecipeAddMultipleRecipesFromMarkor / seed 20260806

- episode：`RecipeAddMultipleRecipesFromMarkor_20260806_d7fd8f16`
- 结果：0；13 次模型调用；第 13 次官方输出无效
- 已完成部分：模型正确进入 Markor 的 `recipes.txt`，完整页面同时显示三份目标食谱；它能够全选、Copy、返回桌面、打开 Broccoli，并进入 New Recipe 的 Title 字段
- 最早策略问题：源文本是三份食谱、每份含标题/描述/份量/时间/原料/步骤六类字段，而模型只把整篇文本复制进一个普通剪贴板。它离开 Markor 前没有把内容拆成目标表单需要的结构化字段，也没有在动作历史中保存任何目标值
- 显性终止错误：在 Broccoli 的 Title 字段，模型生成 `mobile_use(action="paste")`；官方冻结 action schema 不支持 `paste`，控制器严格拒绝执行并以 `official_output_invalid` 结束。该轮没有偷偷把 paste 映射成别的动作
- 为什么不能只怪协议：模型文字声称要“paste the first recipe title”，但剪贴板中实际是三份食谱的整篇文本；即使实现 paste，也会把错误粒度的数据写进单一 Title 字段，无法完成六字段×三记录的目标
- 分层判断：更早的因果问题是跨 app 状态表示与目标表单 schema 不匹配（WM/计划）；L2 的不存在动作让错误更早暴露。若只增加 paste 动作，可能把协议失败变成数据库内容错误，不构成真正救援
- 与 H06 对照：H06 是三次 Copy 覆盖前两份内容；本例避免了覆盖，却把全部内容压成一个不可按字段寻址的剪贴板块。两者共同说明剪贴板只是一种传输资源，不等于结构化任务记忆

## 12. RecipeAddMultipleRecipesFromMarkor2 / seed 20260806

- episode：`RecipeAddMultipleRecipesFromMarkor2_20260806_b77e9af2`
- 结果：0；14 次模型调用；模型自报 success
- 任务约束：只录入 `recipes.txt` 中总时长为 2 小时的食谱；源文件中符合条件的实际有三份：Zucchini Noodles、Moroccan Chickpea Stew、Spicy Tuna Wraps
- 已完成部分：模型打开了正确源文件，也在首屏识别出 Zucchini Noodles 的总时长为 2 小时；随后能够打开 Broccoli、新建食谱并保存一条记录
- 最早任务相关失败：模型在尚未遍历并形成“全部符合项”集合时就离开源文件，只保留了第一条候选；它没有继续检查后两份食谱，也没有记录目标数量
- 写入问题：保存的记录只包含标题和泛化描述，缺少源文件给出的 servings、prep/cook time、ingredients、directions 等字段；最后把“一条不完整记录已保存”当成“所有匹配食谱已录入”
- 分层判断：最早是条件筛选与集合闭包没有完成（L1/WM/计划），随后出现字段级跨 app 状态缺失与过早完成（L5）。这不是简单的“记不住很多字”，而是离开源页面前根本没有建立完整、可计数的目标集合

## 13. RecipeDeleteMultipleRecipesWithConstraint / seed 20260806

- episode：`RecipeDeleteMultipleRecipesWithConstraint_20260806_ad293d85`
- 结果：0；15 次模型调用；模型自报 success
- 任务约束：删除 directions 中使用 zucchini 的全部食谱；初始化数据库中共有三条 Zucchini Noodles 变体需要删除
- 已完成部分：模型搜索 `zucchini` 后，前两条均经历“打开详情—菜单—删除—确认—返回列表”的完整可见闭环，动作链路是正确的
- 最早导致最终失败的步骤：剩下第三条时，模型只点击进入该列表项，就在自然语言 Action 中把它写成“已删除最后一条”，随后直接终止；它没有打开菜单、点击 Delete 或确认
- 分层判断：这是明确的 L4 进度记账超前，并被 L5 过早完成放大。前两条成功证明控件定位和删除流程不是问题，真正缺的是“已完成数量必须由删除后列表变化支持”的计数闭环
- 研究价值：同一 episode 内出现 2/3 成功，使根因比总 reward=0 更清楚。这里不需要教模型新的删除知识，而需要阻止一次点击被错误升级为整条子任务完成

## 14. RetroSavePlaylist / seed 20260806

- episode：`RetroSavePlaylist_20260806_c44b826d`
- 结果：1；32 次模型调用；模型自报 success，evaluator 同意
- 完成内容：创建 `Metal Mayhem 375`，按指定顺序加入 Heartbeat Away、Reflections、Endless Summer，并通过播放列表菜单 `Save as file` 导出到 Downloads
- 恢复过程：模型曾进入 Settings / Backup & Restore 的错误分支，但没有把该分支记成任务完成；返回后继续探索目标播放列表菜单，最终进入系统文件选择器并完成保存
- 为什么长而成功：任务所需的歌名与顺序始终存在于用户指令和历史中；每加入一首歌、打开播放列表和进入保存文件界面都有显式反馈；即使走错路径，也没有破坏不可恢复的瞬时资源
- 对照价值：32 步并不天然意味着失败。与 H06/H11 相比，本例同样跨多个页面且调用很多，但关键目标是显式字符串，子步骤可局部验证，错误分支可回退。因此“长度”只是风险放大器，不是充分根因

## 15. SaveCopyOfReceiptTaskEval / seed 20260806

- episode：`SaveCopyOfReceiptTaskEval_20260806_d1d528de`
- 结果：0；10 次模型调用；模型自报 success
- 已完成部分：模型打开正确的 Gallery/DCIM，选择了正确文件 `receipt_pretty_deer_CS0k.jpg`，进入 `Copy to`，最终也获得了系统提示 `File copied successfully`
- 决定性证据：选择目标目录的页面面包屑明确显示 `Internal > DCIM > Download`。模型没有返回 `Internal` 根目录再选择真正的 `Download`，而是在 DCIM 内的同名子目录确认复制
- 为什么“复制成功”仍是任务失败：toast 只证明复制动作成功，不证明复制到了任务指定的目标位置；evaluator 检查的是根目录 Download 中同名文件，因此返回 0 是一致的
- evaluator 源码复核：`SaveCopyOfReceiptTaskEval.is_successful()` 固定以 `device_constants.DOWNLOAD_DATA` 为 `base_path` 检查同名文件；初始化和 teardown 还会清空设备存储。因此 `DCIM/Download` 中的文件不会误判为成功，也不能用先前任务残留解释 0 分
- 分层判断：最早是目标目录的路径/角色绑定错误（L1），随后是 L5 证据粒度错误——模型把动作级成功提示当成任务级目标证明。模型并没有忘记字符串 `Download`，而是没有约束其父路径必须是 `Internal`
- 研究价值：这是 `Correct operation, wrong destination` 的干净实例，也直接支持“目标身份应包含层级路径，而不只是叶子名称”；这种约束比泛化的“请仔细检查”更可检验

## 16. SimpleCalendarAddOneEvent / seed 20260806

- episode：`SimpleCalendarAddOneEvent_20260806_739e8ebf`
- 结果：1；17 次模型调用；模型自报 success，evaluator 同意
- 完成路径：选择 2023-10-26，进入新建事件，准确填写标题与描述，把开始时间由 16:00 改为 08:00、结束时间改为 09:00，保存后终止
- 为什么能成功：全部目标字段从任务开始就显式给出，不需要跨 app 抽取；表单的标题、描述、开始时间、结束时间彼此分槽；保存前所有字段可在同一页面核验，结束后数据库可直接验证
- 对照价值：该例证明官方链路的文本输入、时间选择器、坐标映射、保存和 evaluator 都能正常工作。与失败的多记录/跨媒体任务相比，它更接近单对象、显式字段、单次提交的闭环

## 17. SportsTrackerActivitiesOnDate / seed 20260806

- episode：`SportsTrackerActivitiesOnDate_20260806_fdbba51c`
- 结果：0；3 次模型调用；模型直接 answer
- 任务要求：查找 October 02 的活动，并只返回 activity type
- 实际观察：打开 OpenTracks 后首屏可见多天记录；模型既没有滚动到 October 02，也没有打开记录确认类型，却把 October 08 的两条活动标题 `Powder Ride`、`Sailboat Ride` 当成 activity type 返回
- 分层判断：最早同时违反日期身份和字段身份两个硬约束（L1）：选择了错误日期，又把用户自定义标题当成类型。三步结束说明问题不是上下文容量，而是未执行筛选与字段语义核对

## 18. SportsTrackerTotalDistanceForCategoryOverInterval / seed 20260806

- episode：`SportsTrackerTotalDistanceForCategoryOverInterval_20260806_6fba2c5e`
- 结果：0；3 次模型调用；模型回答 `7485`
- 已完成部分：首屏中确实能看到 October 06 的两条 skiing 图标记录，距离分别为 4.35 mi 和 3.11 mi；日期区间与活动类别的候选选择基本正确
- 失败点：模型声称把两条距离相加并得到 7,485 米，但页面单位是 miles；4.35+3.11=7.46 miles，必须再转换并四舍五入为米。回答既没有展示正确的单位转换，也不等于页面数值的合法换算
- 分层判断：这是字段读取后的单位约束/算术变换错误（L1→推理），不是导航或记忆故障。它与 H17 共同说明，问答类 Hard 任务即使只需三次调用，也会因“类型、日期、单位”中任一槽位未对齐而归零

## 19. SportsTrackerTotalDurationForCategoryThisWeek / seed 20260806

- episode：`SportsTrackerTotalDurationForCategoryThisWeek_20260806_a575f564`
- 结果：1；3 次模型调用；模型回答 `180`，evaluator 同意
- 完成过程：模型按 cycling/mountain-biking 图标识别本周的 Intense day（1:45）和 Quick Sweat（1:15），换算为 105 与 75 分钟并相加得到 180
- 为什么能成功：两个目标记录和日期都在同一屏，类别图标一致，单位换算只涉及小时与分钟，且输出格式是单一整数；没有跨页面资源或写入动作
- 对照价值：H17、H18、H19 使用同一 app、同一三调用结构，结果却分别由日期/字段、英里转米、分钟求和决定。它们证明不能把同一 app 的成败笼统归为“模型会/不会使用 OpenTracks”，必须下钻到具体约束槽位
