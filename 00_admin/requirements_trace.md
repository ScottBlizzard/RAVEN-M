# 课题三官方要求可追溯表

来源：`00_admin/assessment/夏令营考核题目.pdf`

| 官方要求 | 本仓库准备内容 | 后续实际证据 | 状态 |
|---|---|---|---|
| 调研 GUI/Mobile-use/MLLM Agent 记忆机制 | 论文清单、PDF、BibTeX、阅读模板、周晟/Eagle Lab 对齐资料 | 文献综述与 related-work matrix | 资料准备中 |
| Qwen3-VL-32B-Instruct baseline | Qwen 官方代码、model card、mobile-agent cookbook；AndroidWorld 官方代码 | 可复现 screenshot-to-action baseline | 尚未实现 |
| AndroidWorld Hard task 评测 | benchmark 仓库、论文、task list 快照、待冻结 task manifest | baseline TSR、原始日志、任务分母 | 尚未冻结 |
| 多智能体记忆框架 | PG-Agent、HAR-GUI、LAMO、D-Artemis、HyMEM 等最近邻材料 | Planner/Executor/Memory/Critic 原型 | 尚未实现 |
| 历史、状态摘要、经验复用、多轮规划 | raw/sliding/summary baseline 与结构化 memory 文献 | 公平 baseline、组件消融 | 尚未实现 |
| 成功率、提升百分比、案例分析 | ProBench/AndroidWorld 评测资料与统计协议占位 | 主结果表、成功/失败案例 | 尚未实验 |
| 可选 Medium task | 只登记，不进入第一阶段 Must | 核心完成后的可选扩展 | Optional |
| 完整代码与实验报告 | 启动仓库、资料锁、后续项目目录 | source/config/log/report/reproduction guide | 尚未实现 |

## 优先级原则

1. 考核原文高于 GPT 生成的 master plan。
2. P0 文献与官方环境资料高于扩展论文。
3. baseline 和同协议比较高于复杂 memory module。
4. 可复现原始证据高于装饰性 demo 或额外 benchmark。

