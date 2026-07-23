# GUI / Mobile-use Agent 记忆机制调研

## 1. 问题定义

长程 Mobile-use Agent 的主要困难并不只是识别按钮，而是在多页面、跨应用、
二十步乃至更长的执行过程中持续维护四类信息：已经完成的子目标、当前页面与
交互状态、后续仍需使用的中间变量，以及刚才的动作是否真正生效。仅使用当前
截图会遗忘早期信息；保留全部截图和动作会造成上下文膨胀与旧状态污染；自由
文本 summary 则可能把推测写成事实，或在页面变化后继续传播失效结论。

本调研将 GUI Agent 记忆分为六类：

1. 当前截图与短窗口历史；
2. 自由文本轨迹摘要；
3. 结构化任务状态与 episodic ledger；
4. 页面图、知识图与可执行结构；
5. 跨任务经验、程序性记忆与检索；
6. 多角色规划、反思与记忆管理。

题录、PDF 校验状态和 BibTeX 分别见 `papers.csv`、`download_status.csv`
与 `references.bib`。截至 2026-07-23，本地登记 43 条文献，42 份 PDF
通过 SHA-256 校验；ExpAct 的 ICML 2026 元数据已核实，但 OpenReview PDF
请求返回 403，因此没有伪造“已下载”状态。

## 2. 单智能体历史与摘要

最简单的 GUI policy 只接收当前截图和任务目标。其优点是成本低、污染少，
但在跨页面变量保留、失败恢复和完成状态判断上缺少持久证据。滑动窗口保留
最近若干动作与截图，可改善短期连续性，却仍会在窗口滚动后丢失早期变量。
全历史策略的信息最完整，但视觉 token、重复动作和过期页面会共同稀释注意力。

HAR-GUI 将历史感知建模为反思场景和动作摘要，并通过训练增强历史利用能力；
HiconAgent 等工作进一步研究历史上下文采样或压缩。这类方法说明“更多历史”
并不等于“更好的记忆”，关键在于保留哪些信息、如何标记它是否仍有效。
本项目因此保留 B0、B1、B2、B3 四种对照：无历史、三步窗口、受限全历史与
LLM summary，避免只与最弱 baseline 比较。

## 3. 结构化状态、页面图与过程证据

PG-Agent 使用 Page Graph 表达页面及转移关系，适合跨页面导航，但全局页面图
可能合并外观相近却语义不同的状态，也可能将旧 UI 经验迁移到新页面。CES 的
Coordinator–Executor–State Tracker 强调角色协同与任务状态压缩；MP-GUI
关注 GUI 感知表征，提示研究者必须区分“看错了”与“记错了”。ProBench 则从
评测角度证明，仅报告最终成功率无法解释具体是感知、规划、执行还是状态维护
失败。

因此，结构化状态的优势是可查询、可更新、可审计；缺点是 schema 设计成本、
错误合并和过期传播风险。RAVEN-M 不构建全局 Page Graph，只保留当前 episode
中的小型 page hint，并把页面兼容性作为检索特征而非永久知识。

## 4. 跨轨迹、程序性与自演化记忆

ReMe、MAGNET、HyMEM、Darwinian Memory、EchoTrail-GUI、Executable
Agentic Memory 与 ExpAct 分别探索程序经验蒸馏、双记忆演化、符号—连续混合
图、效用选择、成功轨迹检索、可执行知识结构和结构化经验构建。这些路线能够
复用成功经验并减少重复探索，但存在三项共同风险：

- 错误经验被反复检索后会放大；
- UI、页面或任务前提变化会使旧经验失效；
- 在 benchmark test 轨迹之间共享经验可能造成难以界定的数据泄漏。

UI-Copilot 进一步使用学习到的策略调用 memory/calculator copilot，说明长程
性能提升也可能来自额外工具和推理调用，而非记忆组织本身。为保持考核范围
清晰，本项目将跨 episode procedural store 降为 Optional；所有正式 Hard
轨迹都只使用从空状态开始的 episode-local memory。

## 5. 多智能体规划与反思

Mobile-Agent-v2/v3、LAMO 与 D-Artemis 表明 Planner、Executor、Critic 或
Reflector 的职责拆分有助于组织长程执行。其优势是将规划、动作和校验显式
分开；不足是额外模型调用本身就是算力优势，且“多智能体”可能只是在同一模型
外包裹多个 prompt。

RAVEN-M 因此只使用同一个冻结 Qwen3-VL endpoint：Executor 每步调用一次；
Planner 仅在首个 transition 和每五步刷新；Critic 只在确定性 loop、
contradiction 或 completion-evidence 事件触发。所有角色调用都进入同一预算
账本，并设置 B3_CALL 对照判断增益是否只是来自额外推理。

## 6. 现有方法的共同不足

综合 15 项最近邻工作的逐项矩阵，当前研究仍常见以下不足：

1. relevance 与 truth 混为一谈：相关记忆不一定正确或仍兼容；
2. memory item 缺少可回溯截图、动作和模型调用证据；
3. stale、contradicted、superseded 等状态未进入检索决策；
4. 只报告 TSR，缺少 harmful-memory use、loop、premature completion
   与 recovery 等机制指标；
5. 方法获得更多 context、图片或 model calls，却未设置预算对照；
6. 失败案例往往事后挑选，容易只展示有利故事。

## 7. 本项目的切入点与边界

2026 年工作已经覆盖 training-free GUI memory、多角色编排、任务状态追踪、
轨迹检索、效用剪枝和可执行结构。因此，本项目不声称这些概念本身新颖。其
可辩护价值是一个可审计、可复现的受控原型：

- 每个持久 memory item 记录 source screenshot/action、SHA-256、scope、
  verification status 和 append-only lifecycle；
- 明确区分 FACT、HYPOTHESIS、ALERT 与 SUPPRESS；
- 页面变化、矛盾、替代和失败事件能够使旧信息失效；
- stale/contradictory memory 不得路由为 FACT；
- B0/B1/B2/B3/S0/M0 与组件消融共享同一模型、任务实例、动作预算、
  context cap、evaluator 和泄漏规则；
- 预注册 memory harm、loop、premature completion、recovery 与调用成本，
  即使 TSR 不提升也保留负结果。

这与周晟老师相关 GUI 研究线形成互补：MP-GUI 关注感知，PG-Agent 关注页面
结构，HAR-GUI 关注历史，ProBench 关注过程证据，LAMO 关注角色协同；本项目
把重点放在 episode 内记忆的证据、失效与伤害审计，而不是继续叠加更复杂架构。

## 8. 调研结论

长期 GUI 记忆的核心不是“存得更多”，而是“知道一条记录来自哪里、现在是否
仍适用、被谁使用、用错后造成了什么”。因此，一个适合本科夏令营考核的高质量
研究原型，应优先保证完整 baseline、公平预算、可追溯 memory lifecycle、
冻结评测和诚实的负结果解释。RAVEN-M 的方法与实验正围绕这一判断展开。

## 9. 核心参考文献

1. Rawles et al. *AndroidWorld: A Dynamic Benchmarking Environment for
   Autonomous Agents*. ICLR 2025.
2. Chen et al. *PG-Agent: An Agent Powered by Page Graph*. ACM MM 2025.
3. *History-Aware Reasoning for GUI Agents*. AAAI 2026.
4. *ProBench: Benchmarking GUI Agents with Accurate Process Information*.
   AAAI 2026.
5. Wang et al. *MP-GUI: Modality Perception with MLLMs for GUI
   Understanding*. CVPR 2025.
6. *Towards Scalable Lightweight GUI Agents via Multi-role Orchestration
   (LAMO)*. Findings of ACL 2026.
7. *Hybrid Self-evolving Structured Memory for Computer-Use Agents
   (HyMEM)*. Findings of ACL 2026.
8. *MAGNET: Towards Adaptive GUI Agents with Memory-Driven Knowledge
   Evolution*. ACL 2026.
9. *UI-Copilot: Advancing Long-Horizon GUI Automation via Tool-Integrated
   Policy Optimization*. ACL 2026.
10. *D-Artemis: A Deliberative Cognitive Framework for Mobile GUI
    Multi-Agents*. Findings of ACL 2026.
11. *Remember Me, Refine Me: A Dynamic Procedural Memory Framework for
    Experience-Driven Agent Evolution*. Findings of ACL 2026.
12. Wang et al. *Mobile-Agent-v2: Mobile Device Operation Assistant with
    Effective Navigation via Multi-Agent Collaboration*. NeurIPS 2024.
13. *Darwinian Memory: A Self-Regulating Memory System for GUI Agents*.
    arXiv preprint, 2026.
14. *EchoTrail-GUI*. CVPR 2026 Findings.
15. *CES: Coordinator–Executor–State Tracker for Long-Horizon GUI Agents*.
    CVPR 2026.

完整 DOI/URL、venue 核验状态与 BibTeX 见
`02_literature/metadata/papers.csv` 和
`02_literature/bib/references.bib`。
