# MobileUse 决策文档机械纠错冻结

日期：2026-08-09  
性质：只纠正上游代码字段与命名，不改变方法、假设、任务、预算或判定门。

1. 决策文档中的“MobileUseMultiAgent”是描述性名称；官方 AndroidWorld 注册类型为 `MultiAgent`。
2. `trajectory_reflector.interval: 5` 对应官方字段 `evoke_every_steps: 5`。
3. `trajectory_reflector.cold_start: 3` 对应官方字段 `cold_steps: 3`。
4. `trajectory_reflector.max_fail: 3` 对应官方字段 `max_fail_count: 3`。
5. `reflect_on_demand: false` 只关闭基于 action logprob 的按需跳过逻辑；官方代码每步将 `skip_reflector` 初始化为 `False`，因此常规动作后仍会调用 `Reflector`。
6. 官方 AndroidWorld 模板启用的角色恰好为 `Operator`、`AnswerAgent`、`Reflector`、`TrajectoryReflector`、`GlobalReflector`、`Progressor`；`Planner`、`NoteTaker` 和主动知识模块均未启用。
7. 官方 `Operator` 默认 `include_a11y_tree: false`，本实验继续禁用无障碍树。
8. 上游 `for range(max_action_retry)` 在最后一次解析失败后仍会生成一个不再解析的额外回复；这会使 `max_action_retry: 3` 产生 4 次生成。为落实已冻结的“原始生成 + 最多两次修复生成”上限，适配层在第三次无效解析时直接返回 `action=None`，记录 `operator_output_invalid`，不执行动作，也不发起第 4 次生成。
9. 上游 `iter_run` 只在 `FINISHED` 时停止，对 `terminate(failure)` 设置的 `FAILED` 状态仍会继续循环。适配层保留原始 `step()` 六角色调度，但由外层按 native budget 驱动，并在 `FINISHED` 或 `FAILED` 时停止；异常直接上抛并判为无效运行，不吞掉后继续计分。

这些纠错在任何模型生成前完成并冻结。
