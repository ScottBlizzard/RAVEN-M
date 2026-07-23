# 课题三官方要求可追溯表

来源：`00_admin/assessment/夏令营考核题目.pdf`

| 官方要求 | 本仓库准备内容 | 后续实际证据 | 状态 |
|---|---|---|---|
| 调研 GUI/Mobile-use/MLLM Agent 记忆机制 | 43 条文献记录、42 份已校验 PDF、BibTeX、周晟/Eagle Lab 资料 | 15 项 related-work matrix 与 2026-07-23 overlap checkpoint | 已完成（ExpAct 原文因 OpenReview 403 明示缺失） |
| Qwen3-VL-32B-Instruct baseline | 精确 revision、BF16 四卡后端、AndroidWorld 官方代码 | G3 B0 与 G4 B0/B1/B2/B3 可复现实跑日志及机器审计 | 已通过非 Hard 开发门 |
| AndroidWorld Hard task 评测 | 官方 task-list 快照、19-task manifest、原生预算、三组 seed | 协议审计 19/19 通过；计分实验须在 G7 后进行 | 待 G7 后冻结，禁止提前运行 |
| 多智能体记忆框架 | Planner/Executor/Memory/Critic、类型化 memory、证据路由与失效 | 代码、schema、append-only events、角色调用审计 | 已实现；v8–v11 的 infra/角色边界均保留并修复，G7 以完整 v12 重跑 |
| 历史、状态摘要、经验复用、多轮规划 | B0 raw、B1/B2 sliding、B3 summary、S0/M0 结构化 memory | G4 公平基线已通过；S0/M0 与组件消融待完成 | 部分完成 |
| 成功率、提升百分比、案例分析 | 冻结 TSR、配对差异、cluster bootstrap、Wilson、McNemar 协议 | 主结果表、统计区间、成功/失败与 memory-harm 案例 | 正式 Hard 实验待运行 |
| 可选 Medium task | 只登记，不进入第一阶段 Must | 核心完成后的可选扩展 | Optional |
| 完整代码与实验报告 | 独立本地运行时、资料锁、代码/config/schema/audit 目录 | 最终 source/config/log/report/reproduction guide | 主体已建，最终交付待正式实验 |

## 优先级原则

1. 考核原文高于 GPT 生成的 master plan。
2. P0 文献与官方环境资料高于扩展论文。
3. baseline 和同协议比较高于复杂 memory module。
4. 可复现原始证据高于装饰性 demo 或额外 benchmark。
