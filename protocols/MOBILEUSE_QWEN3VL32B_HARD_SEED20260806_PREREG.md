# PF01 MobileUse × Qwen3-VL-32B 预注册

## 问题

在保持同一 Qwen3-VL-32B、同一 AndroidWorld Hard 首 seed、同一任务预算和同一 evaluator 的前提下，公开的 MobileUse 分层反思框架能否比冻结端到端基线的 4/19 更好；若不能，失败发生在哪一层。

## 冻结比较

- 比较臂：冻结端到端 Qwen 基线 4/19、总 reward 4.5，对应 329 次首 seed operator decisions。
- 实验臂：上游 commit `babec07fd0e5faa7e7bcc7d3d0ee2320f6b83347` 的六角色层级反思核心。
- 模型、revision、采样、上下文、AndroidWorld commit、19 个任务参数、顺序、native budget、evaluator 全部冻结。
- 唯一 server transport 差异是每次请求允许的图片数从 1 增加到 3。
- 不重跑、不修改旧基线，不用其轨迹、结果或标签给任何模型角色提供信息。

## 冻结算法

角色恰好为 `Operator → Environment → Reflector → Progressor → optional TrajectoryReflector`；首次完成候选触发 `AnswerAgent`（仅答案任务）与 `GlobalReflector`。全局否决后回到同一轨迹。每次 operator decision 最多三次格式解析尝试，最多执行一个原生动作。

允许动作仅为 `tap/swipe/type/back/home/answer/terminate`；坐标为 `[0,999]`。禁止直接启动应用、链接、shell/ADB、clear-text 特权、长按、等待、无障碍节点、数据库和隐藏状态。

## 诊断记录

- L0：模型请求、角色、顺序、图片 SHA256、prompt/response hash、usage、时延、重试。
- L1：原始 operator 输出、解析尝试、规范动作、拒绝原因。
- L2：动作执行、实际像素、前后截图 hash、前台包、异常。
- L3：Reflector/Progressor/TrajectoryReflector/GlobalReflector 原始输出与解析结果。
- L4：来源、对象、跨应用交接、进度证据及逐步转移；只做事后确定性提取，不反馈给 agent。
- L5：任务 evaluator、reward、模型完成候选、全局反思结论、真假完成分类。

## 零计分调用资格门

必须先通过来源哈希、六角色可达性、模型冻结、多图顺序、prompt diff 分类、动作边界与禁用动作、三次解析限制、一次一动作、全局否决恢复、信息隔离、19 条旧轨迹零生成回放、依赖/许可证审计。任一失败，不进行 H01–H19。

随后只允许一个非计分 `ContactsAddContact` 烟雾测试（seed 20260805，最多 3 次 native decisions）。只允许在首个计分调用前修复通用机械适配错误，并须重跑全部资格门与烟雾测试。

## 计分、停止与解释

- 运行顺序与预算以冻结 YAML 为准；所有 19 个任务均尝试，除非发生预注册的基础设施无效或紧急停止。
- 主要指标：full success / 19。5/19 只算单 seed 的描述性进展，不声称泛化。
- 只有成功至少 5/19、核心 source/object/handoff 指标有提升且 false-success 不恶化，才称为“合格公开框架升级”。
- 4/19 且核心机制无提升为无净收益；3/19 或更低为负向结果。
- 若发现角色泄漏 evaluator、基线标签、隐藏参数或数据库，整臂 implementation-invalid，立即停止。
- 不允许在失败 pilot 上调参后把同一任务称为 held-out；计分开始后不改代码、prompt、配置和阈值。
