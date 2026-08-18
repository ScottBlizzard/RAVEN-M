# 夏令营最终汇报总结包

日期：2026-08-18  
状态：总结性材料；不修改任何既有实验身份、分数或正式 verdict。

## 一句话结论

本项目最可靠的完整系统结果仍是 R2 的 6/19；R15 的价值不是成为更强系统，而是由 Browser 正轨迹暴露“信息可能在进入记忆前丢失”，再由固定七题 4/7 补测限定这一解释的适用范围，进而把研究从组件级比较推进到任务事实的逐阶段归因。

## 建议阅读顺序

1. [`PROJECT_SYNTHESIS_FOR_PRO.md`](PROJECT_SYNTHESIS_FOR_PRO.md)：完整故事、数据、结论边界与可检验问题。
2. [`PRO_RETHINK_PROMPT.md`](PRO_RETHINK_PROMPT.md)：可直接交给新 Pro 的复审提示。
3. [`presentation/GUI_Agent记忆机制探索_夏令营最终汇报_v4_R15封存版.pdf`](presentation/GUI_Agent记忆机制探索_夏令营最终汇报_v4_R15封存版.pdf)：14 页、15 分钟正式汇报。
4. [`presentation/index.html`](presentation/index.html)：可编辑、可浏览器播放的演示稿源文件。
5. [`evidence_snapshot/A_SERIES_INFORMATION_LINEAGE_AUDIT_2026-08-18.md`](evidence_snapshot/A_SERIES_INFORMATION_LINEAGE_AUDIT_2026-08-18.md)：R15 Browser 发现后的 A0–A12 离线重审快照。

## 冻结事实

| 对象 | 结果 | 可支持的结论 |
|---|---:|---|
| 三 seed 基线 | 7/57；各 seed 为 4/19、2/19、1/19 | 模型存在明显随机波动；单 seed 结果必须谨慎解释 |
| A1 | 5/19 | 简单工作记忆有正信号，但成本显著增加 |
| A2 | 0/19 | 记忆频繁写入和读取不等于收益 |
| R2 | 6/19 | 当前最强完整结果；相对 A1 为 1 胜、0 负，且 token 与耗时下降 |
| R15 Browser | 1/1 | 原始历史保留关键值与成功同时出现；新增组件读取为 0，不能归因给组件 |
| R15 固定七题 | 描述性 4/7 | 不是通用升级；Browser 解释不能直接外推到导航、恢复和完成验证问题 |

R15 六个新任务的正式结果位于：

- [`../evidence/a1r15_stitched_continuation/A1R15_STITCHED_CONTINUATION_FINAL_RESULT_2026-08-18.md`](../evidence/a1r15_stitched_continuation/A1R15_STITCHED_CONTINUATION_FINAL_RESULT_2026-08-18.md)
- [`../evidence/a1r15_stitched_continuation/A1R15_STITCHED_CONTINUATION_FINAL_RESULT_2026-08-18.json`](../evidence/a1r15_stitched_continuation/A1R15_STITCHED_CONTINUATION_FINAL_RESULT_2026-08-18.json)

R2 正式结果位于：

- [`../evidence/a1r2/A1R2_CVP_SCORED_RESULT_2026-08-14.md`](../evidence/a1r2/A1R2_CVP_SCORED_RESULT_2026-08-14.md)

## R15 七题补测的正确解释

六个新任务得分为 3/6：Expense、Retro、Sports 成功；Calendar、Recipe、OsmAnd 失败。加上旧 Browser 成功，描述性 stitched panel 为 4/7。

- 新六题中，新增寄存器机制为 0 opportunity、0 activation、0 append、0 read、0 use。
- 三个成功属于组件静默成功，不能归因于新增机制。
- 相对历史 R2 六题为 0 个新增胜、3 个持平、3 个回归。
- 新六题共 144 calls、140 actions、586,178 tokens；相对 R2 六题多 180,350 tokens。
- 该比较不是同时期匹配消融，起始 UI 和采样轨迹存在差异，因此不能把回归因果归给 R15 组件。

三项回归分别暴露不同瓶颈：

1. Calendar：无效首步后选择逐日导航，步数预算耗尽仍未保存——路线恢复与预算管理问题。
2. Recipe：未识别并打开 Broccoli，重复滚动且没有无进展恢复——感知、状态变化检测与重定位问题。
3. OsmAnd：把 Add/favorite 误认为 Marker，基于不足证据宣告完成——完成状态与 evaluator 对齐问题。

因此，4/7 不支持把 Browser 的单题解释外推为通用提升，但它支持一个更一般的研究策略：先定位最早失效环节，再判断应该修改记忆、恢复策略还是完成验证。

## 汇报主线

最终汇报不按实验编号流水展开，而按认识变化组织：

1. 建立可信实验基础，区分系统结果、机制激活和因果归因。
2. 横向比较多类记忆，纵向得到 R2 的 6/19 完整结果。
3. 用多维比较解释大量负结果为何仍有科学价值。
4. R15 Browser 暴露历史变换前后的信息断裂。
5. 固定七题 4/7 将 R15 限定为诊断线索，而不是通用系统升级。
6. 提出任务事实的信息谱系：像素 → 原始表述 → 历史变换 → 记忆写入 → 读取 → 动作分叉 → evaluator。
7. 与现有代表工作形成尺度互补：系统级实验回答“是否有效”，事实级谱系进一步解释“为何在这里有效或失效”。

## 禁止越界的表述

- 不把 R15 称为最强系统或 7/7 系统。
- 不把 Browser 的一次成功归因于新增组件。
- 不把 R15 相对 R2 的三项回归解释为组件因果伤害。
- 不把 A3/A4/A5 的最小移植失败扩大为原论文无效。
- 不声称信息保真、事实追踪或信息谱系概念首次出现。
- 不使用“论文级”“重大创新”等自我评价；只呈现差异、证据和可检验预测。

## 当前最值得继续验证的问题

在控制模型、seed、起始状态和成本后，“最早信息断点”是否比记忆激活率更能预测应该采用哪类干预？至少需要分别验证：

- Browser 类任务：选择性事实保真，而不是全量历史保留；
- Calendar/Recipe 类任务：无进展检测、路线恢复与预算感知；
- OsmAnd 类任务：结果动作之前的可见证据核验；
- 机制归因：匹配的 read-disabled / intervention ablation；
- 稳健性：多 seed、多模型和完整 19 题复现。
