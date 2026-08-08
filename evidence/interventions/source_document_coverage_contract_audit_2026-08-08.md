# Source coverage contract audit

这是对冻结轨迹的零模型调用机械审计，不改变任何实验结果。

| 任务 | 打开文档 | 文档内向前滑动 | 首次宣称到底的步数 | 后续页面变化推翻到底判断 | 终止原因 |
|---|---:|---:|---:|---:|---|
| ExpenseAddMultipleFromMarkor | 是 | 53 | — | 否 | max_steps |
| RecipeAddMultipleRecipesFromMarkor | 否 | 0 | — | 否 | max_steps |
| RecipeAddMultipleRecipesFromMarkor2 | 是 | 11 | 12 | 是 | source_stage_exit |

## 结论

一次无明显变化的向前滑动不足以证明文档到底：冻结轨迹中有一次到底判断，但它被后续同方向滑动产生的大幅页面变化直接推翻。因此，覆盖契约至少需要正确文件、已验证起点、单调向前推进和重复或独立的终点确认。

输入 aggregate.json SHA-256：`90149ff0a31c2bff8a8b1599d8348374044f595e23045f459ece2d100312c54c`
