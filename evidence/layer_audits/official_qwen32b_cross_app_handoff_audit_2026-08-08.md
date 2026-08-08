# Official Qwen Hard：跨应用交接漏斗审计

## 核心结果

冻结的 57 条官方式 Hard 轨迹中，有 9 类、27 条任务明确要求先在一个源应用读取或选择信息，再到另一个目标应用完成操作。按 foreground package 做零调用回放后：2 条没有进入源应用，9 条进入源应用但没有到达目标应用，16 条到达了目标应用。

27 条中完整成功 0/27；到达目标应用的 16 条中，完整成功仍为 0，只有 2 条获得正奖励，且都是完成一半要求的 Markor--SMS 任务。因此跨应用到达是必要条件，但远不足以保证目标字段绑定和最终闭环。

## 冻结定义

- 任务集合只包含任务文字明确要求 source→destination 的 9 类任务，每类 3 个 seeds。
- `source_not_reached`：轨迹未出现源应用 foreground package。
- `source_only`：出现源应用，但未出现目标应用 foreground package。
- `destination_reached`：源应用和目标应用都曾成为 foreground package。
- package 出现只证明应用层到达，不证明进入正确页面、读取正确字段或写入正确对象。
- 本审计不调用模型、不修改 reward，也不把 package reach 当作任务成功。

## 漏斗

| 阶段 | 条数 | 完整成功 | 正奖励 |
|---|---:|---:|---:|
| 未进入源应用 | 2 | 0 | 0 |
| 只到源应用 | 9 | 0 | 0 |
| 已到目标应用 | 16 | 0 | 2 |

## 任务级结果

| 任务 | 到达目标/3 | 正奖励/3 | 完整成功/3 |
|---|---:|---:|---:|
| BrowserMultiply | 3/3 | 0/3 | 0/3 |
| ExpenseAddMultipleFromGallery | 2/3 | 0/3 | 0/3 |
| ExpenseAddMultipleFromMarkor | 1/3 | 0/3 | 0/3 |
| MarkorCreateNoteAndSms | 3/3 | 2/3 | 0/3 |
| MarkorTranscribeVideo | 1/3 | 0/3 | 0/3 |
| RecipeAddMultipleRecipesFromImage | 1/3 | 0/3 | 0/3 |
| RecipeAddMultipleRecipesFromMarkor | 3/3 | 0/3 | 0/3 |
| RecipeAddMultipleRecipesFromMarkor2 | 2/3 | 0/3 | 0/3 |
| SaveCopyOfReceiptTaskEval | 0/3 | 0/3 | 0/3 |

## 机制解释

第一道漏斗发生在跨应用导航：11/27 没有抵达目标应用，其中2条连源应用也未进入。第二道漏斗发生在目标应用内部：16条已经抵达目标应用，但14条仍为0奖励，另外2条只完成短信发送而没有同时满足 Markor 笔记要求。也就是说，增加更长记忆既不能自动打开目标应用，也不能自动保证记住的值被写到正确对象。

这个结果与结构化记忆方向的关系不是‘记录正确就会成功’，而是把问题拆成三个分别可测的条件：来源值是否捕获、目标应用/对象是否保持、值是否真正写入并由 evaluator 闭环。本审计只测到中间的应用级 reach；页面角色、字段身份和写入事实仍需要下一层证据。

## 有效性边界

这是 post-hoc 观察，不是把同一任务随机分配到‘成功交接’和‘失败交接’的因果实验。foreground package 还可能高估真正到达：Agent 可以打开正确 App 却停在错误页面。因此 16/27 应理解为应用级上界，而不是跨应用信息传递成功率。

## 可复现性

- 输入 JSON SHA-256：`81b798ee8561f37054354c5a41a16f6b4d7dae3fb7eebe473d5a08802876d242`
- 每条轨迹的 source/destination package、首次到达 step、事件路径和事件 SHA-256 均写入配套 JSON。
- 生成脚本：`05_project/scripts/audit_cross_app_handoff.py`。
