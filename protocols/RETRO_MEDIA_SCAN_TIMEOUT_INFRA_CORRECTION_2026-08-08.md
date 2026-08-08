# Retro Music media-scan timeout：基础设施修正冻结

冻结日期：2026-08-08（Asia/Hong_Kong）  
适用范围：仅用于替换 `RetroSavePlaylist/20260807` 与 `RetroSavePlaylist/20260808` 的零调用基础设施无效记录。

## 观察到的问题

两个独立 task seed 都在 `task.initialize_task()` 阶段执行
`android.intent.action.MEDIA_SCANNER_SCAN_FILE` 时超过 AndroidWorld 默认的 10 秒 ADB
等待上限。两条记录均没有模型调用、动作或 evaluator reward，终止原因为
`infrastructure_or_controller_error`。stdout 已显示广播成功发出，但 Windows 主机上的
`am broadcast` 未在 10 秒内返回。

## 唯一修正

在 `retro_music._scan_music_directory()` 调用 `send_android_intent()` 时显式设置
`timeout_sec=60`。不跳过媒体扫描，不吞掉异常，也不改变广播 action、data URI 或
后续 app reset。

### 60 秒复核与第二阶段修正

2026-08-08 14:18 的精确替补证明该 emulator 会在广播已经输出
`Broadcasting...` 后仍超过 60 秒不返回。按下述预先冻结的停止规则，这条继续判为
0-generation 基础设施无效，不计入模型结果；单纯继续放宽等待上限已经没有意义。

第二阶段保持同一 `MEDIA_SCANNER_SCAN_FILE` action 与 Music data URI，但在设备端
后台启动广播，避免主机 ADB 对已投递的长等待命令反复重试。随后轮询只读的
MediaStore `_display_name`：只有全部冻结 MP3 文件均已出现才允许进入第一次模型
调用，最长 30 秒。该就绪门验证的是任务真实前置条件，不向模型暴露 evaluator、
目标答案或隐藏界面信息。若文件未全部出现仍然抛出异常并保持基础设施无效。

## 保持不变

- Qwen3-VL-32B 权重、revision、vLLM 与采样；
- 官方 Qwen Mobile Agent 提示词、消息结构和工具 schema；
- 冻结 task seed、参数、goal 与原生动作预算；
- AndroidWorld task 初始化内容与 evaluator；
- 所有旧 episode 和旧统计文件。

## 有效性与停止规则

- 旧两条零调用记录永久标为基础设施无效，不计模型成功率；
- 新补跑若初始化成功，才可形成新的科学有效 episode；
- 60 秒内仍超时则继续标基础设施无效，不得吞错后强行进入模型调用；
- 不因补跑 reward 调整该超时值，也不挑选较高分结果。

## 第三阶段：目录广播不刷新第二批文件

`RetroSavePlaylist/20260807` 证明“设备端异步广播 + MediaStore 就绪轮询”本身可行；但随后
`RetroSavePlaylist/20260808` 在模型零调用阶段暴露了更窄的问题：15 个新 MP3 已全部存在于
`/storage/emulated/0/Music`，MediaStore 却只保留上一条任务的旧行。30 秒内新文件一个也没有被目录 URI 发现，因此该 episode 按停止规则继续标为基础设施无效。

零生成诊断进一步验证：对单个文件发送
`MEDIA_SCANNER_SCAN_FILE`（例如 `Moments.mp3`）后，对应 MediaStore 行会出现；对已经被删除的旧文件发送同一单文件扫描后，旧行会消失。因此第三阶段冻结为：

- 不再依赖已经索引过的 Music 目录 URI；
- 初始化时先只读查询 Music 目录现有 MediaStore 行；
- 对已经不存在且不属于当前实例的旧文件逐文件异步扫描，以清除陈旧索引；
- 对当前实例全部 MP3 逐文件异步扫描，文件名使用 URI 百分号编码；
- 轮询直到所有当前文件出现且旧文件行消失，仍保留 30 秒就绪边界；
- 任一前置条件失败仍抛出异常，不进入模型调用。

这仍然只是恢复 AndroidWorld 原任务应有的媒体初始化状态，不改变模型可见信息、任务难度或 evaluator。相关 Retro 与前台动作测试共 23 项通过。最终只精确重跑尚无干净结果的 `RetroSavePlaylist/20260808`。

第一次逐文件代码验证仍在零调用阶段失败。审计表明策略本身没有失败，而是命令被错误包装成
`adb shell sh -c <broadcast>`：ADB 的参数转发使 `<broadcast>` 未可靠作为 `sh -c` 的单一命令字符串执行。修正为与真实手工验证一致的 `adb shell <完整后台广播命令>` 后，先对两个原先缺失的文件做零生成复核：`Reflections.mp3` 与带空格的 `Bright Lights.mp3` 均在 8 秒内出现在 MediaStore。该修正不改变扫描 action，只去掉多余的 shell 包装；23 项测试再次通过。随后仍只重跑同一个最终键。
