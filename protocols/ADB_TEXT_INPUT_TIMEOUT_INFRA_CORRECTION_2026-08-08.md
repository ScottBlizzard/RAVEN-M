# ADB 非幂等文本输入超时修正

冻结时间：2026-08-08 13:40（Asia/Hong_Kong）

## 现象

AndroidWorld 的普通 `input_text` 会逐词调用 ADB。当前 Windows 控制端在 10 秒等待上限处出现了 `subprocess.TimeoutExpired`，而底层 ADB controller 会重启服务并再次执行同一个命令。文本输入不是幂等操作：第一次命令即使被主机判为超时，也可能已经向应用写入全部或部分文字；自动重试会把同一词再次追加，形成查询或文件名重复。

本轮明确观察到：

- `MarkorTranscribeVideo/20260807` 的文件名输入 `recording_41__rwef_transcription` 出现 10 秒超时；
- `OsmAndTrack/20260807` 的 `Planken,` 输入出现 10 秒超时，随后界面出现额外 `Plank` 前缀，模型进入长时间删除循环。

因此这两条替补记录不能作为干净的模型能力结果。它们保留在原目录供审计，但必须从科学有效集合排除并在修正后重跑。

## 唯一修正

不改变动作、文本、坐标、模型、采样、任务参数或 evaluator，仅将 AndroidWorld 普通文本输入调用的 `timeout_sec` 从 10 提高到 60。目的是让同一 ADB 命令有足够时间完成，避免 controller 对非幂等输入进行静默重试。

若提高到 60 秒后仍出现超时，该 episode 继续标为基础设施无效；不得依据 reward 调整超时，也不得从多次结果中挑分数较高者。

## 污染边界

- 无相应超时日志的 `ExpenseAddMultipleFromMarkor/20260807` 替补保留；
- 上述两条受影响替补排除并重跑；
- 尚未开始的后续替补在新进程加载修正后运行；
- 旧目录、旧截图、旧 evaluator 与旧日志均不删除、不覆盖。
