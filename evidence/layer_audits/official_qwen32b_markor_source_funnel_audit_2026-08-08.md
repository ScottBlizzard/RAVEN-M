# Official Qwen Hard：Markor 源材料到最终写入的分层漏斗

## 核心结果

9 条 Markor 批量新增轨迹全部进入了源应用，但只有 8/9 真正打开指定文件；在这 8 条中，离线可见对象提取器只有 5/8 至少找回一个正确对象、3/8 找齐全部对象。5/8 在打开正确文件后到达目标应用，最终只有 2/9 把至少一个正确对象名写进目标应用，完整成功为 0/9。

这条漏斗把‘记忆没有效果’进一步拆开：主要损失在源材料覆盖与对象集合完整性，随后还有目标应用到达、字段写入和保存闭环。记忆即使忠实保存了已经看到的内容，也不能补回没有翻到的记录；而保存了正确对象名，也不等于金额、描述、分类以及最终数据库状态全部正确。

## 累积漏斗

| 条件 | 轨迹数 | 含义 |
|---|---:|---|
| 进入 Markor | 9/9 | 源应用级到达 |
| 打开指定文件 | 8/9 | 页面与文件身份正确 |
| 从已观察画面至少提取一个正确对象 | 5/9 | 局部对象捕获 |
| 从已观察画面找齐全部对象 | 3/9 | 对象集合完整 |
| 打开文件后又到达目标应用 | 5/9 | 跨应用交接 |
| 上述条件中同时有正确提取且到达目标 | 4/9 | 具备可写入的最低前提 |
| 目标应用实际写入至少一个正确对象名 | 2/9 | 可执行动作中的正确值传递 |
| AndroidWorld 完整成功 | 0/9 | 最终闭环 |

## 首个失败位置

| 首个失败位置 | 轨迹数 |
|---|---:|
| 未进入源应用 | 0 |
| 未打开指定文件 | 1 |
| 已打开文件但已观察画面未提取到正确对象 | 3 |
| 提取到对象但未到目标应用 | 1 |
| 已到目标应用但未写入正确对象名 | 2 |
| 写入部分正确对象但未完成闭环 | 2 |
| 完整成功 | 0 |

## 逐轨迹证据

| 任务 | seed | 指定文件 | 正确提取数 | 到目标应用 | 正确写入数 | 首个失败位置 |
|---|---:|---|---:|---|---:|---|
| ExpenseAddMultipleFromMarkor | 20260806 | 是 | 0 | 是 | 0 | no_correct_object_extracted_from_observed_frames |
| ExpenseAddMultipleFromMarkor | 20260807 | 是 | 0 | 否 | 0 | no_correct_object_extracted_from_observed_frames |
| ExpenseAddMultipleFromMarkor | 20260808 | 是 | 2 | 否 | 0 | destination_not_reached_after_source_capture |
| RecipeAddMultipleRecipesFromMarkor | 20260806 | 是 | 3 | 是 | 0 | correct_object_not_written_in_destination |
| RecipeAddMultipleRecipesFromMarkor | 20260807 | 是 | 3 | 是 | 0 | correct_object_not_written_in_destination |
| RecipeAddMultipleRecipesFromMarkor | 20260808 | 否 | 0 | 是 | 0 | correct_document_not_opened |
| RecipeAddMultipleRecipesFromMarkor2 | 20260806 | 是 | 1 | 是 | 1 | some_correct_object_written_but_task_not_closed |
| RecipeAddMultipleRecipesFromMarkor2 | 20260807 | 是 | 0 | 否 | 0 | no_correct_object_extracted_from_observed_frames |
| RecipeAddMultipleRecipesFromMarkor2 | 20260808 | 是 | 2 | 是 | 2 | some_correct_object_written_but_task_not_closed |

## 有效性边界

这是同一批开发轨迹的事后确定性审计，不是随机对照或 held-out 实验。‘打开指定文件’以 Markor `DocumentActivity` 为判据，并依赖 AndroidWorld 该任务初始化时写入指定文件名这一固定夹具；它比仅进入 Markor 更强，但不证明 Agent 浏览了全文。‘提取到正确对象’来自已经冻结、且资格门失败的离线提取器结果；它只能说明现有截图中可恢复的信息，不能证明在线 Agent 当时已经把这些值稳定保存。‘正确写入’只匹配目标应用中的 `type_text` 文本，不证明其余字段、保存动作或数据库状态正确。

## 可复现性

- 官方汇总输入 SHA-256：`81b798ee8561f37054354c5a41a16f6b4d7dae3fb7eebe473d5a08802876d242`
- 提取器汇总输入 SHA-256：`f988458151f02661b3dfd6a33f91cfe2cc2af1a933c7de0b345b5f66e59c331c`
- 对象转移审计输入 SHA-256：`b6e640ac72052d337ddf9a5eb961910224174d0405ad80eddba4630c4e00ae6d`
- 脚本：`05_project/scripts/audit_markor_source_funnel.py`。
