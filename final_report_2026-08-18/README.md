# 夏令营最终汇报总结包

日期：2026-08-19
状态：总结性材料；不修改任何既有实验身份、分数或正式 verdict。

## 一句话结论

本项目最可靠的完整系统结果仍是 R2 的 6/19；R15 暴露“成功与组件因果信用可以错位”，A4-v2 又证明记忆方法可能在 donor coverage 这一前置条件上就被阻断，因此分析框架从组件级比较推进为 P0+L0-L6：先审方法是否有机会成立，再追踪任务事实与行为结果。

## 建议阅读顺序

1. [`PRO_FINAL_REPORT_RETHINK.md`](PRO_FINAL_REPORT_RETHINK.md)：Pro 对全部证据、故事线、逐页方案与答辩边界的完整重审。
2. [`presentation/GUI_Agent记忆机制探索_夏令营最终汇报_v9_最新证据版.pdf`](presentation/GUI_Agent记忆机制探索_夏令营最终汇报_v9_最新证据版.pdf)：纳入 A4-v2 最新封存结果的 12 页、15 分钟正式汇报；先讲做了什么和核心结果，再由 R15 与 donor coverage 证据推出 P0+L0-L6，最后回看旧实验并定位文献坐标。
3. [`presentation/index.html`](presentation/index.html)：新版可编辑、可浏览器播放的演示稿源文件。
4. [`PROJECT_SYNTHESIS_FOR_PRO.md`](PROJECT_SYNTHESIS_FOR_PRO.md)：完整故事、数据、结论边界与可检验问题。
5. [`PRO_RETHINK_PROMPT.md`](PRO_RETHINK_PROMPT.md)：交给 Pro 的复审任务书。
6. [`evidence_snapshot/A_SERIES_INFORMATION_LINEAGE_AUDIT_2026-08-18.md`](evidence_snapshot/A_SERIES_INFORMATION_LINEAGE_AUDIT_2026-08-18.md)：R15 Browser 发现后的 A0–A12 离线重审快照。
7. [`evidence_snapshot/A4V2_DONOR_COVERAGE_SNAPSHOT_2026-08-19.md`](evidence_snapshot/A4V2_DONOR_COVERAGE_SNAPSHOT_2026-08-19.md)：24 个 donor slot 的正式终止结果、结论边界与 P0 扩展依据。

旧版 14 页 PDF `presentation/GUI_Agent记忆机制探索_夏令营最终汇报_v4_R15封存版.pdf` 保留用于版本追溯，不再作为首选汇报稿。

## 冻结事实

| 对象 | 结果 | 可支持的结论 |
|---|---:|---|
| 三 seed 基线 | 7/57；各 seed 为 4/19、2/19、1/19 | 模型存在明显随机波动；单 seed 结果必须谨慎解释 |
| A1 | 5/19 | 简单工作记忆有正信号，但成本显著增加 |
| A2 | 0/19 | 记忆频繁写入和读取不等于收益 |
| R2 | 6/19 | 当前最强完整结果；相对 A1 为 1 胜、0 负，且 token 与耗时下降 |
| R15 Browser | 1/1 | 原始历史保留关键值与成功同时出现；新增组件读取为 0，不能归因给组件 |
| R15 固定七题 | 描述性 4/7 | 不是通用升级；Browser 解释不能直接外推到导航、恢复和完成验证问题 |
| A4-v2 donor acquisition | 24 个有效 slot：6 成功、18 科学失败；3/7 路线达标 | 可复用 donor coverage 是设置相关的上游瓶颈；不能声称 AWM 普遍无效 |

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

## V9 汇报主线

最终汇报不按实验编号流水展开，而按认识变化组织：

1. 先用一页交代本课题完成的三层工作：可信评测、横纵向设计探索、轨迹归因。
2. 用 A0 三 seed 建立可审计基线，明确无显式持久账本时的能力与方差。
3. 正面讲清 A0→A1→R2：从引入结构化任务账本，到压缩为最小 verified/pending 状态。
4. 展示同时开展的横向机制探索，并用 A4-v2 的 24 个 donor slot 证明论文方法还可能受 donor coverage 前置条件限制。
5. 把 R2 的 6/19 作为完整系统主结果，与 MobileUse Hard 消融作有边界的数值/复杂度坐标。
6. 拆解 R2 剩余 13 题，让“为什么针对性补丁仍未涨分”成为自然悬念。
7. 合并讲清 R15 Browser 正例与七题作用域，由“组件未读但任务成功”的矛盾推出新的审计起点。
8. 此时才正式介绍 P0+L0-L6：先审 donor / opportunity 等方法前置条件，再追任务事实、动作分叉和结果。
9. 用新框架回看 R5-R12 的相同 0 分为何包含不同证据，并与 AWM、MemGUI-Bench 比较分析尺度。
10. 明确回顾性诊断已有证据，donor coverage 与最早断点能否前瞻预测有效干预仍待验证。

## 禁止越界的表述

- 不把 R15 称为最强系统或 7/7 系统。
- 不把 Browser 的一次成功归因于新增组件。
- 不把 R15 相对 R2 的三项回归解释为组件因果伤害。
- 不把 A3/A4/A5 的最小移植失败扩大为原论文无效。
- 不把 A4-v2 的 donor coverage blocker 表述为 AWM 普遍无效或七题得分。
- 不声称信息保真、事实追踪或信息谱系概念首次出现。
- 不使用“论文级”“重大创新”等自我评价；只呈现差异、证据和可检验预测。

## 当前最值得继续验证的问题

在控制模型、seed、起始状态和成本后，“最早信息断点”是否比记忆激活率更能预测应该采用哪类干预？至少需要分别验证：

- Browser 类任务：选择性事实保真，而不是全量历史保留；
- Calendar/Recipe 类任务：无进展检测、路线恢复与预算感知；
- OsmAnd 类任务：结果动作之前的可见证据核验；
- 机制归因：匹配的 read-disabled / intervention ablation；
- 稳健性：多 seed、多模型和完整 19 题复现。
