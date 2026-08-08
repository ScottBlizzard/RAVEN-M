# Official Qwen Hard：预期对象标识符跨应用落地审计

## 结论

5 类多对象新增任务、15 条轨迹的 AndroidWorld 隐藏参数共包含 42 个应创建对象。其中 9/15 条轨迹到达目标应用，对应 26 个应创建对象；实际 type_text 命令中只出现 3 个规范化后匹配的正确对象标识符，覆盖率为 3/26 (11.54%)。

只有 2 条轨迹输入过至少一个正确对象名；5 条虽然在目标应用开始输入，却没有输入任何属于该 seed 的预期对象名；2 条到达目标应用但没有执行目标内文本写入。这说明对象集合在来源感知、筛选或跨页面保持阶段已经大量失真。

## 冻结口径

- 任务：两类 Expense 新增任务与三类 Recipe 新增任务，每类 3 个 seeds。
- Ground truth：`episode_start.task_params.row_objects` 中的 expense `name` 或 recipe `title`；这些隐藏参数仅用于事后审计，运行时没有提供给模型。
- 观察：目标应用前台状态下实际执行的 `type_text` 文本。
- 匹配：Unicode NFKC、忽略大小写和标点后的标识符子串匹配；例如两种引号写法不构成差异。
- 本审计只检查对象标识符是否进入动作流，不检查金额、日期、描述、方向、保存动作或数据库最终状态。

## 逐层漏斗

| 阶段 | 轨迹数 | 完整成功 |
|---|---:|---:|
| 未到目标应用 | 6 | 0 |
| 到达但未执行文本写入 | 2 | 0 |
| 已写入，但对象集合全错 | 5 | 0 |
| 至少写入一个正确对象名 | 2 | 0 |

## 出现过的正确标识符

| 任务 | seed | 正确标识符 | 目标应用中的全部输入 |
|---|---:|---|---|
| RecipeAddMultipleRecipesFromMarkor2 | 20260806 | Zucchini Noodles with Pesto | Zucchini Noodles with Pesto；This recipe features zucchini noodles tossed in a creamy pesto sauce. Ingredients: zucchini, basil, pine nuts, parmesan, olive oil. Instructions: Spiralize zucchini, blend basil, pine nuts, parmesan, and olive oil for pesto, then toss together. |
| RecipeAddMultipleRecipesFromMarkor2 | 20260808 | Cauliflower Fried "Rice"；Spicy Tuna Wraps | Cauliflower Fried 'Rice'；This recipe takes 10 mins to prepare. Main ingredients: cauliflower, rice, soy sauce, eggs, vegetables.；Spicy Tuna Wraps；This recipe takes 10 mins to prepare. Main ingredients: tuna, spicy mayo, lettuce, avocado, nori sheets. |

## 解释

这个结果否定了一个容易混淆的说法：这批任务并不是普遍已经‘把正确内容记住，只是最后没保存’。至少从可执行动作看，多数轨迹没有把正确对象标识符带到目标应用；有些轨迹甚至输入了与该 seed ground truth 完全无关的对象。结构化记忆若要发挥作用，首先必须提高来源对象的可核验捕获和全量覆盖，随后才有资格讨论目标绑定与保存闭环。

另一方面，3个正确标识符仍未带来任何完整成功，也说明 object-name transfer 只是必要子条件。两条有匹配的轨迹都只覆盖了部分对象，而且金额、描述、方向、字段和保存状态没有同时闭合。后续应以 object-level recall、field-level exactness、saved-object count 和 evaluator reward 四级指标报告，而不是只问 memory 里有没有一段看似正确的自然语言。

## 有效性边界

这是对实际 `type_text` 动作的严格、可复现下界。它可能漏掉通过非文本控件选择、预填字段或其他输入通道设置的标识符；但这批创建任务的名称/标题通常需要文本输入。标识符匹配也不能证明对应金额、描述等字段正确，更不能替代原生 evaluator。

## 可复现性

- 输入 JSON SHA-256：`81b798ee8561f37054354c5a41a16f6b4d7dae3fb7eebe473d5a08802876d242`
- 逐轨迹 expected identifiers、目标内 type_text、规范化匹配、事件路径与事件 SHA-256 均写入配套 JSON。
- 生成脚本：`05_project/scripts/audit_expected_object_transfer.py`。
