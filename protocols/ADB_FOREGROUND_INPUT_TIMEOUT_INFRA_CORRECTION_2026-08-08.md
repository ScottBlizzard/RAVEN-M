# ADB 前台输入超时基础设施修正（2026-08-08）

## 触发事实

在补跑套件 `official_qwen_20260808T142800_e697484f` 的
`RecipeAddMultipleRecipesFromMarkor2`、seed `20260808` 中，底层日志记录到：

```text
adb shell input tap 661 800
subprocess.TimeoutExpired: ... timed out after 10.0 seconds
```

`android_env` 会在 ADB 命令超时后自动重试。点击、滑动、按键和文本输入都不是幂等操作：Android 可能已经执行第一次输入，只是宿主进程没有在十秒内收到退出状态；自动重试会把一次模型动作变成两次设备动作。因此该 Recipe episode 从出现超时起属于基础设施污染，不能进入科学有效集合。

同一套件中此前已经完成的 `RetroSavePlaylist` seed `20260807` 与
`MarkorMergeNotes` seed `20260808` 在各自完整 stderr 区间内没有这类超时，保留为干净补跑结果。旧目录和旧记录不删除、不覆盖。

## 冻结修正

只修改 AndroidWorld 的动作执行超时，不修改模型、权重、采样、提示词、截图、动作协议、坐标、任务参数、原生步数预算或 evaluator：

- 将前台点击、双击、长按、滑动、导航按键、回车、文本清空和文本输入的 ADB deadline 统一从默认 10 秒提高到 60 秒；
- 目的仅是让原命令在进入底层自动重试前有足够时间返回；
- 不新增动作重试，不读取隐藏任务答案，不向模型暴露 UI tree 或 evaluator；
- 原先单独冻结的文本输入 60 秒修正被包含在这一更一般的前台输入策略中。

相关单元测试：`android_world/env/actuation_test.py`，21 项全部通过。

## 精确补跑边界

新 manifest 只包含尚无干净结果的两个唯一键：

1. `RecipeAddMultipleRecipesFromMarkor2`, seed `20260808`, native max steps `60`；
2. `RetroSavePlaylist`, seed `20260808`, native max steps `50`。

新结果明确标为 replacement，不得声称 pristine held-out；受污染的旧 Recipe episode 只保留审计用途。若 60 秒 deadline 仍触发，停止该 episode 并再次标为基础设施无效，不把部分轨迹计入最终 57 条。
