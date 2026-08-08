# L4 Transition Attestation matched diagnostic

预注册：`05_project/docs/L4_TRANSITION_ATTESTATION_MATCHED_DIAGNOSTIC_PREREG_2026-08-08.md`  
预注册最终 SHA256：`e6276e4cddae94c6ea81fff6aecdee911e611e7bb24a7e21621683d0fcbd5e07`  
运行目录：`runs/official_qwen_mobile/official_qwen_20260808T164238_6af1aaf1`  
性质：同实例配对诊断，不是 pristine held-out

## Pilot：ExpenseDeleteMultiple2/20260808

| 指标 | 官方基线 | L4 attestation v1 |
|---|---:|---:|
| evaluator reward | 0 | 0 |
| 模型调用 / Android 动作 | 34 / 34 | 34 / 34 |
| episode 耗时 | 701.9 s | 915.0 s |
| 停滞动作总数 | 29 | 25 |
| 最长连续停滞 | 27 | 23 |
| 虚假成功 | 否 | 否 |
| 终止原因 | max_steps | max_steps |
| attestation 触发 | 不适用 | 23 |

Pilot 没有通过预注册机制门。最长连续停滞只从 27 降到 23，下降 14.8%，低于要求的 50%；reward 也没有改善。模型在历史已经明确写出“没有观察到页面或 UI 转移、不要在同一状态重复同一动作”后，仍继续执行近似相同的向上 swipe，直至用满 34 步。

这个结果排除了一个过于简单的解释：重复循环不只是因为模型把自己的 `Action:` 摘要误当成事实。纠正事实记录是必要的审计措施，但它本身没有提供可行的替代动作；当模型已经误入错误页面或失去列表层级时，它可能知道“没有进展”，却仍不知道下一步应该返回、换入口还是重新定位目标。

## Frozen confirmation：OsmAndTrack/20260808

| 指标 | 官方基线 | L4 attestation v1 |
|---|---:|---:|
| evaluator reward | 0 | 0 |
| 模型调用 / Android 动作 | 120 / 120 | 49 / 48 |
| episode 耗时 | 3004.8 s | 1461.4 s |
| 停滞动作总数 | 79 | 12 |
| 最长连续停滞 | 72 | 2 |
| 虚假成功 | 否 | 是 |
| 终止原因 | max_steps | model_terminate_success |
| attestation 触发 | 不适用 | 3 |

代码、阈值、提示词、采样和历史文案在 Pilot 后均未修改。表面上看，最长停滞从 72 降到 2，调用数也从 120 降到 49；但这不通过预注册门，因为模型更早自称“已经保存四个 waypoint”，底层 evaluator 仍为 0。较短轨迹来自更早的虚假完成，不能解释为任务能力提升。

轨迹还给出一个比最终数字更关键的因果顺序。模型先在普通搜索中依次访问 Schaan、Balzers、Planken 和 Malbun，每一步页面都发生变化，所以 L4 无转移规则基本不会触发；之后它才进入 `Create new route`，却把此前四次普通搜索错误继承为“已经选择四个 waypoint”，直接点击 Done 并终止。最早错误因此是**正确地点名称绑定到了错误对象角色**，后续虚假完成只是放大结果。

## 最终结论

L4 Transition Attestation v1 整体资格失败，不扩大到更多任务：

- Pilot 没有显著减少循环，也没有改善 reward；
- confirmation 虽减少循环，却违反“不得用 reward 0 的更早虚假成功换取短轨迹”；
- 两条均无协议错误、执行失败、SSH 重连或模型请求重试，因此失败可归于干预能力边界，而不是基础设施污染。

这项负结果仍然缩小了下一步问题。只告诉模型“刚才没有进展”不足以提供恢复动作；而在 OsmAnd 中，错误入口持续产生真实页面变化，单纯 L4 规则甚至看不到上游错误。下一项若继续，应回到更早、更窄的对象角色资格：普通地点搜索只证明 `location_visited`，只有轨迹编辑器中非零 point 计数或 waypoint 列表变化才能提交 `waypoint_added`。这与笼统增加 planner/critic 不同，也不能直接从本次失败跳写成已验证的新方法；必须另立预注册和独立验证边界。
