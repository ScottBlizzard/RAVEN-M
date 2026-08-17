# GPT_PRO_OPEN_V2_RECOVERY_AFTER_FAILURE_DESIGN_2026-08-15.md

> **研究性质**：commit-pinned、matched prospective diagnostic、仅设计  
> **仓库分支**：`a2-verified-progress-audit-20260810`  
> **设计资料提交**：`1854fd2b7a5b3ca488b45e27953186ba7c447f96`  
> **冻结科研证据边界**：`b5635939acd628156f8c8e36aa8219834a3e6ad8`  
> **本轮动作**：不修改仓库；不运行GPU；不生成production code；不改变历史A-series结论  
> **唯一推荐方案**：**TCRA-R2 — Triggered Counterfactual Recovery Arbitration over A1-R2**  
> **当前裁决**：**设计选择GO；live实验暂时NO-GO，必须先通过零生成跨任务trace audit**

---

## 0. 执行摘要

### 0.1 最终只推荐一条机制

本设计推荐：

# **TCRA-R2：基于A1-R2的触发式反事实恢复仲裁**
**Triggered Counterfactual Recovery Arbitration over A1-R2**

其核心不是继续给executor增加一段“你似乎循环了，请换个办法”的文字，也不是让第二个模型充当只说不控制的critic，而是：

1. 保留A1-R2作为默认executor和默认动作来源；
2. 由一个确定性、只看可见轨迹的`RecoveryMonitor`判断是否已出现两次有证据支撑的重复失败路线；
3. 即使触发，仍先让原始R2生成基础提案 \(A\)；
4. 只有当 \(A\) 准备再次进入同一条已失败路线时，才调用一次同一Qwen模型；
5. 额外调用生成一个显式反事实候选动作 \(B\)；
6. 一个不使用reward、evaluator或隐藏状态的确定性`RecoveryArbiter`检查 \(B\) 是否合法、是否真正偏离 \(A\) 和已失败路线；
7. 检查通过则执行 \(B\)，否则原样执行 \(A\)；
8. 每个episode最多介入一次，不增加AndroidWorld native action-step budget。

### 0.2 一句话可证伪假设

> **当可见轨迹已经两次证明某条局部路线回到同一状态，而R2的新基础提案仍将重新进入该路线时，一次专门生成反事实替代动作并将其直接绑定到下一次真实执行，比继续增加memory文字或generic extra reasoning更可能产生可见、持久且最终有用的策略偏离，同时可通过默认执行R2提案、稀疏触发和六题保持门保护R2现有能力。**

### 0.3 为什么不是普通Triggered Recovery Critic

A1-R9已经检测到预期循环并注入三次恢复信息，但executor仍继续原路线；A10-v2、A11、A12的post-hoc diagnostic中也出现过nonempty read，却没有productive divergence。这说明当前主要缺口不是“系统完全不知道自己失败了”，而是：

\[
\text{failure evidence}
\;\not\Rightarrow\;
\text{different candidate}
\;\not\Rightarrow\;
\text{different executed action}
\;\not\Rightarrow\;
\text{visible progress}
\]

因此，继续优化critic措辞只修补了链条的第一段。TCRA-R2直接补上“替代候选生成—动作仲裁—真实执行”三者之间的控制连接。

### 0.4 为什么当前仍是live NO-GO

仓库已提交的R2结果包含正式总分、episode标识与哈希，但R2完整逐步raw run tree仍位于Git之外。当前无法从已提交材料中诚实给出以下分布：

- 两类触发事件在R2六个成功任务中分别出现几次；
- 它们在十三个失败任务中覆盖几题；
- 首次触发时还剩多少native actions；
- 是否会把成功任务中的正常菜单回访误判为失败循环；
- R2的130次same-state refresh中，哪些是真正重复失败路线。

因此，本设计可以被选择为唯一候选，但在完成零生成、哈希绑定的R2跨任务trace audit之前，不得进入live generation。

---

## 1. Commit-pinned证据审计

## 1.1 提交边界核对

分支`a2-verified-progress-audit-20260810`存在；冻结证据边界提交`b5635939...`的提交信息对应开放式Top-3组件设计自由度，设计提交`1854fd2b...`则只进一步完善研究设计要求与文档，没有引入新的live实验结果。`b5635939...`到`1854fd2b...`之间应视为设计与说明层更新，而不是科研证据边界扩展。

本设计采用以下约束：

- **科研事实**只能来自`b5635939...`及其祖先中的正式证据；
- `1854fd2b...`用于确定本轮输出范围、审计要求与设计完整度；
- 不使用任何边界之后可能出现的实验结果；
- 不把设计文档中的预期、候选排序或作者判断当作实验事实。

## 1.2 证据类型定义

| 标签 | 含义 | 可以支持什么 | 不能支持什么 |
|---|---|---|---|
| **FULL** | 冻结配置下完成正式任务集合的实验 | 正式accuracy、reward、calls、tokens | 组件因果性，除非另有消融 |
| **STITCHED-FULL** | 透明记录、基础设施有效，但由多个片段拼接的完整任务结果 | 有限的完整控制结果 | pristine单次运行、严格同分布复现 |
| **GATE** | 只运行冻结能力门中的一个或若干任务 | 该门是否通过、该episode行为 | `0/19`、完整suite准确率 |
| **OFFLINE-QF** | generation为零的offline qualification/replay | 解析、覆盖、状态机或协议资格 | live策略能力和最终reward |
| **PROTOCOL-INVALID** | 预注册协议在生成前即被证明无法满足其门槛 | 该协议不能进入live | 模型或机制accuracy为零 |
| **DIAGNOSTIC** | 对已观察任务进行的post-hoc诊断 | 行为机制线索、失败模式 | pristine generalization、正式主结果 |
| **CODE/CONTRACT** | 实现、prompt、parser、controller或冻结合同 | 系统实际允许看到什么、如何控制 | 组件在任务上有效 |
| **INFERENCE** | 本文从多项事实推导的研究判断 | 候选选择与设计动机 | 作为已验证实验结论 |
| **UNKNOWN** | 当前Git证据不足 | 明确待补证据 | 任何确定数值或分布 |

## 1.3 A-series状态总表

| 系统或材料 | 正确证据身份 | 审计结论 |
|---|---|---|
| **A0** | FULL | `4/19`，reward `4.5`，329 calls，1,273,361 tokens |
| **A1** | FULL | `5/19`，reward `5.5`，603 calls，3,464,267 tokens |
| **A1-R2** | FULL | `6/19`，reward `6.5`，603 calls，595 actions，2,685,730 tokens |
| **A2** | FULL | 正式完整结果；其`0/19`可以保留，因为它确实完成了正式suite |
| **A3–A5** | GATE | 首题能力门结果；不得称为完整`0/19` |
| **A6** | FULL，并附零生成轨迹分析 | 可用于证明重复状态—动作现象在完整任务集合中出现；不能直接当作R2分布 |
| **A7** | STITCHED-FULL | 透明拼接的19题控制结果，不应改写为pristine单次run |
| **A8-v2** | GATE | 首个Expense任务能力门失败；detector/read激活不等于完整accuracy |
| **A9** | GATE | Expense成功但memory silent；随后Retro失败且出现恢复read |
| **A10-v1、A10-v2、A11** | OFFLINE-QF失败 | generation为零的资格失败；没有正式live suite |
| **A12** | PROTOCOL-INVALID | 预注册要求的独立比较数量超过可实现上限，因此没有live结论 |
| **A10-v2/A11/A12六题诊断** | DIAGNOSTIC | 可说明read与productive divergence的关系；不是正式主实验 |
| **A1-R3–R12** | 十个冻结身份不同的GATE结果 | 每个均为首个Expense能力门的有效失败；它们属于连续累积补丁谱系，不是十个独立`0/19`实验，也不是十个统计独立机制 |

这些身份与仓库中的HANDOFF、组件证据账本、纵向R1–R12审计及正式结果相符。

## 1.4 A1-R2已提交事实

A1-R2相对A1为：

\[
1\text{ win},\quad 0\text{ loss},\quad 18\text{ ties}
\]

唯一新增完整成功是`OsmAndMarker`。六个成功任务为：

1. `ExpenseDeleteMultiple2`
2. `RetroSavePlaylist`
3. `SimpleCalendarAddOneEvent`
4. `SportsTrackerTotalDurationForCategoryThisWeek`
5. `RecipeDeleteMultipleRecipesWithConstraint`
6. `OsmAndMarker`

R2共有436次nonempty memory read、205次write及130次same-state refresh；这些计数只说明组件被读取或状态被刷新，不能单独证明memory导致了成功。特别是`OsmAndMarker`的成功没有已提交的因果消融，因此不得归因给memory。

R2 offline replay在零生成条件下覆盖19个episode，并验证了其压缩表示与协议处理；该replay不是新的reward实验，也不能把offline projection解释为live提升。

## 1.5 A1-R3–R12的正确解释

R3–R12不是十个互不相关的候选机制，而是一条针对首个Expense任务不断叠加补丁的连续谱系：

- R3触发前缀未生效；
- R4 writer开始激活，但保留陈旧状态；
- R5转移失效逻辑丢失局部obligation；
- R6保留目标但继续错误空间点击；
- R7未捕捉实际material route；
- R8过度依赖严格ABAB模式；
- R9识别循环并注入三次恢复信息，却没有产生有效策略变化；
- R10增加大量校准read但行为更差；
- R11产生更多注入和检查，仍未成功；
- R12减少重复动作和token，但reward仍未改善。

这条谱系提供的重要负面证据不是“十种记忆都在19题得0分”，而是：

> 在同一首题上不断增加状态、规则和prompt约束，可以提高检测和注入数量，却没有可靠地把这些信号转换为更好的下一步动作。

仓库自身也指出该谱系存在未重置父系统、持续堆叠状态与prompt、过度围绕Expense设计、把activation误当成productive divergence等过程问题。

## 1.6 A7–A12的正式与非正式证据边界

### A7

A7提供透明拼接的19题控制结果，适合作为基础设施有效的对照材料，但不能声称它是单次preregistered pristine run。

### A8/A9

A8的零生成分析使用model-visible screenshot的固定中间区域哈希、canonical action和极低像素变化规则识别复现；A6轨迹中存在大量exact revisit、repeated state-action和repeated no-progress现象。这说明某些可见复现检测器确实能机械激活，但A6的这些数量不是R2的逐题分布。

A9的first-gate证据表明：Expense任务可以成功且memory silent；Retro任务失败时detector/read可以激活。这同时提供两个反例：

- 成功不一定需要恢复组件；
- 恢复组件激活也不一定产生成功。

### A10/A11

A10-v1、A10-v2、A11均在generation为零的offline qualification阶段失败，因此没有正式live accuracy结论。

### A12

A12在preflight阶段被证明无法满足其预注册独立比较数量，属于protocol invalid，而不是模型运行后失败。

### Post-hoc六题diagnostic

A10-v2、A11、A12六题诊断分别出现nonempty read，但已提交分析中的productive divergence均为零；成功任务主要是memory silent。这只能支持“read不足以说明机制有效”，不能成为正式accuracy排名。

## 1.7 已提交事实、本文推断与未知证据

### 已提交事实

- R2是当前正向参考：6/19、reward 6.5、相对A1一胜零负。
- 某些可见重复检测器能够激活。
- R9已将循环信息注入executor，但没有形成有效策略变化。
- 多个诊断arm出现read而无productive divergence。
- R2成功任务存在memory-silent现象。
- R2完整raw trace tree未随Git提交，已提交结果只绑定了episode信息和哈希。

### 本文推断

- 当前最值得修复的链路不是“是否能检测失败”，而是“失败证据如何生成并绑定一个真正不同的动作”。
- 继续添加memory字段或恢复措辞，预期边际收益较低。
- 最小可证伪升级应只在R2即将重入已失败路线时增加一次候选生成，并必须直接影响真实动作。
- 一个独立judge模型会把额外算力、候选质量和仲裁能力混在一起，不适合作为第一验证。

### 当前未知

- R2六个成功任务中的安全触发率；
- R2十三个失败任务中的跨任务触发覆盖率；
- 精确循环是否足以覆盖至少一个可挽救失败任务；
- 同一个Qwen在看到失败轨迹后能否提出比自身基础提案更好的局部替代动作；
- 收益是否仅来自多一次推理；
- 一个不同动作是否会转化为goal-directed visible progress；
- R2在当前推理基础设施上的复现实验是否仍保持6/6成功门。

---

## 2. 选择方案前必须完成的零生成、哈希绑定跨任务trace audit

## 2.1 Audit目标

该audit不生成任何新模型文本，不修改历史episode，不计算新的策略reward。它只回答：

1. 本设计所需的触发条件是否真实存在于R2完整19题轨迹中；
2. 是否主要出现在失败任务而不是六个成功任务；
3. 首次触发时是否还剩足够动作预算；
4. 是否存在多个任务族，而不是仍然只围绕`ExpenseDeleteMultiple2`；
5. trigger是否会在历史R2基础提案已经自行改变路线时误介入。

在该audit通过前，TCRA-R2不得进入live实验。

## 2.2 当前Git中缺少的R2证据

需要从本地原始run tree物化并哈希绑定：

- 每个episode的完整`events.jsonl`或等价逐步记录；
- 每步before/after model-visible PNG；
- 每次基础Qwen调用的原始response；
- 实际解析结果与实际执行的canonical action；
- prompt/history/R2 ledger read内容；
- 每次调用的输入输出token、延迟、request ID和模型收据；
- 可见transition记录；
- evaluator关闭前后的生命周期日志；
- 那一次infrastructure-invalid attempt的完整原始目录；
- invalid attempt与合法replacement的双向链接。

不得因为正式结果JSON已有聚合计数，就推断这些逐步证据已经在Git中可审计。

## 2.3 双视图隔离

原始材料物化后必须拆成两个物理隔离视图。

### `PolicyTraceView`

detector和未来runtime组件唯一允许使用的字段：

- 用户有效goal；
- 当前及历史model-visible RGB；
- 执行过的canonical action；
- 原始模型输出中已被executor看到的内容；
- 当前可见状态是否与历史可见状态完全相同；
- before/after可见transition摘要；
- 已消耗及剩余native action数量。

### `SealedLabelView`

只允许在event ledger冻结并哈希后用于离线统计：

- task name；
- app或任务族标签；
- evaluator结果；
- reward；
- success/failure；
- activity/package；
- UI tree或accessibility；
- invalid/replacement标签；
- 任何其他runtime禁止字段。

detector实现不得import、读取或接收`SealedLabelView`。

## 2.4 哈希链

建议生成以下冻结链：

\[
M_0=\operatorname{SHA256}(\text{raw file manifest})
\]

\[
M_1=\operatorname{SHA256}(M_0 \Vert \text{PolicyTraceView manifest})
\]

\[
M_2=\operatorname{SHA256}(M_1 \Vert \text{detector source/config})
\]

\[
M_3=\operatorname{SHA256}(M_2 \Vert \text{unlabeled event ledger})
\]

\[
M_4=\operatorname{SHA256}(M_3 \Vert \text{label join report})
\]

其中：

- `M0`列出每个原始文件的相对路径、字节数与SHA-256；
- `M1`证明policy视图来自哪些原始证据；
- `M2`冻结检测器实现及全部阈值；
- `M3`在看success/reward标签之前冻结事件位置；
- `M4`才把事件分布与六成功/十三失败标签连接。

任何修改`M2`后重新查看标签的行为都属于重新设计，不能在同一次audit中继续调参。

## 2.5 分析单位：Eligible Recovery Event

不能把单次read、单步像素变化或一次重复点击作为分析单位。建议使用：

> **Eligible Recovery Event，ERE：在一个episode内，由至少两份已完成的可见失败支持形成、当前处于相同anchor状态、且R2新基础提案准备再次进入同一失败路线的最大化事件。**

一个ERE最多记一次。相同anchor与失败路线后续继续重复，不重复增加event数量。

## 2.6 冻结的两类触发证据

### E1：`STATIONARY_REPEAT`

满足：

1. 当前可见状态哈希为 \(S\)；
2. 在最近12个已执行动作内，已至少两次出现：
   \[
   S \xrightarrow{q(a)} S
   \]
3. 两次使用相同的route-action key \(q(a)\)；
4. 当前R2基础提案 \(A\) 的route-action key仍为同一个 \(q(a)\)。

这表示相同局部动作已至少两次没有改变可见状态，而R2准备第三次尝试。

### E2：`CLOSED_ROUTE_REPEAT`

满足：

1. 当前可见状态哈希为anchor \(S\)；
2. 最近12个已执行动作中，存在两次相同的闭合路线：
   \[
   S \xrightarrow{R} S
   \]
3. 每条路线压缩后长度为2至6；
4. 两条路线具有相同的run-length-compressed route signature \(R\)；
5. 当前R2基础提案 \(A\) 与该路线首个route-action key相同。

这用于覆盖R8严格ABAB无法识别、但R9能够捕捉的`A^+B^+`式路线复现。

### 状态与动作签名

- 可见状态签名应逐字节复用A8已审计的model-visible中间92% RGB SHA-256实现；
- exact action key应复用official canonical action JSON的SHA-256；
- route-action key应复用A1-R9中已提交的动作族/空间区域归一化原语；
- 不得根据本次19题结果新发明坐标阈值；
- 若A1-R9原语无法独立抽取、无法通过golden test或包含任务特判，则本设计audit直接NO-GO。

哈希只用于同一episode内的相等性比较；不得存在“某个已知screen hash对应某个动作”的跨episode查表，因此不构成screen-hash特判。

## 2.7 第三类模式只审计、不进入首版触发

还应统计：

### P3：`SEMANTIC_OR_PIXEL_CHANGING_STALL`

例如：

- 错误点击产生短暂动画后回到近似界面；
- 键盘光标、时间、toast或滚动细微变化导致exact hash不同；
- 空间点击错误但每次改变少量像素；
- 任务在语义上没有进展，却没有形成精确闭环。

P3是TCRA-R2的已知盲区。首版不得为了覆盖P3引入感知阈值、视觉语义分类器或额外模型调用，否则会同时扩大误触发面和问题族范围。若零生成audit显示失败任务主要属于P3而非E1/E2，结论应为TCRA-R2 NO-GO，而不是现场扩展检测器。

## 2.8 Audit必须报告的分布

逐任务至少报告：

| 字段 | 含义 |
|---|---|
| `episode_id`与raw hash | 绑定原始证据 |
| `validity_status` | valid或infra-invalid及replacement |
| `native_actions` | 原始执行动作数 |
| `E1_support_count` | stationary重复支持数量 |
| `E2_support_count` | closed-route重复支持数量 |
| `P3_candidate_count` | 仅诊断的非精确stall |
| `ERE_count` | 满足完整call gate的事件数 |
| `first_ERE_step` | 首次可介入位置 |
| `remaining_native_steps` | 首次ERE时剩余预算 |
| `base_would_reenter` | 历史R2下一提案是否重入失败路线 |
| `route_after_event` | 历史R2后来是否自行偏离 |
| `task_outcome` | 只能在M3冻结后join |
| `task_family` | 只能用于离线分布报告 |

必须分别汇总：

- 六个R2成功任务；
- 十三个R2失败任务；
- 不同任务族；
- 首次ERE剩余预算；
- 每类事件的反例和误触发案例。

## 2.9 Audit通过门

在没有任何生成的情况下，必须同时满足：

1. 19个正式R2 episode和infra-invalid lineage全部完成哈希核对；
2. `generation_calls = 0`；
3. 两个独立实现对所有event ID、event step和blocked route逐字节一致；
4. 删除或随机置换reward、evaluator、activity、package、UI tree后，event ledger完全不变；
5. 六个R2成功episode中：
   \[
   \#\text{call-gated ERE}=0
   \]
6. 至少4个不同的R2失败任务存在call-gated ERE；
7. 上述覆盖至少3个不同任务族，不能只来自Expense；
8. 每个可介入event至少剩余6个native actions；
9. detector配置冻结后只允许“通过”或“否决”，不得根据标签重新调窗口、route长度或签名规则。

### Audit裁决

- **全部满足**：TCRA-R2获得live implementation planning GO。
- **任一不满足**：TCRA-R2 NO-GO。
- NO-GO后最小动作是提交完整audit与缺口，不得在同一研究包内临时增加语义检测、坐标教程或任务规则。

---

## 3. 跨任务问题分析

## 3.1 当前已有的跨任务信号

现有证据共同支持以下结构：

### 信号A：可见重复确实存在

A6完整轨迹审计发现大量exact revisit、repeated state-action及repeated no-progress记录，因此重复并非只存在于一个手工挑选的Expense例子中。

### 信号B：检测器可以机械激活

A8/A9以及A1-R9证明某些recurrence detector确实能产生read或恢复提示。

### 信号C：检测到失败并未可靠改变策略

A1-R9已经对预期循环注入三次恢复信息，executor仍继续错误路线。A10-v2、A11、A12诊断也出现read而无productive divergence。

### 信号D：成功任务往往不需要该组件

A9的Expense成功以及A10-v2/A11/A12的若干成功任务均表现为memory silent。因此不能通过“成功episode里memory字段非空”来建立因果故事。

## 3.2 为什么问题不是“再多写一点memory text”

继续增加memory文字至少存在五个已观察风险：

1. **读取不等于使用**：nonempty read不能证明下一动作受其影响；
2. **动作变化不等于改善**：即使文本改变，也可能继续同一空间区域或同一控制族；
3. **prompt栈累积污染**：R3–R12已经展示不断叠加指令和状态机的脆弱性；
4. **成功能力可能被覆盖**：always-on失败叙事可能让本来成功的R2路线过度反思；
5. **无法区分算力与机制**：多一段文字或多一次调用可能只是提高采样机会。

R9尤其关键：它已经跨过“没有检测到循环”这一步，却仍未跨过“产生并执行真正不同的局部策略”。因此下一设计必须把行为因果链推进到真实动作，而不是继续把注入文本数量作为成功代理。

## 3.3 成功任务误触发风险

即使一个轨迹回到相同截图，也不必然表示失败：

- 正常从子页面返回主页面；
- 查看某个条目后返回列表继续处理其他条目；
- 删除或保存后界面视觉上恢复；
- 同一列表页承担多个合法操作；
- 打开键盘、关闭对话框后回到原界面；
- app延迟导致重复等待。

因此，单次状态回访不能触发；单次相同点击不能触发；像素变化很小也不能直接解释为无进展。

TCRA-R2使用“三重保守门”：

\[
\text{两份历史失败支持}
+
\text{当前处于相同anchor}
+
\text{R2基础提案仍将重入}
\]

并在live前要求历史六成功中零call-gated event。

## 3.4 反例与覆盖边界

TCRA-R2不会解决所有失败：

- 错误动作每次导致不同截图；
- 第一次错误后立即耗尽预算；
- 任务需要长程重规划而非局部替代；
- 失败来自目标理解、文本输入内容或最终完成判断；
- Qwen即使看到失败证据，也生成另一个错误动作；
- 正确恢复需要历史截图，而当前VLLM接口只支持当前图片。

这些不是应在首版继续堆叠的理由，而是设计的可证伪边界。当前client只接受一张当前图片，因此本方案只发送当前截图；历史信息使用可见动作和状态别名的文本摘要，不绕过接口加入历史图像。

---

## 4. 候选方向比较

| 候选方向 | 能否解决“检测后仍无策略变化” | 对R2六成功风险 | 因果可辨识性 | 成本 | 裁决 |
|---|---:|---:|---:|---:|---|
| **继续优化critic/memory prompt** | 低；R9已有直接负面证据 | 中到高，容易always-on污染 | 低，文本是否被使用不清楚 | 低 | 否决 |
| **确定性恢复动作，例如强制Back、换区域点击** | 能强制动作变化，但不保证更好 | 高；跨任务缺少安全动作证据 | 高 | 极低 | 否决 |
| **generic extra reasoning** | 可能生成不同动作 | 中 | 只能说明多算一次是否有用 | 中 | 保留为active control，不作为最终机制 |
| **不确定性升级或请求更长思考** | 可能改善候选，但不保证绑定执行 | 中 | 低到中 | 中 | 否决为主方案 |
| **完整局部replanner/子目标规划器** | 可能有效 | 高；改变信息生命周期与长期策略 | 中 | 高 | 暂不选择，且接近另一问题族 |
| **多候选生成＋模型judge** | 可能有效 | 中 | 低；候选数、judge能力和额外算力混杂 | 高 | 否决首轮 |
| **一个恢复候选＋确定性仲裁** | 直接把失败证据连到真实动作 | 可通过默认A、稀疏触发和6/6门控制 | 高；候选、仲裁、执行均有receipt | 最多一次额外调用 | **唯一推荐** |

此前组件选择材料曾把更完整的candidate arbitration推迟，主要顾虑是多角色、额外采样和因果混杂。TCRA-R2并不恢复那个重型版本：它只有一个额外候选调用，没有第二个模型judge，最终选择由确定性规则完成。

---

## 5. 最终系统定义

## 5.1 系统名称

# **TCRA-R2**
**Triggered Counterfactual Recovery Arbitration over A1-R2**

中文：**基于A1-R2的触发式反事实恢复仲裁**

## 5.2 父系统

父系统选择冻结A1-R2，而不是A7、A8、A9、A10、A11或A12。

原因：

1. R2是当前唯一相对A1取得正式一胜零负的纵向系统；
2. R2完整suite为6/19，是需要保护的正向能力边界；
3. R2没有增加executor calls，且已有紧凑的`observed/verified/pending`表示；
4. 失败arm包含累积prompt和状态机负担，继承完整栈会同时继承未隔离变量；
5. A10/A11未通过offline qualification，A12协议无效，不适合作为行为父系统。

R2实现将当前截图声明为权威信息源，memory有明确TTL、容量与事务式commit；TCRA-R2保留这些语义，不重新解释历史memory。

## 5.3 复用的最小已有原语

| 来源 | 只复用什么 | 不继承什么 |
|---|---|---|
| **A1-R2** | 完整executor、prompt、parser、compact verified/pending memory和commit语义 | 不改变其默认行为 |
| **A8** | model-visible中间92% exact state hash、canonical action hash | 不继承像素阈值式progress判断和恢复prompt |
| **A1-R9** | run-length route recurrence与动作族/区域签名原语 | 不继承R3–R9累积prompt栈和三次注入逻辑 |
| **A12 diagnostic tooling** | divergence、progress、relapse的审计思想 | 不继承A12行为协议或无效比较结构 |
| **official protocol** | 正式action schema、parser及坐标语义 | 不新增另一套执行格式 |

仓库组件账本也支持“提取窄原语而不继承完整失败arm”，并明确反对always-on prose、像素变化即进展、复杂状态机及以read数量代替组件有效性。

## 5.4 真正新增的干预

TCRA-R2只新增一个逻辑模块，内部含三个最小部分：

1. **`RecoveryMonitor`**  
   确定性地识别E1/E2事件，不调用模型，不选择动作。

2. **`CounterfactualRecoveryProposer`**  
   在满足完整call gate时，用同一Qwen调用一次，生成候选 \(B\)。

3. **`RecoveryArbiter`**  
   确定性验证 \(B\) 的协议合法性和路线偏离；不预测reward，不调用模型。

没有新增：

- 长期任务规划器；
- app router；
- task whitelist；
- evaluator verifier；
- 独立judge模型；
- 多候选beam；
- 历史截图编码器；
- native action budget；
- 针对Expense的规则。

---

## 6. 完整端到端控制流

```text
当前model-visible screenshot
          │
          ▼
原始A1-R2 read + prompt + executor call
          │
          ▼
基础提案 A（尚未执行）
          │
          ├── A为answer/terminate/无效 ──► 完全遵循R2原路径，不调用恢复组件
          │
          ▼
RecoveryMonitor检查既有可见轨迹
          │
          ├── 无E1/E2事件 ─────────────► 执行A
          │
          ├── A已经偏离失败路线 ───────► 执行A
          │
          ▼
生成冻结的RecoveryPacket
          │
          ▼
同一Qwen一次辅助调用，得到候选 B
          │
          ▼
RecoveryArbiter
          │
          ├── B无效/不安全/不偏离 ─────► 执行A
          │
          └── B合法且偏离 ─────────────► 执行B
                                             │
                                             ▼
                         只commit被真实执行的response/action/memory
                                             │
                                             ▼
                               获取下一张model-visible screenshot
                                             │
                                             ▼
                   更新R2、visible trace及仅用于审计的progress/relapse watch
```

## 6.1 每一步的精确定义

### 步骤1：初始化

- 按冻结R2配置初始化executor与memory；
- 初始化空`VisibleTraceWindow`；
- `recovery_used = false`；
- 不预载任何任务、app、screen hash或历史结果表。

### 步骤2：生成基础提案 \(A\)

- 使用与R2完全相同的goal、当前截图、history和memory read；
- 使用相同Qwen模型、revision、sampling和seed；
- 得到完整原始response \(A_{\text{raw}}\)；
- 用official parser和R2 memory-prefix parser解析；
- 此时**不得提前commit** \(A\)，因为最终执行动作尚未确定。

### 步骤3：不适用恢复的情况

以下情况直接沿用R2：

- \(A\) 是`answer`或`terminate`；
- \(A\) 无法被R2正式parser解析；
- 当前episode已使用过恢复调用；
- 剩余native actions少于6；
- 没有E1/E2；
- \(A\) 已经与blocked route entry不同。

恢复组件不得充当parser repair、completion verifier或终止审查器。

### 步骤4：构造`RecoveryPacket`

Packet包括：

- effective user goal；
- 当前model-visible screenshot；
- 本次R2已经读取的compact ledger文本；
- 最近最多8条已执行动作及可见transition摘要；
- event subtype、anchor别名、两份失败支持和blocked route；
- 尚未执行的基础提案 \(A\)；
- 当前剩余native action数量。

Packet不包含：

- reward；
- evaluator；
- task name字段；
- app ID、package、activity；
- hidden UI tree或accessibility；
- future screenshot；
- 未执行未来动作；
- 已知成功答案；
- 其他task的轨迹。

用户goal中自然出现的app名称不需要删除，但不得据此建立运行时分支或whitelist。

### 步骤5：生成反事实候选 \(B\)

只调用一次同一Qwen。模型需要：

- 指出此前路线隐含的失败假设；
- 提出一个局部、可立即执行、可通过下一截图检验的替代动作；
- 不生成完整长程计划；
- 不判断最终任务是否完成；
- 不输出Home/Menu；
- 使用official action schema和R2兼容memory前缀。

### 步骤6：确定性仲裁

`RecoveryArbiter`只做机械检查：

1. \(B\)能被official parser解析；
2. \(B\)包含合法R2 memory前缀；
3. \(B\)不是`answer`、`terminate`、Home或Menu；
4. \(B\)的route-action key与 \(A\)不同；
5. \(B\)不等于当前event的任何blocked route entry；
6. \(B\)不是从相同anchor已经执行过的同route-action；
7. `wait`只有在blocked route不以wait为核心且 \(A\neq wait\) 时可接受；
8. 当前截图哈希在辅助调用期间没有变化。

通过则选择 \(B\)，否则选择 \(A\)。Arbiter不得判断“哪个动作更可能得分”，也不得读取截图语义、reward或evaluator。

### 步骤7：执行一个动作

每个native step仍只执行一个动作：

\[
a_t =
\begin{cases}
B,& \text{arbiter accepts }B\\
A,& \text{otherwise}
\end{cases}
\]

额外调用不会增加native action-step budget。

### 步骤8：只commit真实执行的决策

这是最高风险集成点。

若执行 \(A\)：

- 按原始R2逻辑commit \(A\) 的history、action summary和memory；
- \(B\)只保留在审计receipt中。

若执行 \(B\)：

- commit \(B\) 的Action、tool call和R2 memory内容；
- 将 \(A\)记录为`unexecuted_base_proposal`；
- 不得把 \(A\)写成已执行动作；
- 不得把 \(A\)的pending/verified ledger写入R2；
- 下一轮history必须反映真实执行的 \(B\)。

Controller当前流程将generation、parse、action execution和memory commit紧密相连，因此实现时必须显式拆分“基础提案生成”和“最终选择后commit”。

### 步骤9：更新可见状态

动作完成后：

- 采集正常的下一张model-visible screenshot；
- 更新exact state hash；
- 写入已执行canonical action；
- 更新visible transition；
- 创建一个只用于后续离线因果审计的`RecoveryWatch`；
- 不因结果好坏再次调用模型；
- 不改变本episode的`recovery_used = true`。

---

## 7. 信息访问边界

| 组件 | 允许看到 | 明确禁止 |
|---|---|---|
| **R2 executor** | 原始R2允许的goal、当前截图、history、compact memory | 新的evaluator、hidden UI或future信息 |
| **RecoveryMonitor** | 过去及当前model-visible RGB hash、已执行canonical actions、native step计数 | goal语义、reward、task name、app、package、activity、UI tree |
| **RecoveryProposer** | effective goal、当前截图、同一R2 ledger副本、最近可见轨迹、event、未执行A | evaluator、reward、task/app ID、hidden UI、activity/package、未来截图 |
| **RecoveryArbiter** | A/B的parsed action、route signatures、event blocked entries、当前截图hash是否稳定 | reward预测、截图语义判断、task规则、模型judge |
| **Runtime logger** | calls、tokens、latency、event与selection receipts | 不得把审计字段反馈给策略 |
| **Offline label join** | outcome、reward、task family及runtime receipts | 不得影响已经冻结或执行过的行为 |
| **AndroidWorld evaluator** | 保持原有episode结束后的评估位置 | 不得进入任何模型prompt或runtime controller分支 |

当前controller内部确实持有UI/activity/package等审计信息，但原始模型主要接收当前截图。新实现必须构造显式`RecoveryPolicyView`，而不能把controller原始before/after字典直接传给新组件。Evaluator仍只在episode生命周期规定的位置使用。

---

## 8. 状态对象、生命周期与容量

| 对象 | 内容 | 生命周期 | 容量与失效 |
|---|---|---|---|
| `VisibleStateSignature` | A8兼容的中间92% RGB SHA-256 | 单步及最近窗口 | screenshot变化即产生新值 |
| `ExactActionKey` | official canonical action JSON hash | episode | 不跨episode查表 |
| `RouteActionKey` | R9兼容动作族/区域签名 | episode | 只用于局部路线比较 |
| `VisibleTraceWindow` | state、执行动作、visible transition | 最近12个native actions | FIFO，最大12 |
| `RecoveryEvent` | subtype、anchor、两份support、blocked route | 一次event | 创建后不可变，哈希绑定 |
| `BaseProposal` | 尚未执行的A response/action | 当前native step | 截图变化即过期 |
| `RecoveryPacket` | 允许字段的冻结副本 | 当前辅助调用 | SHA-256绑定，调用后过期 |
| `RecoveryCandidate` | B原始response及parse结果 | 当前native step | 选定或拒绝后过期 |
| `ArbitrationReceipt` | A/B hash、检查结果、selected action | episode及最终报告 | 不可变 |
| `RecoveryWatch` | anchor、blocked route、selected B | 最多后续4个动作 | 只用于审计，不控制策略 |
| `recovery_used` | episode是否已调用恢复 | episode | 一旦为true不再复位 |
| R2 memory | 原始R2 compact ledger | 完全继承R2 | TTL、容量和事务语义不变 |

历史轨迹只向proposer发送最近8条文本摘要；monitor内部可保留最近12条签名。这使模型上下文和确定性检测窗口彼此解耦。

---

## 9. 推荐完整prompt模板

## 9.1 Specialized recovery system prompt

```text
You are the Counterfactual Recovery Proposer for a mobile GUI agent.

You receive only:
1. the user's effective goal,
2. the current model-visible screenshot,
3. a compact ledger already available to the base executor,
4. a short visible action/transition trace,
5. a frozen recurrence event, and
6. an unexecuted base proposal.

You never receive evaluator output, reward, hidden UI trees, accessibility data,
activity/package identifiers, future screenshots, future actions, or a known answer.

The current screenshot is authoritative.

This call occurs only because the base proposal would re-enter a route that has
already returned to the same visible anchor twice.

Your job is not to write a long plan and not to judge task completion.
Identify the concrete failed assumption behind the repeated route and propose
exactly one locally testable next action that breaks that route.

Prefer:
- a different visible hypothesis,
- a reversible local action,
- a different control or spatial target when the previous one was ineffective,
- an action whose expected visible evidence can be checked on the next screen.

Do not:
- repeat the blocked route entry,
- output answer or terminate,
- press Home or Menu,
- invent hidden controls or unseen state,
- claim that an action has succeeded before it is executed.

Return exactly:

Thought: RECOVERY(
mode=<STATIONARY_REPEAT|CLOSED_ROUTE_REPEAT|SPATIAL_MISGROUNDING|STALE_ASSUMPTION|WRONG_CONTROL_FAMILY|OTHER>;
failed_assumption=<brief>;
expected_visible_evidence=<brief>
)
Action: MEMORY[observed=<visible facts>; verified=<currently verified facts>; pending=<unmet goal>] | <one concise action summary>
<tool_call>{"name":"mobile_use","arguments":{...}}</tool_call>
```

`RECOVERY(...)`只用于诊断审计。行为有效性只依赖已存在的official parser、tool call和R2 `MEMORY[...] |`前缀，不应再引入一种脆弱的行为关键parser。

## 9.2 Specialized recovery user template

```text
[USER GOAL]
{effective_goal}

[CURRENT R2 LEDGER]
{exact_rendered_r2_ledger}

[RECOVERY EVENT]
event_id: {event_id}
type: {event_type}
anchor: {anchor_alias}
support_1: {support_1_summary}
support_2: {support_2_summary}
blocked_route: {blocked_route_summary}
remaining_native_actions: {remaining_actions}

[RECENT VISIBLE TRACE — EXECUTED ACTIONS ONLY]
{up_to_8_action_transition_records}

[UNEXECUTED BASE PROPOSAL]
{base_raw_response}

The attached image is the current and authoritative model-visible screenshot.
Return one counterfactual next action in the required format.
```

## 9.3 Resource-matched generic control prompt

Generic active control使用完全相同的：

- model/revision；
- 当前截图；
- structured packet；
- call timing；
- token上限；
- parser；
- deterministic arbiter；
- native action budget。

唯一差异是system instruction不包含“失败假设分类”“反事实恢复”或“必须打破失败路线”的专业指导：

```text
You are an independent second-opinion action proposer for a mobile GUI agent.

Review the user's goal, the current screenshot, the compact ledger, the recent
visible trace, and the unexecuted base proposal. Produce exactly one candidate
next action that may improve the chance of completing the task.

Do not judge final completion. Do not use evaluator output, reward, hidden UI,
activity/package data, future screenshots, or future actions.

Return the same official Action, MEMORY prefix, and tool-call format.
```

两个prompt在冻结前应通过tokenizer检查，使固定instruction部分长度差异不超过3%，但不得用无意义padding凑长度。所有实际input/output token仍需分别报告。

---

## 10. 触发、调用与资源预算

## 10.1 触发原则

只有同时满足以下条件才允许辅助调用：

\[
\text{EligibleCall}_t =
\text{ERE}_t
\land
\neg\text{recovery\_used}
\land
\text{remaining\_actions}\ge 6
\land
\text{valid\_nonterminal}(A_t)
\land
q(A_t)\in\text{blocked\_entries}
\]

也就是说：

- detector发现历史重复还不够；
- R2基础提案若已经自行改变路线，就不得介入；
- 只在R2准备再次犯同一个局部错误时调用。

## 10.2 调用预算

| 项目 | 冻结上限 |
|---|---:|
| 辅助模型调用 | 每episode最多1次 |
| 辅助调用重试 | 0次模型级重试 |
| 输出token | 最多256 |
| 单次总上下文 | 不超过8192 tokens |
| 文本轨迹 | 最近最多8条 |
| monitor窗口 | 最近12个native actions |
| wall latency | 单次辅助调用最多60秒 |
| native action-step | 与R2完全相同，不增加 |
| 历史截图 | 0张；只附当前截图 |
| 额外judge调用 | 0 |
| 额外reflection调用 | 0 |

这些限制比开放设计文档允许的“每episode最多两次辅助调用”更严格，目的是降低成功任务风险和额外算力混杂。开放设计材料给出的共同上限包括同一Qwen、有限辅助调用、256输出token、8192上下文及不增加native budget。

## 10.3 Cooldown与expiry

- episode级one-shot：第一次辅助调用后永不再次调用；
- 相同event ID不可重复消费；
- `RecoveryPacket`只对生成它的当前截图hash有效；
- 若截图在A与B之间变化，B自动失效；
- B必须在当前native step立即选择，不能存入后续memory等待执行；
- `RecoveryWatch`最多跟踪后续4个动作，但不参与runtime控制。

## 10.4 失败处理

### 有效科学失败

以下情况不能重跑：

- B格式错误；
- B被parser拒绝；
- B重复blocked route；
- B合法但无进展；
- B导致错误页面或任务失败；
- episode达到max steps；
- reward为零；
- Full未通过六题保持门。

这些都是机制或模型的有效失败。

### Infrastructure-invalid

以下情况可在完整留痕后进行一次同任务replacement：

- 辅助调用发生HTTP/transport错误且没有返回模型输出；
- emulator/controller崩溃导致episode无法按协议关闭；
- 服务器在冻结60秒上限前没有完成响应；
- evaluator生命周期异常，无法形成合法结果；
- 日志或截图写入基础设施失败，导致关键receipt缺失。

如果辅助transport失败发生在trigger之后、下一native action之前，应中止该attempt并标记infra-invalid，不能悄悄fallback到A后仍称为完整Full episode。

每个arm、每个task最多允许一次infra-invalid replacement。第二次基础设施失败使该arm在该任务上保持incomplete，不得继续重试。

---

## 11. 主要仓库修改面与高风险集成点

本轮不实现代码；以下是实现规划。

## 11.1 建议新增模块

### `tcra_recovery.py`

包含：

- `VisibleStateSignature`
- `RouteActionSignature`
- `RecoveryMonitor`
- `RecoveryEvent`
- `RecoveryPacket`
- `RecoveryCandidate`
- `RecoveryArbiter`
- `ArbitrationReceipt`
- `RecoveryWatch`

### `tcra_trace_audit.py`

包含：

- raw materialization验证；
- policy/label双视图；
- zero-generation detector replay；
- event ledger与hash chain；
- cross-task分布报告。

## 11.2 `controller.py`

需要进行最小但关键的控制流重构：

1. 将基础response生成与立即执行解耦；
2. 在A parse后、native action前插入可选recovery hook；
3. 构造无隐藏字段的`RecoveryPolicyView`；
4. 支持一次辅助调用并单独计费；
5. 根据arbiter选择A或B；
6. 下游`decision`、`call`、history和memory统一指向被选择者；
7. 记录未执行A与被拒绝B；
8. 保持evaluator位置和native step逻辑不变。

## 11.3 `protocol.py`

原则上不改变行为协议，只需：

- 将official canonical action序列化和签名工具公开为稳定helper；
- 为A8/R9动作签名增加golden tests；
- 保证A/B均使用同一个正式parser；
- 不增加第二套production JSON schema。

Official协议已经定义Thought/Action/tool-call结构、坐标范围和canonical转换，应直接复用。

## 11.4 `working_memory.py`与R2模块

- 不改变R2存储字段；
- 不改变TTL；
- 不改变容量；
- 不改变当前截图权威性；
- 不把event或critic文本永久写入R2；
- B被执行时，只按现有R2规则处理B的memory前缀；
- B被拒绝时，不写入B。

现有working memory是有界、非模型化且不包含隐藏/evaluator数据，应保持该边界。

## 11.5 推理client

需要支持：

- 调用标签：`BASE_EXECUTOR`与`TCRA_AUX`；
- 辅助调用`max_output_tokens=256`；
- 辅助调用禁用模型级自动retry；
- 单独记录input/output tokens、GPU time与wall time；
- 附加的图片必须与A调用的当前截图字节完全一致；
- 仍然只传一张当前图片。

## 11.6 最高风险点

1. **A/B commit错配**  
   执行B却把A写入history或memory，会直接使实验无效。

2. **重复消费R2 read ticket**  
   A已触发一次R2 read；B应读取同一冻结文本副本，但不得把它记成第二次R2 memory read。应单独记录`aux_ledger_exposure`。

3. **隐藏字段泄漏**  
   Controller原始snapshot含activity/package/UI等字段，不能整体传入新组件。

4. **辅助调用改变截图时序**  
   app可能在额外延迟期间自动变化，故必须重新检查截图hash；Shadow arm用于测量纯延迟效应。

5. **parser语义不一致**  
   A与B必须走同一official parser和coordinate mapping。

6. **answer/termination路径被恢复组件劫持**  
   TCRA不得变成完成判断问题族。

7. **成本漏计**  
   即使A最终未执行，它仍是完整模型调用，必须计入总calls/tokens/GPU/wall time。

8. **自动retry隐藏额外算力**  
   所有transport attempts必须显式记录。

---

## 12. 实验arm与因果对照

## 12.1 Arm 0：`R2-BASE-REPLICATE`

- 完全冻结的R2；
- 不包含monitor、auxiliary call或arbiter；
- 用作当前基础设施上的同步无组件基线；
- 不替换历史R2正式6/19结果；
- 新结果只能称为matched prospective R2 replicate；
- 每个有效episode只运行一次。

历史R2仍是主要正向参考；fresh replicate用于检测模型服务、app时序和环境漂移。

## 12.2 Arm 1：`TCRA-R2-FULL`

- 完整E1/E2 trigger；
- specialized counterfactual recovery prompt；
- 一次辅助调用；
- deterministic arbiter；
- 接受时执行B。

这是唯一被推荐的新系统。

## 12.3 Arm 2：`RM-GENERIC-EXTRA-REASONING`

与Full保持：

- 相同trigger；
- 相同packet；
- 相同Qwen；
- 相同当前截图；
- 相同调用次数与token上限；
- 相同call timing；
- 相同parser；
- 相同arbiter；
- 相同native step budget。

唯一改变为generic second-opinion prompt。

该arm回答：

> Full的收益是否只是因为模型多思考了一次，而不是因为显式失败诊断和反事实恢复指导？

## 12.4 Arm 3：`TCRA-SHADOW-NO-BINDING`

- 使用Full的specialized prompt；
- 生成并解析B；
- 运行相同arbiter；
- 记录arbiter本来会选A还是B；
- **真实执行永远是A**；
- 等待辅助调用完成后再执行A，从而匹配额外wall-time延迟；
- 不把B写入R2。

该arm回答：

> 只产生恢复文本、增加一次调用或延迟执行，但不把候选绑定到真实动作时，会发生什么？

## 12.5 核心比较

| 比较 | 解释 |
|---|---|
| `BASE` vs `SHADOW` | 额外调用、延迟和instrumentation本身的影响 |
| `SHADOW` vs `FULL` | 将恢复候选绑定到真实动作的增量影响 |
| `GENERIC` vs `FULL` | 专业反事实恢复指导相对单纯多算一次的影响 |
| 历史R2 vs fresh BASE | 当前基础设施和随机性的复现漂移 |
| 历史R2 vs FULL | 新系统是否达到至少一胜零成功损失 |

---

## 13. Offline replay、preflight与泄漏检查

## 13.1 Zero-generation detector replay

在R2 raw traces上执行：

- E1/E2检测；
- event去重；
- A re-entry gate；
- 剩余预算检查；
- event ledger hash；
- 六成功与十三失败分布。

必须记录：

```text
generation_calls = 0
model_tokens = 0
native_actions = 0
```

## 13.2 Controller shadow replay

在不调用模型、不执行模拟器的条件下，使用历史R2原始A作为基础提案：

- 无event时，selected action必须逐字节等于历史R2动作；
- event但A已偏离时，selected action仍等于历史R2；
- event且A重入时，只创建`would_call_aux=true`；
- 因没有B，不得模拟收益或改写历史动作。

## 13.3 Synthetic arbiter tests

可以使用人工构造的协议样例验证：

- valid divergent B被接受；
- malformed B回退A；
- B重复blocked route被拒绝；
- B为answer/terminate/Home/Menu被拒绝；
- screenshot hash变化后B过期；
- A/B memory commit不会交叉污染。

这些只是软件测试，不是科研任务证据。

## 13.4 泄漏测试

至少包括：

1. 随机改变reward，detector和packet字节不变；
2. 删除evaluator字段，runtime输出不变；
3. 随机改变activity/package，runtime输出不变；
4. 随机替换UI tree，runtime输出不变；
5. 改变task name但保持effective goal相同，runtime输入不变；
6. 在其他episode加入相同screen hash，不得触发跨episode规则；
7. 检索prompt snapshot，确认不存在任务白名单和Expense专用文本；
8. 证明auxiliary screenshot SHA与base当前截图SHA相同；
9. 证明没有future screenshot或未执行动作进入packet。

## 13.5 Source与prompt freeze

首次generation前冻结：

- source tree hash；
- dependency lock；
- model/revision；
- sampling；
- seed；
- task order；
- arm order；
- E1/E2实现；
- prompt全文hash；
- parser版本；
- arbiter规则；
- budgets；
- progress/relapse rubric；
- stop/resume/infra-invalid规则；
- result schema。

任何行为相关修改都需要新系统名和新实验身份，不能继续沿用TCRA-R2结果。

## 13.6 独立审查

至少两名独立审查者分别确认：

- **Evidence reviewer**：实验身份与历史结论没有被改写；
- **Protocol reviewer**：信息边界、controller flow、调用计费和A/B commit正确；
- **Audit reviewer**：M0–M4哈希链、零生成计数和双实现一致性。

---

## 14. 六题保持门、后十三题释放与停止规则

## 14.1 六题固定顺序

所有四个arm首先只运行：

1. `ExpenseDeleteMultiple2`
2. `RetroSavePlaylist`
3. `SimpleCalendarAddOneEvent`
4. `SportsTrackerTotalDurationForCategoryThisWeek`
5. `RecipeDeleteMultipleRecipesWithConstraint`
6. `OsmAndMarker`

六题成功门只判断完整task success，不以reward部分分、read数量、触发次数或动作变化替代。

## 14.2 释放条件

只有以下条件全部成立，才释放后十三题：

1. `R2-BASE-REPLICATE`为6/6；
2. `TCRA-R2-FULL`为6/6；
3. `RM-GENERIC-EXTRA-REASONING`为6/6；
4. `TCRA-SHADOW-NO-BINDING`为6/6；
5. 所有episode均为valid或有唯一、完整链接的infra-invalid replacement；
6. 资源计数、prompt hash及模型receipt完整；
7. 没有泄漏或native budget违规。

这比只要求Full 6/6更严格，但可以避免在控制arm已经破坏R2能力时继续进行难以解释的全suite比较。

## 14.3 Memory/component-silent success

六题中可能没有任何ERE或辅助调用。此类成功：

- 计入系统accuracy；
- 证明默认R2路径被保护；
- 不计作恢复组件有效；
- 不要求为了展示activation而强制触发。

旧Top-3材料中曾希望首题观察productive intervention；本设计明确不沿用该要求，因为稀疏恢复机制在成功任务中保持silent恰恰是安全目标。不能为展示组件而人为制造成功任务介入。

## 14.4 后十三题顺序

释放后，按冻结R2顺序运行其余十三题：

1. `BrowserMultiply`
2. `ExpenseAddMultipleFromGallery`
3. `ExpenseAddMultipleFromMarkor`
4. `MarkorCreateNoteAndSms`
5. `MarkorMergeNotes`
6. `MarkorTranscribeVideo`
7. `OsmAndTrack`
8. `RecipeAddMultipleRecipesFromImage`
9. `RecipeAddMultipleRecipesFromMarkor2`
10. `RecipeAddMultipleRecipesFromMarkor`
11. `SaveCopyOfReceiptTaskEval`
12. `SportsTrackerActivitiesOnDate`
13. `SportsTrackerTotalDistanceForCategoryOverInterval`

## 14.5 Arm与任务调度

- 四个arm必须使用独立、干净的emulator reset；
- 不能在arm间共享memory、history或candidate；
- 任务内arm执行顺序应在首次generation前用提交哈希决定并冻结；
- 建议按任务轮换arm顺序，降低时间漂移；
- 不得根据中途reward改变后续arm顺序；
- 不得看到某个动作后修改prompt或trigger。

## 14.6 停止规则

### 立即停止整个live研究包

- fresh R2 base未通过6/6；
- Shadow未通过6/6，说明额外调用延迟或instrumentation已经污染基础行为；
- Generic未通过6/6，无法形成安全的完整resource-matched comparison；
- Full任一R2成功任务失败；
- 检测到runtime信息泄漏；
- native action budget被增加；
- 任一行为配置在首次generation后被修改。

### 释放十三题后

- 不因“看起来已经不可能达到7/19”提前停止；
- 不因某任务失败重跑；
- 不根据reward选择性省略arm；
- 除基础设施失效外，所有有效episode只运行一次。

## 14.7 Resume规则

允许：

- 从下一个尚未开始的task继续；
- 在唯一infra-invalid attempt后进行一次同task replacement；
- 保留并链接全部旧日志。

禁止：

- 重跑有效失败；
- 选择更好的一次作为正式结果；
- 覆盖旧attempt目录；
- 因模型输出差而声称server invalid；
- 用新prompt恢复原实验身份。

---

## 15. 三类独立判据

## 15.1 Accuracy判据

TCRA-R2-FULL必须同时满足：

\[
\text{successes}\ge 7/19
\]

\[
\text{reward}>6.5
\]

\[
\text{R2 six-task losses}=0
\]

并报告：

- 相对历史R2的win/loss/tie；
- 相对fresh R2 replicate的win/loss/tie；
- 每个task的完整reward；
- 是否存在新成功但部分reward下降；
- 历史R2与fresh replicate差异。

Token下降、episode变短或重复动作减少不能替代accuracy条件。

## 15.2 Resource cost判据

分别报告：

### Base executor资源

- calls；
- input/output/total tokens；
- GPU time；
- wall time；
- native actions。

### Auxiliary资源

- eligible events；
- actual auxiliary calls；
- transport attempts；
- input/output/total tokens；
- GPU time；
- wall time；
- valid/rejected candidates。

### 合计资源

- total calls；
- total tokens；
- total GPU time；
- total wall time；
- native actions；
- 未执行基础提案A数量；
- 被拒绝B数量及理由；
- 每新增一个full success的增量资源。

成本结论必须独立于accuracy：

- Full可以accuracy通过但cost不通过；
- Full可以cost合理但accuracy失败；
- 不得用token减少解释为组件更有效。

## 15.3 Component causality判据

### 15.3.1 Action divergence

介入后第一真实动作满足：

\[
q(B)\neq q(A)
\]

且：

\[
q(B)\notin \text{blocked route entries}
\]

只有arbiter实际选择并执行B才算action divergence。生成一段不同文字、提出一个未执行动作或Shadow中出现B都不算。

### 15.3.2 Route escape

在执行B后最多2个native actions内：

- 当前state不再是anchor；
- 没有重新进入原blocked route；
- 至少出现一个不属于原闭环的可见状态或控制路径。

仅有像素变化、动画或键盘闪动不算goal progress，但可以算route escape。

### 15.3.3 Goal-directed visible progress

由冻结rubric进行post-hoc盲审。审查者只看：

- effective goal；
- 介入前截图；
- B；
- 后续最多2张model-visible截图；
- 可见action/transition。

审查者不得看到：

- arm名称；
- reward；
- evaluator；
-最终task outcome；
- activity/package/UI tree。

以下可以算visible progress：

- 目标对象、条目、字段、选择、创建或删除状态朝目标方向变化；
- 出现完成目标所必需的新可见控制；
- 从错误页面进入与goal明显相关的新页面；
- 明确完成了一个可见必要前置条件。

以下不能单独算：

- 任意新截图；
- 打开又关闭同一菜单；
- toast、动画或时间变化；
- 只是不再重复；
- episode更短；
- 模型在Thought中声称“取得进展”。

由两名独立审查者标注，分歧由第三名裁决。

### 15.3.4 Relapse

在执行B后的4个native actions内，若：

1. 返回相同anchor；
2. 再次执行blocked route entry；
3. 中间没有goal-directed visible progress；

则记为relapse。

若episode在4步内成功结束，记为无relapse；若失败终止但没有完整观察窗口，报告为censored，不得自动记为无relapse。

### 15.3.5 Productive intervention

一次介入只有同时满足以下条件才算productive：

\[
\text{triggered}
\land
\text{B selected}
\land
\text{action divergent}
\land
\text{route escape within 2}
\land
\text{visible progress within 2}
\land
\neg\text{relapse within 4}
\]

### 15.3.6 Decisive intervention

若某个历史R2失败任务在Full中成功，且包含至少一次productive intervention，则可记为decisive intervention候选。因为每episode最多一次辅助调用，因果链比多次恢复更清晰。

仍不得仅凭单episode声称普适因果，但可以作为组件贡献的最强任务级证据。

### 15.3.7 专业机制因果通过门

除accuracy通过外，还必须同时满足：

1. 至少1个新增完整成功任务包含decisive intervention；
2. 全suite至少2次productive intervention；
3. Full完整成功数至少比resource-matched Generic多1；
4. Full的productive intervention数量至少比Generic多1；
5. Full在R2六题中零loss；
6. Shadow中的candidate、文本或“would select B”不获得因果credit；
7. 所有收益不能只来自component-silent成功。

如果Full达到7/19但与Generic持平，则可以说“额外候选计算可能有效”，不能说专业反事实恢复设计获得支持。

---

## 16. 预期收益、主要风险与R2保护

## 16.1 预期收益

### 直接修复“只检测、不改变”

R9的失败链路为：

\[
\text{recurrence detected}
\rightarrow
\text{recovery text injected}
\rightarrow
\text{same route continues}
\]

TCRA-R2将其改为：

\[
\text{recurrence detected}
\rightarrow
\text{base proposal re-entry confirmed}
\rightarrow
\text{counterfactual B generated}
\rightarrow
\text{deterministic selection}
\rightarrow
\text{B actually executed}
\]

### 局部而非全局重写

该机制只解决“已观察到局部方法失败后，下一动作如何变化”，不承担：

- 全任务分解；
- 长程planner；
- completion verifier；
- app navigation policy；
- 坐标校准教程。

### 因果链短

每episode最多一次介入，且先记录A再生成B，可以精确回答：

- 原系统本来会做什么；
- 新组件提出了什么；
- 是否执行；
- 是否产生可见进展；
- 是否复发；
- 最终是否新增成功。

## 16.2 主要失败风险

### 风险1：exact recurrence覆盖不足

许多语义stall可能伴随像素变化，E1/E2无法触发。

**处理**：zero-generation audit达不到4个失败任务覆盖即NO-GO，不增加模糊阈值。

### 风险2：不同动作不等于更好动作

B可能只是随机偏离。

**处理**：要求failed assumption和expected visible evidence；使用Generic control、visible progress及relapse判据。

### 风险3：同一Qwen重复其原有偏差

辅助调用可能继续选择相同区域或控制族。

**处理**：deterministic arbiter拒绝blocked route；不通过时fallback A并记为有效组件失败。

### 风险4：额外延迟改变app状态

即使Shadow不执行B，等待额外调用也可能影响动态界面。

**处理**：Shadow在相同位置等待同一辅助调用；比较Base与Shadow。

### 风险5：B污染R2 memory

执行B却写入A，或B的未验证推断进入verified字段，会破坏后续轨迹。

**处理**：selected-only transactional commit、golden tests和receipt；当前截图仍为权威来源。

### 风险6：观察过的19题导致设计选择偏差

所有任务和seed都已观察。

**处理**：结果只称matched prospective diagnostic；detector在label join前冻结；不声称held-out generalization。

## 16.3 保护R2六成功的具体措施

1. R2是默认路径；
2. 无event时行为逐字节保持R2；
3. R2自行偏离时不调用；
4. 历史六成功要求零call-gated event；
5. 每episode最多一次调用；
6. 不改变R2基础prompt；
7. 不把恢复文本永久注入R2；
8. terminal/answer路径不介入；
9. B无效时fallback A；
10. 六题6/6后才释放十三题；
11. 任何六题valid loss都永久否决当前设计；
12. component-silent success只计作安全保持，不伪造因果故事。

---

## 17. 能够直接否定本设计的结果

以下任一结果足以否定TCRA-R2或其核心机制主张。

## 17.1 实验前否定

1. R2 raw traces无法完整物化或哈希核对；
2. detector依赖task name、app、hidden UI、activity/package或reward；
3. 两个独立零生成实现无法复现相同event ledger；
4. 六成功中出现任何call-gated ERE；
5. 十三失败中少于4题存在call-gated ERE；
6. 覆盖仍集中于少于3个任务族；
7. 必须根据success标签修改窗口、route或阈值才能通过；
8. A1-R9动作签名原语无法安全抽取。

这些结果意味着当前仓库证据不支持该问题族的安全live验证。

## 17.2 六题门否定

1. fresh R2不能复现6/6；
2. Full任一六题失败；
3. Shadow任一六题失败；
4. Generic任一六题失败；
5. Full通过任务但违反native budget或信息边界。

不得继续十三题来“看看总分是否会补回来”。

## 17.3 完整suite accuracy否定

- Full少于7/19；
- Full reward不大于6.5；
- R2六成功出现任何loss。

## 17.4 专业机制因果否定

即使Full达到7/19，以下情况也否定“专业恢复机制有效”的主张：

- 新成功全部是component silent；
- B被执行但没有goal-directed visible progress；
- 有action divergence但频繁relapse；
- Generic与Full相同或优于Full；
- Full的收益可以由Shadow复制；
- 新成功没有任何decisive intervention；
- 只有一个Expense案例发生productive intervention；
- 组件收益依赖未申报的重试、额外token或额外native steps。

此时最多能说：

> 在该matched prospective suite上，多一次模型计算或随机轨迹变化与更高结果同时出现。

不能说TCRA的失败诊断或反事实恢复得到支持。

## 17.5 成本否定

即使accuracy提高，若出现以下情况，也应判定cost目标失败：

- 辅助调用超过每episode一次；
- 输出超过256 tokens；
- 单次上下文超过8192 tokens；
- native action budget增加；
- transport retries未报告；
- 总GPU/wall time无法分离；
- 通过大量未执行提案换取一个偶然成功而没有成本披露。

Accuracy通过与cost通过必须分别记录。

---

## 18. 分阶段实施路线图

## Phase 0：证据闭包

1. 从本地物化R2完整raw tree；
2. 验证正式19题与invalid replacement lineage；
3. 生成M0 raw manifest；
4. 独立审查episode/hash对应关系；
5. 不运行任何模型。

**出口条件**：原始证据完整、可复现、不可变。

## Phase 1：零生成跨任务audit

1. 生成`PolicyTraceView`；
2. 冻结E1/E2 detector；
3. 运行两个独立实现；
4. 生成M1–M3；
5. 再join六成功/十三失败标签生成M4；
6. 应用第2.9节通过门。

**出口条件**：Audit GO，否则设计NO-GO。

## Phase 2：纯软件实现

1. 实现monitor、packet与arbiter；
2. 从controller拆分propose/execute/commit；
3. 添加selected-only commit；
4. 添加cost与receipt字段；
5. 完成synthetic、property和golden tests；
6. 不运行GPU。

**出口条件**：所有行为路径可由单元测试证明。

## Phase 3：Offline controller preflight

1. 在历史R2 response上进行shadow replay；
2. 验证无event路径逐字节保持R2；
3. 验证A/B commit；
4. 运行hidden-field perturbation；
5. 验证current screenshot单图约束；
6. 冻结source与prompt hash；
7. 独立protocol review。

**出口条件**：`generation_calls=0`且全部preflight通过。

## Phase 4：六题live保持门

1. 按冻结arm/task order运行四个arm；
2. 只运行六个R2成功任务；
3. 严格执行valid/infra-invalid规则；
4. 不允许行为修补；
5. 四个arm全部6/6后才释放。

**出口条件**：安全、复现与控制门同时通过。

## Phase 5：后十三题完整实验

1. 按冻结顺序运行所有合格arm；
2. 不根据中间reward停止；
3. 不重跑有效失败；
4. 记录所有cost与receipts；
5. 完成19题后再统一解封结果。

**出口条件**：所有arm形成完整、可比较的matched prospective结果。

## Phase 6：零生成结果终结

1. 计算accuracy与reward；
2. 独立统计resource cost；
3. 对介入片段进行盲法visible progress标注；
4. 计算divergence、route escape、relapse、productive和decisive intervention；
5. 对比Base、Shadow、Generic与Full；
6. 生成唯一正式结果报告；
7. 不重新解释历史A-series结果。

---

## 19. 实现前必须冻结的关键决策清单

### 证据与环境

- [ ] 证据边界`b5635939...`
- [ ] 设计源提交与实现新commit
- [ ] raw trace manifest与M0–M4
- [ ] 19题episode IDs及invalid replacement映射
- [ ] model名称、revision与服务端配置
- [ ] sampling、seed与request配置
- [ ] AndroidWorld版本、任务、seed、evaluator
- [ ] native action-step budgets

### Trigger

- [ ] A8 exact state hash实现
- [ ] official exact action key
- [ ] A1-R9 route-action key
- [ ] 12-action窗口
- [ ] E1两份支持定义
- [ ] E2路线长度2–6及RLE定义
- [ ] base-proposal re-entry gate
- [ ] 剩余动作至少6
- [ ] 每episode最多一次调用
- [ ] P3只审计、不触发

### Auxiliary proposer

- [ ] specialized system prompt全文
- [ ] generic control prompt全文
- [ ] user packet模板
- [ ] prompt hashes
- [ ] 当前截图单图限制
- [ ] 最近轨迹最多8条
- [ ] output 256-token cap
- [ ] total 8192-token cap
- [ ] 60秒wall cap
- [ ] no model-level retry

### Arbiter

- [ ] official parser版本
- [ ] R2 memory-prefix要求
- [ ] terminal/answer/Home/Menu拒绝
- [ ] action divergence定义
- [ ] blocked route拒绝
- [ ] wait约束
- [ ] screenshot hash稳定检查
- [ ] 无效B fallback A
- [ ] selected-only commit

### 实验

- [ ] Base、Full、Generic、Shadow四arm
- [ ] 六题固定顺序
- [ ] 后十三题固定顺序
- [ ] arm轮换顺序及hash
- [ ] 六题四arm全6/6释放条件
- [ ] valid scientific failure定义
- [ ] infra-invalid定义
- [ ] 每任务最多一次replacement
- [ ] resume与停止规则
- [ ] 不允许reward-aware early stop

### 结果判据

- [ ] Full至少7/19
- [ ] reward大于6.5
- [ ] R2六成功零loss
- [ ] action divergence
- [ ] route escape horizon = 2
- [ ] visible progress盲审rubric
- [ ] relapse horizon = 4
- [ ] productive intervention定义
- [ ] decisive intervention定义
- [ ] Full至少2次productive
- [ ] 至少1个新增成功含decisive intervention
- [ ] Full比Generic至少多1个成功
- [ ] accuracy、cost、causality分别裁决

---

## 20. 最终研究裁决

仓库证据**支持继续研究“失败证据如何转化为更好后续决策”这一问题族**，原因是：

- 可见重复检测能够机械激活；
- R9已经证明仅注入恢复提示不足；
- A10-v2、A11、A12诊断进一步表明nonempty read并不自动产生productive divergence；
- R2成功任务大量缺少可归因的memory活动，说明新机制必须默认silent并保护现有路线。

但仓库证据**暂不支持直接授权live TCRA实验**，因为R2完整逐步raw traces尚未在Git中形成可审计的跨任务事件分布。

因此最终结论为：

> **选择TCRA-R2作为唯一值得验证的下一机制，但保持live NO-GO。首先完成零生成、hash-bound的R2完整19题trace audit。只有当冻结的E1/E2检测器在六个成功任务中零误触发、在至少四个失败任务和三个任务族中具有可介入覆盖，并且两套独立实现完全一致时，才进入实现和六题保持门。**

TCRA-R2的研究价值不在于它一定能达到7/19，而在于它首次把以下四件事放进一个最小、可审计、可被active control否定的闭环：

\[
\boxed{
\text{可见失败证据}
\rightarrow
\text{反事实候选}
\rightarrow
\text{真实动作仲裁}
\rightarrow
\text{可见进展与最终成功}
}
\]

若零生成audit、六题保持门、resource-matched Generic或productive-intervention分析中任一关键条件失败，就应明确否定该设计，而不是继续沿着R3–R12式补丁谱系追加状态、prompt或针对单题的恢复规则。