# RAVEN-M GPT Pro 全权科学决策与终止执行计划（2026-08-05）

> **目标文件名：** `RAVEN-M_GPTPro_full_plan_2026-08-05.md`  
> **目标分支：** `protocol-v2-exploratory`  
> **科学决策者：** GPT Pro  
> **本地 Codex 角色：** execution engineer only  
> **决策状态：** `BINDING`  
> **最终结论：** `STOP_RESEARCH_METHOD`  
> **允许的后续工作：** `SCIENTIFIC_CLOSEOUT_ONLY`

---

## 1. 绑定性最终裁决

RAVEN-M **不应继续作为一个独立的“新型 GUI-agent memory method / memory mechanism”研究项目推进**。当前分支应立即进入科学封存与负结果整理阶段，而不是继续设计新假设、增加新模块、修改任务、扩展 pilot、修复 AndroidWorld 基础设施，或实现新的 memory/verification/grounding 方法。

本裁决包含四个同时生效的决定：

```yaml
final_decision: STOP_RESEARCH_METHOD
retain_as_engineering_baseline: true
retain_as_negative_results_archive: true
primary_research_direction: NONE
new_hypothesis_authorized: false
new_model_calls_authorized: false
new_androidworld_runs_authorized: false
new_method_implementation_authorized: false
new_infrastructure_program_authorized: false
automatic_pivot_authorized: false
```

这不是“暂时缺少一个好实验”的 AMBER 状态，而是针对**当前 RAVEN-M 研究叙事、当前证据链和当前最接近文献**作出的 RED/STOP 决定。原因不是 GUI-agent memory 不重要，而是：

1. 当前项目没有证明 RAVEN-M 的 task-level 净收益；
2. 项目中最清楚的正信号仅限于局部 source–entity–value 记录正确，不会自动转化为正确目标选择或任务成功；
3. AndroidWorld Hard 的主要失败发生在 memory 可检验节点之前；
4. 最新的 `Correct Memory, Wrong Target` reminder-timing 假设已按预注册规则停止；
5. v0.2 与 v0.3 的主要差异更符合普通 destination grounding / semantic identifiability，而不是新的 memory mechanism；
6. 剩余最有科学含量的 screenshot–accessibility temporal skew / cross-modal conflict 方向，已经被更接近、规模更大、包含 AndroidWorld 行为后果和 mitigation 的同期工作直接覆盖；
7. 继续投入的预期 scientific information gain 已低于整理负结果和封存证据的价值。

因此，不再选择新的 primary direction。用户要求“若方向仍值得继续，只能选择一个 primary direction”；本计划的判断是**没有方向通过继续门槛**，故 `primary_research_direction: NONE`。

---

## 2. 决策范围、证据优先级与执行权边界

### 2.1 本计划覆盖的证据范围

本决策整合以下当前分支证据，而不是只依赖 handoff 或最后一份 verdict：

- 根目录和 research-direction reports；
- legacy RAVEN-M baseline/full-system 结果；
- 全部 EEST-AC 阶段性报告和冻结判定；
- AndroidWorld Hard failure-chain audit；
- role-binding-timing 的 protocol、contract、v0.1–v0.3 配置、实现、测试、preflight certificate、summary 和 raw per-cell outputs；
- M1–M14 以及 r52–r59 等历史基础设施、freshness、lifecycle 和 proof-binding 工作；
- 最新 `Correct Memory, Wrong Target` stop verdict；
- 当前实现所能支持与不能支持的科学结论。

分支 README 本身已经明确区分：测试通过不等于方法有效、记录合法不等于使用正确、局部 guard 正确不等于 task success、全失败并列不等于方法等价、开发中使用过的任务不能重新命名为 held-out。该解释原则与本计划一致。

### 2.2 证据优先级

发生冲突时，Codex 必须机械采用以下优先级，不得自行解释：

1. **Raw per-cell artifacts / raw trajectories / frozen machine-readable outputs**
2. **与 raw 对应的冻结 summary 和 stop verdict**
3. **预注册 protocol、qualification gate 和 contract**
4. **实现与测试**
5. **后验诊断报告**
6. **研究方向建议或 brainstorm**
7. **任何由本地 executor 独立提出但未获本计划授权的方向**

旧的研究方向建议不能覆盖新的 raw negative evidence。executor 后来独立提出的 `Destination-First Binding Gate`、generic workflow memory、额外 verifier、更多 planner/critic 模块或其他未授权 redesign 均无科学决策效力。

### 2.3 GPT Pro 与 Codex 的权限边界

GPT Pro 独占以下权力：

- 研究问题与 hypothesis；
- task、state、arm、prompt 和 model 的选择；
- causal estimand；
- outcome、diagnostic 和 cost metric；
- threshold、sample size 和统计规则；
- continue/revise/stop/pivot；
- novelty interpretation；
- claims allowed/forbidden。

Codex 只可：

- 读取文件；
- 校验 raw 与 summary；
- 生成本计划明确要求的封存文件；
- 计算文件 hash；
- 运行纯离线、无模型、无 Android 环境的完整性检查；
- 在触发停止条件时输出机械式异常包。

Codex 不得把“发现一个可能有趣的现象”转化成新研究方向，也不得因为某个旧报告中的建议而自行执行新实验。

---

## 3. 当前证据实际建立了什么

### 3.1 Legacy RAVEN-M：没有 task-level 净收益证据

在 legacy 四任务对照中，简单摘要 baseline B3 完成 4/4，而完整 RAVEN-M M0 完成 3/4；M0 同时使用更多 actions、model calls 和 tokens。现有审计记录的成本增量约为：actions +27%、calls +38.6%、prompt tokens +69.5%、completion tokens +84.4%。该样本很小，不能证明“所有 structured memory 都有害”，但足以否定“本项目已经证明完整 RAVEN-M 优于简单 baseline”这一说法。

因此，legacy 证据允许的结论是：

> 在该冻结的小规模配对设置中，完整 RAVEN-M 没有取得 task-success 优势，并出现更高执行成本。

不允许的结论是：

> Structured memory 一般无效，或 RAVEN-M 已被统计学证明普遍劣于所有 baseline。

### 3.2 EEST-AC：记录正确与任务正确被明确分离

最有信息量的 EEST v0.1.1 smoke 包含 2 个模板、1 个 seed、4 个 arms，共 8 个 cells。四个 arms 都完成 1/2：EEST-N1 全部成功，EEST-P1 全部失败，因此 intent-to-treat 没有任何方法获得 paired task win。

但 structured-memory arms 在 4/4 相关记录中正确保存了：

- source entity：`Petar Muller`
- field：`event_address`
- exact value：正确地址

即使如此，agent 仍没有导航到正确 destination entity `Gabriel`。B3 也曾把正确地址发送给错误对话对象，并因界面 checkmark 过早判定任务完成。由此，项目真正证明的是：

> 狭窄设置中的 source–entity–field–value capture/retention 可以正确，同时 destination-role selection、action execution 和 completion judgment 仍然失败。

这不是 task-level memory benefit，而是一个负面的 pipeline decomposition：**正确记录不是正确使用的充分条件**。

### 3.3 AndroidWorld Hard：绝大多数失败发生在 memory-testable edge 之前

AndroidWorld Hard 审计覆盖 95 个 cells，仅 1 个成功。15 个 QA cells 因 action interface 中没有 `answer` action 而在结构上不可支持；剩余 80 个受支持 cells 中：

- 1 success；
- 50 budget exhaustion；
- 14 model-declared infeasible；
- 14 premature `done`；
- 1 repair 后仍 invalid。

此外：

- 59/80 cells 重复同一 action 至少 3 次；
- 32/80 重复至少 10 次；
- 477 个已执行 actions 没有造成 screenshot change；
- M0 产生 758 次 memory-bundle decisions、457 次 memory citations、270 次 auxiliary calls，但 19 个对应任务中 0/19 成功。

最重要的解释不是“memory 太差”，而是这些任务通常在以下阶段就已失败：

- source acquisition；
- visual perception；
- GUI element grounding；
- action schema/interface；
- transition detection；
- loop escape；
- completion detection。

因此 Hard 结果不能用来估计“memory module 对成功率的因果增益”，因为大量 trajectory 根本没有到达 memory 内容能够决定结果的节点。它同时否定了用 step count 或“任务很长”直接代理 memory dependency 的做法。

### 3.4 EEST v0.2–v0.2.4：主要建立的是基础设施失效史

后续 EEST 阶段没有形成新的有效 task-level 方法对比：

- v0.2：9/9 在 environment action 之前停止，原因是 action-interface mismatch；
- v0.2.1：首次 decision 在一次 repair 后仍违反 schema；
- v0.2.2：3 个 command 达到 valid/executable，其中一个因过严 terminal-pixel rule 失败；
- v0.2.3：没有构造出有效 held-out trace corpus；
- v0.2.4：AndroidEnv 因缺失 `settings` service 失败，readiness 和 executed actions 均为零。

这些结果可以作为严谨的基础设施负结果保留，但不能被描述为 memory hypothesis 的正面或负面 task-level 检验。

### 3.5 M1–M14：继续进行长基础设施计划的机会成本已被实际证明

历史阶段连续出现：

- frozen log 在 shutdown 时被追加写入；
- terminal accounting 调用不存在的 helper；
- runner/process identity drift；
- display feature probe 全部关闭；
- ADB command 被错误识别；
- parent identity 与 ancestry validation 误报；
- unrelated service 污染 ancestry；
- historical child 与 current universe 错误比对；
- protocol freeze 前已有实现，导致实验永久 invalid；
- 同一开发链造成 protocol contamination；
- issuer authority、caller-substitutability、proof binding 不成立；
- 最终 frozen trusted-initializer harness 仍未形成已执行的科学证据。

M2–M9 主要失败于日志、运行时身份、显示状态和 parent-chain 约束。

M10–M14 又依次遭遇历史身份绑定、协议污染、proof authority 和未实际执行等问题。

这并不证明 AndroidWorld 永远不可运行，但它证明了一个与决策直接相关的事实：

> 在当前项目中，再启动一轮未被独特科学问题强制要求的基础设施修复，具有很高的预期成本和很低的边际信息价值。

### 3.6 `Correct Memory, Wrong Target`：timing hypothesis 已按规则停止

full-control handoff 冻结的模型与 backend 为：

- `Qwen/Qwen3-VL-32B-Instruct`
- revision：`0cfaf48183f594c314753d30a4c4974bc75f3ccb`
- backend：`qwen3_vl_32b_transformers_bf16_4x4090_v1`

v0.1–v0.3 共计：

- 96 cells；
- 192 model calls；
- 0 parser failures；
- exact-value recall 100%；
- early/late condition 的相关 token content 精确匹配；
- 0 selective retry；
- 0 live AndroidWorld interactions；
- 全部属于 development-contaminated templates。

三版结果分别是：

**v0.1：** target ID、visible label、human cue 和 bounds 均提供。目标选择为 ceiling，未发现 timing effect。

**v0.2：** target 变为 anonymous ID，仅保留 bounds。出现显著 wrong-target 行为，但 early/late 两种 timing 都失败，不能归因于 reminder timing；该版本落入 destination-grounding floor。

**v0.3：** 恢复 visible labels 和 bounds，但移除 human cue。目标选择重新达到 ceiling，仍未发现 timing effect。

handoff 明确记录：v0.1–v0.3 总计 96 cells、192 calls、100% exact-value recall，且这些任务全部是 development-contaminated；未获得 fresh held-out corpus，也没有 live Android actions。

最终 verdict 因此停止 reminder-timing hypothesis，并给出如下经验边界：

- destination grounding 可靠时，没有观察到通过资格门槛的 timing effect；
- destination grounding 不可靠时，grounding failure 主导，且并未表现为 timing-specific failure。

这一结果仅适用于当前 8 个 dev templates、3 个 app scenes 和当前 Qwen revision，不能外推为“所有模型、任务和提示中 timing 永远无效”。

### 3.7 Cross-modal temporal skew：机制真实，但尚未形成 RAVEN-M 独有贡献

历史 r52–r59 证据表明，AndroidWorld/GUI pipeline 中确实出现过：

- screenshot 已变化，但 accessibility tree/hash 仍旧；
- delayed DOM / delayed structured state；
- stale tree 对可见 action 的拒绝；
- freshness fix 通过局部机制检查，但完整任务仍因 stale summary、operand loss 或错误 action-key binding 失败。

因此，“像素与结构化表示可能不同步”是项目中真实存在的工程机制。

但现有 RAVEN-M 结果没有证明：

- 该机制在目标任务分布中的自然发生率；
- 它是 task failure 的主要因果来源；
- RAVEN-M 比简单 freshness check 更能解决它；
- 其 mitigation 产生 task-level 净收益；
- 该方向仍具有足够独立的新颖性。

---

## 4. 因果问题重建：哪些量被检验，哪些量没有被识别

### 4.1 原始方法主张所需要的 causal estimand

要证明完整 RAVEN-M 有价值，理想 estimand 应接近：

\[
\Delta_{\text{RAVEN-M}}
=
\mathbb{E}_{\tau \sim \mathcal{D}}
\left[
S(\tau;\mathrm{M0})-S(\tau;\mathrm{B3})
\right],
\]

其中：

- \(\mathcal{D}\) 是预先声明的自然 GUI-task 分布；
- \(\tau\) 是 task instance、initial state、app state 和 seed；
- \(S\) 是 task-level success；
- M0 与 B3 除 memory intervention 外应具有可比 controller、action interface、budget 和 observation。

当前数据没有识别一个正的 \(\Delta_{\text{RAVEN-M}}\)。主要原因不是只缺少更大样本，而是：

1. legacy 小样本中方向并不支持 M0；
2. Hard 数据大量处于 controller/interface/grounding floor；
3. EEST 正确信息记录没有转化为 task win；
4. 部分阶段没有实际环境 action；
5. fresh held-out distribution 未建立。

因此不能通过简单增加 cells、把 calls 当作独立样本，或汇总异质任务来补救。

### 4.2 EEST 实际识别的是 pipeline 非充分性

将成功分解为：

\[
S = C \land R \land G \land A \land V,
\]

其中：

- \(C\)：正确 capture source information；
- \(R\)：正确 retain/retrieve；
- \(G\)：正确 grounding 到 destination entity/UI target；
- \(A\)：正确 action execution；
- \(V\)：正确 verify completion。

EEST 提供了 \(C=1,R=1\) 而 \(S=0\) 的明确样例，因此证明：

\[
(C=1 \land R=1) \centernot\Rightarrow S=1.
\]

这是一条有价值的负结论，但不是一个新的方法贡献。

### 4.3 Reminder-timing pilot 的局部 estimand

该 pilot 试图考察：

\[
\Delta_{\text{timing}}(g)
=
\mathbb{E}[Y\mid do(T=\text{late}),G=g]
-
\mathbb{E}[Y\mid do(T=\text{early}),G=g],
\]

其中：

- \(Y\)：是否选择正确 destination；
- \(T\)：reminder 出现在 early 或 late；
- \(G\)：destination grounding 可辨识程度；
- exact-value recall 被保持为 ceiling。

preflight/token certificate 降低了“两个条件使用不同事实内容或不同 value tokens”的解释，但它不能消除：

- dev-template contamination；
- 单一模型 revision；
- synthetic frame distribution；
- 无 live transition；
- v0.1/v0.2/v0.3 之间的 configuration-level 差异；
- template/app scene 的有限覆盖。

现有结果没有支持一个通过预注册 gate 的 \(\Delta_{\text{timing}}(g)\)。相反，跨版本最简洁的诊断解释是：

> semantic target identifiability 比 reminder timing 更能解释正确目标选择。

但 v0.2→v0.3 不是同一冻结实验内对 label availability 的完整随机化，因此也不能把版本间差异升级为普遍 causal theorem。

### 4.4 Cross-modal skew 所需但尚未识别的 estimand

若要主张 temporal skew 是新的 task-level 因果机制，需要估计类似：

\[
\Delta_{\text{skew}}
=
\mathbb{E}
\left[
S\mid do(\text{aligned observation})
-
S\mid do(\text{temporally skewed observation})
\right]
\]

并要求：

- 同一 latent GUI state；
- 只改变 screenshot/structure 的时间一致性；
- action representation、prompt、budget 不变；
- state conflict 有明确 oracle；
- 观察到 action consequence，而不只是 preference；
- 样本来自 fresh、预先冻结的 task/state distribution。

RAVEN-M 当前只建立了部分工程实例，没有完成上述 task-level identification。更关键的是，最接近的新工作已经直接执行了这类 paired conflict、natural stale 和 action-consequence 实验，见第 6 节。

---

## 5. 先前假设与创新主张审计

| 编号 | 假设或主张 | 当前状态 | 依据与解释 |
|---|---|---|---|
| A1 | 长 GUI 任务因此必然需要复杂 structured memory | **Unsupported** | 任务长度不是 dependency topology；Hard 任务大量在 memory edge 前失败。 |
| A2 | natural stale、conflicting、untrusted memory 是标准 AndroidWorld 的主要失败源 | **Unresolved** | 项目发现过实例，但未估计自然发生率或 attributable task failure。 |
| A3 | 完整 RAVEN-M 已提高 task success | **Contradicted in observed scope** | legacy B3 4/4、M0 3/4，且 M0 成本更高；EEST 无 paired win。 |
| A4 | typed slots 能正确保存 source–field–value | **Supported narrowly** | 在 development-contaminated EEST smoke 中 4/4 正确，但范围极窄。 |
| A5 | 正确保存信息会带来正确任务执行 | **Contradicted** | EEST 中记录正确但 destination/action 错误。 |
| A6 | provenance、confidence、risk gate 或 verification status 已产生 task benefit | **Unsupported** | 当前没有隔离且有效的 task-level 增益证据，部分 gate 未真正被触发。 |
| A7 | memory citation 数量代表 memory 被有效使用 | **Unsupported** | Hard 中大量 citations 和 auxiliary calls 与 0/19 success 并存。 |
| A8 | reminder timing 导致 `Correct Memory, Wrong Target` | **Stopped / not supported** | v0.1–v0.3 未通过 timing-effect gate；grounding floor/ceiling 更能解释结果。 |
| A9 | v0.2→v0.3 证明了新的 role-binding memory mechanism | **Unsupported** | 最直接变化是 target semantic labels/identifiability，属于 grounding 条件。 |
| A10 | screenshot/tree temporal skew 不存在或可忽略 | **Contradicted** | 历史 r52–r59 提供真实工程实例。 |
| A11 | temporal skew 是 RAVEN-M 可独占的新研究问题 | **Preempted** | 当前已有更直接的跨模态冲突、natural stale、AndroidWorld action harm 和 consistency-gate 研究。 |
| A12 | generic event log、typed slot、goal ledger、workflow graph、critic 即构成新颖性 | **Rejected** | 这些模块分别已有 GUI grounding、workflow memory、history-aware reasoning、critic 和 process evaluation 先例。 |
| A13 | 修改现有 dev templates 后可以称为 held-out | **Forbidden** | 已用于设计、debug、preflight 或 threshold 的模板仍是 contaminated。 |
| A14 | 再进行一轮大规模 infrastructure repair 是科学上不可避免的 | **Unsupported** | 当前没有通过 novelty 和 causal gate 的问题要求该投入。 |
| A15 | 当前结果可推广至其他 VLM 或所有 AndroidWorld tasks | **Forbidden** | role-binding 结果来自单一 Qwen revision、8 个 dev templates、3 个 scenes。 |

---

## 6. Closest-prior novelty audit

### 6.1 最接近的直接覆盖工作

#### [Do GUI Agents Believe Their Eyes? Diagnosing State-Belief Reliance on Pixels versus Structure](https://arxiv.org/abs/2607.04334v2)

**状态：** arXiv preprint，v2 日期为 2026-07-18；截至本计划日期不能标为 peer-reviewed archival publication。

该工作不是仅使用“cross-modal consistency”相似术语，而是已经执行了 RAVEN-M 剩余方向所需的核心等价实验：

- 构造 pixels 与 structured representation 冲突的 paired probes；
- 覆盖 web、mobile 和 desktop；
- 收集 natural zero-edit / stale divergences；
- 在 AndroidWorld 检查冲突如何改变实际 action 与 landing outcome；
- 比较 coordinate、element-id、index、text-label 等 action formats；
- 比较 baseline、pixel-priority prompt、certificate 和 source-aware consistency gate；
- 同时报告 hijack tendency 与 task error，而不是只报告模型口头偏好。

论文报告了数百个跨平台 probes，并包含 natural stale 条件及 AndroidWorld 行为后果。

其 mitigation 部分还直接比较了 consistency gate 等方案，而不是停留在故障描述。

**对 RAVEN-M 的意义：**

RAVEN-M 不能再把以下任何单独一项作为主要 novelty：

- screenshot 与 accessibility tree 不一致；
- agent 更相信结构或像素；
- stale structured state 导致错误点击；
- 在执行前进行 cross-view consistency checking；
- 使用一个 freshness/consistency gate；
- 比较不同 action representations 对 conflict reliance 的影响。

该工作是 preprint，并不意味着独立 replication 没有价值；但当前 RAVEN-M 没有预先建立一个与其明显不同、且已有正证据支持的 residual question。仅把 conflict 称为“memory provenance conflict”“episodic stale state”或“role-bound observation memory”不能制造新颖性。

### 6.2 已发表的 cross-view consistency 邻近工作

#### [Cross-View Consistency Checking for Multimodal Web Agents under Adversarial UI Perturbations](https://dl.acm.org/doi/10.1145/3804601.3804623)

**状态：** CAICE 2026 ACM conference proceedings paper。

该工作已经明确研究 multimodal web agents 在 adversarial UI perturbation 下的 cross-view consistency checking。它不与 RAVEN-M 的移动端 temporal skew 完全等价，但进一步排除了“跨视图一致性检查”本身作为新颖贡献的可能。

### 6.3 GUI grounding 已是成熟问题，而不是新的 memory 机制

#### [AndroidWorld: A Dynamic Benchmarking Environment for Autonomous Agents](https://proceedings.iclr.cc/paper_files/paper/2025/hash/01a83bc2f2732a58e6aa731e659e7101-Abstract-Conference.html)

**状态：** ICLR 2025，peer-reviewed conference paper。

AndroidWorld 提供 20 个 Android apps 上的 116 个任务，是本项目环境和任务主张的核心 benchmark 背景。

#### [SeeClick: Harnessing GUI Grounding for Advanced Visual GUI Agents](https://aclanthology.org/2024.acl-long.505/)

**状态：** ACL 2024，peer-reviewed conference paper。

SeeClick 直接把 GUI grounding 定义为从指令定位屏幕元素，并验证 grounding 能力与下游 GUI-task performance 的关系。因而，“模型知道文本值但点错视觉区域”首先是一个标准 grounding failure，除非有额外、被隔离的 memory-specific mechanism。

#### [VisualWebArena: Evaluating Multimodal Agents on Realistic Visual Web Tasks](https://aclanthology.org/2024.acl-long.50/)

**状态：** ACL 2024，peer-reviewed conference paper。

该工作进一步说明视觉网页 agent 的 observation、grounding 和 action execution 已有成熟评估框架，不能把通用目标定位失败重新包装为 structured-memory novelty。

### 6.4 Workflow、history 和 reusable memory 已有直接先例

#### [PG-Agent: An Agent Powered by Page Graph](https://dl.acm.org/doi/10.1145/3746027.3755189)

**状态：** ACM Multimedia 2025，peer-reviewed conference paper。

PG-Agent 已采用 page graph、retrieval 和 reusable navigation knowledge。generic workflow graph 或 procedure cache 不能单独构成 RAVEN-M 的新贡献。

#### [History-Aware Reasoning for GUI Agents](https://ojs.aaai.org/index.php/AAAI/article/view/40966)

**状态：** AAAI 2026，peer-reviewed conference paper。

该工作已明确研究 GUI agents 的历史感知、episodic reasoning 和 reflective learning。把 RAVEN-M 改写为“history-aware episodic memory”不会产生充分区别。

#### [Agent Workflow Memory](https://arxiv.org/abs/2409.07429)

**状态：** arXiv/OpenReview work；在没有进一步 archival venue 证明时必须标为 preprint/OpenReview，而非 peer-reviewed publication。

该工作已经覆盖从经验中归纳和复用 workflows 的核心概念。

#### [Mobile-Agent-E: Self-Evolving Mobile Assistant for Complex Tasks](https://arxiv.org/abs/2501.11733)

**状态：** arXiv preprint。

该工作包含 persistent tips、shortcuts 和 self-evolution；generic persistent memory 不是开放的命名空间。

#### [MemGUI-Bench](https://arxiv.org/abs/2602.06075)

**状态：** 截至本计划日期按 arXiv preprint 处理；除非存在可核验的正式 proceedings 页面，不得称为 peer-reviewed。

该工作已提出面向 GUI-agent memory 的任务集合和 taxonomy。RAVEN-M 若仅转向“构造一个 memory-centric GUI benchmark”，仍需证明与其 task mechanism 和 evaluation units 的实质区别。

### 6.5 Critic、verification 和 process evaluation 也已有直接先例

#### [Look Before You Leap: A GUI-Critic-R1 Model for Pre-Operative Error Diagnosis in GUI Automation](https://proceedings.neurips.cc/paper_files/paper/2025/hash/05f7fb7bc9a3cc4608f1c6f2cdc79eae-Abstract-Conference.html)

**状态：** NeurIPS 2025 Main Conference，peer-reviewed conference paper。

该工作已经研究 GUI action 之前的 critic/error diagnosis，并在移动端和网页场景中评估其对自动化的作用。因此，给 RAVEN-M 增加 generic pre-action critic 不能构成独立研究方向。

#### [ProBench: Process-Aware Evaluation for GUI Agents](https://ojs.aaai.org/index.php/AAAI/article/view/39974)

**状态：** AAAI 2026，peer-reviewed conference paper。

ProBench 已明确占据 process information 和 process-aware GUI evaluation。generic completion guard、trajectory verifier 或“不能只看 final success”也不是足够的新贡献。

### 6.6 文献审计结论

现有最接近文献并非只覆盖相似术语，而是覆盖了 RAVEN-M 候选方向的关键实验操作：

| RAVEN-M 候选主张 | 最近文献是否执行等价关键实验 | 判定 |
|---|---:|---|
| Pixel–structure conflict | 是 | 非新颖 |
| Natural stale structured observation | 是 | 非新颖 |
| AndroidWorld action consequence | 是 | 非新颖 |
| Action-format sensitivity | 是 | 非新颖 |
| Cross-view consistency gate | 是 | 非新颖 |
| Generic GUI grounding | 是 | 非新颖 |
| Workflow/page graph memory | 是 | 非新颖 |
| History-aware episodic reasoning | 是 | 非新颖 |
| Generic pre-action critic | 是 | 非新颖 |
| Process-aware verification | 是 | 非新颖 |
| Reminder timing 导致 wrong target | 本项目自身已停止 | 不可继续 rescue |

当前唯一可能的区别只能是更复杂的长时程、多实体、多阶段 causal binding；但项目没有 fresh task-level evidence 表明该机制自然出现、是主要瓶颈或可被当前 RAVEN-M 解决。直接把研究升级为更复杂的版本，会是在证据不足时重新发明假设，而不是由结果逻辑推出的 next test。

---

## 7. 所有候选研究方向的最终处理

### 7.1 方向 A：继续 rescue reminder timing

**判定：拒绝。**

理由：

- v0.1、v0.2、v0.3 已覆盖有 cue、有 semantic labels、anonymous target 等关键诊断条件；
- exact-value recall 为 100%，避免把 failure 归结为忘记值；
- wrong-target 在 v0.2 中不是 late-specific；
- v0.3 恢复 labels 后无论 timing 都成功；
- 最新冻结 verdict 已按预注册规则停止。

再增加 templates、修改 threshold 或挑选更容易产生差异的例子，属于 post-hoc rescue。

### 7.2 方向 B：实现 `Destination-First Binding Gate`

**判定：拒绝，保持未实现。**

现有数据只表明 destination grounding 很重要，没有表明需要一个新的 memory gate。一个要求模型先确认 destination 的 prompt/check 本质上接近：

- target verification；
- GUI grounding confirmation；
- pre-action critic；
- workflow guard。

这些均已有相邻 prior art。当前没有 task-level causal evidence 证明该 gate 比更简单的 semantic labels、普通 grounding model 或 action confirmation 更优。

### 7.3 方向 C：研究“正确文本值映射到错误视觉区域”

**判定：拒绝作为 primary research direction。**

该现象真实，但在现有设置下最直接属于 GUI grounding。若没有 memory-specific intervention，它不能与 SeeClick 等 grounding 工作区分。

### 7.4 方向 D：研究 screenshot–accessibility temporal skew

**判定：不作为 RAVEN-M 主方向继续。**

这是现有证据中最真实、最有机制含量的现象，但已被 `Do GUI Agents Believe Their Eyes?` 更直接地覆盖，包括 natural stale、AndroidWorld actions、action-format sweep 和 consistency-gate mitigation。RAVEN-M 没有剩余的、已被自身证据支持的明确差异。

### 7.5 方向 E：generic structured memory / workflow graph / RAG / provenance ledger

**判定：拒绝。**

这些组件可以作为工程 baseline 保留，但不构成 narrow causal contribution。当前数据也没有证明其 task-level 净收益。

### 7.6 方向 F：增加 verifier、critic、completion guard

**判定：拒绝。**

现有失败确实包含 premature done 和错误 completion，但：

- generic critic/process evaluation 已有直接 prior；
- 当前项目没有隔离 verifier 的独立效应；
- 增加 verifier 还可能增加 calls、latency 和 false blocking；
- 它不能挽救原始 memory novelty。

### 7.7 方向 G：再做一轮 fresh AndroidWorld collector/infrastructure repair

**判定：拒绝。**

基础设施只有在一个已通过 novelty、causal relevance 和 feasibility gate 的问题无法用更小手段测试时才是逻辑必需。当前没有这样的研究问题，因此基础设施修复本身不能成为下一阶段。

---

## 8. 继续与停止的决策矩阵

| 决策条件 | 继续所需状态 | 当前状态 | 结果 |
|---|---|---|---|
| 明确、自然存在的 causal failure | 已隔离且不是 floor/ceiling | memory-specific failure 未被隔离；Hard 受早期 floor 主导 | Fail |
| 当前 hypothesis 尚未被测试或停止 | 仍有预注册未决结果 | timing hypothesis 已停止 | Fail |
| 与 closest prior 有实质实验区别 | 不只是命名差异 | cross-modal/grounding/workflow/critic 均被覆盖 | Fail |
| 正结果能直接支持一种方法 | method 与 mechanism 一一对应 | destination label 效应不指向独特 memory method | Fail |
| 负结果能立即终止而不继续 rescue | 有单次 bounded test | 项目已多次进入 repair/rescue 链 | Fail |
| fresh held-out 数据边界 | 未用于 design/debug | role-binding 全部 dev-contaminated | Fail |
| 可在最小基础设施上运行 | 首阶段快速 actual calls | live collector 不可用，且无值得修复的问题 | Fail |
| 信息增益/时间比高 | 一轮即可改变决策 | 新 calls 不会修复 novelty 缺口 | Fail |
| task-level 净收益迹象 | 至少存在方向一致的 paired signal | legacy 方向不利，EEST 无 win，Hard 为 floor | Fail |

没有候选方向通过全部必要条件。因此继续不是谨慎，而是违反已有 stop evidence。

---

## 9. 用户要求的实验设计字段：绑定性“不适用”定义

由于本计划决定停止研究方法开发，以下字段不得由 executor 自行补充。

| 字段 | 绑定值 |
|---|---|
| Exact research question | `NONE — no new research question authorized` |
| Primary hypothesis | `NONE` |
| Primary direction | `NONE` |
| New causal estimand | `NOT DEFINED` |
| New causal variables | `NOT DEFINED` |
| Alternative explanations to manipulate | `NONE` |
| Task/state selection | `NO NEW TASKS OR STATES` |
| Fresh-development split | `NO NEW DEVELOPMENT SET` |
| Held-out split | `NO NEW HELD-OUT SET` |
| AndroidWorld app families | `NONE` |
| Inclusion rules | `NONE` |
| Exclusion rules | `NONE` |
| Oracle construction | `NONE` |
| Experimental arms | `NONE` |
| Controls | `NONE` |
| Counterbalancing | `NONE` |
| Randomization | `NONE` |
| Prompt text | `NO PROMPT` |
| Prompt-construction procedure | `NO PROMPT CONSTRUCTION` |
| Model identifier for new calls | `NO MODEL INVOCATION` |
| Frozen model provenance | `Qwen/Qwen3-VL-32B-Instruct@0cfaf48183f594c314753d30a4c4974bc75f3ccb` |
| Decoding parameters | `N/A` |
| New model calls | `0` |
| New prompt-token ceiling | `0` |
| New completion-token ceiling | `0` |
| New Android actions | `0` |
| New action budget | `0` |
| Model retry policy | `0 retries because no calls` |
| Primary scientific outcome | `NONE` |
| Diagnostic metrics | `NO NEW SCIENTIFIC METRICS` |
| Cost metrics | `Only closeout file/process counts` |
| Invalid model output handling | `N/A` |
| New sample size | `0 tasks, 0 states, 0 cells, 0 calls` |
| Statistical analysis | `No new hypothesis test; descriptive integrity checks only` |
| Method-implementation gate | `FAILED` |
| Exact method to implement | `NONE` |
| Subsequent experiments after positive result | `NONE; any unexpected evidence triggers return to GPT Pro` |
| Automatic scientific pivot | `FORBIDDEN` |

“第一阶段尽快使用 actual model calls”的要求只适用于继续研究时。当前没有未决科学问题，任何新 model call 的预期决策价值为零，因此最优 calls 数量是 0。

---

## 10. 唯一授权的后续工作：Scientific Closeout

### 10.1 Closeout 目标

Codex 必须把当前分支整理成一个可审计、不可被后续叙事重写的负结果与工程基线档案，完成：

1. source inventory；
2. content hashes；
3. raw-summary consistency checks；
4. claim–evidence matrix；
5. closest-prior novelty audit；
6. negative-results data card；
7. final scientific stop verdict；
8. machine-readable completion manifest。

Closeout 不得产生新科学数据。

### 10.2 硬资源和尝试上限

```yaml
maximum_closeout_passes: 1
maximum_retry_per_failed_read_or_hash_command: 1
maximum_total_wall_clock_hours: 4
maximum_model_calls: 0
maximum_androidworld_runs: 0
maximum_adb_commands: 0
maximum_qwen_server_starts: 0
maximum_new_scientific_tests: 0
maximum_existing_files_modified: 0
dependency_installation_allowed: false
network_literature_search_allowed: false
```

唯一允许的 retry 是对确定属于瞬时文件读取或 hash 失败的同一命令重试一次。第二次失败立即停止并返回异常包。

### 10.3 禁止的操作

Codex 不得执行：

```text
git reset
git checkout -- <path>
git clean
git stash
git add
git commit
git push
pip install
conda install
adb ...
启动 Android emulator
启动 Qwen server
调用任何 LLM/VLM API
重跑任一 v0.1–v0.3 model cell
修改 task/config/prompt/threshold
实现 Destination-First Binding Gate
增加 memory/critic/verifier/workflow module
重新标记 contaminated task 为 held-out
```

---

## 11. Closeout 的精确执行序列

输出目录固定为：

```text
reports/research_direction/final_closeout_2026-08-05/
```

若该目录在开始执行前已经存在，Codex 不得覆盖、删除或复用，必须立即停止并返回：

```text
STOP_REASON=OUTPUT_DIRECTORY_ALREADY_EXISTS
```

### C0. 保存 working-tree 边界

依次执行只读命令：

```bash
git rev-parse --show-toplevel
git branch --show-current
git rev-parse HEAD
git status --porcelain=v1 -uall
git diff --name-only
git diff --cached --name-only
```

要求：

- observed branch 必须为 `protocol-v2-exploratory`；
- 不要求 working tree 必须 clean；
- 任何已存在的 dirty/protected WIP 均按原样记录，不得 reset、stash 或覆盖；
- 开始时对所有 pre-existing modified/untracked evidence files 计算 SHA-256；
- closeout 结束时必须重新计算并确认完全不变。

若 branch 不匹配，立即停止：

```text
STOP_REASON=WRONG_BRANCH
```

### C1. 建立完整 source inventory

至少纳入：

```text
README.md
RAVEN-M_GPTPro_full_plan_2026-08-05.md
reports/research_direction/**
reports/eest_ac/**
reports/role_binding_timing/**
04_protocols/role_binding_timing/**
05_project/configs/role_binding_timing/**
05_project/src/raven_m/role_binding_timing/**
05_project/artifacts/role_binding_timing/stage1_dev_pilot_v0_1/**
05_project/artifacts/role_binding_timing/stage1_dev_pilot_v0_2/**
05_project/artifacts/role_binding_timing/stage1_dev_pilot_v0_3/**
所有与 AndroidWorld Hard、r52–r59、M1–M14、EEST 和 legacy comparison 关联的 tracked files
相关 tests、scripts、contracts、certificates、JSON、JSONL、CSV 和 logs
```

执行原则：

- 使用 `git ls-files -z` 获取全部 tracked files；
- 对上述 evidence paths 中的相关 untracked files 也纳入；
- 排除 `.git/`、`__pycache__/`、`.pytest_cache/`、虚拟环境、外部 model cache、临时文件；
- symlink 只记录 link target，不跟随到 repository 外；
- binary frame/video 只做 metadata 和 hash，不做 OCR；
- 不允许以文件太大为由跳过 hash；若 streaming hash 失败一次并重试仍失败，停止。

每个文件记录：

```text
path
tracked
git_blob_oid_if_available
sha256
size_bytes
file_type
evidence_family
worktree_status
protected
parse_status
```

### C2. Raw artifact 与 summary 的机械一致性检查

只允许使用 Python standard library 或 repository 已存在且无需安装依赖的纯离线工具。

必须验证以下冻结不变量：

| 检查 ID | 冻结不变量 |
|---|---|
| V01 | role-binding v0.1–v0.3 aggregate cells = 96 |
| V02 | role-binding aggregate model calls = 192 |
| V03 | role-binding parser failures = 0 |
| V04 | role-binding exact-value recall = 100% |
| V05 | role-binding selective retries = 0 |
| V06 | role-binding live environment interactions = 0 |
| V07 | role-binding 所有任务均标记为 development-contaminated，而非 held-out |
| V08 | v0.1 的 frozen verdict 为 grounding ceiling / no qualified timing effect |
| V09 | v0.2 的 frozen verdict 为 grounding floor / no qualified timing effect |
| V10 | v0.3 qualified 且未通过 timing-effect continue gate |
| V11 | EEST v0.1.1 cells = 8 |
| V12 | EEST 四 arms 的 task result 均为 1/2 |
| V13 | structured legs 的相关 source-binding records = 4/4 correct |
| V14 | structured legs 的 net paired task wins = 0 |
| V15 | AndroidWorld Hard total cells = 95 |
| V16 | structurally unsupported QA cells = 15 |
| V17 | supported cells = 80 |
| V18 | supported-cell successes = 1 |
| V19 | budget exhaustion = 50 |
| V20 | model-declared infeasible = 14 |
| V21 | premature done = 14 |
| V22 | invalid after repair = 1 |
| V23 | same action repeated ≥3 的 cells = 59/80 |
| V24 | same action repeated ≥10 的 cells = 32/80 |
| V25 | executed actions with no screenshot change = 477 |
| V26 | legacy B3 success = 4/4 |
| V27 | legacy M0 success = 3/4 |
| V28 | 没有有效 fresh held-out role-binding corpus |
| V29 | `Destination-First Binding Gate` 未被实现为已授权方法 |
| V30 | closeout 期间新 model calls = 0 |

检查规则：

- 如果 raw schema 能直接重算，必须从 raw 重算；
- 如果某项只存在于冻结 report，记录 `verification_level=FROZEN_REPORT_ONLY`；
- 不得为了让 summary 与 raw 一致而修改 raw；
- 不得自动选择“更可信的数字”；
- 任一不一致必须停止，并输出差异位置、文件 hash、raw numerator/denominator 和 summary value。

禁止把 model calls、repair calls 或同一 task-template 的多个 prompt 当作独立 task samples 进行新的显著性检验。

### C3. 生成最终 claim–evidence matrix

必须包含以下 15 个 claim IDs，不得删除或改写成更有利的说法：

```text
C001 Long GUI tasks automatically require complex structured memory
C002 Natural stale/conflicting memory is a dominant AndroidWorld failure source
C003 Full RAVEN-M improves task success over a simple summary baseline
C004 Typed records can preserve source–field–value bindings in the EEST smoke
C005 Correct recording is sufficient for correct destination execution
C006 Provenance/confidence/risk verification improves task success
C007 Step count is a valid proxy for memory dependency
C008 Reminder timing causes Correct Memory, Wrong Target
C009 Destination semantic identifiability affects target selection in the dev pilots
C010 Screenshot/accessibility temporal skew occurs in the engineering stack
C011 Temporal skew is established as a dominant task-level causal failure
C012 Cross-modal consistency checking is novel to RAVEN-M
C013 The role-binding corpus contains fresh held-out evidence
C014 Results generalize beyond the frozen Qwen revision and dev scenes
C015 Another infrastructure repair program is scientifically necessary
```

允许的状态值固定为：

```text
SUPPORTED_NARROWLY
UNSUPPORTED
CONTRADICTED_IN_OBSERVED_SCOPE
UNRESOLVED
PREEMPTED_BY_PRIOR_WORK
FORBIDDEN_GENERALIZATION
```

每一行必须包含至少一个具体 repository source path。没有 source 的 claim row 使整个 closeout 失败。

### C4. 生成冻结 literature novelty audit

只使用本计划第 6 节列出的 primary literature，不再由 executor 搜索或选择文献。

每篇文献必须记录：

```text
title
direct_url
publication_status
venue_or_repository
year
closest_experimental_overlap
remaining_difference
effect_on_raven_m_novelty
```

`publication_status` 只允许：

```text
PEER_REVIEWED_CONFERENCE
ARCHIVAL_CONFERENCE_PROCEEDINGS
PREPRINT
OPENREVIEW_OR_PREPRINT_UNVERIFIED
```

以下错误任一出现即失败：

- 把 arXiv paper 标成 peer-reviewed；
- 使用博客或二手综述替代 primary source；
- 只比较术语，不比较 experiment；
- 声称 “first”；
- 把 “Do GUI Agents Believe Their Eyes?” 遗漏出 closest-prior；
- 把 cross-view conflict、consistency gate 或 generic workflow memory 判为未覆盖。

### C5. 生成 Negative Results Data Card

必须单独记录：

1. 项目原始 claim；
2. 数据与任务来源；
3. model/revision；
4. unit of analysis；
5. development contamination；
6. baseline/full-system results；
7. task-success 与 record-correctness 的区别；
8. Hard failure taxonomy；
9. role-binding pilot 的 three-version design；
10. infrastructure failures；
11. known unsupported app/task cells；
12. cost overhead；
13. invalid generalizations；
14. raw artifact locations；
15. reproduction limitations；
16. no-new-run declaration。

禁止通过合并异质 cells 生成一个新的总体 success rate，并禁止对 96 个 role-binding cells 做声称跨任务普遍性的 iid inference。

### C6. 生成最终 Stop Verdict

Stop Verdict 必须逐字包含以下绑定性核心：

```text
RAVEN-M is stopped as an independent research-method project on the
protocol-v2-exploratory branch. The repository is retained as an engineering
baseline, negative-results archive, and reproducibility case study. No new
hypothesis, model call, AndroidWorld experiment, method implementation, or
infrastructure program is authorized by this plan.
```

同时必须包含：

- `primary_direction: NONE`；
- stopped hypotheses；
- unsupported claims；
- closest-prior conclusion；
- allowed claims；
- forbidden claims；
- exact reason no new model call was performed；
- no automatic pivot。

### C7. 生成并运行 closeout validator

必须在输出目录创建一个纯 standard-library validator：

```text
07_VALIDATE_CLOSEOUT.py
```

validator 必须：

- 解析所有生成的 JSON 和 CSV；
- 检查所需文件存在；
- 检查 C001–C015 全部存在且唯一；
- 检查每个 claim 至少有一个 source path；
- 检查每篇 literature 有 direct URL 和 publication status；
- 检查 preprints 未被标记为 peer-reviewed；
- 检查 V01–V30 均有 pass/fail/verification-level；
- 检查 `new_model_calls == 0`；
- 检查 `new_androidworld_runs == 0`；
- 检查 `new_adb_commands == 0`；
- 检查 `existing_source_files_modified == 0`；
- 检查 worktree baseline 中的 protected file hashes 未变化；
- 检查 Stop Verdict 包含绑定文本；
- 成功时 exit code 0；
- 任一失败时 exit code 非 0。

validator 不得访问网络、启动 emulator 或导入 model packages。

### C8. Hash、completion manifest 与终止

所有 deliverables 完成后：

1. 对生成文件计算 SHA-256；
2. 输出 validation log；
3. 输出 machine-readable completion manifest；
4. 再次计算 pre-existing protected files 的 hash；
5. 确认无 source file 被修改；
6. 结束，不进入任何新研究阶段。

---

## 12. 必须生成的文件及精确格式

输出目录：

```text
reports/research_direction/final_closeout_2026-08-05/
```

### 12.1 `00_EXECUTION_RECEIPT.json`

必需字段：

```json
{
  "plan_file": "RAVEN-M_GPTPro_full_plan_2026-08-05.md",
  "decision": "STOP_RESEARCH_METHOD",
  "branch_expected": "protocol-v2-exploratory",
  "branch_observed": "",
  "head_commit": "",
  "worktree_initial_status_sha256": "",
  "executor_role": "execution_only",
  "new_model_calls": 0,
  "new_androidworld_runs": 0,
  "new_adb_commands": 0,
  "new_qwen_server_starts": 0,
  "new_scientific_hypotheses": 0,
  "existing_source_files_modified": [],
  "started_at_utc": "",
  "completed_at_utc": ""
}
```

### 12.2 `01_SOURCE_INVENTORY.tsv`

列顺序固定：

```text
path
tracked
git_blob_oid
sha256
size_bytes
file_type
evidence_family
worktree_status
protected
parse_status
```

`evidence_family` 只允许：

```text
research_direction
legacy_raven_m
eest_ac
androidworld_hard
role_binding_timing
infrastructure_history
implementation
test
raw_artifact
protocol
configuration
other
```

### 12.3 `02_SOURCE_HASHES.sha256`

格式采用标准：

```text
<sha256><two spaces><relative_path>
```

只包含执行前已存在的 source/evidence files，不包含 closeout 新文件。

### 12.4 `03_VALIDATION_ASSERTIONS.csv`

列顺序固定：

```text
assertion_id
expected_value
observed_value
status
verification_level
source_paths
notes
```

必须恰好包含 V01–V30。

`status` 只允许：

```text
PASS
FAIL
NOT_MACHINE_RECOMPUTABLE
```

`verification_level` 只允许：

```text
RAW_RECOMPUTED
RAW_AND_SUMMARY
FROZEN_REPORT_ONLY
```

`NOT_MACHINE_RECOMPUTABLE` 不等于自动通过；只有本计划明确允许使用 `FROZEN_REPORT_ONLY` 的字段才可继续。

### 12.5 `04_CLAIM_EVIDENCE_MATRIX.csv`

列顺序固定：

```text
claim_id
claim_text
status
evidence_level
source_paths
raw_artifact_paths
development_contaminated
scope
allowed_wording
forbidden_wording
notes
```

必须恰好包含 C001–C015。

### 12.6 `05_LITERATURE_NOVELTY_AUDIT.md`

必须包含：

- status legend；
- direct closest prior；
- adjacent grounding prior；
- workflow/history prior；
- critic/process prior；
- experiment-level overlap table；
- final novelty verdict：`NO_DEFENSIBLE_PRIMARY_DIRECTION`。

### 12.7 `06_NEGATIVE_RESULTS_DATA_CARD.md`

标题固定：

```markdown
# RAVEN-M Negative Results and Engineering Baseline Data Card
```

结尾必须包含：

```yaml
task_level_method_benefit_established: false
record_level_binding_signal_observed: true
fresh_heldout_role_binding_evidence: false
timing_hypothesis_continues: false
cross_modal_skew_novelty_established: false
new_experiments_authorized: false
```

### 12.8 `07_VALIDATE_CLOSEOUT.py`

仅可使用 Python standard library。

### 12.9 `08_VALIDATION_LOG.txt`

必须记录：

```text
command
start_time
end_time
exit_code
stdout_sha256
stderr_sha256
retry_count
```

不得把 secrets、tokens 或 model credentials 写入 log。

### 12.10 `09_FINAL_SCIENTIFIC_STOP_VERDICT.md`

必须采用本计划的结论，不能添加新的 future-work direction。

### 12.11 `10_DELIVERABLE_HASHES.sha256`

包含 `00`–`09`，但不包含自身与 completion manifest。

### 12.12 `11_CLOSEOUT_COMPLETION.json`

必需字段：

```json
{
  "decision": "STOP_RESEARCH_METHOD",
  "primary_direction": "NONE",
  "closeout_status": "PASS_OR_STOPPED",
  "all_required_files_present": false,
  "all_validation_assertions_resolved": false,
  "all_claims_have_sources": false,
  "literature_statuses_valid": false,
  "protected_files_unchanged": false,
  "new_model_calls": 0,
  "new_androidworld_runs": 0,
  "new_method_implementations": 0,
  "new_infrastructure_repairs": 0,
  "validator_exit_code": null,
  "deliverable_hash_manifest_sha256": "",
  "stop_return_triggered": false,
  "stop_reason": null
}
```

成功完成时：

```text
closeout_status = PASS
all_required_files_present = true
all_validation_assertions_resolved = true
all_claims_have_sources = true
literature_statuses_valid = true
protected_files_unchanged = true
validator_exit_code = 0
stop_return_triggered = false
```

---

## 13. 数值化资格门与自动状态机

### Gate Q0：Repository integrity

通过条件：

- branch 精确等于 `protocol-v2-exploratory`；
- output directory 事先不存在；
- 所有 pre-existing dirty/protected files 已记录 hash；
- 0 个 source files 被修改。

失败动作：立即停止并返回异常包。

### Gate Q1：Evidence integrity

通过条件：

- V01–V30 全部解析；
- 没有 raw-summary contradiction；
- 所有 JSON/JSONL 均可解析，或被明确标为无法解析并触发停止；
- raw row count 与冻结 summary 一致；
- development-contaminated 数据未被标为 held-out。

失败动作：停止，不修 raw，不改 summary。

### Gate Q2：Claim accountability

通过条件：

- C001–C015 恰好各出现一次；
- 15/15 claims 有具体 source paths；
- 15/15 claims 有 allowed wording；
- 15/15 claims 有 forbidden wording；
- 0 个 broad positive method claims。

失败动作：停止，不由 executor 重新解释 claim。

### Gate Q3：Novelty integrity

通过条件：

- 所有要求文献均出现；
- 100% 有 direct link；
- 100% 有 publication status；
- 100% preprints 正确标记；
- closest-prior 明确为 `Do GUI Agents Believe Their Eyes?`；
- novelty verdict 为 `NO_DEFENSIBLE_PRIMARY_DIRECTION`；
- 0 个 “first” claims。

失败动作：停止，不进行新的文献搜索。

### Gate Q4：No-new-science invariant

必须同时满足：

```text
new_model_calls = 0
new_androidworld_runs = 0
new_adb_commands = 0
new_qwen_server_starts = 0
new_scientific_hypotheses = 0
new_method_implementations = 0
new_infrastructure_repairs = 0
existing_source_files_modified = 0
```

任一非零即 closeout 失败。

### Gate Q5：Closeout completeness

通过条件：

- 12/12 指定 deliverables 存在；
- validator exit code = 0；
- protected file hashes 100% 不变；
- deliverable hashes 完整；
- completion manifest 自洽。

通过 Q5 后，Codex 必须结束。不存在 Q6 research stage。

---

## 14. 对所有可能结果类型的精确下一动作

即使 closeout 中发现意外情况，Codex 也不得进行科学判断。

| 结果类型 | 机械定义 | 精确下一动作 |
|---|---|---|
| Positive | 发现 frozen summary 未报告的、RAVEN-M matched task win，或 raw 与当前 stop verdict 存在方向性冲突 | 冻结相关文件 hash，生成 discrepancy bundle，停止并返回 GPT Pro；不得实现方法 |
| Null | raw 与当前 null/stop verdict 一致 | 完成 closeout，不增加样本 |
| Floor | baseline/arms 因 grounding、interface、parser、environment 等原因无可解释成功差异 | 记录 floor，停止；不得修基础设施后重跑 |
| Ceiling | 所有 arms 接近或达到 100%，无法区分 | 记录 ceiling，停止；不得自行构造更难任务 |
| Mixed | app/template/seed 间方向不一致 | 不做 post-hoc subgroup mining；若与 summary 一致则归档，否则停止返回 |
| Model-specific | 现象只在冻结 Qwen revision 中观察 | 明确限制 scope；不得外推，不换模型重跑 |
| Infrastructure-limited | 缺失 service、emulator、action interface 或 collector 阻止有效运行 | 记录历史 failure code；不修复、不重跑 |
| Missing artifact | 计划要求的 raw/summary/config 不存在 | 停止返回；不得从其他文件推测重建 |
| Corrupt artifact | JSON/JSONL 解析失败或 hash 在执行中变化 | 重试读取一次；仍失败则停止 |
| Prior-status ambiguity | 文献页面与本计划给定 status 不一致或不可机械核验 | 保持本计划 status，记录 inaccessible；不得自行升级为 peer-reviewed |
| New idea discovered | executor 认为出现新 hypothesis | 不记录为方向，只在异常包中逐字列出观察到的 raw fact，停止返回 |

---

## 15. 必须停止并返回 GPT Pro 的节点

以下任一条件触发后，Codex 只能生成一个异常包，不得继续下一阶段：

1. branch 不是 `protocol-v2-exploratory`；
2. output directory 已存在；
3. required raw artifact 缺失；
4. raw 与冻结 summary 的 counts 不一致；
5. 同一 cell 在多个文件中有冲突 outcome；
6. protected local WIP 的 hash 在 closeout 中变化；
7. 需要修改现有代码才能完成完整性检查；
8. 需要安装新依赖；
9. 需要启动 emulator、ADB 或 Qwen 才能验证；
10. 无法确定一个文件属于 dev、held-out 或 contaminated；
11. 发现未报告的 task-level matched win；
12. 发现 frozen stop verdict 使用了错误数据；
13. 任何步骤要求重新定义 hypothesis、metric 或 threshold；
14. 任何人要求 executor 选择 follow-up experiment；
15. 总 wall-clock 达到 4 小时；
16. 同一读取/hash 操作第二次失败；
17. validator 非零退出；
18. source file 被意外修改。

异常包固定包含：

```text
stop_reason
current_stage
branch
head_commit
worktree_status
affected_paths
pre_execution_hashes
current_hashes
exact_command
exit_code
raw_observed_value
expected_value
minimal_factual_description
```

不得包含未经授权的解释或实验建议。

---

## 16. Closeout 后允许与禁止的科学表述

### 16.1 允许表述

以下措辞可在技术报告、README 或 data card 中使用：

1. **Task-level net benefit**

   > 在当前冻结的小规模对照中，完整 RAVEN-M 未显示相对于简单摘要 baseline 的 task-success 优势，并产生更高调用和 token 成本。

2. **Record-level signal**

   > 在 development-contaminated EEST smoke 中，structured-memory arms 对 4/4 相关 source–field–value records 实现了正确绑定，但没有获得 paired task win。

3. **Pipeline separation**

   > 正确保存源信息并不足以保证正确 destination grounding、action execution 或 completion judgment。

4. **Hard failure structure**

   > AndroidWorld Hard 的大部分 trajectory 在 memory-specific decision edge 之前即因 perception、grounding、action-interface、loop 或 completion failure 失效。

5. **Timing result**

   > 在当前 8 个 dev templates、3 个 app scenes 和冻结 Qwen revision 中，reminder timing 未通过预注册 continue gate。

6. **Grounding boundary**

   > 当前 diagnostic pilots 表明，destination semantic identifiability 与 target-selection performance 具有强关联；该结果不构成新的 memory mechanism claim。

7. **Temporal skew**

   > 项目工程日志包含 screenshot 与 accessibility/structured state 暂时不同步的实例。

8. **Project positioning**

   > RAVEN-M 当前最适合作为 engineering baseline、negative-results archive 和 reproducibility case study 保留。

### 16.2 禁止表述

以下表述一律禁止：

- “RAVEN-M improves AndroidWorld performance.”
- “Structured memory has been proven effective.”
- “Structured memory has been proven ineffective in general.”
- “Correct Memory, Wrong Target is caused by reminder timing.”
- “Timing never matters for role binding.”
- “v0.3 proves a novel destination-binding mechanism.”
- “RAVEN-M is the first cross-modal consistency framework.”
- “RAVEN-M is the first GUI-agent provenance memory system.”
- “The project discovered pixel–accessibility conflict.”
- “A consistency gate is novel.”
- “All 96 cells are held-out.”
- “The result generalizes to other VLMs.”
- “The Hard benchmark proves memory is the bottleneck.”
- “Memory citations demonstrate causal memory use.”
- “Longer tasks are more memory-dependent.”
- “The negative result is statistically conclusive across AndroidWorld.”
- 把 arXiv preprints 称为 peer-reviewed papers；
- 用“role-binding memory”“causal ledger”“episodic provenance graph”等新名词包装已有通用概念；
- 从基础设施测试通过推导方法有效；
- 从局部 correct record 推导 task success；
- 从单个成功/失败 cell 推导普遍结论。

### 16.3 各阶段 claim 权限

| 阶段 | 可新增的表述 |
|---|---|
| C0–C2 | 仅文件、hash、count 和 parse 状态 |
| C3 | 仅 claim–evidence 状态，不得提出新解释 |
| C4 | 仅按本计划冻结的 novelty comparison |
| C5 | 仅负结果 data-card 描述 |
| C6 | 绑定性 stop verdict |
| C7–C8 | 仅验证与 completion 状态 |
| Closeout 后 | 不得自动进入新研究阶段 |

---

## 17. 项目保留形式与发表边界

### 17.1 可以保留的资产

RAVEN-M 仍有以下工程和科学记录价值：

- 展示 structured record correctness 与 task success 的分离；
- 展示 GUI agents 中 source binding、destination grounding、action execution 和 verification 的链式依赖；
- 记录 AndroidWorld 中 unsupported action、loop、no-op、premature done 和 stale observation 等 failure modes；
- 记录高强度 protocol/infrastructure work 如何仍可能无法形成有效 causal test；
- 提供 negative-results reproducibility archive；
- 作为未来外部项目的 baseline implementation，但不是默认主方法。

### 17.2 不应提交为哪类论文

当前证据不支持：

- 新 memory architecture paper；
- 新 role-binding method paper；
- 新 cross-modal consistency method paper；
- 新 GUI-agent critic paper；
- 新 workflow-memory paper；
- 声称 task-level improvement 的 AndroidWorld paper。

### 17.3 最多可以形成的输出

在不新增实验的前提下，后续由 GPT Pro 另行授权后，最多可以考虑：

- technical report；
- negative-results case study；
- reproducibility/infrastructure lessons report；
- benchmark failure-analysis appendix；
- engineering baseline release。

即使如此，也不能把普通负结果包装成方法 novelty。是否公开或投稿不属于本地 Codex 的自动权限。

### 17.4 重新开启研究的唯一合法方式

本分支不得自动 pivot。未来只有在出现**外部新证据或全新项目问题**时，用户重新提交完整材料，由 GPT Pro 重新进行：

1. primary-literature audit；
2. causal-question selection；
3. task distribution definition；
4. pre-registration；
5. feasibility decision。

当前 Codex 不得主动收集用于“重新开启”的数据。

---

## 18. 最终绑定指令

```yaml
document: RAVEN-M_GPTPro_full_plan_2026-08-05.md
date: 2026-08-05
branch: protocol-v2-exploratory

scientific_authority:
  hypothesis_design: GPT_PRO_ONLY
  experiment_design: GPT_PRO_ONLY
  metric_and_threshold_design: GPT_PRO_ONLY
  interpretation: GPT_PRO_ONLY
  pivot_decision: GPT_PRO_ONLY

executor_authority:
  inspect_files: true
  hash_files: true
  validate_raw_outputs: true
  generate_closeout_artifacts: true
  run_offline_standard_library_validator: true
  redesign_science: false

final_decision: STOP_RESEARCH_METHOD
primary_direction: NONE
research_continuation: false
method_implementation: false
destination_first_binding_gate: DO_NOT_IMPLEMENT
new_prompts: 0
new_tasks: 0
new_states: 0
new_cells: 0
new_model_calls: 0
new_androidworld_runs: 0
new_adb_commands: 0
new_qwen_server_starts: 0
new_infrastructure_repairs: 0
new_statistical_tests: 0

retained_value:
  engineering_baseline: true
  negative_results_archive: true
  reproducibility_case_study: true
  positive_method_claim: false

allowed_next_action:
  - execute_scientific_closeout_C0_through_C8
  - stop_after_successful_completion
  - return_immediately_on_any_stop_trigger

automatic_followup_experiment: NONE
automatic_pivot: FORBIDDEN
binding_verdict: RED
```
