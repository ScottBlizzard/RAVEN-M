# Markor 源文档覆盖提示实验：资格失败后停止

## 结论

这轮实验在第一条任务上就触发了预注册停止规则。模型确实进入了 `my_expenses.txt` 的 Markor 文档页，但没有执行任何向前纵向滑动，也没有按冻结格式写出 `Coverage scan; bottom anchor...` 的覆盖账本；下一步直接按 Home 离开文档。因为资格门要求3/3条任务在首次离开文档前至少真实向前滚动一次，这个条件已经不可逆失败，剩余两条没有继续运行。

因此，当前证据否定的是一个很具体的最小解法：仅在官方 Qwen 系统提示后追加“翻到底、记录页尾锚点与累计对象”，不足以使模型遵守长文档覆盖协议。它不否定外部执行的 coverage gate，也没有产生任何任务成功率结论。

## 冻结与执行证据

- 预注册：`05_project/docs/SOURCE_DOCUMENT_COVERAGE_MARKOR_DEV_PREREG_2026-08-08.md`。
- 冻结队列：3个既有 Markor task--seed 实例；官方基线不重跑。
- 实际启动：第1个实例 `ExpenseAddMultipleFromMarkor`, seed 20260806。
- 模型：`Qwen/Qwen3-VL-32B-Instruct`，revision `0cfaf48183f594c314753d30a4c4974bc75f3ccb`。
- 系统提示 SHA-256：`ef6a2125c5b36e55bab5bfe2e06b30fc2987423d1b11a2c394e3e510a773ae85`，与预注册一致。
- manifest snapshot SHA-256：`170510c468ead303bb588f776b7808efbcfa0c9b7378215277383c83f40f5a37`，与冻结清单一致。
- 运行目录：`runs/official_qwen_mobile/official_qwen_20260808T193239_42804705/`。
- 在人工终止前落盘15个完整 step/model-call 事件，合计56,819个提示 token 和1,778个输出 token。

## 首个不可逆失败

step 5 的点击把 Markor 从文件列表带入 `DocumentActivity`。step 6 仍在文档页，但执行的是一次 tap；step 7 的 `before` 截图仍显示长文档首屏，目标对象位于更后方，模型却执行 `press_home`，动作摘要为 “I navigated back to the home screen to prepare for opening the pro expense app.”。在首次文档退出前，向前纵向滑动数为0，覆盖账本使用次数为0。

step 7 截图 SHA-256 为 `51dd7465bc1f46900711268e500135d244c1a65d5d5b3ce56052feb055a0ed25`；原始事件文件 SHA-256 为 `ad67a24f36d13208e456075f2aa7f2e418bd25bd1c5cd6a8d546a976d7927ee8`。这两个证据共同避免了依据模型“已经阅读”的自述判断覆盖完成。

## 为什么没有把它算成任务0分

停止发生在原生 evaluator 之前，因而这条任务既不是成功，也不是可计分的普通失败。它被标记为 `QUALIFICATION_FAIL_STOP`：回答的是“提示式覆盖合同是否真正改变源文档行为”，不是“任务最终得分是多少”。继续运行剩余两条已经不能让3/3过程门重新成立，只会增加调用成本。

## 下一步边界

同一批实例上不再修改文字后重跑。下一步若继续，必须把 coverage 从建议变成外部可执行状态机：控制器识别进入源文档后，阻止 `Home`、`Back`、`answer` 或 `terminate`，直到至少执行向前扫描、记录页面指纹，并由重复页尾锚点或无新页面证据关闭 coverage 子目标。该机制应先离线测试动作拦截与状态转移，再在新实例上单独预注册；不能把这次失败 pilot 调参后包装成 held-out。

