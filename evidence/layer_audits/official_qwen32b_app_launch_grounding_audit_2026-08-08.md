# Official Qwen Hard：首个任务相关应用进入审计

## 结论

在冻结的 57 条官方 Qwen3-VL-32B Hard 轨迹中，49 条第一次离开桌面后就进入正确的任务相关应用，6 条先进入错误应用但随后恢复，2 条从未进入任务相关应用。

因此，应用入口定位确实是一个可测的早期失败层，但不是总体 0/低成功率的主因：正确首入组成功 6/49 (12.24%)，错误后恢复组成功 1/6 (16.67%)，未进入组成功 0/2 (0.00%)。大量失败发生在 Agent 已经进入正确应用之后。

## 冻结口径

- 数据：`reports/official_qwen32b_full_hard_combined_corrected_final.json` 中的 57 条科学合格轨迹。
- 首个任务相关应用：由任务文字显式要求的第一个源应用或目标应用决定；例如先从 Gallery/Markor/VLC 读取信息的任务，把该源应用视为正确入口。
- `correct_first`：第一次进入的非 Launcher/SystemUI 包就是预期包。
- `wrong_then_recovered`：先进入其他应用，后来才进入预期包。
- `never_reached`：整条轨迹均未进入预期包。
- 本审计不调用模型、不改变旧结果，也不重新判定任务成功。

## 汇总

| 类别 | 条数 | 成功 | 解释 |
|---|---:|---:|---|
| 首次即正确 | 49 | 6 | 应用入口不是该轨迹的首要瓶颈 |
| 点错后恢复 | 6 | 1 | 视觉图标定位先失败，但控制器后来纠正 |
| 始终未进入 | 2 | 0 | 启动层本身足以导致任务失败 |

## 异常轨迹

| 任务 | seed | 类别 | 首个错误包 | 进入正确包的 step | reward |
|---|---:|---|---|---:|---:|
| OsmAndTrack | 20260807 | wrong_then_recovered | com.flauschcode.broccoli | 7 | 0 |
| OsmAndTrack | 20260808 | wrong_then_recovered | com.flauschcode.broccoli | 6 | 0 |
| RecipeAddMultipleRecipesFromImage | 20260806 | never_reached | None | 未进入 | 0 |
| RecipeAddMultipleRecipesFromImage | 20260807 | never_reached | None | 未进入 | 0 |
| RecipeDeleteMultipleRecipesWithConstraint | 20260808 | wrong_then_recovered | com.android.chrome | 7 | 0 |
| RetroSavePlaylist | 20260808 | wrong_then_recovered | com.android.stk | 5 | 0 |
| SimpleCalendarAddOneEvent | 20260807 | wrong_then_recovered | com.google.android.deskclock | 6 | 1 |
| SportsTrackerActivitiesOnDate | 20260807 | wrong_then_recovered | com.dimowner.audiorecorder | 6 | 0 |

## 解释边界

这是一项 post-hoc 机制审计，不是随机化干预。它能够回答“最早是否进入正确应用”，不能证明消除入口错误会提高多少最终成功率。尤其是点错后恢复组只有 6 条，而且其中成功的日历轨迹说明早期错误并非必然失败。后续分层实验应把‘进入正确应用’作为 L1/L2 的观察量，而不是把它误当作任务完成代理。

更重要的是，两条始终未进入任务应用的轨迹都属于 `RecipeAddMultipleRecipesFromImage`，表现为在 Launcher 上重复上滑。这是明确的早期循环；而另外 55 条均最终进入了正确应用，说明后续研究应优先分析应用内控件定位、状态更新、跨应用副作用和完成验证。

## 可复现性

- 输入 JSON SHA-256：`81b798ee8561f37054354c5a41a16f6b4d7dae3fb7eebe473d5a08802876d242`
- 逐轨迹事件文件：57 个，每个 SHA-256 写入配套 JSON。
- 生成脚本：`05_project/scripts/audit_app_launch_grounding.py`。
