# GPT_PRO_A10_STANDALONE_MEMORY_DESIGN_2026-08-12.md

> **文档状态**：A10 机制设计、实现规范与前瞻性预注册
> **证据冻结分支**：`a2-verified-progress-audit-20260810`
> **证据冻结 Commit**：`ee6df0d11e8e45a903ec291e5a2dbe7fbacb60aa`
> **设计日期**：2026-08-12
> **A10 机制名称**：证据校准的义务—分支前沿记忆
> **英文名称**：Evidence-Calibrated Obligation–Branch Frontier Memory
> **缩写**：ECOBF
> **Mechanism ID**：`a10_evidence_calibrated_obligation_branch_frontier_v1`
> **Experiment ID**：`A10_ECOBF_QWEN3VL32B_AW_HARD_S20260806_V1`
> **结论边界**：本文只提出可实现、可证伪的设计与实验协议，不宣称 A10 已经超过 A0 或 A1。

---

## 1. 审阅范围、版本边界与证据限制

本设计固定审阅仓库 commit `ee6df0d11e8e45a903ec291e5a2dbe7fbacb60aa`。该 commit 的标题为 “Add A7-A9 evidence and four-task diagnostic design handoff”，包含 A7–A9 的证据、实现、测试、配置和新的交接文档；本文不使用该 commit 之后的实现或实验结果。

本次审阅覆盖：

- `HANDOFF_2026-08-11.md`
- `HANDOFF_2026-08-12.md`
- `GPT_PRO_MEMORY_MECHANISM_DESIGN_REQUEST_2026-08-12.md`
- A3–A7 失败取证与继任约束
- A7 透明拼接控制
- A8-v2 离线轨迹审计、设计协议和实现
- A9 zero-generation 证据、预注册和实现
- A8-v2/A9 初次 live gate 结果
- A0/A1 配对参考
- `official_qwen_mobile` 下 A1–A9 相关记忆、controller、protocol、runner、contract、preflight、live receipt 代码
- 相关单元测试和集成测试
- 冻结的 19 个 AndroidWorld Hard 实例清单

需要明确一个证据限制：固定 commit 中的 `A0_A1_PAIRED_REFERENCE_20260810.json` 保存了每个 episode 的哈希、相对路径和外部 `source_roots`，但完整 A0/A1 episode 目录并未作为普通仓库文件提交。因此，本文可以使用已提交的汇总、任务级结果、哈希和仓库取证结论，但不会虚构未包含在 commit 中的 A0/A1 逐步行为细节。A10 的 zero-generation 离线 replay 必须先从这些冻结 source root 物化原始 `episode.json` 与截图，并逐一核对已提交哈希。

---

## 2. 首席设计结论

### 2.1 最终选择

A10 采用一个统一的、controller-authored、确定性的 **义务条件分支前沿**：

\[
F_t=
\left(
O_t,\,
S_t,\,
\{B_{t,j}\},\,
R_t,\,
C_t
\right)
\]

其中：

- \(O_t\)：当前仍未获得可靠局部证据的任务义务；
- \(S_t\)：当前模型可见截图对应的视觉决策状态；
- \(B_{t,j}\)：模型曾从这一状态、针对这一义务阶段尝试过的动作分支；
- \(R_t\)：这些分支是否无进展、产生局部变化、离开页面后返回，或形成了暂时持久的离开；
- \(C_t\)：各条义务证据和分支失败证据的置信度。

A10 不把每一步历史重新发给模型，不要求模型输出新的记忆格式，也不在第一次普通页面重访时立即发言。它只在以下两个条件同时成立时读取：

1. 仍存在未解决的任务义务，或任务完成尚未被任何允许证据支持；
2. 当前轨迹已经出现了“分支收缩”或“完成部分义务后错误离开工作阶段”的早期证据。

### 2.2 一句话因果假设

> **当模型在尚有任务义务未解决的情况下，开始重访同一视觉决策状态、重复已经无进展的动作分支，或在只处理部分目标后离开相关工作页面时，向模型一次性呈现“仍开放的义务 + 已尝试分支的对比结果”，可以在完整循环形成之前诱导一次非强制的策略分化；而在持续获得新义务证据的正常轨迹上保持静默，可以最大限度保留 A0 能力。**

这是一项待实验检验的因果假设，不是性能保证。

---

## 3. 冻结实验事实

### 3.1 A0 与 A1

配对参考固定 task seed `20260806`。A0 为 4/19、reward 4.5；A1 为 5/19、reward 5.5。A1 相对 A0 为 1 个胜出、0 个丢失、18 个平局，但模型调用从 329 增至 603，总 token 从 1,273,361 增至 3,464,267，非空记忆读取达到 580 次。

| 指标 | A0 | A1 |
|---|---:|---:|
| 成功数 | 4/19 | 5/19 |
| Reward sum | 4.5 | 5.5 |
| Executed actions | 316 | 596 |
| Model calls | 329 | 603 |
| Prompt tokens | 1,233,321 | 3,376,888 |
| Completion tokens | 40,040 | 87,379 |
| Total tokens | 1,273,361 | 3,464,267 |
| 有效 episode 时间 | 6,541.82 s | 14,595.49 s |
| Memory writes | 0 | 515 |
| Nonempty reads | 0 | 580 |

A1 的实现保存模型自己生成的 `MEMORY[...]` 原始内容，最多保留六条，读取时按近期顺序重新渲染；模块级 `max_chars` 为 3000。它不根据当前截图状态、当前目标阶段或历史动作结果决定是否读取。

A0 已成功的四个任务固定为：

1. `ExpenseDeleteMultiple2`
2. `RetroSavePlaylist`
3. `SimpleCalendarAddOneEvent`
4. `SportsTrackerTotalDurationForCategoryThisWeek`

这些任务也是所有后续正式实验臂的能力保持门。模型、revision、官方 system prompt 哈希、task seed 和 generation seed 已在仓库 contract 中冻结。

### 3.2 A2–A9 的关键结果

| 实验臂 | 结果 | 对 A10 最重要的结论 |
|---|---:|---|
| A2 | 0/19 | 结构化“进度”仍是模型自述；格式负担、陈旧状态和持续注入严重干扰策略 |
| A3 | 首题 0；12/34 写入、33/34 非空读 | 机制激活很高，但没有形成退出错误状态的有效链条 |
| A4 | 首题 0；同一 donor 34 步持续注入 | 工作流与当前操作方向、对象和页面不匹配 |
| A5 | 首题 0；0/34 合规图写入 | 依赖额外模型格式导致机制没有真正形成 |
| A6 | 0/19；625 actions；2,674,422 tokens | 高频 transition replay 与已有历史重复，并放大错误局部策略 |
| A7 | 透明拼接 4/19，reward 4.0 | 仅有目标条目状态不足以决定下一步；若 ledger 不激活也可能成功 |
| A8-v2 | 初次门控 0/1；14 次非空读 | 发现失败和页面返回并不自动产生策略转换 |
| A9 | 初次门控 1/2；Expense 静默成功，Retro 三次 canary 后失败 | 稀疏有助于能力保持，但仅报告 recurrence 往往介入太晚、信息太弱 |

A3–A7 的仓库取证明确指出，这些机制通常没有闭合：

\[
\text{write}
\rightarrow
\text{relevant retrieval}
\rightarrow
\text{leave repeated action/state}
\rightarrow
\text{task success}
\]

A6 中有 250 次写入发生在 changed-pixel fraction 小于 0.001 的转移之后；其中 243 个位置随后发生非空读取，131 个位置又重复了相同 canonical action。这说明“记忆被读到”甚至“记忆描述了无变化”都不等于策略发生有效改变。

A7 的 19 题结果是由原始七题和后续声明过的 diagnostics 透明拼接而成，不是一套单次 pristine prospective suite；最终为 4/19、reward 4.0，并且 Calendar 这一项 A0 能力未保持。

A8 离线审计在 A6 的 628 个记录步中发现 274 次 exact revisit、182 次 repeated exact state-action、117 次 repeated state-action no-progress。尽管这说明 A8 的触发对象真实存在，A8-v2 live Expense 仍以 34 步、14 次非空读取和 `max_steps` 失败。

A9 的普通读取严格为空，只在重复文本、stationary exact screen、period-2/3 exact route 时一次性发出 canary。初次门控中，Expense 在记忆完全静默时成功；Retro 出现三次 activation 和三次非空读取后仍在 50 步耗尽。

---

## 4. 现有 controller 对 A10 设计的约束

官方 controller 在每个 step：

1. 获取当前截图；
2. 调用 `memory.read({"before": before, "goal": effective_goal})`；
3. 将读取文本追加到当前 user prompt；
4. 进行一次 `client.generate(...)`；
5. 执行模型选择的 canonical action；
6. 获取执行后截图；
7. 调用 `memory.observe_step(...)`；
8. episode 结束后才调用 evaluator。

因此，记忆不会得到独立模型调用。当前 user prompt 已经包含所有此前 action summary；如果记忆再持续回放近期 action summary，就会与原有历史高度重复。

Controller 的审计 snapshot 同时含有 RGB、UI tree 哈希、前台 activity 等字段。A10 必须在自己的实现中采用白名单提取，只读取：

- `before["pixels"]`
- `after["pixels"]`
- task query
- `canonical_action`
- `action_summary`
- `source_step`

A10 不读取 controller 已计算的 `transition` 字典，而是重新从 `before["pixels"]` 和 `after["pixels"]` 计算像素变化，避免 `activity_changed`、`ui_sha_changed` 等隐藏字段意外进入决策。

Evaluator 只在 episode 循环结束后调用，并标记为对 agent 不可见；A10 也不提供任何接收 evaluator 结果的方法。

---

## 5. A0 和 A1 失败时真正缺少的是什么

### 5.1 缺少的不是“更多历史”

A0 已经把此前全部 action summary 放在 prompt 中。A1 又增加了最多六条近期 model-authored memory。两者仍然可能失败，说明问题不是历史条目数量不足。

真正缺少的是一个可以直接支持当前决策的、状态条件化的对比变量：

> **在当前仍有某项任务义务未解决的前提下，从当前这类视觉页面已经尝试过哪些动作分支？它们分别导致了无变化、局部变化、离开后返回，还是暂时持久离开？**

原始时间序列历史没有显式回答这一问题。模型必须自己从越来越长的文本中重构：

- 哪些旧动作发生在与当前类似的页面；
- 哪些动作针对的是同一个任务对象；
- 哪些是正常的多对象重复；
- 哪些已经无效；
- 哪些页面变化只是往返；
- 哪些目标项仍未获得可靠证据。

A1 的 raw recency memory 也没有对这些记录进行状态绑定、结果合并或置信度校准。

### 5.2 A10 需要补充的四类信息

A10 只保存四类当前策略真正缺少的信息：

1. **未解决义务**：query 中可以确定性抽取的显式对象、数值、时间或约束，哪些仍没有足够局部证据；
2. **决策状态**：当前截图是否与某个旧视觉决策状态相同或保守近似；
3. **已尝试分支**：在同一义务阶段、同一视觉状态上，尝试过哪些动作类型、目标区域或任务对象；
4. **分支结果**：这些尝试是否无变化、只在当前页局部变化、离开后返回，或至少若干步没有返回。

### 5.3 为什么这些信息可以从允许输入中确定性产生

| 信息 | 允许来源 | 确定性产生方式 |
|---|---|---|
| 显式任务义务 | task query | 正则规则抽取 quoted/list/numeric/temporal literals |
| 当前视觉状态 | 模型可见 RGB | exact hash + 固定下采样视觉描述符 |
| 动作分支 | executed canonical action | 固定坐标网格、方向、文本哈希、动作类型 |
| 动作针对的对象 | policy action summary + query anchors | 精确字符串匹配，不做自由语义推断 |
| 无变化 | before/after RGB | 像素完全相同或变化比例不超过阈值 |
| 页面往返 | 已观察到的 RGB 序列 | 先离开匹配状态，后在冻结 horizon 内返回 |
| 义务局部证据 | action summary、type_text、RGB 转移 | 固定事件权重和置信度公式 |
| 策略分化 | 后续 canonical action | 与该 frontier 已记录 branch key 比较 |

没有任何一项需要 UI tree、accessibility、app package、evaluator、未来信息或额外模型。

---

## 6. 为什么 A2–A9 没有把“记住”转化为“下一步更好”

### 6.1 A2：存的是模型对进度的声明，而不是分支证据

A2 要求模型输出 `PROGRESS[observed; verified; pending; expected]`，其中 `verified` 仍然只是模型的 screenshot-visible assertion。其独立 guard 只覆盖少数动作类型，且 guard 与记忆是两个因果干预。

A2 的问题是：

- 让模型承担额外结构化输出；
- 只保存一个最近状态；
- 将“模型声称 verified”作为主要进度描述；
- 无法表达多个目标对象在不同页面上的分支尝试；
- 持续的结构化文本改变了原有动作生成分布。

A10 不要求模型输出任何额外字段，也不使用“最近一条进度”作为状态。

### 6.2 A6：回放的是最近历史，不是当前分叉所需信息

A6 始终读取最近两条 action-transition receipt。其内容通常已经存在于官方 action history 中，不能告诉模型“这次需要改变动作类型、目标对象还是页面路线”。A6 频繁写、频繁读，却在 19 题中丢失全部 A0 成功。

A10 将多次相同或近似尝试合并成一个 branch record，并且普通步骤读取为空。

### 6.3 A7：只有“目标条目状态”，没有状态与策略分支

A7 只从 quoted spans 或最后一个冒号后的逗号/分号列表抽取目标项；状态仅为 `pending` 或 `attempted; visible outcome`，并且在发生第一步 action 后持续呈现所有条目。

A7 无法回答：

- 这一条 attempt 是在哪个页面发生的；
- 相同对象是否被重复处理；
- 页面是否离开后又返回；
- 当前应该继续同一动作还是改变分支；
- visible change 是否只是无关动画。

A10 中的义务状态只用于限定一个视觉分支前沿，义务 ledger 不会被独立、持续注入。

### 6.4 A8-v2：能发现失败，但没有形成策略差异轴

A8-v2 按 exact middle-92%-RGB screen 聚合 canonical action family，并报告 no/negligible-change 计数和 closed route。它在 exact revisit 时就读取，没有全 episode one-shot、phase、义务进展或 cooldown。

A8 的提示告诉模型：

- 某动作失败过；
- 某路线返回过。

但没有告诉模型：

- 当前还有哪个 query obligation 没有得到支持；
- 当前重复是否其实是删除另一个对象的正常重复；
- 应该改变的是动作 family 还是 target；
- 这一失败证据是否足够可信；
- 是否已经有另一个分支产生了较好的结果。

因此它可能成为重复的“失败解说器”，而不是决策分叉信息。

### 6.5 A9：过于保守，而且只有 recurrence，没有对比内容

A9 需要相同文本两次、同屏跨三次观察，或者 period-2/3 route 完整重复两轮。它只说 recurrence 已发生，不保留当前义务，也不显示每个 branch 的差异。

A10 比 A9 更早介入：

- 一次完整页面往返且无义务增益即可形成候选；
- 同一 branch 两次 no-progress 即可形成候选；
- 在处理部分对象后离开工作阶段，也可形成候选；
- 不要求完整周期重复两次。

同时，A10 比 A8 更保守：

- 第一次普通重访不读取；
- 有新的义务证据时不读取；
- 同一动作针对不同目标项时不视为失败重复；
- 每 phase 最多两次、每 episode 最多五次；
- 每个 evidence signature 一次性读取。

---

## 7. 被拒绝的设计类别与最终选择理由

| 设计类别 | 拒绝理由 |
|---|---|
| 更长的 raw action history | A6 已表明高频回放会重复官方历史并增加注意力负担 |
| 更严格的 completed/pending ledger | 允许输入无法可靠判断 evaluator-level completion；A7 已证明 ledger 本身不足 |
| 更强 exact loop detector | A8 已能检测大量 exact revisit，但检测不等于策略转换 |
| 更稀疏 recurrence canary | A9 保护能力较好，但可能等到轨迹已经形成完整循环才出现 |
| 跨任务 donor workflow | A4 暴露 operation/object/state mismatch；新机制应 episode-local |
| 额外模型 summarizer/verifier | 明确违反实验约束，并改变因果归因 |
| Action guard/override | 会把提升归因混入安全控制，而不是纯记忆 |

最终选择 ECOBF，不是把 A7、A8、A9 文本简单拼接。它的最小检索单位是：

\[
\boxed{
\text{unresolved obligation}
\land
\text{matching decision state}
\land
\text{collapsed branch evidence}
}
\]

缺少任意一项，该 frontier 均不应被读取。义务、视觉状态和分支结果共同决定一条记录是否存在以及是否可检索，而不是三个旧模块分别输出三段文本。

---

## 8. 输入边界与基本符号

在 step \(t\)：

- \(q\)：task query；
- \(I_t\)：执行动作前、模型可见 RGB；
- \(a_t\)：已经由模型生成并执行的 canonical action；
- \(u_t\)：policy-authored action summary；
- \(I_{t+1}\)：动作执行后、模型可见 RGB；
- \(M_t\)：A10 episode-local memory state。

A10 的状态更新为：

\[
M_{t+1}
=
U(M_t,q,I_t,a_t,u_t,I_{t+1})
\]

读取为：

\[
m_t
=
R(M_t,q,I_t)
\]

其中 \(U\) 和 \(R\) 均为确定性函数。

以下字段明确禁止进入 \(U\) 或 \(R\)：

\[
\{
\text{evaluator reward},
\text{UI tree},
\text{accessibility},
\text{activity},
\text{foreground package},
\text{task database},
\text{future frame}
\}
\]

---

## 9. Query 义务抽取

### 9.1 规范化

对 query 执行：

```text
Unicode NFKC
→ casefold 版本用于匹配
→ 连续空白折叠为一个空格
→ 原始字符串只用于保存允许显示的 literal
```

### 9.2 候选规则

按以下规则产生候选：

1. **Quoted literal**
   双引号、单引号、弯引号或反引号中的 2–64 字符片段。

2. **Colon-list literal**
   最后一个冒号后的内容，若按逗号、分号或换行分割后至少产生两个有效项，则每项为候选。

3. **Marker-list literal**
   在固定 marker
   `following, these, named, called, titled, containing`
   之后，直到句号为止；若能分出至少两个 2–64 字符项，则加入候选。

4. **Numeric/date/time literal**
   金额、数字、日期、时间、区间、距离、时长等固定正则匹配。

5. **Temporal literal**
   `today, tomorrow, yesterday, this week, last week`、星期、月份等固定词表。

### 9.3 去重与容量

每个候选生成：

```text
normalized = NFKC + casefold + 非字母数字折叠
```

相同 normalized 只保留最早一项。

优先级：

```text
quoted = 4
colon-list = 3
marker-list = 3
numeric/date/time = 2
temporal = 2
```

按 `priority desc, source_offset asc` 排序，最多保留 8 项。

若没有抽取出任何义务，不虚构对象；使用一个不渲染为对象名的 sentinel：

```text
OPEN_TASK_COMPLETION_NOT_ESTABLISHED
```

### 9.4 Operation class

仅用于 episode 内的记录匹配和审计，不用于生成计划。

固定类别：

```text
DELETE
CREATE_OR_ADD
TRANSFER
TRANSFORM
QUERY_OR_CALCULATE
NAVIGATE
OTHER
```

固定 lexicon 优先级：

```text
DELETE:
  delete, remove, erase

TRANSFER:
  send, share, sms, export

TRANSFORM:
  merge, transcribe, copy, convert

CREATE_OR_ADD:
  add, create, save, make, mark

QUERY_OR_CALCULATE:
  find, calculate, total, report, list, what

NAVIGATE:
  open, launch, navigate
```

---

## 10. 视觉决策状态抽象

### 10.1 RGB 输入校验

允许：

- `ndim == 3`
- `H >= 25`
- `W >= 8`
- `C >= 3`
- `uint8`，或值域完全在 `[0,255]` 的其他整数 dtype

使用前 3 个通道。浮点、NaN、负值或大于 255 的输入直接抛出 `A10VisibleInputError`，该 episode 属于 infrastructure/controller invalid，而不是科学失败。

### 10.2 Exact fingerprint

裁掉顶部和底部各 4%：

\[
I_t^{crop}
=
I_t[
\lfloor0.04H\rfloor:
\lceil0.96H\rceil
]
\]

对 shape、dtype 和连续 RGB bytes 做 SHA256：

\[
h_t^{exact}
=
\operatorname{SHA256}
(
\text{shape}
\Vert
\text{dtype}
\Vert
I_t^{crop}
)
\]

### 10.3 保守近似描述符

将裁剪图像固定划分为 \(9\times16\) 个 cell。

每个 cell 计算整数 RGB 均值，并计算：

\[
Y=\frac{77R+150G+29B}{256}
\]

量化为：

\[
q_{r,c}
=
\left\lfloor
\frac{Y_{r,c}}{16}
\right\rfloor
\in\{0,\dots,15\}
\]

亮度距离：

\[
D_L(Q,Q')
=
\frac{1}{144\cdot15}
\sum_{r,c}
|q_{r,c}-q'_{r,c}|
\]

边缘 bit：

\[
e^H_{r,c}
=
\mathbf 1[q_{r,c+1}>q_{r,c}]
\]

\[
e^V_{r,c}
=
\mathbf 1[q_{r+1,c}>q_{r,c}]
\]

共 \(135+128=263\) 个 bit。边缘距离：

\[
D_E(E,E')
=
\frac{\operatorname{Hamming}(E,E')}{263}
\]

总距离：

\[
D_V
=
0.7D_L+0.3D_E
\]

### 10.4 Match 与 merge

两个状态满足任一条件即为可检索 match：

1. exact fingerprint 相同；或
2. 同时满足：

\[
D_L\le 0.06,\quad
D_E\le 0.12,\quad
D_V\le 0.055
\]

只有更严格的：

\[
D_V\le0.035
\]

才允许合并到同一个 frontier bucket。

每个 frontier 最多保留 3 个视觉 exemplar。新 exemplar 与全部已有 exemplar 的 \(D_V>0.02\) 时才加入；超过容量后移除最旧 exemplar。

这一设计相对于 A8/A9 的 exact-only 做了保守近似，但不会使用 OCR、UI tree 或 learned embedding。

---

## 11. Canonical action 分支抽象

### 11.1 Intent class

从 action summary 中按固定词表识别第一个匹配类别：

```text
COMMIT:
  delete, remove, add, create, save, send, share,
  submit, confirm, merge, copy, mark

OPEN_OR_SELECT:
  open, launch, navigate, select, choose

INPUT_OR_SEARCH:
  type, enter, fill, search

INSPECT:
  inspect, check, view, read, find, calculate

RECOVER:
  back, return, close, cancel

SCROLL:
  scroll, swipe

WAIT
ANSWER
OTHER
```

Intent class 是模型自述意图，不被视为动作成功证据。

### 11.2 Target anchor mask

若某个 query anchor 的 normalized literal：

- 出现在 action summary 中；或
- 与 `type_text.text` 精确匹配或是其完整 token-bounded 子串，

则该 anchor 的 bit 被加入 `target_anchor_mask`。

这能区分：

- 在相同坐标删除对象 A；
- 列表重排后在相同坐标删除对象 B。

若两次 canonical tap 坐标相同但目标 anchor 不同，则不是同一 branch。

### 11.3 几何 action family

#### Tap / long press

\[
x_{bin}=\min(11,\lfloor12x\rfloor)
\]

\[
y_{bin}=\min(23,\lfloor24y\rfloor)
\]

Family：

```text
(type, x_bin, y_bin)
```

`long_press` 另外保留 duration bucket：

```text
short  : < 700 ms
medium : 700–1500 ms
long   : > 1500 ms
```

#### Swipe

计算：

\[
dx=x_2-x,\quad dy=y_2-y
\]

方向为 dominant axis 上的 `up/down/left/right`。

长度：

\[
l=\sqrt{dx^2+dy^2}
\]

长度 bucket：

```text
short  : l < 0.25
medium : 0.25 <= l < 0.55
long   : l >= 0.55
```

起点划分为 \(3\times4\) 区域。

Family：

```text
("swipe", direction, length_bucket, start_x_bin, start_y_bin)
```

#### Type text

```text
(
  "type_text",
  SHA256(NFKC(text)),
  length_bucket,
  clear_text
)
```

长度 bucket：

```text
1–8
9–32
33–96
97+
```

#### System / wait / answer

```text
press_back
press_home
press_enter
press_recents
wait + duration bucket
answer + text digest
```

### 11.4 最终 branch key

\[
BKey=
\operatorname{Hash}
(
\text{geometric family},
\text{intent class},
\text{target anchor mask}
)
\]

Branch label 只用于渲染和审计，最长 40 字符；最新 intent excerpt 最长 56 字符。

---

## 12. 可见转移与路线结果

### 12.1 像素变化

A10 从 RGB 自行计算：

\[
P_t
=
\frac{1}{HW}
\sum_{i,j}
\mathbf 1
\left[
\max_c
|I_t(i,j,c)-I_{t+1}(i,j,c)|>5
\right]
\]

### 12.2 Immediate outcome

| 条件 | Immediate outcome |
|---|---|
| RGB 完全相同 | `NO_PROGRESS_EXACT` |
| \(P_t\le0.001\) | `NO_PROGRESS_NEGLIGIBLE` |
| \(P_t>0.001\)，且视觉状态仍 match | `LOCAL_VISIBLE_CHANGE` |
| 视觉状态不 match | `DEPARTURE_PENDING` |

`LOCAL_VISIBLE_CHANGE` 只表示截图变化，不表示任务进展。

### 12.3 路线解析

对于 `DEPARTURE_PENDING`：

- 若在接下来的 4 个已执行动作内重新 match 原 source frontier，更新为 `RETURNED`；
- 若 4 个已执行动作内未返回，更新为 `DURABLE_DEPARTURE`；
- 若在第 5–8 个动作内才返回，将原状态修订为 `LATE_RETURN`；
- 超过 8 个动作后不再修改该 receipt。

所有解析只在相应后续 frame 已经真实出现后进行。早期 read 的 audit 不会被重写成“当时已经知道未来”。

### 12.4 分支有效计数与衰减

对当前 step \(s\)，每个 outcome event 的时间衰减：

\[
d(e,s)
=
0.85^{\left\lfloor\frac{s-e.step}{8}\right\rfloor}
\]

定义：

\[
N
=
\sum_{\text{NO\_PROGRESS}}d
\]

\[
R
=
\sum_{\text{RETURNED}}1.25d
+
\sum_{\text{LATE\_RETURN}}0.75d
\]

\[
L
=
\sum_{\text{LOCAL\_VISIBLE\_CHANGE}}0.5d
\]

\[
D
=
\sum_{\text{DURABLE\_DEPARTURE}}d
\]

\[
A=N+R+L+D
\]

失败后验：

\[
p_{\text{bad}}
=
\frac{1+N+R}
{2+N+R+L+D}
\]

支持强度：

\[
s_{\text{evidence}}
=
1-e^{-0.7A}
\]

失败置信度：

\[
C_{\text{bad}}
=
p_{\text{bad}}
\cdot
s_{\text{evidence}}
\]

逃离置信度：

\[
C_{\text{escape}}
=
\frac{1+D}
{2+N+R+L+D}
\cdot
s_{\text{evidence}}
\]

一个 branch 只有同时满足以下条件才被称为 `trusted_bad_branch`：

\[
C_{\text{bad}}\ge0.55
\]

并且至少满足：

- raw no-progress count \(\ge2\)；
- raw return count \(\ge2\)；
- no-progress 和 return 各至少一次。

单次失败不会被渲染成“已证明错误”。

---

## 13. 义务置信度与状态修订

### 13.1 Anchor evidence event

每个 anchor 最多保存 6 个 evidence event。

正证据权重：

| Event | 权重 |
|---|---:|
| `ACTION_MENTION`：summary 精确提到 anchor | +0.20 |
| `TYPE_EXACT`：canonical type_text 精确包含 anchor | +0.25 |
| `COMMIT_INTENT`：anchor 附近 48 字符内出现 commit verb | +0.20 |
| `MATERIAL_VISIBLE_CHANGE`：该 anchor 分支后产生可见变化 | +0.10 |
| `DURABLE_ROUTE_DEPARTURE`：该分支离开 source，4 步内未返回 | +0.15 |
| `INDEPENDENT_SECOND_SUPPORT`：另一 step 的独立支持事件 | +0.15 |

负证据权重：

| Event | 权重 |
|---|---:|
| `NO_PROGRESS_COMMIT`：commit intent 但无变化 | -0.20 |
| `ROUTE_RETURN`：commit 分支离开后 4 步内返回 | -0.25 |
| `REVERSAL_OR_FAILURE_PROSE`：附近出现 cancel/undo/failed/not 等 | -0.45 |
| `LATER_REOPEN_ATTEMPT`：已支持 anchor 后又重新开始处理 | -0.30 |

同一 `(anchor_id, source_step, event_kind)` 只记一次。

### 13.2 Anchor confidence

对证据事件 \(e\)：

- `DURABLE_ROUTE_DEPARTURE` 和 `INDEPENDENT_SECOND_SUPPORT` 的 \(\lambda_e=0.995\)；
- 其他正证据的 \(\lambda_e=0.97\)；
- 负证据的 \(\lambda_e=0.99\)。

\[
C_a(s)
=
\operatorname{clip}
\left(
\sum_e
w_e
\lambda_e^{
\left\lfloor
\frac{s-e.step}{6}
\right\rfloor
},
0,
1
\right)
\]

### 13.3 Anchor status

| 置信度与条件 | 状态 |
|---|---|
| \(C_a<0.35\) | `OPEN` |
| \(0.35\le C_a<0.60\) | `TOUCHED` |
| \(0.60\le C_a<0.80\) | `PROVISIONAL` |
| \(C_a\ge0.80\) 且满足 hard support gate | `LOCALLY_SUPPORTED` |
| 曾为 `LOCALLY_SUPPORTED`，后发生强负证据 | `REOPENED` |

Hard support gate：

1. 至少一个 `ACTION_MENTION` 或 `TYPE_EXACT`；
2. 至少一个 `COMMIT_INTENT`；
3. 并且满足以下之一：
   - 一个 `DURABLE_ROUTE_DEPARTURE`；
   - 两个不同 step 的 material/support event。

### 13.4 不声称 evaluator-level completion

A10 永远不输出：

```text
completed
success
verified by evaluator
task finished
```

`LOCALLY_SUPPORTED` 只表示：

> 根据 query literal、policy action、canonical action 和可见 RGB，某一显式义务已经获得了较强的局部处理证据。

全任务是否完成仍只能由 episode 结束后的 AndroidWorld evaluator 决定。

---

## 14. 任务 phase

### 14.1 Open mask

以下状态均计入 open mask：

```text
OPEN
TOUCHED
PROVISIONAL
REOPENED
```

只有 `LOCALLY_SUPPORTED` 不计入 open mask。

### 14.2 Phase switch

`phase_id` 初始为 0。以下条件触发递增：

1. 任一 anchor 进入或离开 `LOCALLY_SUPPORTED`，导致 open mask 改变；
2. query 没有可抽取 anchor，且一个 `COMMIT` intent 分支同时满足：
   - `MATERIAL_VISIBLE_CHANGE`；
   - 在 4 步内没有返回 source frontier。

Phase switch 后：

- 旧 frontier 保留，但不会与新 phase 合并；
- 当前 phase 的 read cooldown 重置；
- 旧 evidence 仍可审计；
- 新 phase 不继承旧 phase 的 repeat counter；
- 不删除 anchor 的负证据或历史 receipt。

这可避免把“删除对象 A 后又在同一列表位置删除对象 B”误判成同一阶段的失败重复。

---

## 15. 七种轨迹情况的确定性区分

判定优先级按下表从上到下执行。

| 类型 | 确定性定义 | 是否增加 loop pressure |
|---|---|---:|
| **任务阶段切换** | open mask 改变，或无 anchor 任务出现受支持 commit phase | 否，重置本 phase pressure |
| **正常重复** | action family 相同，但 target anchor mask、phase 或 frontier 不同；或前次产生 anchor confidence 增益 \(\ge0.15\) | 否 |
| **必要重试** | 同 branch、同 frontier 仅失败过一次，且存在 wait、clear/re-entry、exact hash 改变、局部变化仍在解析等 retry exemption | 否 |
| **无进展重复** | 同 branch、同 frontier、同 open mask，至少两次 no-progress，且无 retry exemption | 是 |
| **页面往返** | 从 source frontier 离开，并在 4 个已执行动作内返回 | 是，但若 anchor 增益 \(\ge0.15\) 则视为正常 |
| **尚未完成的目标** | anchor 状态为 OPEN/TOUCHED/PROVISIONAL/REOPENED | 作为 open obligation |
| **已可靠处理的目标** | anchor 为 LOCALLY_SUPPORTED | 仅称 locally supported，不称全局完成 |

### 15.1 Retry exemption

以下任一成立时，不将第二次动作直接计为无进展重复：

- action type 为 `wait`，且此前少于 2 次 no-progress wait；
- `type_text` 前出现 `clear_text=True`；
- summary 在最近 2 步出现明确 clear/erase input intent；
- exact hash 已变，而 coarse page 仍 match；
- target anchor mask 已改变；
- 前一次结果仍为 `DEPARTURE_PENDING`；
- 前一次 `LOCAL_VISIBLE_CHANGE` 后任一 open anchor confidence 增加至少 0.10。

---

## 16. A10 memory state schema

### 16.1 顶层状态

| 字段 | 类型 | 容量 | 含义 |
|---|---|---:|---|
| `mechanism_id` | `str` | 常量 | A10 版本标识 |
| `goal_sha256` | `str[64]` | 1 | query 完整哈希 |
| `operation_class` | enum | 1 | 冻结词表得到的操作类别 |
| `anchors` | `list[GoalAnchor]` | 8 | 显式 query 义务 |
| `phase_id` | `int` | \(\le\) step 数 | 当前义务阶段 |
| `frontiers` | ordered map | 16 | 状态条件化分支前沿 |
| `attempt_receipts` | deque | 32 | 最近动作结果证据 |
| `pending_routes` | list | 4 | 等待 return/durable 解析的路线 |
| `escape_watches` | list | 2 | 部分义务后离开工作阶段的监视器 |
| `trigger_candidates` | list | 8 | 尚未读取的候选事件 |
| `delivered_signatures` | deque | 12 | 已读取证据签名 |
| `screen_trace` | deque | 17 | 最近视觉描述符哈希 |
| `read_events` | list | 5 | 已发生的非空读取 |
| `counters` | dict | 常量字段 | 写入、合并、淘汰、触发等统计 |

### 16.2 `GoalAnchor`

| 字段 | 类型 | 上限 |
|---|---|---:|
| `anchor_id` | `str` | 24 chars |
| `literal` | `str` | 64 chars |
| `normalized` | `str` | 64 chars |
| `source_kind` | enum | 1 |
| `source_offset` | `int` | 1 |
| `specificity_weight` | `int` | 1–4 |
| `confidence` | `float` | [0,1] |
| `status` | enum | 1 |
| `last_evidence_step` | `int or None` | 1 |
| `evidence_events` | list | 6 |
| `contradiction_count` | `int` | saturating 255 |

### 16.3 `VisualDescriptor`

| 字段 | 类型 | 上限 |
|---|---|---:|
| `exact_sha256` | `str[64]` | 1 |
| `descriptor_sha256` | `str[64]` | 1 |
| `luma_q` | `tuple[int]` | 144 |
| `edge_bits` | bytes | 33 bytes |
| `crop_shape` | tuple | 3 ints |

### 16.4 `FrontierRecord`

| 字段 | 类型 | 上限 |
|---|---|---:|
| `frontier_id` | `str` | 32 chars |
| `phase_id` | `int` | 1 |
| `open_anchor_mask` | `int` | 8 bits |
| `visual_exemplars` | list | 3 |
| `first_step` | `int` | 1 |
| `last_visit_step` | `int` | 1 |
| `recent_visit_steps` | deque | 8 |
| `visit_count` | `int` | saturating 255 |
| `branches` | ordered map | 5 |
| `return_count` | `int` | saturating 255 |
| `durable_departure_count` | `int` | saturating 255 |
| `anchor_confidence_at_first_visit` | tuple | 8 floats |
| `read_count_in_phase` | `int` | 0–2 |

### 16.5 `BranchRecord`

| 字段 | 类型 | 上限 |
|---|---|---:|
| `branch_id` | `str` | 32 chars |
| `canonical_family` | tuple | 固定长度 |
| `intent_class` | enum | 1 |
| `target_anchor_mask` | `int` | 8 bits |
| `label` | `str` | 40 chars |
| `latest_intent_excerpt` | `str` | 56 chars |
| `first_step` | `int` | 1 |
| `last_step` | `int` | 1 |
| `attempt_count` | `int` | saturating 255 |
| `raw_no_progress_count` | `int` | saturating 255 |
| `raw_local_change_count` | `int` | saturating 255 |
| `raw_return_count` | `int` | saturating 255 |
| `raw_durable_count` | `int` | saturating 255 |
| `failure_confidence` | `float` | [0,1] |
| `escape_confidence` | `float` | [0,1] |
| `canonical_action_sha256s` | deque | 3 |

### 16.6 `AttemptReceipt`

| 字段 | 类型 |
|---|---|
| `attempt_id` | `str` |
| `source_step` | `int` |
| `resolve_step` | `int or None` |
| `frontier_id` | `str` |
| `branch_id` | `str` |
| `source_exact_sha256` | `str` |
| `destination_exact_sha256` | `str` |
| `open_anchor_mask` | `int` |
| `immediate_outcome` | enum |
| `resolved_outcome` | enum |
| `route_length` | `int or None` |
| `touched_anchor_ids` | list，最多 3 |
| `source_response_sha256` | audit-only hash |
| `canonical_action_sha256` | audit-only hash |

### 16.7 `TriggerCandidate`

| 字段 | 类型 |
|---|---|
| `trigger_id` | `str` |
| `kind` | enum |
| `created_step` | `int` |
| `expires_step` | `int` |
| `phase_id` | `int` |
| `open_anchor_mask` | `int` |
| `query_frontier_id` | `str` |
| `expected_current_descriptor` | descriptor hash/exemplar |
| `evidence_strength` | `float` |
| `route_return_strength` | `float` |
| `anchor_gain` | `float` |
| `evidence_signature` | `str[64]` |
| `evidence_payload` | bounded struct，不保存渲染全文 |

---

## 17. 写入、合并、修订、衰减与淘汰

### 17.1 写入条件

`observe_step(...)` 每步都会被调用，但只有以下任一发生时 `written=True`：

- 创建新 frontier；
- 新增视觉 exemplar；
- 创建新 branch；
- branch outcome 计数发生变化；
- 新增或修订 anchor evidence；
- pending route 被解析为 return/durable/late return；
- phase switch；
- 创建 trigger candidate；
- merge 或 eviction 发生。

没有新证据的重复 bookkeeping 返回 `written=False`。

### 17.2 Frontier 合并

只有同时满足以下条件才合并：

1. `phase_id` 相同；
2. `open_anchor_mask` 完全相同；
3. exact hash 相同，或 \(D_V\le0.035\)。

若多个 frontier 都可合并，依次选择：

1. 最小 \(D_V\)；
2. 最近访问者；
3. `frontier_id` 字典序最小者。

### 17.3 Branch 合并

仅当以下三者完全相同：

```text
canonical_family
intent_class
target_anchor_mask
```

才合并计数。

### 17.4 Anchor event 淘汰

每个 anchor 超过 6 个 event 时，按以下顺序淘汰：

1. 计算当前 step 下每个 event 的绝对衰减贡献；
2. 优先保留最新负证据；
3. 其余淘汰绝对贡献最小者；
4. 相同贡献时淘汰最旧；
5. 再以 `event_kind` 字典序打破平局。

### 17.5 Branch 淘汰

一个 frontier 超过 5 个 branch 时，计算：

\[
U_b
=
2C_{\text{bad}}
+
C_{\text{escape}}
+
0.5\cdot\mathbf1[
\text{target mask intersects current open mask}
]
+
e^{-(s-last\_step)/8}
\]

淘汰最小 \(U_b\)；平局时淘汰最旧，再按 `branch_id`。

### 17.6 Frontier 淘汰

超过 16 个 frontier 时：

\[
U_f
=
3A_f
+
1.5J_f
+
1.5E_f
+
T_f
+
e^{-(s-last\_visit)/12}
\]

其中：

- \(A_f=1\)：它是当前匹配 frontier，否则 0；
- \(J_f\)：与当前 open mask 的 weighted Jaccard；
- \(E_f=\min(1,(N+R+L+D)/3)\)；
- \(T_f=1\)：存在未读取 trigger，否则 0。

淘汰最小 \(U_f\)；平局时淘汰最旧，再按 `frontier_id`。

### 17.7 Trigger 淘汰

Trigger candidate 最多 8 个。

初步保留分：

\[
U_t
=
\text{evidence strength}
+
\text{unresolved ratio}
+
e^{-(s-created)/8}
+
b_{\text{kind}}
\]

其中：

```text
PARTIAL_OBLIGATION_ESCAPE = 0.25
CLOSED_ROUTE_WITHOUT_ADVANCE = 0.20
BAD_BRANCH_REPEAT = 0.15
VALUE_REENTRY_AFTER_BAD_OUTCOME = 0.10
FRONTIER_COLLAPSE = 0.05
```

超过容量时淘汰最低分；平局时淘汰最旧。

所有 trigger 最长存活 8 步；`PARTIAL_OBLIGATION_ESCAPE` 最长存活 6 步。

---

## 18. 五种读取触发器

### T0：`PARTIAL_OBLIGATION_ESCAPE`

目的是保留 A1 中“仍有对象待处理”的潜在收益，但不在每次正常删除后持续提示。

触发条件：

1. 至少有 2 个 query anchors；
2. 最近 4 步内，一个 commit branch 使某 anchor confidence 增加至少 0.20；
3. 仍有至少一个其他 unresolved anchor；
4. 创建 `escape_watch` 后，连续两个已观察 destination screen 均不再 match commit source frontier；
5. 这两个 step 中，其他 open anchor 的最大 confidence gain 小于 0.10；
6. 没有相同 evidence signature 已经读取。

若模型在原列表继续处理下一个对象，或者新的对象立即获得 evidence，watch 取消，不读取。

### T1：`BAD_BRANCH_REPEAT`

触发条件：

- 当前 state match 某 frontier；
- phase/open mask 相同；
- 某 branch 满足：

\[
N\ge1.8
\]

或：

\[
N\ge0.9\land R\ge0.9
\]

- 自该 frontier 第一次相关尝试以来，任一 open anchor 最大增益小于 0.15；
- 不满足 retry exemption。

这通常对应两次 no-progress，而不是一次普通失败。

### T2：`CLOSED_ROUTE_WITHOUT_ADVANCE`

触发条件：

1. 从某 frontier 发生真实视觉 departure；
2. 在 4 个动作内返回该 frontier；
3. 路线期间 open anchor 最大 confidence gain 小于 0.15；
4. phase/open mask 未变化；
5. 当前 screen 与返回 frontier match。

一次完整无进展往返即可触发，不要求同一周期重复两轮，因此早于 A9。

### T3：`FRONTIER_COLLAPSE`

触发条件：

- 同一 frontier 在最近 7 步中至少出现 3 次；
- 至少有 2 个已解析 attempt；
- 没有可信的 durable branch escape；
- open anchor 最大 gain 小于 0.15；
- 未满足 T1 或 T2。

这是 T1/T2 未覆盖时的低优先级候选。

### T4：`VALUE_REENTRY_AFTER_BAD_OUTCOME`

触发条件：

1. 同一 normalized `type_text` 在 12 步内第二次出现；
2. 第一次输入所关联 attempt 为：
   - `NO_PROGRESS_*`；
   - `RETURNED`；
   - 或输入后的 source frontier 被重新进入且无 anchor gain；
3. 两次处于相同 open mask；
4. 中间没有 clear evidence，或者 clear 后仍回到相同坏 frontier。

与 A9 不同，单纯重复文本但已有可见进展时不触发。

---

## 19. 检索条件与评分公式

### 19.1 Hard eligibility

Trigger candidate 必须同时满足：

- 当前 `phase_id` 与 candidate 相同；
- 当前 `open_anchor_mask` 与 candidate 相同；
- 当前截图与 candidate 预期 frontier/destination match；
- evidence signature 未读取；
- 当前 step 不超过 `expires_step`；
- episode 非空读取数少于 5；
- 本 phase 非空读取数少于 2；
- 距离上次非空读取至少 4 个 executed actions。

### 19.2 评分组成

视觉匹配：

\[
M=
\begin{cases}
1, & exact\\
\max(0,1-D_V/0.055), & near
\end{cases}
\]

Evidence strength \(E\)：

- T0：最近 partial commit 的 anchor confidence；
- T1：最大 branch failure confidence；
- T2：\(\max(0.75,C_{\text{bad}})\)；
- T3：\(\min(1,(visits_{7}-1)/3)\)；
- T4：首次输入坏结果对应的 failure confidence；最低取 0.65。

Unresolved ratio：

\[
O
=
\frac{
\sum_{a\in unresolved}specificity(a)
}{
\sum_{a}specificity(a)
}
\]

无 anchor 时 \(O=1\)。

No-gain：

\[
G=
1-
\min
\left(
1,
\frac{\max anchor\_gain}{0.15}
\right)
\]

Visit pressure：

\[
V=
\min
\left(
1,
\frac{visits_{recent}-1}{2}
\right)
\]

T0 固定 \(V=1\)。

Route return：

\[
R=
\min(1,\text{return count since candidate start})
\]

Freshness：

\[
F=e^{-(s-created\_step)/8}
\]

最终评分：

\[
Score
=
M
\left(
0.30E+
0.20O+
0.20G+
0.15V+
0.10R+
0.05F
\right)
\]

读取阈值：

\[
Score\ge0.68
\]

### 19.3 排序

按以下顺序选择一个 candidate：

1. `Score` 降序；
2. trigger priority：
   - T0
   - T2
   - T1
   - T4
   - T3
3. visual distance 升序；
4. created step 降序；
5. trigger ID 字典序。

每次 `read()` 最多输出一条 memory block。

---

## 20. 完整注入文本模板

### 20.1 固定模板

```text
A10 frontier; past visible evidence only, current screen wins.
Open: {OPEN}. Supported locally: {SUPPORTED}. Evidence: {EVIDENCE}.
Retry only if pixels/open items changed; otherwise reassess a different action family or target. Nothing is blocked or selected.
```

### 20.2 字段预算

| 字段 | 最大字符 |
|---|---:|
| `OPEN` | 56 |
| `SUPPORTED` | 40 |
| `EVIDENCE` | 90 |
| 完整 block | 420 |
| UTF-8 bytes | 720 |

固定 suffix：

```text
Retry only if pixels/open items changed; otherwise reassess a different action family or target. Nothing is blocked or selected.
```

必须完整保留，不可因截断丢失。

### 20.3 Open rendering

最多显示两个 unresolved anchor：

```text
"Bike Repairs", "Public Transit" (+1 more)
```

每个 label 最长 24 字符。

若无可抽取 anchors：

```text
task completion is not established
```

### 20.4 Supported rendering

最多显示一个最近进入 `LOCALLY_SUPPORTED` 的 anchor：

```text
"Tuition Fees"
```

否则：

```text
none
```

### 20.5 Evidence rendering

#### T0

```text
"Tuition Fees" gained local support, but the route left while other items stayed open
```

#### T1

```text
tap lower-middle for "Bike Repairs" had no/negligible screen change 2x
```

#### T2

```text
swipe-up route left this screen and returned in 3 actions without open-item gain
```

#### T3

```text
this decision screen appeared 3x in 7 steps with no durable open-item advance
```

#### T4

```text
the same text was re-entered after its earlier route returned without open-item gain
```

### 20.6 为什么不构成 planner 或 action override

模板没有：

- 生成动作序列；
- 指定坐标；
- 指定必须点击的控件；
- 屏蔽任何 action；
- 声称某个未尝试 action 一定存在；
- 替换模型的 canonical action；
- 强制停止。

“reassess a different action family or target”只是对历史分支缺乏多样性的非强制说明。模型仍可以重试原动作，controller 也会原样执行。

---

## 21. `read(context)` 伪代码

```python
def read(self, context: dict | None = None) -> tuple[str, dict]:
    context = context or {}

    # A10 has exactly one read per model call and no guard/override path.
    current_step = self.read_count
    self.read_count += 1

    goal = str(context.get("goal") or "")
    self._initialize_goal_once(goal)

    before = dict(context.get("before") or {})
    pixels = self._extract_visible_rgb_only(before)
    current_descriptor = describe_visual_state(pixels)

    # Recompute confidence at the current time; no new evidence is introduced.
    self._refresh_anchor_confidences(current_step)
    current_open_mask = self._open_anchor_mask()

    # Remove expired or structurally stale candidates.
    self._expire_candidates(
        step=current_step,
        phase_id=self.phase_id,
        open_mask=current_open_mask,
    )

    empty_reason = None

    if self.nonempty_read_count >= 5:
        empty_reason = "episode_read_cap"
    elif self.last_nonempty_read_step is not None:
        if current_step - self.last_nonempty_read_step < 4:
            empty_reason = "cooldown"

    candidates = []
    if empty_reason is None:
        for candidate in self.trigger_candidates:
            if candidate.phase_id != self.phase_id:
                continue
            if candidate.open_anchor_mask != current_open_mask:
                continue
            if candidate.evidence_signature in self.delivered_signatures:
                continue
            if current_step > candidate.expires_step:
                continue

            visual_distance = candidate_visual_distance(
                candidate,
                current_descriptor,
            )
            if not visual_match(visual_distance):
                continue

            frontier = self.frontiers.get(candidate.query_frontier_id)
            phase_reads = 0 if frontier is None else frontier.read_count_in_phase
            if phase_reads >= 2:
                continue

            score, components = retrieval_score(
                candidate=candidate,
                current_descriptor=current_descriptor,
                current_step=current_step,
                current_open_mask=current_open_mask,
                anchors=self.anchors,
                frontier=frontier,
            )
            if score >= 0.68:
                candidates.append(
                    (score, candidate_priority(candidate.kind),
                     visual_distance, candidate, components)
                )

    if not candidates:
        return "", self._read_audit(
            nonempty=False,
            step=current_step,
            reason=empty_reason or "no_eligible_candidate",
            current_descriptor=current_descriptor,
            candidate_count=0,
        )

    candidates.sort(
        key=lambda x: (
            -x[0],          # score descending
            -x[1],          # priority descending
            x[2],           # visual distance ascending
            -x[3].created_step,
            x[3].trigger_id,
        )
    )

    score, _, distance, selected, components = candidates[0]

    rendered = render_a10_memory(
        candidate=selected,
        anchors=self.anchors,
        max_chars=420,
        max_utf8_bytes=720,
    )
    assert len(rendered) <= 420
    assert len(rendered.encode("utf-8")) <= 720

    self.nonempty_read_count += 1
    self.last_nonempty_read_step = current_step
    self.delivered_signatures.append(selected.evidence_signature)
    self.delivered_signatures = self.delivered_signatures[-12:]

    frontier = self.frontiers.get(selected.query_frontier_id)
    if frontier is not None:
        frontier.read_count_in_phase += 1

    read_event = make_read_event(
        step=current_step,
        candidate=selected,
        score=score,
        score_components=components,
        visual_distance=distance,
        rendered=rendered,
    )
    self.read_events.append(read_event)
    self.read_events = self.read_events[-5:]

    selected.delivered = True

    return rendered, self._read_audit(
        nonempty=True,
        step=current_step,
        reason="selected",
        current_descriptor=current_descriptor,
        candidate_count=len(candidates),
        selected=selected,
        score=score,
        components=components,
        rendered=rendered,
    )
```

---

## 22. `observe_step(...)` 伪代码

```python
def observe_step(self, **kwargs) -> dict:
    self.write_attempt_count += 1

    source_step = int(kwargs["source_step"])
    if source_step != self.last_observed_step + 1:
        raise A10IntegrityError("non-monotonic source_step")

    # Whitelist extraction only.
    before_pixels = self._extract_visible_rgb_only(
        dict(kwargs.get("before") or {})
    )
    after_pixels = self._extract_visible_rgb_only(
        dict(kwargs.get("after") or {})
    )
    action = validate_canonical_action(
        dict(kwargs.get("canonical_action") or {})
    )
    summary = compact_text(
        kwargs.get("action_summary") or "",
        limit=256,
    )

    # Hashes are stored for audit only and never enter score or matching.
    response_sha = str(kwargs.get("source_response_sha256") or "")
    screenshot_sha = str(kwargs.get("source_screenshot_sha256") or "")

    before_desc = describe_visual_state(before_pixels)
    after_desc = describe_visual_state(after_pixels)
    pixel_fraction = changed_pixel_fraction(before_pixels, after_pixels)

    self._refresh_anchor_confidences(source_step)
    open_mask_before = self._open_anchor_mask()

    source_frontier, frontier_created, frontier_merged = (
        self._match_or_create_frontier(
            descriptor=before_desc,
            phase_id=self.phase_id,
            open_anchor_mask=open_mask_before,
            step=source_step,
        )
    )
    source_frontier.register_visit(source_step)

    intent_class = classify_intent(summary, action)
    target_anchor_mask = match_target_anchors(
        summary=summary,
        action=action,
        anchors=self.anchors,
    )
    branch_key = canonicalize_branch(
        action=action,
        intent_class=intent_class,
        target_anchor_mask=target_anchor_mask,
    )
    branch, branch_created = source_frontier.get_or_create_branch(branch_key)

    immediate_outcome = classify_immediate_outcome(
        before_desc=before_desc,
        after_desc=after_desc,
        before_pixels=before_pixels,
        after_pixels=after_pixels,
        changed_fraction=pixel_fraction,
    )

    receipt = AttemptReceipt(
        attempt_id=make_attempt_id(source_step, source_frontier, branch, action),
        source_step=source_step,
        resolve_step=source_step if immediate_outcome != "DEPARTURE_PENDING" else None,
        frontier_id=source_frontier.frontier_id,
        branch_id=branch.branch_id,
        source_exact_sha256=before_desc.exact_sha256,
        destination_exact_sha256=after_desc.exact_sha256,
        open_anchor_mask=open_mask_before,
        immediate_outcome=immediate_outcome,
        resolved_outcome=immediate_outcome,
        route_length=None,
        touched_anchor_ids=anchor_ids_from_mask(target_anchor_mask)[:3],
        source_response_sha256=response_sha,
        canonical_action_sha256=sha256_json(action),
    )

    branch.register_attempt(
        step=source_step,
        action=action,
        intent_excerpt=summary,
        immediate_outcome=immediate_outcome,
    )

    self.attempt_receipts.append(receipt)
    self.attempt_receipts = self.attempt_receipts[-32:]

    if immediate_outcome == "DEPARTURE_PENDING":
        self._append_pending_route(receipt, before_desc)
    else:
        self._update_branch_outcome(branch, immediate_outcome)

    anchor_events = self._derive_anchor_events(
        step=source_step,
        summary=summary,
        action=action,
        target_anchor_mask=target_anchor_mask,
        intent_class=intent_class,
        immediate_outcome=immediate_outcome,
    )
    self._apply_anchor_events(anchor_events)

    route_resolutions = self._resolve_pending_routes(
        current_step=source_step,
        current_descriptor=after_desc,
    )

    for resolution in route_resolutions:
        self._apply_route_resolution_to_branch(resolution)
        self._apply_route_resolution_to_anchors(resolution)

    self._update_escape_watches(
        current_step=source_step,
        after_descriptor=after_desc,
        new_anchor_events=anchor_events,
    )

    old_open_mask = open_mask_before
    self._refresh_anchor_confidences(source_step)
    new_open_mask = self._open_anchor_mask()

    phase_switch = False
    if self._should_switch_phase(
        old_open_mask=old_open_mask,
        new_open_mask=new_open_mask,
        intent_class=intent_class,
        immediate_outcome=immediate_outcome,
        route_resolutions=route_resolutions,
    ):
        self.phase_id += 1
        phase_switch = True

    destination_frontier, _, _ = self._match_or_create_frontier(
        descriptor=after_desc,
        phase_id=self.phase_id,
        open_anchor_mask=new_open_mask,
        step=source_step + 1,
    )
    destination_frontier.register_visit(source_step + 1)

    new_triggers = []

    # T1
    if self._bad_branch_repeat_conditions(
        frontier=source_frontier,
        branch=branch,
        step=source_step,
        open_mask=old_open_mask,
    ):
        new_triggers.append(
            self._make_bad_branch_trigger(source_frontier, branch, source_step)
        )

    # T2
    for resolution in route_resolutions:
        if self._closed_route_without_advance(resolution):
            new_triggers.append(
                self._make_closed_route_trigger(resolution, source_step)
            )

    # T3
    if self._frontier_collapse_conditions(source_frontier, source_step):
        new_triggers.append(
            self._make_frontier_collapse_trigger(source_frontier, source_step)
        )

    # T4
    value_trigger = self._value_reentry_trigger(
        step=source_step,
        action=action,
        receipt=receipt,
        open_mask=old_open_mask,
    )
    if value_trigger is not None:
        new_triggers.append(value_trigger)

    # T0 is generated only by a mature escape watch.
    new_triggers.extend(
        self._mature_partial_obligation_escape_triggers(
            current_step=source_step,
            current_destination=destination_frontier,
        )
    )

    enqueued = []
    for trigger in new_triggers:
        if self._enqueue_trigger_if_novel(trigger):
            enqueued.append(trigger.trigger_id)

    self._refresh_branch_confidences(source_step)
    evictions = self._enforce_all_capacities(source_step)
    self._update_post_read_behavioral_receipts(
        current_step=source_step,
        action_branch=branch,
        after_descriptor=after_desc,
    )

    self.last_observed_step = source_step

    written = any(
        (
            frontier_created,
            frontier_merged,
            branch_created,
            bool(anchor_events),
            bool(route_resolutions),
            phase_switch,
            bool(enqueued),
            bool(evictions),
        )
    )

    if written:
        self.write_success_count += 1

    return {
        "written": written,
        "source_step": source_step,
        "source_frontier_id": source_frontier.frontier_id,
        "destination_frontier_id": destination_frontier.frontier_id,
        "branch_id": branch.branch_id,
        "immediate_outcome": immediate_outcome,
        "anchor_events": [event.audit_record() for event in anchor_events],
        "route_resolutions": [item.audit_record() for item in route_resolutions],
        "phase_switch": phase_switch,
        "phase_id_after": self.phase_id,
        "trigger_ids_enqueued": enqueued,
        "evictions": evictions,
    }
```

---

## 23. `audit_record()` 必须记录的字段

```text
schema
mechanism_id
experiment_id
version
parameters
  max_anchors
  max_anchor_events
  max_frontiers
  max_branches_per_frontier
  max_attempt_receipts
  max_pending_routes
  max_escape_watches
  max_trigger_candidates
  max_nonempty_reads
  max_reads_per_phase
  read_cooldown_steps
  max_chars
  max_utf8_bytes
  visual_thresholds
  confidence_thresholds
  route_horizons

decision_boundary
  allowed_inputs
  ignored_snapshot_fields
  model_calls_added = 0
  evaluator_used_for_decision = false
  hidden_ui_used_for_decision = false
  future_information_used = false
  guard_enabled = false
  action_override_count = 0
  forced_termination_count = 0
  history_summary_method = false

goal
  goal_sha256
  operation_class
  anchor_count
  anchors

phase
  current_phase_id
  phase_switch_count
  phase_switch_events

frontiers
  current_count
  merge_count
  eviction_count
  records

attempts
  retained_count
  raw_outcome_counts
  receipts

routes
  pending_count
  return_count
  late_return_count
  durable_departure_count

triggers
  candidate_count
  created_counts_by_kind
  delivered_counts_by_kind
  expired_count
  duplicate_suppressed_count
  candidates

reads
  read_count
  nonempty_read_count
  last_nonempty_read_step
  delivered_signatures
  read_events

post_read_behavior
  next_branch_novel_count
  same_branch_after_read_count
  escaped_frontier_within_3_count
  returned_within_4_count
  anchor_gain_after_read_count

capacity
  max_observed_frontiers
  max_observed_branches
  max_observed_receipts
  max_observed_rendered_chars
  max_observed_rendered_utf8_bytes
  serialized_audit_bytes
```

### 23.1 每个 `read_event`

```text
read_id
step
trigger_id
trigger_kind
frontier_id
phase_id
open_anchor_mask
score
score_components
visual_distance
evidence_signature
rendered_sha256
rendered_chars
rendered_utf8_bytes
retrieved_anchor_ids
retrieved_branch_ids
next_action_branch_id
next_action_was_novel
escaped_frontier_within_3
returned_within_4
open_anchor_confidence_delta_within_4
```

最后五项可以在后续已观察 step 到达后更新，但不得包含 evaluator reward。Evaluator reward 由 suite 结果聚合器在 episode 结束后单独 join。

---

## 24. 与现有 controller 的集成

### 24.1 新文件

```text
implementation/src/raven_m/official_qwen_mobile/
  a10_obligation_branch_frontier.py
  a10_contract.py

implementation/tests/official_qwen_mobile/
  test_a10_obligation_branch_frontier.py
  test_a10_controller_integration.py
  test_a10_contract.py
  test_a10_offline_replay.py

implementation/configs/
  a10_evidence_calibrated_obligation_branch_frontier_hard_seed20260806.json
```

本文本身作为设计和预注册源文件：

```text
GPT_PRO_A10_STANDALONE_MEMORY_DESIGN_2026-08-12.md
```

### 24.2 Runner

在现有 arm 选择中增加：

```text
--arm a10
```

构造：

```python
memory = EvidenceCalibratedObligationBranchFrontierMemory(
    max_anchors=8,
    max_anchor_events=6,
    max_frontiers=16,
    max_branches_per_frontier=5,
    max_attempt_receipts=32,
    max_pending_routes=4,
    max_escape_watches=2,
    max_trigger_candidates=8,
    max_nonempty_reads=5,
    max_reads_per_phase=2,
    read_cooldown_steps=4,
    max_chars=420,
    max_utf8_bytes=720,
)
```

Controller：

```python
controller = OfficialQwenMobileController(
    client,
    max_steps=native_max_steps,
    max_tokens=32768,
    system_prompt=OFFICIAL_SYSTEM_PROMPT,
    history_policy="official_text_action_summaries_only",
    working_memory=memory,
    cost_guard=None,
    source_document_coverage_gate=None,
    stop_after_markor_source_exit=False,
)
```

### 24.3 不修改 action history

A10 不实现：

```text
history_summary(...)
record_protocol(...)
```

因此 action history 仍保存模型原始 action summary，不加入 A10 自己的前缀或重写文本。现有 controller 会把 memory block 只加到当前 user prompt，而不会自动把 memory block 本身写入后续 history。

### 24.4 Proposed action 与 executed action

每个有效 step 必须满足：

```text
decision.canonical_action == executed_canonical_action
```

A10 不在 action mapping 前后提供任何 filter、guard 或 override API。

---

## 25. 不泄漏 evaluator 或 hidden UI 的证明

### 25.1 代码级白名单

`read()` 只允许执行：

```python
goal = context.get("goal")
pixels = context["before"]["pixels"]
```

即使 `context` 包含：

```text
evaluator_reward
ui_tree
ui_sha256
foreground
activity
package
accessibility_nodes
task_ground_truth
```

也不得读取或分支。

`observe_step()` 只允许：

```text
source_step
action_summary
canonical_action
before["pixels"]
after["pixels"]
source_response_sha256  # audit-only
source_screenshot_sha256 # audit-only
```

A10 完全忽略 controller 传入的 `transition` 字典，并自行计算 RGB 差异。

### 25.2 运行时不变性

对任意相同：

\[
(q,I_t,a_t,u_t,I_{t+1})
\]

若只改变隐藏字段 \(H\)，则必须满足：

\[
U(M,q,I_t,a_t,u_t,I_{t+1},H_1)
=
U(M,q,I_t,a_t,u_t,I_{t+1},H_2)
\]

以及：

\[
R(M,q,I_t,H_1)
=
R(M,q,I_t,H_2)
\]

测试必须比较：

- 返回文本完全相同；
- audit score 完全相同；
- trigger IDs 完全相同；
- 序列化 memory state 完全相同。

现有 A8/A9 测试已经采用“相同 pixels、不同 evaluator/UI metadata”的模式验证 controller-only 边界，A10 应延续并强化这一模式。

### 25.3 无 future information

Route outcome 只有在真实后续截图出现后才更新：

- step \(t+1\) 未返回时，不能在 step \(t\) 的 read 中称为 durable；
- step \(t+4\) 后才能得到 `DURABLE_DEPARTURE`；
- step \(t+6\) 若晚返回，只能从此时起修订为 `LATE_RETURN`；
- 以前已经写入的 read audit 保留当时证据状态。

---

## 26. 有界性证明

### 26.1 记录数量

A10 最多保留：

\[
8\text{ anchors}
\]

\[
8\times6=48\text{ anchor events}
\]

\[
16\text{ frontiers}
\]

\[
16\times3=48\text{ visual exemplars}
\]

\[
16\times5=80\text{ branches}
\]

\[
80\times3=240\text{ canonical action hashes}
\]

\[
32\text{ attempt receipts}
\]

\[
4\text{ pending routes}
\]

\[
2\text{ escape watches}
\]

\[
8\text{ trigger candidates}
\]

\[
12\text{ delivered signatures}
\]

\[
17\text{ screen trace entries}
\]

\[
5\text{ read events}
\]

因此对象数量上界固定，不随 native max steps 线性无限增长。

### 26.2 字符串有界

所有动态字符串均有上限：

- anchor literal：64
- normalized anchor：64
- branch label：40
- intent excerpt：56
- trigger evidence payload：96
- rendered read：420
- rendered UTF-8：720 bytes
- query 本体不保存在 frontier 中，只保留 hash 和 anchors

单元测试必须构造最大容量状态，并断言：

```text
len(json.dumps(audit_record(), ensure_ascii=True).encode("utf-8"))
<= 131072
```

### 26.3 时间复杂度

每次 `read()`：

\[
O(
8\text{ trigger candidates}
+
16\text{ frontiers}
)
\]

每次 `observe_step()`：

\[
O(
16\text{ frontiers}
+
32\text{ receipts}
+
8\text{ anchors}
)
\]

所有项均为固定上界。

---

## 27. 最坏情况下的 prompt 和 token 负担

### 27.1 Character exposure

每次非空读取最多 420 字符，每 episode 最多 5 次：

\[
420\times5=2100
\]

个 memory 字符曝光。

完整 19 题最多：

\[
19\times5\times420=39{,}900
\]

个 memory 字符曝光。

A1 的配对运行发生了 580 次非空读取；A10 的硬上限为整套 95 次，且 A0 四条历史成功轨迹的 preflight 目标是 0 次。

### 27.2 严格 byte/token 上界

每次渲染额外限制为 720 UTF-8 bytes。

对采用 byte fallback 的 tokenizer，保守 token 上界不超过 byte 数，因此：

\[
\le720\text{ tokens/read}
\]

\[
\le3600\text{ tokens/episode}
\]

这是非常宽松的理论上界。

### 27.3 Frozen tokenizer 实测门

Zero-generation preflight 必须使用冻结 Qwen tokenizer 对：

- 19 个真实 query；
- 所有 trigger 模板；
- 最大长度 anchors；
- Unicode 对抗性摘要；

进行 token 计数。

准入要求：

```text
max added tokens per nonempty read <= 192
max added memory tokens per episode <= 960
```

任何一项超限，则在首次 generation 前缩短模板并创建新的设计版本；不得在 live gate 期间改变。

---

## 28. 完整测试矩阵

### 28.1 单元测试

| ID | 测试 | 必须断言 |
|---|---|---|
| U01 | Query normalization | NFKC、casefold、空白折叠确定 |
| U02 | Quoted extraction | quoted literal 顺序、容量、截断正确 |
| U03 | Colon/marker list | 只在至少两项时激活 |
| U04 | Numeric/temporal extraction | 数值、日期、this week 等稳定 |
| U05 | Anchor dedup | normalized 相同只保留一次 |
| U06 | Operation class | 固定词表与优先级正确 |
| U07 | Exact RGB hash | 相同像素产生相同 hash |
| U08 | Near descriptor | 轻微亮度噪声可 match |
| U09 | Layout separation | 平均亮度相近但边缘结构不同不得 match |
| U10 | Crop boundary | 仅状态栏微变不破坏 descriptor |
| U11 | RGB validation | 错误 shape/dtype/value 必须拒绝 |
| U12 | Tap binning | 小坐标 jitter 合并，跨 bin 分离 |
| U13 | Swipe family | 方向、长度、起点 bucket 正确 |
| U14 | Type family | text digest、长度和 clear_text 正确 |
| U15 | Target mask | 同坐标不同 anchor 形成不同 branch |
| U16 | Intent classification | 固定词表、确定性优先级 |
| U17 | Immediate no-progress | exact 和 `P<=0.001` 正确 |
| U18 | Local change | 同 coarse page 的 material change 正确 |
| U19 | Route return | 4 步内返回解析为 RETURNED |
| U20 | Durable departure | 4 步未返回解析为 DURABLE |
| U21 | Late return revision | 5–8 步返回修订，不双计数 |
| U22 | Anchor confidence | 每个正负事件权重与 decay 精确 |
| U23 | Hard support gate | 模型 prose alone 不能进入 LOCALLY_SUPPORTED |
| U24 | Reopen | 后续重新处理导致 REOPENED |
| U25 | Phase switch | open mask 变化只递增一次 |
| U26 | Branch confidence | 给定 N/R/L/D 得到冻结数值 |
| U27 | T0 | 部分义务后真正离开两屏才触发 |
| U28 | T1 | 两次 no-progress 才触发 |
| U29 | T2 | 一次无增益 closed route 即触发 |
| U30 | T3 | 三次 frontier visit 且无进展触发 |
| U31 | T4 | 重复文本必须绑定坏结果 |
| U32 | Retrieval score | 每个 component 和最终 score 精确 |
| U33 | Candidate ranking | score、priority、distance、时间 tie-break 正确 |
| U34 | Renderer | 字符和 byte cap 永不超限 |
| U35 | Completion claim boundary | 文本不出现 evaluator-level completion |

### 28.2 容量与淘汰

| ID | 测试 | 必须断言 |
|---|---|---|
| B01 | 9 anchors | 只保留冻结排序前 8 个 |
| B02 | 7 anchor events | 按贡献、符号和时间淘汰 |
| B03 | 17 frontiers | 只淘汰最低 retention frontier |
| B04 | 6 branches | 只淘汰最低 branch utility |
| B05 | 33 receipts | FIFO 保留最后 32 个 |
| B06 | 5 pending routes | 只保留最高优先级 4 个 |
| B07 | 9 triggers | 按 trigger utility 淘汰 |
| B08 | 6 reads | 第 6 次强制空读取 |
| B09 | Serialized size | 最大状态 audit JSON 不超过 128 KiB |

### 28.3 One-shot、cooldown 与重复触发

| ID | 测试 | 必须断言 |
|---|---|---|
| O01 | Same signature | 同 evidence signature 只读取一次 |
| O02 | Cooldown | 4 个 executed actions 内不再次读取 |
| O03 | Same phase cap | 每 phase 最多 2 次 |
| O04 | Evidence changed | 新 branch/outcome 可形成新 signature |
| O05 | Expiration | 超过 8 步候选不得读取 |
| O06 | Phase change | 旧 phase trigger 自动失效 |

### 28.4 RGB 边界

必须覆盖：

- `(24,W,3)`；
- `(H,7,3)`；
- `(H,W,2)`；
- float RGB；
- NaN；
- negative integer；
- >255 integer；
- RGBA；
- non-contiguous array；
- 全黑、全白；
- 只改变顶部/底部 4%；
- keyboard 出现；
- loading spinner 小区域；
- 全屏亮度变化。

RGBA 只使用前 3 通道；合法 non-contiguous array 转为 contiguous；其他非法输入显式失败。

### 28.5 Evaluator 与 hidden UI 泄漏测试

构造两条输入：

```python
visible_input_A == visible_input_B
hidden_fields_A != hidden_fields_B
```

hidden fields 包括：

```text
evaluator_reward
task_success
ui_tree
ui_elements
ui_sha256
foreground
activity
package_name
accessibility
database_state
```

断言：

```text
read_text_A == read_text_B
read_audit_A == read_audit_B
observe_result_A == observe_result_B
audit_record_A == audit_record_B
```

忽略 audit 中故意记录的 `ignored_key_count`，若实现该字段则只比较决策状态部分。

### 28.6 0 额外模型调用测试

- A10 模块不得 import `VLLMClient`、transformers model、OpenAI client 或网络库；
- monkeypatch 所有 `.generate()` 和 HTTP 方法为立即抛错；
- 执行全部 A10 单元测试和 offline replay；
- 断言无异常且：

```text
audit_record["model_calls_added"] == 0
```

### 28.7 Guard/override 禁用测试

Controller 集成测试必须断言：

```text
controller.cost_guard is None
controller.source_document_coverage_gate is None
memory.audit_record()["guard_enabled"] is False
memory.audit_record()["action_override_count"] == 0
memory.audit_record()["forced_termination_count"] == 0
```

对每个执行 step：

```text
model_canonical_action == executed_canonical_action
```

### 28.8 Prompt 长度测试

对所有 trigger 类型和最大字段：

```text
len(rendered) <= 420
len(rendered.encode("utf-8")) <= 720
```

并使用冻结 tokenizer 验证：

```text
added_tokens <= 192
```

固定 suffix 必须完整保留。

---

## 29. 假阳性、正常重复和必要重试测试

### 29.1 正常多对象删除

合成轨迹：

1. 在列表相同坐标删除 `"A"`；
2. 屏幕发生局部变化；
3. `"A"` confidence 增加；
4. 列表重排；
5. 在相同坐标删除 `"B"`。

断言：

- 两次 branch target mask 不同；
- 不产生 T1；
- 不产生 T3；
- 读取为空。

### 29.2 合法滚动

连续四次 swipe，每次都出现新页面内容：

- 不得产生 no-progress；
- 不得产生 recurrence trigger；
- 到达底部后第一次无变化 swipe 允许一次必要重试；
- 第二次相同 no-progress swipe 才可产生 T1。

### 29.3 Loading / wait

- 第一次和第二次 wait 不触发 T1；
- 第三次相同状态 wait 且没有任何 anchor gain 时可形成 T3；
- 若中间出现 material visible change，则 pressure 清零。

### 29.4 Clear and re-entry

- 输入 `"abc"`；
- 明确 clear；
- 页面变化；
- 再输入 `"abc"` 并进入新状态。

不得触发 T4。

若清除后回到同一坏 frontier，第二次输入仍无变化，则允许触发。

### 29.5 正常页面返回

完成 anchor A 后返回主列表：

- anchor confidence gain \(\ge0.15\)；
- 返回路线视为 normal;
- 不产生 T2。

### 29.6 对抗性视觉 alias

构造两个具有相同全局平均亮度、但一个为左右分割、一个为上下分割的页面。

断言：

- \(D_L\) 可能较小；
- \(D_E\) 超阈值；
- 不 match、不 merge。

---

## 30. Offline trace replay

### 30.1 原始轨迹物化

Zero-generation replay 前必须：

1. 从配对 reference 和 evidence JSON 读取 episode 路径与 SHA256；
2. 从冻结 source roots 复制：
   - `episode.json`
   - before/after PNG
   - aggregate/checkpoint 中引用的必要元数据；
3. 对每个文件验证提交的 SHA256；
4. 生成只读 trace manifest；
5. replay 过程中 `generation_calls=0`。

哈希不匹配、文件缺失或截图不可解析时，preflight 失败；不得用合成轨迹代替正式 replay。

### 30.2 A0 四个成功轨迹静默门

对历史 A0 的四个成功 episode 逐步 replay。

必须满足：

```text
nonempty_read_count == 0
delivered_trigger_count == 0
max_rendered_chars == 0
```

允许内部写入和置信度更新，但不允许 prompt exposure。

这项测试用于检验“良好轨迹上保持静默”，不是把历史成功结果冒充 A10 live success。

### 30.3 A6 失败轨迹激活

对 A6 19 个 episode replay。

在离线标签中存在至少两次 repeated state-action no-progress 的局部循环上，要求：

- A10 在第三次相同 branch 重复之前产生 T1、T2 或 T3；
- 第一次普通 exact/near revisit 不读取；
- 每 episode 非空读取不超过 5；
- 不因 visible change 本身产生 completion claim。

聚合准入标准：

```text
>= 80% qualifying loop segments
have an eligible A10 trigger before the third repeated bad branch
```

该比例仅用于机制资格，不是任务成功预测。

### 30.4 A8-v2 Expense live failure replay

对 A8-v2 的 Expense episode：

- A10 至少产生一个候选；
- 第一次读取不晚于：
  - 第二次同 branch no-progress；或
  - 第一次无 anchor gain 的 closed route；
- 总非空读取不超过 5；
- 不得复现 A8 的 14 次 exposure；
- 输出必须包含 open obligation 或明确说明 task completion 未建立；
- 输出必须包含已尝试 branch 的结果，而不是只说 recurrence。

A8-v2 初次 gate 的冻结结果为 34 actions、34 calls、14 nonempty reads、`max_steps`，因此这一 replay 主要检验 A10 是否比 A8 更早但更稀疏。

### 30.5 A9 Retro live failure replay

要求：

- A10 的首个有资格 trigger 不晚于 A9 首个 canary；
- 若 A10 读取，其证据必须包含 branch outcome 或 open obligation；
- 不允许只有 “route repeated” 的 canary 文本；
- 总读取不超过 5。

### 30.6 A1 新增成功任务 replay

对 `RecipeDeleteMultipleRecipesWithConstraint` 的 A0/A1 原始轨迹：

- 确认 query anchors 能抽取多个显式目标或约束；
- 若 A0 轨迹存在部分处理后离开或重复坏 branch，A10 必须形成 T0/T1/T2 候选；
- 不得根据 A1 最终 reward 直接修改 anchor status；
- A1 reward 只用于事后分析，不进入 replay 决策。

### 30.7 对抗性轨迹组

至少包含：

- exact A-B-A 页面往返；
- near-match A-B-A；
- A-B-C-A 长路线；
- period-2 正常切换但 anchor 持续增益；
- 同坐标不同目标；
- 同文本不同 phase；
- model summary 幻觉“completed”，但 RGB 无变化；
- summary 未提 anchor，但 type_text 精确包含；
- commit summary + screen change + route return；
- 支持 anchor 后重新打开并修改；
- 120 步最大长度、持续创建新状态；
- 反复触发候选以验证容量和 cooldown。

---

## 31. Source freeze

### 31.1 父证据版本

必须记录：

```text
parent_evidence_commit =
ee6df0d11e8e45a903ec291e5a2dbe7fbacb60aa
```

### 31.2 A10 实现版本

A10 实现完成后创建独立 commit：

```text
a10_implementation_commit = <FULL_SHA>
```

正式 preflight 和 live run 均绑定这一 SHA。

### 31.3 Freeze 文件

至少冻结：

```text
GPT_PRO_A10_STANDALONE_MEMORY_DESIGN_2026-08-12.md

implementation/configs/
  androidworld_hard_v2_instances.json
  a10_evidence_calibrated_obligation_branch_frontier_hard_seed20260806.json

implementation/src/raven_m/official_qwen_mobile/
  a10_obligation_branch_frontier.py
  a10_contract.py
  controller.py
  protocol.py
  __init__.py

implementation/scripts/
  run_official_qwen_mobile.py
  run_a678_arm.py
  preflight_a10.py
  qualify_a10_live_server.py

implementation/src/raven_m/models/
  vllm_client.py

implementation/src/raven_m/env/
  androidworld_adapter.py

implementation/src/raven_m/multi_framework_benchmark/
  task_instances.py

implementation/tests/official_qwen_mobile/
  test_a10_obligation_branch_frontier.py
  test_a10_controller_integration.py
  test_a10_contract.py
  test_a10_offline_replay.py
```

每个文件记录 SHA256，并生成整个 source closure 的稳定 JSON hash。

---

## 32. Zero-generation preflight

Preflight 必须满足：

```text
status = pass
generation_calls = 0
```

现有仓库的 A6–A9 preflight 已采用 source freeze、config validation、测试和 `generation_calls=0` 的模式；A10 应独立建立 `preflight_a10.py`，而不是覆盖旧 A678 证据。

### 32.1 Preflight 检查项

1. 当前 git commit 与声明的 A10 implementation commit 相同；
2. 工作区无已跟踪文件修改；
3. source closure hashes 全部匹配；
4. model ID：

```text
Qwen/Qwen3-VL-32B-Instruct
```

5. revision：

```text
0cfaf48183f594c314753d30a4c4974bc75f3ccb
```

6. official prompt SHA256：

```text
9d060af15f62acb31b9fb197649ec001d4096491d7fb102de929316944b3e26d
```

7. task seed `20260806`；
8. generation seed `3407`；
9. sampling：
   - temperature 0.7
   - top-p 0.8
   - top-k 20
   - presence penalty 1.5
   - repetition penalty 1.0
   - max tokens 32768
10. 19-task manifest hash；
11. native max steps 未修改；
12. system prompt 为 exact `OFFICIAL_SYSTEM_PROMPT`；
13. `cost_guard=None`；
14. action override count 固定 0；
15. 所有 A10 测试通过；
16. A0 四条历史成功轨迹 replay 0 nonempty reads；
17. A6/A8/A9 离线激活测试通过；
18. token/character/byte cap 通过；
19. AST/runtime 检查无额外模型或网络调用；
20. `generation_calls=0`。

以上任一失败都不得启动 live model generation。

---

## 33. Live receipt

A10 必须生成新的 live receipt，不能复用 A678/A89 旧 receipt。

Live receipt 绑定：

```text
schema
status = pass
generation_calls = 0
a10_preflight_sha256
a10_source_freeze_sha256
launch_intent_sha256
served_model_id
model_realpath
model_manifest_sha256
process_pid
process_cmdline
host
port = 18000
vllm_version
torch_version
transformers_version
observed_served_model_ids
qualification_timestamp
```

现有 live qualification 代码已经验证：

- preflight 必须 pass 且 generation calls 为 0；
- `/proc/<pid>/cmdline` 与 launch intent 一致；
- served model ID 唯一匹配；
- vLLM、torch、transformers 版本与启动意图一致；
- receipt 绑定 preflight hash。A10 应复用这一审计模式，但输出独立的 A10 receipt。

---

## 34. 正式任务顺序

冻结 manifest 的 19 个任务和 native max steps 为：

| ID | Task | Native max steps |
|---|---|---:|
| H01 | BrowserMultiply | 22 |
| H02 | ExpenseAddMultipleFromGallery | 60 |
| H03 | ExpenseAddMultipleFromMarkor | 60 |
| H04 | ExpenseDeleteMultiple2 | 34 |
| H05 | MarkorCreateNoteAndSms | 18 |
| H06 | MarkorMergeNotes | 78 |
| H07 | MarkorTranscribeVideo | 20 |
| H08 | OsmAndMarker | 20 |
| H09 | OsmAndTrack | 120 |
| H10 | RecipeAddMultipleRecipesFromImage | 60 |
| H11 | RecipeAddMultipleRecipesFromMarkor | 60 |
| H12 | RecipeAddMultipleRecipesFromMarkor2 | 60 |
| H13 | RecipeDeleteMultipleRecipesWithConstraint | 40 |
| H14 | RetroSavePlaylist | 50 |
| H15 | SaveCopyOfReceiptTaskEval | 16 |
| H16 | SimpleCalendarAddOneEvent | 34 |
| H17 | SportsTrackerActivitiesOnDate | 20 |
| H18 | SportsTrackerTotalDistanceForCategoryOverInterval | 22 |
| H19 | SportsTrackerTotalDurationForCategoryThisWeek | 16 |

---

## 35. 四题 4/4 fail-fast 门控

正式 suite 前四个有效 episode 必须依次为：

1. H04 `ExpenseDeleteMultiple2`
2. H14 `RetroSavePlaylist`
3. H16 `SimpleCalendarAddOneEvent`
4. H19 `SportsTrackerTotalDurationForCategoryThisWeek`

每题要求：

```text
evaluator reward == 1.0
```

任一题科学失败：

```text
suite status = stopped_capability_gate_failure
remaining tasks released = false
```

不得继续下一题，也不得重跑该科学失败。

### 35.1 Gate episode 是否计入正式 19 题

为与仓库 frozen runner 的 “four-task A0 preservation gate, then frozen manifest remainder” 一致，四个 gate episode 构成该次正式 19 题 suite 的前四个有效结果；通过后只释放其余 15 题，不重复运行 gate 四题。

因此：

```text
4 gate tasks + 15 remaining tasks = 19 valid tasks
```

若另行再次运行完整 19 题，那是新的 replication suite，不能与主 paired result 拼接。

---

## 36. Gate 通过后的 15 题顺序

按冻结 manifest 顺序排除 H04、H14、H16、H19：

1. H01 `BrowserMultiply`
2. H02 `ExpenseAddMultipleFromGallery`
3. H03 `ExpenseAddMultipleFromMarkor`
4. H05 `MarkorCreateNoteAndSms`
5. H06 `MarkorMergeNotes`
6. H07 `MarkorTranscribeVideo`
7. H08 `OsmAndMarker`
8. H09 `OsmAndTrack`
9. H10 `RecipeAddMultipleRecipesFromImage`
10. H11 `RecipeAddMultipleRecipesFromMarkor`
11. H12 `RecipeAddMultipleRecipesFromMarkor2`
12. H13 `RecipeDeleteMultipleRecipesWithConstraint`
13. H15 `SaveCopyOfReceiptTaskEval`
14. H17 `SportsTrackerActivitiesOnDate`
15. H18 `SportsTrackerTotalDistanceForCategoryOverInterval`

不得根据中间结果调整顺序。

---

## 37. Infrastructure invalid 与 scientific failure

### 37.1 Infrastructure invalid

仅以下情况允许标为 infrastructure invalid：

- vLLM 进程退出或连接中断；
- HTTP transport 没有返回完整响应；
- `transport_attempts != 1`；
- ADB disconnected；
- emulator crash；
- UIAutomator 无法提供有效 state；
- app/task reset 或 initialization 抛异常；
- screenshot 文件损坏或 RGB 不合法；
- evaluator 调用抛异常、返回缺失或非有限值；
- frozen task params/hash 不匹配；
- live receipt、model ID、revision、manifest 或 package version 不匹配；
- controller 在执行模型 action 前出现非模型原因异常；
- artifact 写入在 evaluator 结果形成前不可恢复损坏。

处理：

1. 保留 invalid episode 全部痕迹；
2. 不计入正式成本和 reward；
3. 修复基础设施；
4. 不改变代码、prompt、阈值、容量、seed；
5. 从同一 task 重新开始；
6. 新 episode 记录 `resolves_invalid_episode_id`。

### 37.2 Scientific failure

以下均属于科学失败，不允许重跑：

- evaluator reward 为 0 或不足 1；
- `max_steps`；
- 模型错误 terminate；
- 模型错误 answer；
- official response 格式不合法；
- 模型选择错误 app、对象、字段、动作或路线；
- 模型重复循环；
- memory 误导模型；
- memory 完全不激活；
- memory 激活但未改变行为；
- app 界面正常工作但模型未完成任务；
- 模型自己造成的超长执行。

### 37.3 代码变更

以下任一改变都必须：

- 新 mechanism version；
- 新 experiment ID；
- 新 source freeze；
- 新 preflight；
- 新 live receipt；
- 从 gate 第一题重启。

包括：

```text
代码
阈值
视觉描述符
anchor parser
容量
confidence 权重
trigger 条件
retrieval score
injection template
max chars
cooldown
read cap
```

不得拼接变更前后的 episode。

---

## 38. 正式性能验收

A10 总体通过必须同时满足：

### 38.1 能力保持

```text
gate success = 4/4
```

### 38.2 完整性能

```text
valid tasks = 19/19
success_count >= 6
reward_sum > 5.5
```

### 38.3 纯记忆因果边界

每个 episode：

```text
memory_added_model_calls = 0
guard_enabled = false
action_override_count = 0
forced_termination_count = 0
hidden_ui_used = false
evaluator_used = false
```

### 38.4 机制证据

至少一个成功任务满足：

```text
nonempty_read_count >= 1
```

并且至少存在一条可审计链：

```text
eligible frontier evidence
→ nonempty A10 read
→ next one or two actions use a novel branch
→ no return to the same frontier within 4 actions
→ open-anchor confidence increases or final task succeeds
```

该链只能称为 trace-grounded causal hypothesis，不称为单轨迹因果证明。

### 38.5 非静默要求

若：

```text
suite nonempty_read_count == 0
```

则即使 A10 恰好得到 6/19，也不能通过 A10 机制验收，因为它只是在随机条件下复现了无记忆 controller。

---

## 39. 最终结果统计格式

### 39.1 Suite summary

```json
{
  "schema": "a10_ecobf_result_v1",
  "parent_evidence_commit": "...",
  "a10_implementation_commit": "...",
  "source_freeze_sha256": "...",
  "preflight_sha256": "...",
  "live_receipt_sha256": "...",
  "task_seed": 20260806,
  "generation_seed": 3407,
  "valid_episode_count": 19,
  "invalid_episode_count": 0,
  "gate": {
    "status": "pass",
    "success_count": 4,
    "required": 4
  },
  "summary": {
    "success_count": 0,
    "reward_sum": 0.0,
    "executed_actions": 0,
    "model_calls": 0,
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "total_tokens": 0,
    "elapsed_seconds": 0.0
  },
  "memory": {
    "write_attempt_count": 0,
    "write_success_count": 0,
    "trigger_count": 0,
    "nonempty_read_count": 0,
    "active_success_count": 0,
    "max_reads_per_episode": 0,
    "rendered_chars_total": 0,
    "rendered_tokens_total": 0,
    "model_calls_added": 0,
    "guard_enabled": false,
    "action_override_count": 0
  }
}
```

### 39.2 Per-task

```text
task_id
task_name
task_seed
native_max_steps
episode_id
episode_json_sha256
reward
success
termination_reason
executed_actions
model_calls
transport_attempt_max
prompt_tokens
completion_tokens
total_tokens
elapsed_seconds
memory_active
memory_write_success_count
memory_trigger_count
memory_nonempty_read_count
first_nonempty_read_step
memory_rendered_chars
memory_rendered_tokens
phase_switch_count
frontier_eviction_count
branch_eviction_count
model_calls_added
guard_enabled
action_override_count
```

### 39.3 Pairwise comparison

对 A0 和 A1 分别报告：

```text
wins
losses
ties
success_delta
reward_delta
action_delta
call_delta
prompt_token_delta
total_token_delta
elapsed_delta
```

不得只报告成功率提升而隐藏成本。

由于主比较只有固定单 seed 的 19 个任务，置信区间和 exact McNemar 结果可以作为描述性补充，但不能把它们包装成跨任务分布上的强统计结论。

---

## 40. 因果分析格式

每个非空 read 生成一条分析记录：

```text
task
episode
read_step
trigger_kind
trigger_score
open_obligations_before_read
locally_supported_obligations
matching_frontier
prior_branches
prior_branch_outcomes
exact_injected_text
rendered_sha256
next_action
next_branch_id
next_branch_was_novel
screen_left_frontier_within_3
screen_returned_within_4
anchor_confidence_delta_within_4
episode_reward
final_success
```

### 40.1 正向因果假设

只有满足以下条件才写：

> A10 在 step \(t\) 基于某 matching frontier 的无进展或部分义务逃离证据发出非空读取；模型在接下来两步内选择了此前未在该 frontier 尝试的 branch；轨迹随后在 4 步内没有返回该 frontier，并产生了新的 open-anchor evidence 或最终任务成功。因此，A10 的对比分支信息可能促成了这次策略转换。

### 40.2 不允许的结论

以下表述均禁止：

```text
A10 read caused success.
The memory verified the task.
The alternative action was correct.
The branch was proven impossible.
```

单 episode 不能排除采样随机性。

### 40.3 负向 read 分析

若 read 后：

- 立即重复同一 branch；
- 4 步内回到同一 frontier；
- open anchor 无增益；
- 最终失败；

则记录为：

```text
activation_without_productive_divergence
```

不得将其计为机制成功。

---

## 41. 明确的 falsification criteria

以下任一成立，A10 总体结论为失败。

### 41.1 性能证伪

1. 四题 gate 任一失败；
2. 完整 suite 成功数小于 6；
3. reward sum 不大于 5.5；
4. A10 未严格超过 A1。

### 41.2 因果边界证伪

5. 任一额外模型调用；
6. 任一 guard；
7. 任一 action override；
8. 任一 forced termination；
9. evaluator、UI tree、activity、package 或 accessibility 参与决策；
10. 使用未观察到的未来 frame。

### 41.3 机制证伪

11. 全 suite 始终静默；
12. 没有任何成功 episode 包含非空读取；
13. 有 active success，但 read 后没有 novel branch、frontier escape 或 anchor gain；
14. 所有新增成功都发生在 memory inactive 的 episode；
15. 超过一半非空读取后，模型在两步内仍重复同一坏 branch，并且没有 anchor gain；
16. 所有读取都发生在 native max steps 已消耗 75% 之后，说明“提前干预”假设失败；
17. A0 历史成功 replay 上出现非空读取；
18. live gate 中出现明显正常重复误报并导致能力丢失；
19. prompt、byte、state capacity 任一越界；
20. 通过科学失败重跑、换 seed、改阈值或拼接版本才达到目标。

### 41.4 即使分数提高也可能被证伪

若 A10 得到 6/19，但：

- 六个成功都没有 memory read；
- 或有 read 的成功任务在 read 前已经进入不可逆成功阶段；
- 或 read 后没有策略差异；
- 或 A10 的新增成功来自与 memory 无关的轨迹随机性，而 active episode 均失败；

则可以记录“performance target reached”，但 **ECOBF 的机制因果假设仍被证伪或未得到支持**，整体不能称为成功的记忆机制。

---

## 42. A10 与各实验臂的实质差异

| 对比臂 | 旧机制核心 | A10 的实质区别 |
|---|---|---|
| **A1** | 模型生成 raw `MEMORY[...]`，最多六条，持续回注 | A10 无模型格式、无 system prompt suffix；记录 controller-derived state-conditioned branch evidence；普通 step 为空 |
| **A2** | 一个最新 structured progress state，另有 guard | A10 保存多个 bounded frontier；置信度来自动作、RGB 和路线结果；没有 guard，也不把模型自述当验证 |
| **A6** | 最近两条 transition receipt 每步回放 | A10 不回放 raw timeline；重复动作被合并；仅在义务未解决且分支收缩时读取 |
| **A7** | query item 的 pending/attempted ledger | A10 的义务状态不能单独读取，只是 frontier key；还包含视觉状态、动作 branch、route outcome 和置信度 |
| **A8-v2** | exact-screen action failure counts，exact revisit 即读取 | A10 使用保守 near state、义务 phase、置信度、one-shot、cooldown 和 read cap；第一次普通 revisit 不读取 |
| **A9** | 完整 recurrence 后的一次 canary | A10 在两次坏 branch 或第一次无增益 closed route 时即可介入，并给出 branch 对比与 open obligation，而不只报告 recurrence |

A10 不是容量更大的 A8，也不是 A7 加 A9。它改变了最基本的记忆对象：

```text
旧对象：
  recent event
  latest progress
  goal item
  exact recurrence

A10 对象：
  unresolved-obligation-conditioned decision frontier
```

---

## 43. 如何逐项解决项目要求中的关键问题

### 43.1 模型表现良好时如何保持静默

- 第一次页面访问不读；
- 第一次普通 revisit 不读；
- 单次失败不读；
- 有 anchor gain 时不读；
- phase/open mask 变化时重置 pressure；
- 同坐标不同目标不是同 branch；
- 正常返回主列表但处理了新对象时不读；
- 历史 A0 四条成功轨迹要求 0 nonempty reads；
- 每 phase 最多两次、episode 最多五次。

### 43.2 如何在循环形成前介入

- 两次同 branch no-progress，而不是等待完整周期；
- 一次无义务增益的 closed route，而不是等待 route 重复两遍；
- 部分对象处理后连续离开工作页面，而其他对象仍开放；
- 同文本第二次输入，但必须绑定坏结果。

### 43.3 一条记录如何获得信任

一条注入记录必须同时通过：

1. 视觉 match；
2. phase/open mask match；
3. 至少一个 hard trigger；
4. branch/route/obligation evidence confidence；
5. retrieval score \(\ge0.68\)；
6. signature 未读取；
7. cooldown 和容量检查。

### 43.4 何时修订、降低置信度、合并、衰减或淘汰

- Late return 修订 durable departure；
- route return、no-progress commit、失败 prose 降低 anchor confidence；
- 重新处理 locally supported anchor 将其标为 REOPENED；
- 同 branch 新的 durable outcome 降低 failure confidence；
- evidence 每 6 或 8 步衰减；
- 视觉、phase、open mask、branch key 完全满足时才合并；
- 超容量按冻结 utility 淘汰。

### 43.5 如何促进策略多样性但不成为 planner

A10 只告诉模型：

- 当前仍有什么未解决；
- 哪些 branch 已经得到坏结果；
- 当前页面是否曾离开后返回；
- “different family or target”这一差异轴还没有被探索。

它不告诉模型具体用哪个动作、不生成计划、不阻止重试、不修改 canonical action。

### 43.6 如何避免上下文膨胀

- 不改 system prompt；
- 不要求 MEMORY/PROGRESS/GRAPH prefix；
- 普通读取严格为空；
- 单次 420 字符；
- 最多五次；
- 不写入 action history；
- 不重复所有近期 transition；
- 同 branch 聚合计数而不是保存无限重复条目。

### 43.7 如何避免 A8 只能发现失败

A8 的输出中心是“此前失败”。A10 的输出中心是：

```text
open obligation
+
failed branch contrast
+
permitted strategy-difference axis
```

它告诉模型为什么当前失败与当前任务仍然相关，以及下一次决策至少应该重新审视哪一维，而不选择具体动作。

### 43.8 如何避免 A9 介入太晚

- 第一次无进展 closed route 即可候选；
- 两次坏 branch 即可候选；
- 部分义务后离开工作阶段即可候选；
- 不需要 exact period 重复两轮；
- near-match 允许轻微视觉变化下识别同一决策页面。

---

## 44. 可能引入的新失败模式

| 新失败模式 | 产生原因 | 缓解措施 |
|---|---|---|
| Near-match 错合并不同页面 | 粗视觉描述符碰撞 | edge distance、严格 merge threshold、phase/open mask 条件 |
| Near-match 漏掉动画页面 | 页面变化超过阈值 | exact exemplar + 最多 3 个近似 exemplar |
| Anchor parser 误抽 generic phrase | 固定 query 规则有限 | specificity 排序；义务本身不触发，仍需 branch collapse |
| Anchor parser 未抽到对象 | query 没有显式 literal | branch-only sentinel fallback |
| Action summary 幻觉完成 | model prose 不可信 | prose 权重低；hard support 需要 canonical/RGB/route evidence |
| 同坐标不同对象被合并 | 列表重排 | target anchor mask 进入 branch key |
| 必要重试被误导为换策略 | 网络等待、输入框清除 | retry exemption；至少两次坏证据；模板允许 changed-context retry |
| T0 误认为模型离开未完成任务 | 正常跨页面 workflow | 连续两屏离开、无其他 anchor gain、历史 A0 silent replay |
| 过度追求多样性 | 模型把提示理解为必须换动作 | 明确 “Nothing is blocked or selected” |
| 读取上限过低 | 长任务需要多次救援 | 这是可证伪风险；不得 live 后临时提高 |
| 读取上限过高仍扰动 | 五次提示可能累积 | 每 phase 两次、四步 cooldown、420 字符 |
| Phase 切换过早 | false locally-supported anchor | 0.80 hard support gate、负证据修订 |
| Phase 切换过迟 | action summary 不提目标 | confidence gain 可抑制 trigger，即使未进入 supported |
| Branch bins 过粗 | 多个附近控件合并 | 12×24 tap 网格、intent 和 target mask |
| Branch bins 过细 | 微小 jitter 被拆开 | 网格而非 0.01 精确坐标 |
| 成功提升但机制无关 | 固定 seed 仍可能有随机差异 | active-success 和 post-read divergence 双重要求 |

---

## 45. 预期收益路径，而非保证

A10 被设计为通过三条路径获得潜在收益：

### 45.1 保持 A0 四项能力

目标路径：

```text
competent trajectory
→ ongoing visual/anchor progress
→ no trigger
→ no prompt perturbation
→ preserve A0 behavior
```

Zero-generation replay 要求历史四条成功轨迹完全静默，live gate 再做真正的前瞻性 4/4 验证。

### 45.2 保留 A1 的多对象提醒价值

目标路径：

```text
one item obtains local evidence
→ other explicit items remain open
→ model leaves relevant work stage
→ sparse T0 reminder
→ return to remaining obligation
```

它不持续输出整个 ledger，也不要求模型每步重新生成 pending 字段。

### 45.3 在循环重任务上产生第二个新增成功

目标路径：

```text
same obligation phase
→ same decision frontier
→ two bad attempts or one failed round trip
→ contrastive branch read
→ novel branch
→ durable escape
→ task progress
```

这条路径主要针对 A6/A8 取证中已经确认存在的大量 repeated state-action no-progress 和 closed routes。

要达到预注册目标，A10 最终仍需在真实 19 题上：

```text
至少保住 4 个 A0 成功
+
至少获得 2 个额外成功
```

具体新增任务不能在实验前指定或保证。

---

## 46. 最终执行判定

A10 只有在以下全部成立时才能得到：

```text
A10 OVERALL PASS
```

```text
1. Source freeze pass
2. Zero-generation preflight pass
3. Fresh live receipt pass
4. A0 preservation gate 4/4
5. Full valid suite 19/19
6. Success >= 6/19
7. Reward > 5.5
8. Zero extra calls
9. Zero guard
10. Zero override
11. At least one successful active-memory episode
12. At least one trace-grounded productive divergence hypothesis
13. No capacity, prompt or leakage violation
14. No scientific rerun or version stitching
```

否则根据原因输出：

```text
A10 SCIENTIFIC FAILURE
A10 INFRASTRUCTURE INVALID
A10 PERFORMANCE PASS / MECHANISM EVIDENCE FAIL
A10 PROTOCOL INVALID
```

不得把不同 verdict 合并成含糊的“部分成功”。

---

## 47. 最终设计裁决

在固定 commit 的证据下，继续增加 raw history、结构化模型自述、持续 goal ledger、exact revisit 解说或更晚的 recurrence canary，都没有直接解决最关键的因果缺口：

> 记忆必须把“当前仍未解决的任务义务”与“当前视觉决策状态上已经尝试并失败的策略分支”绑定起来，并只在这一局部策略空间开始收缩时进入 prompt。

因此，A10 选择 **Evidence-Calibrated Obligation–Branch Frontier Memory**。

它的核心不是保存更多，而是只保存和读取一个当前决策真正缺失的对比事实：

```text
What is still open?
What has already been tried here?
What happened to those branches?
Is this repetition still justified by new visible or obligation evidence?
```

A10 不保证达到 6/19。其价值在于：

- 因果假设明确；
- 输入边界严格；
- 读取时机可编码；
- 置信度可复算；
- 状态和文本有硬上限；
- 能够同时解释静默、触发、行为分化和失败；
- 任何提升都必须通过 4/4 gate、完整 19 题、active-success 和 post-read divergence 的联合验收。

这使它成为当前证据约束下，最有希望在不引入 planner、critic、verifier、guard 或额外模型调用的情况下，同时超过 A0 与 A1 的独立记忆机制。
