# Markor 文档浏览覆盖与对象召回审计

## 结论

8条已打开 Markor 文档的轨迹中，8/8 没有执行任何向前浏览文档的纵向滑动，全部轨迹合计为 0 次向前滑动。整个零滑动组的对象召回为 11/21（52.38%）。

这里不存在可比较的‘已滚动组’，所以不能估计滑动动作的因果效应；但它给出了更直接的过程事实：原 Agent 从未通过纵向滑动系统遍历文档，却在多个轨迹中声称已经读完、已经筛选或没有符合条件的对象。更严格的下一步需要预注册 coverage contract，例如持续采样直到页面指纹不再前进，并在新实例上测覆盖率与对象召回。

## 逐轨迹结果

| 任务 | seed | 提取截图 | 文档唯一画面 | 向前滑动 | 找回/目标 | 完整召回 |
|---|---:|---:|---:|---:|---:|---|
| ExpenseAddMultipleFromMarkor | 20260806 | 1 | 1 | 0 | 0/2 | 否 |
| ExpenseAddMultipleFromMarkor | 20260807 | 1 | 2 | 0 | 0/2 | 否 |
| ExpenseAddMultipleFromMarkor | 20260808 | 1 | 2 | 0 | 2/2 | 是 |
| RecipeAddMultipleRecipesFromMarkor | 20260806 | 4 | 4 | 0 | 3/3 | 是 |
| RecipeAddMultipleRecipesFromMarkor | 20260807 | 1 | 1 | 0 | 3/3 | 是 |
| RecipeAddMultipleRecipesFromMarkor2 | 20260806 | 1 | 1 | 0 | 1/3 | 否 |
| RecipeAddMultipleRecipesFromMarkor2 | 20260807 | 2 | 3 | 0 | 0/3 | 否 |
| RecipeAddMultipleRecipesFromMarkor2 | 20260808 | 2 | 2 | 0 | 2/3 | 否 |

## 有效性边界

本审计只复用冻结事件日志和已经完成的提取器结果，模型调用为0。滑动方向由规范化动作坐标判定，文档画面数按 screenshot SHA-256 去重；页面哈希不同可能来自光标、滚动或其他局部变化，不能等价于覆盖了新的完整记录。零滑动轨迹仍可能在首屏看见全部目标，而有滑动轨迹也可能反复浏览同一区域。

## 可复现性

- 提取器汇总 SHA-256：`f988458151f02661b3dfd6a33f91cfe2cc2af1a933c7de0b345b5f66e59c331c`
- 逐轨迹事件路径与事件 SHA-256 均保存在 JSON 结果中。
- 脚本：`05_project/scripts/audit_markor_document_coverage.py`。
