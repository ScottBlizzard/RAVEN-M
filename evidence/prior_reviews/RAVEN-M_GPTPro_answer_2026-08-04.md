# RAVEN-M 下一研究方向独立审计：从“更可靠的记忆”转向“正确记忆为何驱动错误目标”

> **建议文件名：** `RAVEN-M_next_research_direction_independent_audit.md`  
> **审计截止日期：** 2026-08-04  
> **审计对象：** [RAVEN-M repository](https://github.com/ScottBlizzard/RAVEN-M)  
> **结论性质：** 独立、怀疑主义、机制优先的研究方向审计；不把仓库中的既有报告视为必须维护的结论。

## 1. Executive verdict

### 1.1 总结性判断

**RAVEN-M 应当改变研究方向。**

需要停止的不是整个代码库，而是下面这条尚未得到证据支持的论文主线：

> 通过更丰富的 structured episodic memory、provenance、confidence、verification、conflict、supersession、recovery records、completion guards，以及 planner/executor/memory/critic 分工，能够普遍提高 mobile GUI agent 的长程任务成功率。

当前证据最多支持一个窄结论：

> RAVEN-M 的结构化记录在一个极小且受开发污染的 EEST-AC smoke 中，能够保存正确的 source entity–field–value；但没有证据表明这些正确记录被绑定到了正确的 destination entity，更没有证据表明它们改善了任务成功率。

在 legacy 四任务比较中，简单摘要基线 B3 完成 4/4，而完整 RAVEN-M M0 完成 3/4，并使用更多 actions、model calls 和 tokens。在最有信息量的 EEST-AC smoke 中，四个 arms 都只完成 1/2；structured-memory arms 虽然正确记录了 4/4 source bindings，但没有产生 paired task win，也没有到达正确 destination。后续 v0.2–v0.2.4 则分别停留在 action contract、terminal measurement、collection floor 或 Android environment readiness 层面，不能作为 memory efficacy 的新增证据。

同时，AndroidWorld Hard 的绝大多数失败发生在 memory 真正可能发挥作用之前：界面感知、目标 grounding、action interface、无效重复动作、延迟状态变化、premature completion、postcondition verification 和环境稳定性。这意味着：

- 不能把 controller failure 算作 memory failure；
- 不能把正确 memory-record capture 算作 task success；
- 不能把所有方法都失败的 tie 算作 equivalence；
- 也不能因为 M0 没有成功，就反向证明 memory 一定无效。

### 1.2 对候选重构的判断

候选重构：

> “Task length is not the same as memory difficulty. Memory difficulty depends more on dependency distance、interference、role confusion 和 outcome observability。”

作为**实验设计原则**是合理的，但作为论文的主要 novelty claim 已经过宽。

原因是：

- [AndroTMem](https://arxiv.org/abs/2603.18429) 已经把 Android 长程任务的难点明确描述为跨步骤 causal dependencies，并使用 sparse intermediate-state anchors，反对把完整历史或普通摘要直接等同于有效长期记忆。
- [AgentProg](https://arxiv.org/abs/2512.10371) 已经从 program variables、data-flow persistence、control-flow pruning 和 global belief state 出发，区分了具有强依赖关系的 compositional tasks 与主要测试 interference 的 iterative tasks。

因此，**“任务长度不等于记忆难度”不能作为 RAVEN-M 的主要创新点**。它可以保留为任务匹配和分层分析中的一个 covariate。

### 1.3 唯一推荐方向

本审计只推荐一个方向：

## **正确记忆，错误目标：移动 GUI Agent 中的角色绑定放大效应**  
### *Correct Memory, Wrong Target: Causal Role-Binding Amplification in Mobile GUI Agents*

核心问题不是继续问：

> “怎样设计更复杂的 memory？”

而是先问：

> **当 agent 已经获得完全正确的 source fact 时，这条正确事实是否会因为出现得太早，在 source/destination role ambiguity 较高的界面中，反而诱导 agent 更确定地操作错误对象？**

建议检验的机制是：

> 在事实内容、任务、截图、模型、calls、tokens 和 action budgets 都匹配时，若正确 source fact 在 destination identity 被明确 grounding 之前暴露，则高角色歧义条件下的 wrong-target first-action rate 将高于“先 grounding destination、再暴露同一事实”的条件。

这一方向的 novelty 状态必须标记为：

> **UNRESOLVED — narrowly plausible**

它不是“entity binding”本身的首次提出，也不是“role-aware memory”的首次提出。[ATMem](https://arxiv.org/abs/2606.31612)、[Entity Binding Failures in Tool-Augmented Agents](https://arxiv.org/abs/2606.30531)、[Binding Drift in Multi-Step Tool-Augmented Agents](https://arxiv.org/abs/2607.18316) 和 [Salience Induction against Multi-Hop RAG Agents](https://arxiv.org/abs/2607.17535) 已经分别覆盖 role/status representation、wrong-entity actions、错误绑定持续与放大、以及 position/emphasis/proximity 对属性绑定的影响。剩余的窄区别，是在 mobile GUI critical decisions 上固定正确 value，正交操纵其相对 destination grounding 的暴露时序和 role ambiguity，并以 matched budgets 测量 interaction。现有搜索尚未发现完全相同的 controlled intervention，但并不足以支持“first”或“无先例”的表述。

### 1.4 对 RAVEN-M 代码库的重新定位

RAVEN-M 不应继续作为“待证明优越性的 memory architecture”，而应降级并重用为：

> **一个用于分离 acquisition、binding、retention、retrieval、destination grounding、execution 和 postcondition verification 的实验仪器与 failure-chain logger。**

保留有价值的部分：

- 结构化事件记录；
- source/destination entity 标识；
- field/value provenance；
- action target 与 screenshot-state 对齐；
- first-broken-edge 分析；
- 调用、token、action 和 wall-time 成本记录。

不再把以下内容默认包装成贡献：

- 更多 ledger fields；
- 更多 memory states；
- 更多 planner/critic 分工；
- 更多 verification labels；
- 更多 retrieval heuristics。

---

## 2. 审计标准、范围与证据等级

### 2.1 本次审计采用的因果链

所有 task-level 结果都应沿以下链条分析：

\[
\text{Acquire}
\rightarrow
\text{Bind source entity/role/field}
\rightarrow
\text{Retain}
\rightarrow
\text{Retrieve}
\rightarrow
\text{Ground destination}
\rightarrow
\text{Execute}
\rightarrow
\text{Observe effect}
\rightarrow
\text{Verify postcondition}
\]

只有当上游环节成立后，下游失败才有资格被归因于 memory。

例如：

- 没有进入正确页面：不能评价 memory；
- 事实记对但联系人选错：是 role/destination binding 或 grounding 问题；
- 目标和动作计划都正确，但 tap/long-press 不生效：是 controller/action-interface 问题；
- 动作已经生效但 agent 重复执行：是 observation/update/postcondition 问题；
- evaluator 无法确认最终状态：是 measurement 问题。

### 2.2 证据等级

| 等级 | 含义 |
|---|---|
| **Supported** | 有直接、有效、与 claim 对齐的实验支持 |
| **Narrowly supported** | 只支持 claim 的一个窄子命题，不能外推 |
| **Unsupported** | 尚无有效实验支持 |
| **Contradicted in current sample** | 当前小样本方向与 claim 相反，但不足以证明普遍反例 |
| **Not identifiable** | 由于共同上游 failure floor，无法识别方法效应 |
| **Invalid comparison** | measurement、contract、污染或统计单位使比较不能解释 |
| **UNRESOLVED novelty** | 检索未发现完全等价工作，但搜索或 concurrent work 不足以支持强 novelty claim |

### 2.3 文献状态标签

- **Published：** 已进入正式会议或期刊 proceedings。
- **Accepted：** 有官方或作者侧接收信息，但本次未必检查到正式 proceedings。
- **Preprint：** 本次只验证到 arXiv/OpenReview 等公开稿。
- **Concurrent：** 在 RAVEN-M 核心方向形成期间或临近本审计截止日期公开；即使未正式发表，也构成必须正面处理的 novelty threat。
- **UNRESOLVED：** 不能因未搜到而推断不存在。

---

## 3. 现有实验的 claim–evidence audit

### 3.1 总表

| 既有或潜在 claim | 实际证据 | 审计结论 | 对下一步的含义 |
|---|---|---|---|
| Structured memory 能更准确地保存 source entity–field–value | EEST-AC smoke 中 structured arms 的 4/4 source records 正确 | **Narrowly supported**。4 条记录来自极小、开发污染的任务集合，不能当作 4 个独立任务 | 可把 exact-value retention 作为实验前置资格条件，不能作为论文终点 |
| Structured memory 提高 task success | 四个 arms 都是 1/2，M-SLOTS 没有 net win；部分 positive structured cells 因 truncation/evaluator 问题无效 | **Unsupported** | 不应继续写成 task-level efficacy claim |
| Full RAVEN-M 优于 simple summary | legacy 中 B3 为 4/4，M0 为 3/4，且 M0 成本更高 | **Contradicted in current tiny sample** | 至少不能把 full stack 当作默认 stronger method |
| AndroidWorld Hard 证明 memory 无效 | 绝大多数失败在 perception、grounding、controller、action interface、verification 或 infrastructure | **Not identifiable** | Hard 结果不能用于 memory efficacy 正反结论 |
| 自然任务中 stale/conflict/supersession 是高频关键问题 | 10,884 memory events 中 stale、superseded、revoked、archived、invalidated 均为 0；15 个 contradiction flags 中 14 个更像兼容性 paraphrase，且分析非 blind、单人完成 | **Unsupported** | 不应把 stale/conflict lifecycle 当作近期主线 |
| Action-conditioned verification 提高完成率 | 没有合格的 paired intervention；后续实验停在 contract/measurement/collection floors | **Untested** | 先修复可识别性，不应再叠加 verification module |
| 所有 arms 都失败，因此方法等价 | all-failure tie | **Invalid inference** | 只能说没有观察到成功差异，不能做 equivalence claim |
| 正确 capture memory record 就意味着任务中的 memory use 成功 | EEST 中 source binding 正确，但 destination 没有达到 | **False category substitution** | 必须区分 record fidelity 与 downstream binding/use |
| v0.2–v0.2.4 增加了 memory efficacy evidence | 分别停在 action contract、terminal pixel measurement、无 collection corpus 或缺失 settings/readiness | **No** | 这些结果只支持 engineering floor diagnosis |
| Task length 与 memory difficulty 不同 | 当前仓库没有可估计该关系的 matched-task design | **Plausible but untested internally**；外部广义 novelty 已被 AndroTMem/AgentProg 显著覆盖 | 可作为控制变量，不能作为主创新 |

仓库中的 [README.md](https://github.com/ScottBlizzard/RAVEN-M/blob/main/README.md)、[GPTPRO_NOVEL_IDEA_AUDIT_BRIEF_2026-08-04.md](https://github.com/ScottBlizzard/RAVEN-M/blob/main/reports/research_direction/GPTPRO_NOVEL_IDEA_AUDIT_BRIEF_2026-08-04.md) 和 [eest_ac_smoke_v0_1_1_analysis.md](https://github.com/ScottBlizzard/RAVEN-M/blob/main/reports/eest_ac/eest_ac_smoke_v0_1_1_analysis.md) 对上述数字提供了主要证据。

### 3.2 Legacy 四任务比较

可观察结果是：

- B3：4/4；
- M0：3/4；
- M0 使用更多 actions、model calls 和 tokens。

这不能证明“structured memory 普遍有害”，因为：

1. 样本只有四个任务；
2. 任务不一定覆盖需要记忆的关键机制；
3. 没有足够的 paired replications；
4. 一个任务差异可能来自 controller stochasticity；
5. 没有置信区间或模型/seed 层面的稳定性。

但它已经足以否定一种论文写法：

> 不能继续把 M0 当成已经由结果支持的 superior full system。

正确表述应是：

> 在已有极小样本中，full RAVEN-M 没有显示 task-success advantage，并出现了明确的 cost disadvantage。

### 3.3 EEST-AC smoke

[eest_ac_smoke_v0_1_1_analysis.md](https://github.com/ScottBlizzard/RAVEN-M/blob/main/reports/eest_ac/eest_ac_smoke_v0_1_1_analysis.md) 的最重要信息不是“memory 成功”或“memory 失败”，而是两个层级被分离了：

1. **记录层：** structured arms 正确保存了 4/4 source entity–field–value bindings；
2. **行为层：** 四个 arms 都只完成 1/2，structured arms 没有 paired win，并且没有到达正确 destination entity Gabriel。

此外：

- 实验规模为 2 templates × 1 seed × 4 arms，共 8 cells；
- positive structured arms 受到 256-token truncation 和 evaluator 缺失影响；
- completion precision 为 0.50，recall 为 0.25；
- task/seed 受到 development contamination；
- “4/4 records”是 arm-level observations，不是四个彼此独立的任务成功样本。

因此，唯一可以保留的经验性判断是：

> **structured representation 可以使 source-value capture 在这个小样本中保持准确，但 source capture 与 destination use 是两个不同的科学问题。** 

这也给出了本审计推荐方向的直接动机：Petar Muller 的地址可以被记对，但系统仍然没有把它用于 Gabriel Fernandez。

### 3.4 v0.2–v0.2.4

后续轮次分别揭示：

- v0.2 blind smoke 没有形成合格的 environment action；
- v0.2.2 action schema 可以通过，但 terminal-state measurement 受到 pixel/evaluator 问题影响；
- v0.2.3 没有形成可用于 efficacy 分析的 collection corpus；
- v0.2.4 缺失 settings 或 collector lifecycle readiness，不能进入有效收集。

对应文件包括：

- [eest_ac_v0_2_blind_smoke_analysis.md](https://github.com/ScottBlizzard/RAVEN-M/blob/main/reports/eest_ac/eest_ac_v0_2_blind_smoke_analysis.md)
- [eest_ac_v0_2_2_qualification_final_report.md](https://github.com/ScottBlizzard/RAVEN-M/blob/main/reports/eest_ac/eest_ac_v0_2_2_qualification_final_report.md)
- [eest_ac_v0_2_3_collection_floor_verdict.md](https://github.com/ScottBlizzard/RAVEN-M/blob/main/reports/eest_ac/eest_ac_v0_2_3_collection_floor_verdict.md)
- [eest_ac_v0_2_4_collector_lifecycle_verdict.md](https://github.com/ScottBlizzard/RAVEN-M/blob/main/reports/eest_ac/eest_ac_v0_2_4_collector_lifecycle_verdict.md)

这些轮次的贡献是暴露了 action contract、measurement 和 infrastructure floor，而不是验证了 memory 方法。

### 3.5 Conflict、staleness 与 lifecycle

[RAVEN-M_研究假设与实验方向审计_2026-08-03.md](https://github.com/ScottBlizzard/RAVEN-M/blob/main/RAVEN-M_%E7%A0%94%E7%A9%B6%E5%81%87%E8%AE%BE%E4%B8%8E%E5%AE%9E%E9%AA%8C%E6%96%B9%E5%90%91%E5%AE%A1%E8%AE%A1_2026-08-03.md) 对 10,884 个 memory events 的审计显示：

- stale：0；
- superseded：0；
- revoked：0；
- archived：0；
- invalidated：0。

15 个 contradiction flags 中，14 个被认为更可能是可以兼容的 paraphrases，只有 1 个较为实质；而这一判断还是单人、非 blind，并以 event 为单位，而不是以真正需要做决策的 opportunity 为单位。

因此，当前没有经验依据支持：

> “自然 AndroidWorld 任务中的主要瓶颈是 stale-memory rejection 或 conflict resolution。”

合成 stale-memory 实验可以测试一个人为构造能力，但不能被包装成普通 AndroidWorld task improvement。

---

## 4. AndroidWorld Hard 的 failure-chain 诊断

### 4.1 关键统计

[ANDROIDWORLD_HARD_FAILURE_INFORMATION_CHAIN_AUDIT_2026-08-04.md](https://github.com/ScottBlizzard/RAVEN-M/blob/main/reports/research_direction/ANDROIDWORLD_HARD_FAILURE_INFORMATION_CHAIN_AUDIT_2026-08-04.md) 汇总了 95 个 cells：

- 总成功数：1；
- 15 个 QA 类型任务因 action interface 不支持而不具可执行性；
- 其余 80 个 supported cells 中：
  - 1 success；
  - 50 budget exhausted；
  - 14 infeasible；
  - 14 premature done；
  - 1 invalid；
- 59/80 出现至少 3 次连续相同动作；
- 32/80 出现至少 10 次连续相同动作；
- 记录了 477 次动作后 screenshot 没有变化。

这不是一个可以直接比较 memory efficacy 的实验平面，而是一个被共同 controller floor 主导的平面。

### 4.2 Memory 被调用，不等于 memory 被有效检验

M0 在 Hard runs 中产生了：

- 758 个 memory bundles；
- 457 个 citations；
- 270 个额外 model calls；
- 在对应 19 个 M0 cells 中为 0/19；
- 相比轻量方法，calls 约增加 33%、tokens 约增加 53%、wall time 约增加 52%。

这些数字说明 memory pipeline 实际运行并产生了成本，但不能说明它对任务成功率的 treatment effect 为零，因为：

\[
\text{Observed success}
=
\text{Upstream reachability}
\times
\text{Memory-use correctness}
\times
\text{Controller execution}
\times
\text{Outcome verification}
\]

当 upstream reachability 或 controller execution 几乎为零时，memory effect 不可识别。

### 4.3 主要 first-broken edges

| First-broken edge | 典型表现 | 是否可归因于 memory |
|---|---|---|
| Perception → source acquisition | 没有识别正确 app、页面或字段 | 否 |
| UI grounding → action | 点错控件、错误 long-press、找不到 target | 否，除非能证明 target identity 来自错误 memory binding |
| Action proposal → environment execution | action schema 不受支持、动作无效 | 否 |
| Execution → state transition | delayed transition、screenshot 不变 | 否 |
| State transition → replanning | 重复同一动作 3 次、10 次以上 | 通常是 controller/state-update 问题 |
| Observation → completion judgment | premature done | postcondition/evaluator 问题 |
| Source retention → destination binding | 值记对，但没有用于正确联系人/目标对象 | **可能是 memory-use 或 role-binding 问题** |
| Correct action → final task success | 动作正确但未保存、未确认或 evaluator 不识别 | controller/postcondition/measurement 问题 |

目前唯一直接靠近 memory-use 机制的 failure，是：

> **source fact 已被正确保存，但 destination role 或 destination entity 没有被正确连接到后续 action。**

这正是 EEST-P1 比大量 Hard all-failure cells 更有科学价值的原因。

### 4.4 Hard 结果允许和不允许的结论

**允许：**

- 当前 end-to-end environment 不适合直接检验细微的 memory treatment effect；
- controller、grounding、action contract 和 postcondition verification 是优先级更高的工程障碍；
- M0 带来显著额外成本；
- first-broken-edge logging 比简单 success/failure 更重要。

**不允许：**

- “structured memory 已被证明无效”；
- “所有方法失败，所以等价”；
- “更多 memory calls 接近成功，因此值得继续扩展”；
- “正确记录已经证明 RAVEN-M 的核心机制成功”；
- “通过再加一个 critic 或 verifier 就能修复整体结果”。

---

## 5. Mechanism-based novelty landscape

### 5.1 广义候选假设为何不够新

“Task length 不等于 memory difficulty”包含四个子构念：

1. dependency distance；
2. interference；
3. source/destination role confusion；
4. final-outcome observability gap。

这四个构念都能在已有工作中找到强近邻。真正需要寻找的不是新名词，而是一个尚未被等价 intervention 检验的、足够窄的机制。

### 5.2 GUI-agent 与 agent-memory 近邻

| 机制区域 | 主要 primary sources 与状态 | 与 RAVEN-M 候选方向的精确重叠 | 删除重叠后仍可能剩余的区别 |
|---|---|---|---|
| 跨步骤 causal dependency | [AndroTMem](https://arxiv.org/abs/2603.18429)，preprint | 直接强调 long-horizon Android tasks 的强跨步骤依赖、dependency-critical information 和 sparse anchors | 同长度、同 UI 难度下连续操纵 dependency topology 的 matched causal estimate；但不足以作为强 headline novelty  |
| Data-flow 与 control-flow memory | [AgentProg](https://arxiv.org/abs/2512.10371)，preprint | 用 variables、data-flow persistence、control-flow pruning、global belief state 和 runtime verification 表达长程依赖；区分 compositional 与 iterative tasks | GUI 中某个具体 dependency-edge failure 的局部干预，而不是再提出程序化 memory  |
| Role/status-aware memory | [What Memory Do GUI Agents Really Need? / ATMem](https://arxiv.org/abs/2606.31612)，preprint、concurrent | 明确指出“取回一个 value”并不说明其当前 role，跟踪 role/status，并设置 near-identical entries 与 confusable distractors | 固定同一正确 value，操纵其相对 destination grounding 的暴露时序，并估计 timing × ambiguity interaction；novelty 仍为 UNRESOLVED  |
| Wrong-entity action | [Entity Binding Failures in Tool-Augmented Agents](https://arxiv.org/abs/2606.30531)，preprint、concurrent | 正确 tool 仍可作用于错误 entity；比较 entity-aware mechanisms | mobile GUI critical-state 中“正确 episodic value 的暴露时序”是否因果改变 wrong-target action  |
| Binding persistence/amplification | [Binding Drift in Multi-Step Tool-Augmented Agents](https://arxiv.org/abs/2607.18316)，preprint、concurrent | seeded wrong entity 可被 entity lock 放大，re-verifier 可减少错误 action | 不是注入错误 entity，而是提供正确 source fact，测试它是否在 destination 未 grounding 时诱发错误角色绑定  |
| Salience 与属性错绑 | [Salience Induction against Multi-Hop RAG Agents](https://arxiv.org/abs/2607.17535)，preprint、concurrent | position、emphasis、proximity 即使不改变事实真值，也能重定向 attribute binding | 需要用 position/recency placebo 排除一般 salience，证明 effect 特异于 source/destination role order  |
| 更多视觉历史可能有害 | [Naive Visual Memory Is Not Enough](https://arxiv.org/abs/2606.14106)，preprint | full-image memory 可减少 state-level failure，却增加 hidden-operation/grounding 等 action-level failure | 从相关性进一步缩小到正确 value 如何改变 target binding 的 causal intervention  |
| Workflow/experience retrieval | [Agent Workflow Memory](https://proceedings.mlr.press/v267/wang25bx.html)，ICML 2025 published；[PG-Agent](https://arxiv.org/abs/2509.03536)，ACM MM 2025 accepted；[HyMEM](https://arxiv.org/abs/2603.10291)，preprint | 学习、检索、复用 workflow；page graph；symbolic graph 与 trajectory retrieval | generic workflow/page/KG memory 已高度拥挤，不应作为 RAVEN-M 新主线  |
| Dynamic/procedural/executable memory | [MAGNET](https://aclanthology.org/2026.acl-long.1299/)，ACL 2026 published；[Executable Agentic Memory](https://arxiv.org/abs/2605.12294)，preprint | stationary/procedural memory、动态更新、KG retrieval-and-execution、action-group mining | 再构建一层 executable graph 不构成清晰区别  |
| Learned memory selection | [MementoGUI](https://arxiv.org/abs/2605.18652)，preprint；[STAMP](https://arxiv.org/abs/2605.29324)，preprint | working/episodic memory 的选择、压缩、检索；可控 encode/retrieve 环境 | 普通的“学会何时记忆/检索”已经拥挤；本项目应先做机制诊断  |
| Process evaluation | [ProBench](https://arxiv.org/abs/2511.09157)，AAAI 2026 accepted | 不只评估 terminal success，也评估执行过程，并提供 Process Provider | first-broken-edge 可以作为具体 process diagnostic，但不能声称 process evaluation 本身新颖  |
| Memory-focused benchmark | [MemGUI-Bench](https://arxiv.org/abs/2602.06075)，作者侧标记 ACM MM 2026 accepted；[AndroTMem](https://arxiv.org/abs/2603.18429) | 长程、memory-challenging、staged evaluation、跨步骤依赖 | 现在提出新 benchmark 会先遇到 benchmark novelty 和 environment validity 两重风险；应先做 matched study  |
| 多 agent 架构和 grounding | [Mobile-Agent-E](https://arxiv.org/abs/2501.11733)，preprint；[Agent S2](https://openreview.net/forum?id=zg5is4GJ3R)，COLM 2025 published | Manager/Perceptor/Operator/Action Reflector/Notetaker，以及 Mixture-of-Grounding 与 hierarchical planning | planner/executor/memory/critic 拆分和多 grounding expert 不再是可信 novelty  |
| 最新 Mobile-Agent 系列扩展 | [Mobile-Agent-v3.5](https://arxiv.org/abs/2602.16855)，preprint | 多平台、多模型规模、20+ benchmarks，覆盖 memory/knowledge 等能力 | broad system scaling 不是 RAVEN-M 当前证据能竞争的方向  |
| Test-time scaling | [GTA1](https://arxiv.org/abs/2507.05791)，preprint | 多个 proposal 加 judge，用额外 test-time compute 提升质量 | 更多 calls/context 必须视为 compute treatment，不能与 memory representation 混为一谈  |

### 5.3 邻近领域对广义 novelty 的进一步压缩

| 邻近领域 | 已存在的核心思想 | 对 RAVEN-M 的限制 |
|---|---|---|
| POMDP belief states | [Planning and Acting in Partially Observable Stochastic Domains](https://people.csail.mit.edu/lpk/papers/aij98-pomdp.pdf) 已把 belief state 作为部分可观测环境中的决策状态 | “把历史压缩成可决策状态”不是新概念；必须提出可检验的 GUI-specific mechanism  |
| Program slicing/dataflow | [Program Slicing](https://ieeexplore.ieee.org/document/5010248/) 根据变量依赖确定哪些历史语句影响目标位置 | “只保留与后续决策有关的信息”属于经典 data-dependency 思想  |
| Data provenance | [Why and Where: A Characterization of Data Provenance](https://link.springer.com/chapter/10.1007/3-540-44503-X_20) 区分 why/where provenance | source、lineage、origin 字段本身不能构成新颖贡献  |
| GUI testing | [An Event-Flow Model of GUI-Based Applications for Testing](https://www.cs.umd.edu/~atif/papers/MemonSTVR2007.pdf) 使用 event-flow 与 GUI oracle 思想描述可执行路径和验证 | page/action graph 和 postcondition oracle 均有深厚先例  |
| Workflow verification | [Verification of Workflow Nets](https://link.springer.com/chapter/10.1007/3-540-63139-9_48) 使用 Petri-net 风格方法验证 workflow correctness | workflow consistency 或 completion guard 不是空白领域  |
| Runtime verification | [A Brief Account of Runtime Verification](https://www.isp.uni-luebeck.de/research/publications/brief-account-runtime-verification) 讨论运行时监测和违反条件时的介入 | “执行时验证高风险动作”需要具体新机制，不能作为一般性创新  |
| Active perception | [Active Perception](https://doi.org/10.1109/5.5968) 把感知视为面向任务、可主动控制的过程 | 根据不确定性重新观察 UI 是经典思路，不应被包装成全新模块  |
| Temporal sensor fusion | [Track-to-track fusion using out-of-sequence track information](https://ieeexplore.ieee.org/document/4408008/) 研究异步、乱序观测融合 | screenshot、OCR、accessibility tree 的时间错位有明确邻近理论 |
| Temporal GUI consistency | [Temporal UI State Inconsistency in Desktop GUI Agents](https://arxiv.org/abs/2604.18860) 直接研究 observation–action 的 TOCTOU gap | “执行前再次确认当前界面”已经有直接 GUI-agent 近邻  |
| Credit assignment | [RUDDER](https://proceedings.neurips.cc/paper/2019/hash/16105fb9cc614fc29e1bda00dab60d41-Abstract.html) 处理 delayed reward 与 contribution redistribution | 将最终失败追溯到早期 dependency edge 是 credit assignment 的具体实例，而非全新问题  |
| Event sourcing | [Event Sourcing](https://martinfowler.com/eaaDev/EventSourcing.html) 把状态变化保存为事件序列 | 完整事件 ledger 有工程价值，但 event log 本身不是研究 novelty  |

### 5.4 Landscape 总结

经过删除已有重叠后：

- **generic structured memory：不成立；**
- **generic role-aware memory：不成立；**
- **generic dependency graph：不成立；**
- **generic workflow/page graph：不成立；**
- **generic verification：不成立；**
- **generic test-time retrieval：不成立；**
- **generic memory benchmark：不成立；**
- **generic “more history can hurt”：不够窄。**

仍可能成立的只是一条小而具体的 causal claim：

> **正确 source fact 的暴露顺序，是否会与 source/destination role ambiguity 发生交互，从而改变 mobile GUI agent 的 first wrong-target action？**

---

## 6. 四个 counterintuitive、falsifiable 候选方向

## 6.1 候选一：Dependency-topology threshold

1. **一句话机制假设**

   在 controller difficulty 被匹配后，任务成功率主要受非局部 causal dependency topology 影响，而不是受总 action length 影响。

2. **直接动机**

   AndroidWorld Hard 的长任务多数在真正使用 memory 前失败，而较短的 EEST cross-entity transfer 仍出现 source 已记录、destination 未到达的断裂。

3. **反直觉性**

   一个 20-step、每一步都局部可见的任务，可能比一个 6-step、需要跨 app/跨角色传递一个事实的任务更容易。

4. **最近 prior work 与精确重叠**

   [AndroTMem](https://arxiv.org/abs/2603.18429) 已直接使用 strong cross-step causal dependencies；[AgentProg](https://arxiv.org/abs/2512.10371) 已区分强 compositional dependencies 与主要测试 interference 的 iterative tasks。

5. **删除重叠后的窄区别**

   在相同 action length、相同页面、相同控件和相同模型预算下，只改变一条 source-to-use dependency edge 的距离或 fan-out。

6. **为什么可能改变行为**

   非局部依赖要求 agent 在后续状态中恢复并重新绑定早期事实；局部任务则可以直接根据当前 observation 行动。

7. **最小实现或测量**

   不增加新 memory framework，只给任务标注或操纵：
   - dependency distance；
   - number of competing bindings；
   - fan-out；
   - final-use location。

8. **Matched experiment**

   构造同一 UI workflow 的 matched pairs：
   - local condition：值在使用页面直接可见；
   - nonlocal condition：相同值必须在早期页面观察并在后续页面使用；
   - action count 和 UI targets 完全匹配。

9. **Negative control 与预算**

   - task-literal value control；
   - 无需记忆的 local copy control；
   - 相同 model、calls、tokens、actions；
   - 相同页面切换次数。

10. **Outcomes 与成本**

    - primary：正确 destination action；
    - diagnostics：value recall、destination identification、first-broken edge；
    - cost：calls、tokens、actions、wall time。

11. **Falsification**

    在 controller/UI difficulty 被匹配后，dependency distance 或 fan-out 对正确 action 没有稳定效应。

12. **Redirect condition**

    若错误主要发生在读取 source 之前，转向 perception；若值与 destination 都正确但动作失败，转向 controller。

13. **即使 task success 不提高仍有用的贡献**

    一个经过控制的 task-stratification protocol，说明 step count 不是充分难度指标。

**候选结论：拒绝作为主要 novelty。**  
原因不是机制不合理，而是 AndroTMem 与 AgentProg 已经覆盖过于接近的核心构念。可把 dependency topology 保留为推荐实验中的分层变量。

---

## 6.2 候选二：Correct-memory role-binding amplification

1. **一句话机制假设**

   在正确 source fact 被完美保留的前提下，若它在 destination identity 完成 grounding 之前暴露，则高 source/destination role ambiguity 条件下的 wrong-target first-action rate 会高于先 grounding destination、后暴露同一事实的条件。

2. **直接动机**

   EEST-AC 中 structured arms 正确保存了 source entity–field–value，却没有到达正确 destination Gabriel；这表明断裂不在 value capture，而可能位于 source-role/destination-role 到 action target 的绑定。

3. **反直觉性**

   一条完全正确、看似有帮助的事实，可能不是“没有帮助”，而是让 agent 对错误对象形成更高置信度的 premature commitment。

4. **最近 prior work 与精确重叠**

   - [ATMem](https://arxiv.org/abs/2606.31612)：value 本身不能确定其当前 role，使用 role/status 表示和 confusable distractors；
   - [Entity Binding Failures](https://arxiv.org/abs/2606.30531)：正确 tool 仍会作用于错误 entity；
   - [Binding Drift](https://arxiv.org/abs/2607.18316)：错误 entity binding 会在后续步骤持续并被某些机制放大；
   - [Salience Induction](https://arxiv.org/abs/2607.17535)：位置、强调和邻近性能够改变 attribute binding；
   - [Naive Visual Memory Is Not Enough](https://arxiv.org/abs/2606.14106)：更多历史可能改善 state-level information，却恶化 action-level grounding。

5. **删除重叠后的窄区别**

   同时满足以下五个条件的 intervention 尚未在本次检索中被确认：

   1. value 内容保持完全正确且相同；
   2. 只改变 value 相对 destination grounding 的暴露时序；
   3. role ambiguity 被正交操纵；
   4. 测量 mobile GUI first targeting action；
   5. calls、tokens、actions 和模型完全匹配。

   该区别只能标记为 **UNRESOLVED**。

6. **为什么可能改变行为**

   正确 source fact 在 destination 尚未确定时成为最强 salient entity cue，使模型把“值来自谁”误当成“动作应作用于谁”；一旦 source-linked target 被选中，后续推理可能围绕该错误目标自洽化。

7. **最小实现或测量**

   不训练模型，不新增 memory architecture。只对同一个“retrieved episodic record”做 block-order manipulation，并记录：
   - grounding phase 的 destination ID；
   - action phase 的 target ID；
   - exact value recall；
   - confidence；
   - first wrong-target action。

8. **Matched experiment**

   采用 \(2\times2\) factorial：

   - Fact timing：before destination grounding / after destination grounding；
   - Role ambiguity：low / high。

   两个 timing 条件都使用同一 UI snapshot、同一正确 fact 和两个相同预算的 model calls。

9. **Negative controls 与预算**

   - low-ambiguity condition；
   - task-literal/no-memory condition；
   - irrelevant but same-format fact；
   - position/recency placebo；
   - source/destination label swap；
   - delay-only、无 destination commitment control；
   - 相同 model revision、temperature、calls、prompt/completion token ceilings 和 action budget。

10. **Outcomes 与成本**

    - primary：`WrongTarget@FirstTargetingAction`；
    - diagnostics：destination grounding accuracy、post-grounding drift、value fidelity、role classification、confidence；
    - downstream：live task success；
    - costs：calls、tokens、proposed/live actions、wall time。

11. **Falsification**

    以下任一结果都将否定核心机制：
    - Timing × Ambiguity interaction 接近零；
    - early/late 差异在 low ambiguity 中同样大；
    - 差异可完全由普通 recency/position placebo 解释；
    - destination 已先正确 commitment 后仍以同样频率漂移；
    - exact-value fidelity 无法达到资格阈值。

12. **Redirect condition**

    - destination 在 fact 出现前就经常识别错误：转向 grounding；
    - destination 和 proposed action 正确，但 live action 失败：转向 controller/action interface；
    - action 成功但 task evaluator 判错：转向 postcondition/evaluation；
    - exact value 本身无法保留：才转向 retention/retrieval memory。

13. **即使 task success 不提高仍有用的贡献**

    - 对 timing × role ambiguity effect 给出可信的 causal null bound；
    - 建立 source retention 与 destination use 的可重复分离协议；
    - 提供 first-broken-edge taxonomy；
    - 为停止 memory-method 路线和转向 grounding/controller 提供证据，而不是凭直觉 pivot。

**候选结论：唯一保留并推荐，但 novelty 为 UNRESOLVED。**

---

## 6.3 候选三：Multimodal temporal-skew interference

1. **一句话机制假设**

   即使 screenshot、OCR、accessibility tree 和 action logs 各自都正确，只要它们对应不同时间点，联合输入也可能比同步的单一 modality 产生更多错误动作。

2. **直接动机**

   Hard runs 中存在大量 delayed transitions、无 screenshot change、重复动作和 observation–action 不一致。

3. **反直觉性**

   更多正确 modalities 不一定提供更多信息；时间不一致的正确证据可能形成一个从未真实存在过的合成 UI state。

4. **最近 prior work 与精确重叠**

   - [MP-GUI](https://openaccess.thecvf.com/content/CVPR2025/html/Wang_MP-GUI_Modality_Perception_with_MLLMs_for_GUI_Understanding_CVPR_2025_paper.html) 已研究 textual、graphical、spatial perception 与融合；
   - [Temporal UI State Inconsistency](https://arxiv.org/abs/2604.18860) 直接研究 observation–action TOCTOU gap；
   - [Why Are GUI Agents Correct but Late?](https://arxiv.org/abs/2607.28399) 研究 transient events 和 latency critical path；
   - out-of-sequence measurement fusion 是长期存在的传感器融合问题。

5. **删除重叠后的窄区别**

   在 mobile GUI snapshot 上系统操纵 cross-modal timestamp skew，并比较同步多模态、异步多模态和同步单模态。

6. **为什么可能改变行为**

   stale accessibility tree 指向旧控件，而新 screenshot 表示新页面；模型可能生成在任何单一时刻都不合法的 action。

7. **最小实现或测量**

   给已有 replay 增加 modality timestamp 和人为 one-step lag，不新增 agent module。

8. **Matched experiment**

   同一状态分别提供：
   - aligned screenshot + tree；
   - current screenshot + one-step-old tree；
   - current screenshot only。

9. **Negative controls 与预算**

   - 静态页面；
   - 同步但随机删除一项 modality；
   - 相同 token、call 和 action budget。

10. **Outcomes 与成本**

    stale-target click、invalid action、wrong-current-state action、recovery steps、latency。

11. **Falsification**

    可控 timestamp skew 对 action correctness 没有稳定影响。

12. **Redirect condition**

    若 skew 是 environment collector 导致，转向 infrastructure；若同步后仍失败，转向 grounding。

13. **即使 task success 不提高仍有用的贡献**

    建立 UI modality synchronization 的资格测试和 skew-sensitivity profile。

**候选结论：拒绝作为主要研究方向。**  
它是高优先级 engineering diagnosis，但与 temporal UI inconsistency、multimodal fusion 和 out-of-sequence sensing 的已有工作过近。

---

## 6.4 候选四：Outcome-observability inversion

1. **一句话机制假设**

   对许多 mobile GUI tasks，真正最困难的“记忆”发生在最后一个动作之后：当 postcondition 弱可观测或延迟出现时，agent 比在前序事实保留阶段更容易失败。

2. **直接动机**

   Hard 中出现大量重复动作、premature done、无 screenshot change；v0.2.2 也受到 terminal-state pixel measurement 问题影响。

3. **反直觉性**

   长程任务的主要困难不一定是“记住开头”，而可能是“知道刚才是否已经成功”。

4. **最近 prior work 与精确重叠**

   - [ProBench](https://arxiv.org/abs/2511.09157) 已推动 process-level evaluation；
   - GUI testing 长期研究 event-flow 和 oracle；
   - runtime verification 研究执行时监测；
   - [AgentProg](https://arxiv.org/abs/2512.10371) 包含 global belief state/runtime verification。

5. **删除重叠后的窄区别**

   固定 action outcome，只改变 postcondition 是立即、延迟还是部分隐藏。

6. **为什么可能改变行为**

   缺乏可靠 outcome evidence 会导致：
   - 重复执行已经成功的动作；
   - 对未成功动作 premature done；
   - 用旧 screenshot 更新 belief state。

7. **最小实现或测量**

   在 replay 或 controllable environment 中延迟、遮蔽或弱化同一个 postcondition cue。

8. **Matched experiment**

   同一任务、同一动作和同一真实结果，比较 immediate-visible、delayed-visible 和 hidden-until-check 三种条件。

9. **Negative controls 与预算**

   - 等时延但不隐藏证据；
   - no-op 动作；
   - 相同 observation calls、tokens 和 action budgets。

10. **Outcomes 与成本**

    false completion、unnecessary repeats、time-to-certainty、task success、extra observations。

11. **Falsification**

    postcondition observability 对重复、premature done 和成功率没有影响。

12. **Redirect condition**

    如果动作在结果出现前已经错误，转向 grounding/controller；如果 evaluator 与真实状态不一致，转向 measurement。

13. **即使 task success 不提高仍有用的贡献**

    建立 outcome-observability qualification 和 postcondition contract。

**候选结论：拒绝作为主要 novelty，保留为基础设施优先项。**  
它非常可能解释现有 failure，但 process evaluation、runtime verification 和 GUI testing 已覆盖其广义思想。

---

## 7. 对明显重叠或不合格方向的拒绝表

| 被拒绝方向 | 拒绝理由 | 主要重叠或证据 |
|---|---|---|
| 再设计 planner/executor/memory/critic architecture | 架构分工本身已高度常见，且现有结果没有显示分工带来 task win | [Mobile-Agent-E](https://arxiv.org/abs/2501.11733)、[Agent S2](https://openreview.net/forum?id=zg5is4GJ3R)  |
| 更大的 structured ledger | 增加字段不等于发现机制；还会增加 calls/tokens 和解析错误 | RAVEN-M 当前 M0 成本明显更高但无成功优势  |
| Entity–field–value–source storage 本身 | EEST 只证明窄 capture fidelity；ATMem、HyMEM、EAM 等已有更强表示 | [ATMem](https://arxiv.org/abs/2606.31612)、[HyMEM](https://arxiv.org/abs/2603.10291)、[Executable Agentic Memory](https://arxiv.org/abs/2605.12294)  |
| Confidence、recency、provenance、verification、conflict、supersession labels | 标签本身不是机制；自然生命周期审计中相关事件几乎未出现 | RAVEN-M 10,884 events 审计；经典 provenance/event sourcing  |
| Generic reliability-aware retrieval | 已有 page/workflow/graph/learned retrieval；没有说明为什么会改变具体 action | [PG-Agent](https://arxiv.org/abs/2509.03536)、[Agent Workflow Memory](https://proceedings.mlr.press/v267/wang25bx.html)、[HyMEM](https://arxiv.org/abs/2603.10291)、[MementoGUI](https://arxiv.org/abs/2605.18652)  |
| Page graph、workflow memory、knowledge graph | 该设计空间已经拥挤 | PG-Agent、AWM、MAGNET、EAM、AgentProg  |
| Generic high-risk action verification | Action Reflector、runtime verification、Process Provider 等已有直接近邻 | Mobile-Agent-E、AgentProg、ProBench、runtime verification  |
| 更多 RAG context 或更多 model calls | 与 representation 混入 compute confound；更多历史甚至可能恶化 action grounding | [GTA1](https://arxiv.org/abs/2507.05791)、[Naive Visual Memory Is Not Enough](https://arxiv.org/abs/2606.14106)  |
| Synthetic stale-memory rejection 作为普通 AndroidWorld improvement | 当前自然任务中 stale/superseded 等几乎为零；合成能力不能外推自然收益 | RAVEN-M lifecycle audit；STAMP 等可控 memory benchmark 已存在  |
| 从反复查看同一任务中学习 task-specific rules | 构成 development contamination，难以证明泛化 | EEST task/seed 已受开发污染  |
| “Task length ≠ memory difficulty”作为 headline | AndroTMem 和 AgentProg 已高度重叠 |  |
| Generic role-aware memory | ATMem 已直接覆盖 role/status 与 confusable entries |  |
| 先提出一个新 benchmark | MemGUI-Bench、AndroTMem、MementoGUI、STAMP 已使空间拥挤；当前最缺的是 controlled causal evidence |  |
| 用 all-failure ties 声称 equivalence | 共同 floor 使 treatment effect 不可识别 | Hard 和 v0.2–v0.2.4 证据  |
| 用正确 memory capture 代替 task success | capture、destination binding、execution 和 verification 是不同因果环节 | EEST structured arms 的 4/4 capture 与无 destination/task win 并存  |

---

## 8. 唯一推荐方向的精确定义

### 8.1 中文标题与 English working title

**中文标题：**  
**正确记忆，错误目标：移动 GUI Agent 中的角色绑定放大效应**

**English working title：**  
**Correct Memory, Wrong Target: Causal Role-Binding Amplification in Mobile GUI Agents**

### 8.2 精确 research question

> 在 mobile GUI critical decisions 中，当 agent 获得一条完全正确的 source entity–field–value 记录时，该记录相对 destination grounding 的暴露时序，是否会与 source/destination role ambiguity 发生交互，因果性地改变 agent 首次选择错误目标对象的概率？

该问题刻意不问：

- 整个 AndroidWorld success 是否立即提升；
- 哪种 memory architecture 最强；
- 是否需要更大的 knowledge graph；
- 是否应该训练一个新的 GUI foundation model。

### 8.3 主假设

令：

- \(T\)：correct fact 的暴露时序，`early` 或 `late`；
- \(A\)：source/destination role ambiguity，`high` 或 `low`；
- \(W\)：首次 target-selecting action 是否作用于错误实体；
- \(V\)：exact-value fidelity；
- \(G\)：在 action 前 destination grounding 是否正确。

主要 interaction 为：

\[
\Delta =
\Big[
P(W\mid T=\text{early},A=\text{high})
-
P(W\mid T=\text{late},A=\text{high})
\Big]
-
\Big[
P(W\mid T=\text{early},A=\text{low})
-
P(W\mid T=\text{late},A=\text{low})
\Big].
\]

主假设：

\[
H_1:\Delta>0
\]

即，early exposure 的危害应主要出现在 high-ambiguity 条件，而不是所有任务中普遍出现。

### 8.4 Constructs 的操作化

| Construct | 操作化定义 | 不应混入的因素 |
|---|---|---|
| Correct source fact | source entity、field、value 均由 oracle 提供且内容完全正确 | retrieval recall error |
| Early exposure | 在模型必须输出 destination entity ID 之前提供 fact | 更多总 tokens、更多重复次数 |
| Late exposure | 先要求模型 grounding destination，再提供同一 fact | 不同 UI state 或不同任务 |
| Role ambiguity | source 与 destination 在姓名、列表位置、字段类型、视觉结构或语义角色上具有可混淆性 | 页面总体复杂度、控件数量 |
| Destination grounding | action 前输出唯一 destination entity ID/row ID/widget ID | 最终 tap 是否成功 |
| WrongTarget@FTA | 首个具有明确 target entity 的 proposed action 指向 source 或其他非 destination entity | controller 执行漂移 |
| Binding drift | grounding phase 正确，但 action phase target 改成错误 entity | grounding phase 本身错误 |
| Premature commitment | early fact 使模型在 destination evidence 充分出现前锁定 source-linked target | 普通短期记忆衰减 |
| Infrastructure failure | manipulation 发生前 app、snapshot、parser 或 action contract 已失效 | method failure |

### 8.5 候选机制图

\[
\text{Early correct source fact}
\times
\text{High role ambiguity}
\rightarrow
\text{Source-salient premature commitment}
\rightarrow
\text{Wrong destination binding}
\rightarrow
\text{Wrong-target first action}
\]

需要与以下 alternative explanations 区分：

1. **普通 recency effect：** 后出现的信息总是更强；
2. **position effect：** prompt 前部或后部本身影响注意力；
3. **general grounding weakness：** 即使没有 fact 也认错 destination；
4. **instruction misunderstanding：** 模型没有理解 source 与 destination 的语义；
5. **controller failure：** proposed target 正确，但执行到了错误控件；
6. **retrieval failure：** value 本身记错；
7. **postcondition failure：** action 已正确完成，但系统没有识别成功。

### 8.6 最窄的 novelty claim

在本次检索覆盖范围内，尚未确认有工作同时完成：

1. 固定完全相同且正确的 episodic value；
2. 显式操纵该 value 相对 destination grounding 的暴露顺序；
3. 正交操纵 source/destination role ambiguity；
4. 在 mobile GUI action 上测量 wrong-target interaction；
5. 匹配 model calls、tokens 和 actions。

但 ATMem、Entity Binding Failures、Binding Drift 和 Salience Induction 在 2026 年 6–7 月形成了非常接近的 concurrent prior-art cluster。因此，最强可接受表述只能是：

> **UNRESOLVED：本审计尚未发现完全等价的 intervention，但 role-aware memory、entity binding、binding amplification 和 salience-induced misbinding 均已有直接先例。**

不得使用：

- “first”；
- “unprecedented”；
- “no prior work”；
- “首次发现正确记忆会有害”；
- “首次研究 entity binding”。

### 8.7 Boundary conditions

该假设只预测以下条件：

- source fact 本身正确；
- source 与 destination 是不同实体或不同 role；
- task 需要把 source fact 应用于 destination；
- destination 在 fact 使用前需要从 GUI 中 grounding；
- 存在至少一个可混淆 source/destination cue；
- model 能稳定解析基本任务和输出结构化 target。

它不预测：

- 所有 long-horizon tasks 都有该效应；
- 低歧义任务也有显著 timing effect；
- 事实越早出现总是越差；
- 对所有模型、语言、app 和视觉布局均成立；
- offline critical-state effect 必然转化为 end-to-end task success。

### 8.8 Explicit non-claims

本方向明确不声称：

1. RAVEN-M 已经提高 AndroidWorld aggregate success；
2. structured memory 普遍优于 summary；
3. role-aware memory 是本项目提出的；
4. entity binding 是本项目首先发现的；
5. destination-first gate 是通用 long-horizon solution；
6. 一次 offline action prediction 等价于完整任务成功；
7. 一个模型上的结果可以泛化到全部 GUI agents；
8. 所有 failure 都应归因于 memory；
9. 新 benchmark 是主要贡献；
10. 原始 EEST-P1 本身已经构成 causal evidence。

### 8.9 即使结果为 null，仍然诚实成立的贡献

如果得到可信 null result，仍可保留：

- 一个控制了正确 value、fact timing、role ambiguity 和 compute budget 的 causal test；
- 对 early-fact role-binding amplification 的 effect-size 上界；
- source retention、destination grounding、action targeting、controller execution 与 postcondition verification 的分层协议；
- 一项说明 RAVEN-M 不应继续沿 memory-method 路线扩展的证据；
- 可复用的 critical-state replay 和 first-broken-edge evaluation harness。

---

## 9. Stage 1：廉价 diagnostic gate

### 9.1 目的

Stage 1 不检验完整 AndroidWorld success，也不运行长程 agent。它只回答：

> 是否存在足够大、足够稳定、不能被普通 recency/position effect 解释的 Timing × Role-Ambiguity interaction？

如果没有，就停止该 memory-mechanism 方向，不进入方法开发。

### 9.2 Critical-state replay

从已有或新资格化任务中抽取“即将使用 source fact 的第一个关键 UI 状态”，保存：

- screenshot；
- accessibility/UI tree；
- task instruction；
- source entity、destination entity；
- target field；
- oracle value；
- valid target widget IDs；
- oracle next action；
- negative target IDs。

使用 oracle prefix 或 replay snapshot 到达该状态，从而排除：

- 打不开 app；
- 找不到 source 页面；
- action loop；
- environment initialization；
- delayed transitions；
- unsupported action interface。

这不是新 benchmark，只是 matched causal study 的实验材料。

### 9.3 主 \(2\times2\) 设计

| 条件 | Grounding phase | Action phase |
|---|---|---|
| Early × High ambiguity | 提供正确 fact；要求输出 destination ID | 提供等长 neutral block；要求输出 target/action |
| Late × High ambiguity | 提供等长 neutral block；要求输出 destination ID | 提供同一正确 fact；要求输出 target/action |
| Early × Low ambiguity | 同 Early，但 source/destination 明显可区分 | 同上 |
| Late × Low ambiguity | 同 Late，但 source/destination 明显可区分 | 同上 |

每个 cell 都有两个 calls：

- **Call 1：Grounding**
  - 输出 `destination_entity_id`；
  - 输出 `destination_role`；
  - 输出 confidence；
  - 不执行 live action。

- **Call 2：Action**
  - 输出 `target_entity_id`；
  - 输出 `widget_id`；
  - 输出 action type；
  - 输出使用的 value；
  - 输出 confidence。

Early 与 Late 在两个 calls 中都只出现一次真实 fact；另一个 phase 使用 token-matched neutral block。

### 9.4 Role ambiguity 的控制

High ambiguity 可以通过以下可控变量产生，但每次只改变一类：

- source 与 destination 均为联系人姓名；
- 两者在列表中相邻；
- 姓名长度、词形或头像相似；
- source 与 destination 都具有相同字段类型；
- instruction 同时提及两者；
- UI 中 source 最近被访问；
- source row 与 destination row 使用相同 layout。

Low ambiguity matched condition：

- destination 有唯一显著标签；
- source 不在当前列表；
- 两者视觉和名称差异大；
- instruction 中 destination role 显式且唯一。

不应通过增加页面控件总量来制造 high ambiguity，否则 ambiguity 会与一般 UI difficulty 混淆。

### 9.5 必要的 negative controls

| Control | 排除的 alternative explanation |
|---|---|
| Low-ambiguity early/late | 排除“所有 early fact 都有害” |
| Task-literal value | 排除 episodic-memory 特异性；值直接写在任务中 |
| Irrelevant same-format fact | 排除单纯增加一个地址/号码字符串的影响 |
| Position placebo | 在相同位置放置与 target 无关但等长的事实 |
| Recency placebo | 仅改变 neutral information 的早晚顺序 |
| Source/destination label swap | 检验 effect 是否跟随语义 role，而不是固定姓名或列表位置 |
| Destination-provided control | 直接提供正确 destination ID，检验 early fact 是否仍能造成 post-grounding drift |
| No-commitment control | Call 1 不要求输出 destination ID，检验显式 commitment 是否是机制的一部分 |
| Delay-only control | 两阶段之间加入同样延迟，但不改变 fact timing |
| No-memory/local-visible control | value 在当前 UI 中直接可见，不依赖 episodic record |

### 9.6 Budget matching

| 项目 | 匹配规则 |
|---|---|
| Model | 固定同一模型名称、revision 或 hash |
| Decoding | greedy 或固定 temperature/seed |
| Calls | 每个 cell 固定 2 calls |
| Prompt tokens | phase-level 与 total-level 均限制在预设容差内；必要时 padding |
| Completion tokens | 相同上限和输出 schema |
| Screenshots | 同一图像 bytes 或 hash |
| UI tree | 同一版本 |
| Action budget | Stage 1 不执行 live action；每个 cell 只允许一个 proposed target action |
| Tools | 不允许额外 search/retrieval/tool call |
| Memory content | early/late 使用完全相同的正确 fact |
| Retry | 不允许 selective retry；解析失败按预注册规则计入 |
| Wall-time measurement | 记录但不作为主要机制变量 |

### 9.7 Outcomes

#### Primary outcome

\[
\texttt{WrongTarget@FirstTargetingAction}
=
\mathbf{1}
[\text{first target entity}\ne\text{oracle destination}]
\]

使用 first targeting action，而不是最终自我修正后的 action，原因是它最接近 hypothesized premature commitment。

#### Key diagnostic outcomes

1. `DestinationID@Grounding`；
2. `DestinationID@Action`；
3. `PostGroundingDrift`：
   \[
   G_{\text{call1}}=\text{correct},
   \quad
   G_{\text{call2}}=\text{wrong}
   \]
4. `ExactValueRecall`；
5. `SourceAsTargetRate`；
6. `OtherWrongEntityRate`；
7. `CorrectTargetWrongWidgetRate`；
8. role classification accuracy；
9. confidence calibration；
10. parser/schema failure rate。

#### Cost metrics

- model calls；
- prompt tokens；
- completion tokens；
- proposed actions；
- live actions；
- wall time；
- retry count；
- invalid-output rate。

### 9.8 资格阈值

在解释 role-binding effect 前，数据必须满足：

- `ExactValueRecall ≥ 95%`；
- snapshot 和 oracle target qualification 通过率 ≥ 95%；
- parser/schema failure ≤ 5%；
- manipulation 前 infrastructure failure ≤ 10%；
- low-ambiguity baseline target accuracy 足够高，例如 ≥ 80%。

如果 exact value 都无法稳定保持，实验检验的是 retrieval failure，不是 correct-memory binding。

### 9.9 统计分析

主要模型可以使用 conditional logistic regression：

\[
\operatorname{logit}P(W=1)
=
\beta_0
+
\beta_T T
+
\beta_A A
+
\beta_{TA}(T\times A)
+
u_{\text{template}}
\]

主要检验：

\[
H_0:\beta_{TA}=0
\]

同时报告：

- absolute risk difference；
- relative risk；
- paired McNemar test；
- cluster bootstrap confidence intervals；
- template-level random effect 或 fixed effect；
- source-as-target 与 other-wrong-target 的分解。

分析单位应是 matched task instance，而不是 model call 或 memory event。多个 counterbalanced variants 必须按 base template 聚类。

### 9.10 Sample-size reasoning

对 paired binary outcome，使用近似：

\[
n
\approx
\frac{(z_{0.975}+z_{0.80})^2p_d}{\delta^2},
\]

其中：

- \(p_d\) 为 pair 中 discordant outcome 的比例；
- \(\delta\) 为 early 与 late 的 paired absolute difference。

若预期：

\[
p_d=0.40,\qquad \delta=0.20,
\]

则：

\[
n
\approx
\frac{(1.96+0.84)^2\times0.40}{0.20^2}
=
78.4.
\]

考虑 template clustering、invalid cells 和资格失败，confirmatory study 至少需要约：

> **100 个 retained high-ambiguity matched pairs**

最好来自至少 50 个 base templates，并为每个 template 使用 source/destination counterbalancing。若 pilot 显示 cluster correlation 较高，则应进一步增加，而不是把同一模板的重复采样当作独立样本。

### 9.11 廉价 gate 的规模

先运行：

- 48 个 qualified base instances；
- 4 个主 factorial cells；
- 共 192 个 critical decisions；
- 每个 decision 固定两个 calls。

这一规模只用作 screening gate，不做最终“普遍机制成立”的 claim。

### 9.12 进入 Stage 2 的 gate

只有同时满足以下条件才进入方法实验：

1. high-ambiguity 条件中，early 相对 late 的 wrong-target increase 至少约 15 percentage points；
2. Timing × Ambiguity interaction 的 paired/clustered 95% CI 不包含 0；
3. exact-value fidelity ≥ 95%；
4. low-ambiguity early–late difference 不超过约 5 percentage points；
5. position/recency placebo 不能解释主要效应；
6. effect 在 source/destination swap 后随语义 role 移动；
7. 至少一个机制指标支持 premature commitment，例如 source-as-target 增加或 grounding 后 drift 改变。

15 percentage points 被设为 gate，不是因为较小效应“不科学”，而是因为若 effect 太小，就不足以证明额外 grounding call 或 gate 的工程成本是合理的。

---

## 10. Stage 2：仅在 gate 通过后测试最小方法

### 10.1 方法名称

**Destination-First Binding Gate / Deferred Value Exposure**

它不是新的 memory architecture，而是一个最小的 decision-order intervention。

### 10.2 方法步骤

1. **Grounding call**
   - 输入当前 UI；
   - 不暴露 retrieved value；
   - 输出唯一 `destination_entity_id`、role 和 target field；
   - 将 destination commitment 固定为结构化 ID。

2. **Action call**
   - 暴露完全正确的 retrieved value；
   - 将 value 绑定到已 commitment 的 destination ID；
   - 输出 target widget/action。

3. **Optional re-verification**
   - 仅当当前 UI 与 commitment 的 destination ID 不一致时触发；
   - 不能无条件增加第三个 model call。

### 10.3 Matched comparators

| Arm | Call 1 | Call 2 | 目的 |
|---|---|---|---|
| Early-value baseline | 先看到 value，再输出 destination | 输出 action | 原始 hypothesized risk condition |
| Destination-first gate | 不看 value，先输出 destination | 再看到 value 并输出 action | 目标方法 |
| Delay-only control | 不要求 destination commitment，仅推迟 value | 输出 action | 区分“推迟”与“先 grounding” |
| Explicit-role-label control | value 仍早出现，但加 source/destination role labels | 输出 action | 检验简单 prompting 是否已经足够 |
| No-memory/task-literal control | value 作为任务文字而非 memory record | 输出 action | 判断 effect 是否对 episodic framing 特异 |

所有 arms 必须匹配：

- 两次 calls；
- token ceilings；
- action budget；
- screenshot/UI tree；
- value 内容；
- decoding；
- retry policy。

不能让方法 arm 通过更多 calls 获得隐性 test-time compute 优势。

### 10.4 实验顺序

#### Stage 2A：confirmatory critical-state experiment

- 至少 100 个 retained high-ambiguity matched pairs；
- 预注册主要 outcome、exclusion、gate 和 analysis；
- 使用未参与 pilot prompt 调整的 held-out templates；
- evaluator 对 condition blind；
- 报告所有 invalid cells，不进行 selective rerun。

#### Stage 2B：小规模 live transport check

只有 2A 成功后，再运行约 24–32 个 held-out live end-to-end matched pairs。

该规模主要回答：

> critical-state action improvement 是否能穿过 controller 和 postcondition pipeline？

它通常不足以支撑精确的 aggregate task-success superiority claim。因此：

- critical-state wrong-target reduction 可以是 confirmatory；
- live task success 只能作为 transport evidence 或 direction check；
- 如果 live success 为 null，不得声称整体 memory efficacy 已被证明。

### 10.5 Primary and secondary outcomes

**Stage 2A primary：**

- `WrongTarget@FirstTargetingAction`。

**Stage 2B co-primary：**

- end-to-end task success；
- destination-correct first action。

**Diagnostics：**

- correct destination commitment；
- post-commitment drift；
- exact-value fidelity；
- action-interface validity；
- postcondition verification accuracy；
- first-broken edge。

**Costs：**

- calls；
- tokens；
- actions；
- wall time；
- invalid outputs；
- additional observations。

### 10.6 认为方法有继续价值的最低结果

至少满足：

- wrong-target rate 绝对下降 ≥ 10 percentage points，或相对下降 ≥ 20%；
- paired confidence interval 的方向为正且不跨越零；
- effect 不只来自一个模板、app 或姓名组合；
- calls 保持匹配；
- tokens、actions 或 wall time 不增加超过约 10%；
- exact-value fidelity 不下降；
- live task success 至少不显示明确负方向。

如果只改善 target action，而 task success 没有改善，论文结论必须收窄为：

> destination-first ordering 改善了 role-binding decision，但 downstream controller/postcondition floors 阻止了 task-level transport。

这时应停止扩展 memory method，转向 controller 或 verification。

---

## 11. Continue、revise、stop 与 pivot 规则

| 观察结果 | 科学解释 | 决策 |
|---|---|---|
| Stage 1 出现稳定 Timing × Ambiguity interaction，placebo 不解释 | 候选机制获得初步支持 | **Continue**：进入 Stage 2，但 novelty 仍标记 UNRESOLVED |
| Stage 1 interaction 接近零且 CI 排除有工程意义的效应 | 早暴露正确事实不是主要瓶颈 | **Stop**：停止 role-binding memory 方法路线 |
| Early 与 Late 在 high/low ambiguity 中同样不同 | 更像一般 recency/position effect | **Revise**：改为 prompt-order/salience 研究；不再声称 role binding |
| Destination 在 fact 暴露前已经频繁识别错误 | 基础 visual/semantic grounding 不足 | **Pivot to grounding/perception** |
| ExactValueRecall < 95% | 实验没有满足“正确记忆”前提 | **Pivot to retention/retrieval qualification**，暂不检验 role binding |
| Grounding call 正确，但 action call target 漂移到 source | 支持 post-grounding binding drift | **Continue narrowly**，重点分析 commitment persistence |
| Proposed target/action 正确，live controller 执行错误 | memory-use 不是当前 task-success floor | **Pivot to controller/action interface** |
| 动作生效但 agent 重复或 premature done | outcome observability/postcondition 问题 | **Pivot to runtime verification/evaluation** |
| Critical-state effect 为正，live task success 为 null | 机制存在但未转化为系统成功 | **Revise claim** 为 diagnostic contribution；停止扩大 memory stack |
| Critical-state 与 live task success 都改善，成本匹配 | 最强正结果 | **Continue**：在第二模型、第二 app family、held-out tasks 上确认 |
| 结果只在一个模型成立 | model-specific interaction | **Narrow scope**，不做 general GUI-agent claim |
| Late condition反而更差 | 可能是普通 memory decay 或 delayed retrieval cost | **Reject original mechanism**，重新分析 recency/working-memory explanation |
| >10% cells 在 manipulation 前 infrastructure failure | treatment effect 被 qualification floor 污染 | **Infrastructure-limited**：不做 efficacy claim，先修 replay/collector |
| 新发现的 concurrent paper 已做完全相同 factorial intervention | novelty 不成立 | **Stop novelty claim**；最多作为 independent replication |
| 所有 arms 都失败 | 不可识别 | **No equivalence claim**；回到 first-broken-edge 分析 |
| 所有 arms 都成功 | ceiling effect | **Revise task qualification**，提高 ambiguity 而不是增加框架模块 |

---

## 12. 两周执行计划

| 日期 | 任务 | 必须产出 | Stop condition |
|---|---|---|---|
| Day 1 | 冻结 primary-source novelty ledger；逐项核对 ATMem、Entity Binding、Binding Drift、Salience Induction supplements/code | overlap–distinction 表；明确 UNRESOLVED 范围 | 若发现完全等价 intervention，停止 novelty 路线 |
| Day 2 | 预注册 RQ、DAG、constructs、outcomes、exclusion、budgets、gate 和 decision rules | preregistration Markdown；不可事后修改的 primary metric | 无法定义唯一 wrong target 或 oracle target 时停止该任务 |
| Day 3 | 实现 critical-state replay schema | snapshot、UI tree、source/destination IDs、oracle action、hash | replay 无法稳定复现则先修基础设施 |
| Day 4 | 实现 exact-token early/late prompt builder 和 structured-output parser | 两阶段 matched calls；token audit | phase-level token 差异无法控制则不运行 |
| Day 5 | 8-template qualification pilot | value fidelity、grounding ceiling、parser failure、ambiguity manipulation check | ExactValueRecall <95% 或 low-ambiguity accuracy <80% |
| Day 6 | 扩展并冻结 48 个 base instances；进行 source/destination counterbalancing | 不再调整的 Stage 1 corpus | 明显 template leakage 或 task contamination |
| Day 7 | 运行 Stage 1 主 \(2\times2\) factorial 与关键 placebos | 192 critical decisions 和完整成本日志 | infrastructure failure >10% |
| Day 8 | Blind analysis；计算 interaction、paired effects、cluster bootstrap 和 mechanism diagnostics | Stage 1 gate verdict | gate 不通过则停止方法开发 |
| Day 9 | 若 gate 通过，实现 destination-first gate；若未通过，转为 grounding/controller failure audit | 最小方法或正式 pivot report | 禁止新增 ledger/module 来“挽救”null |
| Day 10 | 对 Stage 2 arms 做独立 qualification | call/token/action budget equivalence report | 方法 arm 获得额外 compute 则重做设计 |
| Day 11 | 运行 Stage 2A confirmatory subset/首批 matched pairs | blind evaluator 输出 | effect 方向反转则暂停扩展 |
| Day 12 | 完成 Stage 2A；若环境稳定，运行少量 held-out live transport pairs | confirmatory action结果；descriptive live结果 | controller floor 再次主导则停止 live efficacy claim |
| Day 13 | 进行 first-broken-edge forensic analysis | retention、grounding、binding、execution、verification 分层表 | 不允许把 downstream failure 重新标成 memory failure |
| Day 14 | 冻结代码、数据、报告和 claims | continue/revise/stop/pivot 最终决策；可复现脚本 | 没有通过预注册 gate 时，不写方法 superiority narrative |

若 Stage 1 在 Day 8 失败，Day 9–14 不应继续“调 prompt 直到有效”，而应完成：

- effect-size upper bound；
- grounding/controller/postcondition error decomposition；
- RAVEN-M 作为 instrumentation harness 的整理；
- 终止 memory-method 主线的书面依据。

---

## 13. 面向导师的第一人称说明

我不再把下一步定义为继续完善 RAVEN-M。现有结果只证明结构化记录可以把 Petar Muller 的地址记对，没有证明系统能把地址用于 Gabriel Fernandez；legacy 结果里简单摘要还完成了 4/4，而完整 RAVEN-M 是 3/4 且成本更高。更重要的是，广义的“依赖结构比任务长度重要”已经与 AndroTMem、AgentProg 高度重叠，角色化状态也被 ATMem 直接覆盖。我准备先做一个很小的因果实验：在任务、截图、正确事实、模型、calls、tokens 和 actions 都匹配时，只改变正确事实是在目标联系人完成定位之前还是之后出现，检验高角色歧义下的错发对象率是否上升。若没有稳定的 Timing × Ambiguity interaction，我会停止把项目包装成新的记忆方法，转向 grounding、controller 或 postcondition evaluation；若效应成立，再测试一个最小的 destination-first gate，而不是继续扩展整个框架。

---

## 14. 尚未解决的假设与仍需补证的 claims

| 未解决事项 | 当前状态 | 所需证据 |
|---|---|---|
| 是否已有论文做过完全相同的 timing × role ambiguity factorial | **UNRESOLVED**；ATMem、Binding Drift、Salience Induction 极为接近 | 逐页检查 supplements、appendices、代码和实验配置，而不只看 abstract |
| ATMem 的 DataScope 是否已经隐含操纵 value exposure order | 本次检索确认了 role/status 与 confusable distractors，但未确认完全相同的顺序 intervention | 检查完整实验表和 prompt templates |
| Entity Binding Failures 是否包含 mobile GUI target selection | 已确认 wrong-entity tool actions，但具体 GUI overlap 需要继续核实 | 检查任务域、action schema 和 entity-aware baselines |
| Early/late manipulation 是否只是 prompt position effect | 高风险 alternative explanation | position、recency 和 irrelevant-fact placebos |
| 显式 destination commitment 是否是中介，而不是额外 reasoning compute | 未知 | 两个 calls 完全匹配；delay-only 和 no-commitment controls |
| Critical-state replay 是否能外推 live GUI | 未知 | Stage 2B held-out transport check |
| High role ambiguity 的操作化是否具有 construct validity | 未知 | manipulation check；人类或独立模型判断；多种 ambiguity 类型复现 |
| EEST-P1 的 failure 是否真的由 role binding 引起 | 当前只是一条动机，不是 causal evidence | 新的 matched intervention；原始日志不能替代 |
| 该效应是否跨模型成立 | 未知 | 主模型通过后再使用第二个冻结模型验证 |
| 该效应是否跨 app family 成立 | 未知 | held-out app families；不以同一联系人 app 的重复采样冒充泛化 |
| destination-first gate 的额外 call 是否值得 | 未知 | matched two-call baseline 与成本阈值 |
| WrongTarget@FTA 是否会转化为 task success | 未知 | live transport study；不能从 offline action 直接推断 |
| 当前 AndroidWorld 环境是否足以进行 end-to-end confirmatory study | 尚未证明 | qualification pass rate、action contract、terminal evaluator、state-transition reliability |
| 原生任务中 source/destination role ambiguity 是否足够常见 | 尚无 prevalence estimate | 在 held-out tasks 中 blind annotation，不以合成例子代替自然频率 |
| Null result 是否可能来自 ceiling/floor | 高风险 | low-ambiguity ceiling qualification 与 high-ambiguity nonzero baseline |
| Concurrent work 的正式发表状态 | 多数为 preprint | 在投稿前再次检查 proceedings、OpenReview 和作者官方仓库 |
| Broad task-length reframing 是否仍有可发表价值 | 作为主 novelty 不足；作为控制设计有价值 | 在推荐实验中作为 covariate，而不是单独立项 |

---

## 15. Primary-source audit ledger

### 15.1 RAVEN-M repository evidence

| 文件 | 在本审计中的用途 |
|---|---|
| [README.md](https://github.com/ScottBlizzard/RAVEN-M/blob/main/README.md) | legacy B3/M0、EEST、v0.2–v0.2.4 总结；区分 valid record 与 efficacy，反对 all-failure equivalence  |
| [GPTPRO_NOVEL_IDEA_AUDIT_BRIEF_2026-08-04.md](https://github.com/ScottBlizzard/RAVEN-M/blob/main/reports/research_direction/GPTPRO_NOVEL_IDEA_AUDIT_BRIEF_2026-08-04.md) | 候选 reframing、实验事实与待拒绝方向  |
| [ANDROIDWORLD_HARD_FAILURE_INFORMATION_CHAIN_AUDIT_2026-08-04.md](https://github.com/ScottBlizzard/RAVEN-M/blob/main/reports/research_direction/ANDROIDWORLD_HARD_FAILURE_INFORMATION_CHAIN_AUDIT_2026-08-04.md) | 95 cells、supported/unsupported tasks、重复动作、无 screenshot change、M0 成本和 first-broken-edge  |
| [RAVEN-M_研究假设与实验方向审计_2026-08-03.md](https://github.com/ScottBlizzard/RAVEN-M/blob/main/RAVEN-M_%E7%A0%94%E7%A9%B6%E5%81%87%E8%AE%BE%E4%B8%8E%E5%AE%9E%E9%AA%8C%E6%96%B9%E5%90%91%E5%AE%A1%E8%AE%A1_2026-08-03.md) | lifecycle event 与 contradiction audit  |
| [eest_ac_smoke_v0_1_1_analysis.md](https://github.com/ScottBlizzard/RAVEN-M/blob/main/reports/eest_ac/eest_ac_smoke_v0_1_1_analysis.md) | 4/4 source binding、所有 arms 1/2、destination failure、truncation/evaluator 和 contamination  |
| [claim_evidence_v0_1_1_verdict.md](https://github.com/ScottBlizzard/RAVEN-M/blob/main/reports/eest_ac/claim_evidence_v0_1_1_verdict.md) | claim 与 evidence 的资格判断 |
| [eest_ac_v0_2_blind_smoke_analysis.md](https://github.com/ScottBlizzard/RAVEN-M/blob/main/reports/eest_ac/eest_ac_v0_2_blind_smoke_analysis.md) | blind smoke 的 action/environment floor  |
| [eest_ac_v0_2_2_qualification_final_report.md](https://github.com/ScottBlizzard/RAVEN-M/blob/main/reports/eest_ac/eest_ac_v0_2_2_qualification_final_report.md) | action schema 与 terminal measurement floor  |
| [eest_ac_v0_2_3_collection_floor_verdict.md](https://github.com/ScottBlizzard/RAVEN-M/blob/main/reports/eest_ac/eest_ac_v0_2_3_collection_floor_verdict.md) | collection corpus 未形成 |
| [eest_ac_v0_2_4_collector_lifecycle_verdict.md](https://github.com/ScottBlizzard/RAVEN-M/blob/main/reports/eest_ac/eest_ac_v0_2_4_collector_lifecycle_verdict.md) | settings/readiness 与 collector lifecycle floor  |

### 15.2 GUI-agent、memory 与 evaluation primary sources

| 工作 | 状态与本审计使用方式 |
|---|---|
| [AndroidWorld](https://arxiv.org/abs/2405.14573) | ICLR 2025 published；116 个 programmatic tasks、20 个 apps、动态初始化与评估，是 RAVEN-M 环境判断的基础  |
| [PG-Agent](https://arxiv.org/abs/2509.03536) | ACM MM 2025 accepted；page graph、episode-derived knowledge 与 perception guidelines，压缩 page/workflow-memory novelty  |
| [History-Aware Reasoning for GUI Agents / HAR-GUI](https://arxiv.org/abs/2511.09127) | AAAI 2026 accepted；reflective learning、correction guidelines、episodic reasoning，压缩 generic history-aware reasoning claim  |
| [ProBench](https://arxiv.org/abs/2511.09157) | AAAI 2026 accepted；200+ mobile tasks、process-related evaluation 与 Process Provider，压缩 generic process-evaluation claim  |
| [MP-GUI](https://openaccess.thecvf.com/content/CVPR2025/html/Wang_MP-GUI_Modality_Perception_with_MLLMs_for_GUI_Understanding_CVPR_2025_paper.html) | CVPR 2025 published；textual、graphical、spatial perceivers 和 fusion gate  |
| [Mobile-Agent-E](https://arxiv.org/abs/2501.11733) | preprint；Manager、Perceptor、Operator、Action Reflector、Notetaker，以及 Tips/Shortcuts persistent memory  |
| [Mobile-Agent-v3.5](https://arxiv.org/abs/2602.16855) | preprint；本次检索覆盖的较新 Mobile-Agent family 工作，包含多平台、多尺寸和广泛 benchmarks  |
| [Agent Workflow Memory](https://proceedings.mlr.press/v267/wang25bx.html) | ICML 2025 published；离线/在线诱导、检索和复用 workflow  |
| [HyMEM](https://arxiv.org/abs/2603.10291) | preprint；symbolic graph、trajectory embeddings、多跳 retrieval 和 working-memory refresh  |
| [MAGNET](https://aclanthology.org/2026.acl-long.1299/) | ACL 2026 published；stationary/procedural memory 与动态演化  |
| [Executable Agentic Memory](https://arxiv.org/abs/2605.12294) | preprint；KG、retrieval-and-execution、state-aware action-group mining 和 search  |
| [MemGUI-Bench](https://arxiv.org/abs/2602.06075) | preprint；作者官方仓库标记 ACM MM 2026 accepted，本审计未核对正式 proceedings；128 tasks、26 apps、staged evaluation  |
| [Agent S2](https://openreview.net/forum?id=zg5is4GJ3R) | COLM 2025 published；Mixture-of-Grounding 与 Proactive Hierarchical Planning  |
| [AndroTMem](https://arxiv.org/abs/2603.18429) | preprint；1,069 tasks、平均约 32.1 steps、强跨步骤 causal dependencies 与 sparse anchors；是广义 dependency reframing 的最直接 novelty threat  |
| [AgentProg](https://arxiv.org/abs/2512.10371) | preprint；program variables、data-flow persistence、control-flow pruning、global belief state 和 runtime verification  |
| [What Memory Do GUI Agents Really Need? / ATMem](https://arxiv.org/abs/2606.31612) | preprint、concurrent；role/status tracking、memory-on/off intervention、near-identical/confusable entries，是推荐方向最强近邻之一  |
| [Entity Binding Failures in Tool-Augmented Agents](https://arxiv.org/abs/2606.30531) | preprint、concurrent；系统研究正确 tool 下的 wrong-entity actions，并比较 entity-aware mechanisms  |
| [Binding Drift in Multi-Step Tool-Augmented Agents](https://arxiv.org/abs/2607.18316) | preprint、concurrent；研究 entity binding 的持续、放大与 re-verification  |
| [Salience Induction against Multi-Hop RAG Agents](https://arxiv.org/abs/2607.17535) | preprint、concurrent；truth-preserving position、emphasis、proximity 可以重定向 attribute binding  |
| [Naive Visual Memory Is Not Enough](https://arxiv.org/abs/2606.14106) | preprint；更多视觉历史可能改善 state-level 指标但恶化 action-level grounding  |
| [Temporal UI State Inconsistency in Desktop GUI Agents](https://arxiv.org/abs/2604.18860) | preprint；研究 observation–action TOCTOU gap 和执行前再确认  |
| [Why Are GUI Agents Correct but Late?](https://arxiv.org/abs/2607.28399) | preprint、concurrent；研究 transient events、decode latency critical path 和预编译 policy structures  |
| [MementoGUI](https://arxiv.org/abs/2605.18652) | preprint；learned memory selection、compression、retrieval 与 working/episodic memory  |
| [STAMP](https://arxiv.org/abs/2605.29324) | preprint；可控虚拟环境中操纵何时 encode/retrieve，压缩“先做新 benchmark”的空间  |
| [GTA1](https://arxiv.org/abs/2507.05791) | preprint；多 proposal 加 judge 的 test-time scaling，说明更多 calls 应独立作为 compute treatment  |

### 15.3 邻近领域 primary sources

| 工作 | 对本审计的作用 |
|---|---|
| [Planning and Acting in Partially Observable Stochastic Domains](https://people.csail.mit.edu/lpk/papers/aij98-pomdp.pdf) | POMDP belief-state 基础，说明历史压缩为决策状态是经典问题  |
| [Program Slicing](https://ieeexplore.ieee.org/document/5010248/) | 数据依赖和与目标计算相关的历史选择，限制 generic dependency-memory novelty  |
| [Why and Where: A Characterization of Data Provenance](https://link.springer.com/chapter/10.1007/3-540-44503-X_20) | why/where provenance 的经典形式化，限制 provenance-field novelty  |
| [An Event-Flow Model of GUI-Based Applications for Testing](https://www.cs.umd.edu/~atif/papers/MemonSTVR2007.pdf) | GUI event-flow、测试路径和 oracle 的直接先例  |
| [Verification of Workflow Nets](https://link.springer.com/chapter/10.1007/3-540-63139-9_48) | workflow correctness 与 Petri-net verification 的先例  |
| [A Brief Account of Runtime Verification](https://www.isp.uni-luebeck.de/research/publications/brief-account-runtime-verification) | 运行时监测和干预的基础，不支持 generic verification novelty  |
| [Active Perception](https://doi.org/10.1109/5.5968) | 任务导向、主动控制感知的经典工作  |
| [Track-to-track fusion using out-of-sequence track information](https://ieeexplore.ieee.org/document/4408008/) | 异步和乱序观测融合的近邻理论  |
| [RUDDER](https://proceedings.neurips.cc/paper/2019/hash/16105fb9cc614fc29e1bda00dab60d41-Abstract.html) | delayed outcome 与 credit redistribution，说明从末端失败追溯早期 dependency 是既有问题族  |
| [Event Sourcing](https://martinfowler.com/eaaDev/EventSourcing.html) | 状态变化的事件序列化记录；属于经典工程模式而非本项目的新研究机制  |

## 16. 最终研究决策

最终建议不是继续“完善 RAVEN-M”，也不是立即提出一个更大的 memory benchmark。

最终建议是：

> **将 RAVEN-M 从待证明优越性的 memory system，改造成 controlled causal instrumentation；首先检验“正确事实在 destination grounding 前暴露，是否会在高角色歧义下放大 wrong-target action”这一窄机制。**

该方向只有在 Stage 1 diagnostic gate 通过后，才允许进入 destination-first method experiment。

若 Stage 1 为 null：

> **停止 memory-method 主线，转向 perception、grounding 或 controller。**

若 critical-state action 改善但 live task success 为 null：

> **保留机制诊断贡献，停止扩大 memory framework，并转向 execution/postcondition pipeline。**

若两阶段都获得预算匹配、held-out、可重复的正结果：

> 才能把项目收窄为一篇关于 **fact-exposure order、role ambiguity 与 wrong-entity action** 的机制论文，而不是一篇声称 RAVEN-M 普遍解决 long-horizon GUI memory 的系统论文。