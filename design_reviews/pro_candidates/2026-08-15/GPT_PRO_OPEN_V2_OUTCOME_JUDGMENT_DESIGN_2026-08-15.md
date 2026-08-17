# GPT_PRO_OPEN_V2_OUTCOME_JUDGMENT_DESIGN_2026-08-15.md

## 文档元数据与研究裁决

| 字段 | 冻结值 |
|---|---|
| 仓库 | `ScottBlizzard/RAVEN-M` |
| 分支 | `a2-verified-progress-audit-20260810` |
| 当前设计资料提交 | `1854fd2b7a5b3ca488b45e27953186ba7c447f96` |
| 冻结科研证据边界 | `b5635939acd628156f8c8e36aa8219834a3e6ad8` |
| 默认正向参考 | A1-R2 Compact Verified + Pending |
| 本轮性质 | 只做设计；不修改仓库；不运行GPU；不生成新实验结果 |
| 唯一推荐系统 | **R2-SCER v1：Selective Claim–Evidence Reconciliation，选择性声明—证据对账** |
| 对初始 VOV 假设的裁决 | **修改并替换原形**：保留稀疏、独立的可见证据判断原语；否定逐动作 verifier、固定三值总判决和 pixel-change 语义化 |
| 当前科学状态 | **允许开展零生成审计与实现规划；禁止进入 live generation** |
| Live NO-GO 原因 | Git 中没有 R2 原始运行树，尚不能独立量化跨任务错误类型、触发覆盖率、六个成功任务反例和 false-reject 风险 |

> **最终唯一建议**
>
> 不采用“每个动作后都让 verifier 输出 `SUPPORTED / UNSUPPORTED / UNCERTAIN`”的 Sparse Visible-Outcome Verifier。  
> 推荐在 **R2 原机制之上**增加一个极稀疏的、发生在“声明边界”而不是“每个动作边界”的 **选择性声明—证据对账机制**：
>
> 1. executor 仍负责观察、动作和终止；
> 2. auxiliary role 只把当前开放声明与已有 `before/after/current RGB` 中的直接可见事实进行对账；
> 3. 它不输出任务成功与否，不推荐动作，不充当 AndroidWorld evaluator；
> 4. 普通动作不被阻断，证据回执只影响下一次 executor request；
> 5. 对带开放义务的成功终止或 answer，最多提供一次重新考虑机会；
> 6. 判断结果以“已由哪些像素事实建立了哪些声明片段、哪些片段仍不可见或互相矛盾”的结构化账目表示，不压缩成一个全局三值 verdict；
> 7. Full 必须与相同模型调用、相同触发器、相同视觉输入和相同预算的 generic visual reasoning active control 比较。

---

# 1. Commit-pinned 证据审计与证据等级

## 1.1 Commit 边界

审计采用两层冻结：

- `b5635939...` 是经验事实和正式实验状态的冻结边界；
- `1854fd2...` 增加的是设计约束、候选组件选择和完整蓝图要求，不能被解释为新增正向实验结果；
- 两个提交之间的差异属于设计资料更新，而不是对 A1、R2、A2、A6 或 A7–A12 历史结果的重写。

因此，本设计只接受以下事实顺序：

1. 正式 live scored result；
2. 行为冻结且 hash-bound 的零生成 replay/preflight；
3. 明确标为 diagnostic 的 post-hoc 分析；
4. 设计文档中的假设；
5. 未物化原始轨迹所涉及的问题保持未知。

## 1.2 本文采用的证据等级

| 等级 | 定义 | 可支持的结论 | 不可支持的结论 |
|---|---|---|---|
| **A：正式 live scored** | 冻结协议下真实运行并由正式 evaluator 评分 | 系统级 accuracy、reward、cost、任务级 win/loss/tie | 某个子组件的独立因果作用，除非有 matched control |
| **A−：正式但可比性受限** | 正式运行有效，但由补跑或拼接构成 | 该系统在已记录任务上的结果 | 与单次完整套件的严格成本或时序比较 |
| **B：零生成 replay / preflight** | 不调用模型生成，复用并验证历史轨迹 | 可实现性、触发暴露、格式覆盖、成本投影、哈希完整性 | 改变动作之后的 accuracy |
| **C：post-hoc diagnostic** | 在正式失败后进行的诊断性读取或重放 | 暴露、读取、动作差异、短窗纠正等诊断事实 | 修复原实验状态或追认正式成功 |
| **D：设计假设** | charter、proposal、prompt 或接口草案 | 可证伪机制和实验计划 | 机制已经有效 |
| **U：未物化事实** | 需要 raw trace，但 Git 中不存在 | 只能声明信息缺口 | 任何基于想象的事件数量或跨任务规律 |

## 1.3 已建立的核心事实

### A1 与 R2

A1 的正式结果为 5/19。它相对 A0 唯一清晰的 paired gain 是 `RecipeDeleteMultipleRecipesWithConstraint`：A1 保持“删除操作仍待确认”，没有过早把操作视为完成；与此同时，A1 出现了 stale pending、同一记忆状态反复刷新以及 memory/history 重复膨胀。

A1-R2 保留 compact `verified + pending`，删除 observation prose 和重复历史前缀，在不增加模型调用数的情况下取得 6/19、reward 6.5，并把总 token 从 A1 的约 3.464M 降到约 2.686M；它相对 A1 是 1 win、0 loss、18 ties。R2 的新增成功是 `OsmAndMarker`。这些事实支持把 R2 作为 preservation parent，但尚未证明“compact memory”是唯一因果来源。

### A2 与 A6

A2 把 model-authored verified-progress memory、可见 transition 描述和 repeated-no-progress guard 组成完整包，正式结果为 0/19，丢失了 A1 的五个成功任务。A2 实现自己也明确区分：所谓 `verified` 仍然是模型声明，不是 controller 或 evaluator 的确认；其 material/minor/no-change 分类只来自像素差异。

A6 在大量步骤中写入 action→visible-transition receipt，但完整结果仍为 0/19。它证明“可以记录像素变化”，没有证明“像素变化构成 semantic progress”，也没有证明高频可见 transition 注入会改善 accuracy。

### A7–A12

A7 的 goal-item ledger 只允许 `pending/attempted`，没有把 ledger 当 completion oracle；其 4/19 是透明拼接结果，可用于表示层分析，但可比性弱于单次完整套件。A10/A11 的正式离线资格门失败，A12 preflight 为 protocol invalid；后续 A10-v2、A11、A12 diagnostic 中出现的读取、动作变化或局部分析均不能修复这些正式状态。诊断中也没有形成可归因的 productive divergence。

## 1.4 当前最重要的证据缺口

R2 scored result 对 19 个有效 episode 的身份和 episode JSON SHA-256 进行了绑定，并保留了一个 infrastructure-invalid attempt 的替换关系；但是完整 raw suite tree 和逐步截图文件不在 Git 中。现有 R2 offline replay 是从 A1 轨迹投影 R2 memory footprint 的可行性重放，不是 R2 自身 19 题的 outcome/completion 事件审计。

因此，以下数量目前均属于 **U 级未知**，不得脑补：

- unsupported continuation 的准确次数；
- 可见证据不足却清除 obligation 的次数；
- repeated ineffective commitment 的语义次数；
- terminal claim 在当时截图上究竟是直接可支持、直接矛盾还是不可判定；
- 六个成功任务中会被新判断组件错误干预的反例；
- 目标触发器的 false-positive 和 false-negative；
- 哪些失败实际上无法仅靠 RGB 判断。

---

# 2. R2 全 19 题 outcome/completion 问题分析

## 2.1 正式聚合结果

R2 的正式汇总为：

- 19 个有效任务；
- 6 个 full success；
- 1 个 0.5 reward；
- reward 总计 6.5；
- 603 次 generation calls；
- 595 个 canonical actions；
- 2,685,730 tokens；
- 11,230.18 秒；
- 436 次 non-empty memory read；
- 205 次成功 memory write；
- 130 次 same-state refresh；
- 389 次 invalid-prefix write attempt。

## 2.2 逐题冻结事实与审计优先级

| # | 任务 | R2 reward / 终止方式 | Calls / Actions | Same-state refresh | 当前可成立的审计结论 |
|---:|---|---|---:|---:|---|
| 1 | `ExpenseDeleteMultiple2` | 1.0 / `model_terminate_success` | 18 / 17 | 5 | 成功保护样本；存在 recurrence-trigger 暴露代理，但不能据此称为无效重复 |
| 2 | `RetroSavePlaylist` | 1.0 / `model_terminate_success` | 25 / 24 | 0 | 成功保护样本；多义务证据能否同时可见须看 raw trace |
| 3 | `SimpleCalendarAddOneEvent` | 1.0 / `model_terminate_success` | 23 / 22 | 1 | 成功保护样本；一次刷新不是错误证据 |
| 4 | `SportsTrackerTotalDurationForCategoryThisWeek` | 1.0 / `model_answer` | 6 / 6 | 1 | 证明 `answer` 不能被统一视为可疑或统一阻断 |
| 5 | `RecipeDeleteMultipleRecipesWithConstraint` | 1.0 / `model_terminate_success` | 18 / 17 | 2 | A1 唯一 paired-gain 内核的保护样本 |
| 6 | `BrowserMultiply` | 0 / `max_steps` | 22 / 22 | 5 | 需审计 unsupported continuation、错误中间结果或纯执行失败；聚合结果无法区分 |
| 7 | `ExpenseAddMultipleFromGallery` | 0 / `model_terminate_success` | 14 / 13 | 2 | evaluator-disconfirmed success termination；是否当时像素可判定仍未知 |
| 8 | `ExpenseAddMultipleFromMarkor` | 0 / `max_steps` | 60 / 60 | 6 | 需审计 dropped obligation 与持续错误路径 |
| 9 | `MarkorCreateNoteAndSms` | 0.5 / `max_steps` | 18 / 18 | 1 | silent partial success 风险；不能用 full-task 二值标签反推每个动作 |
| 10 | `MarkorMergeNotes` | 0 / `max_steps` | 78 / 78 | 27 | 高 recurrence-proxy 暴露；语义上的 ineffective commitment 尚待 raw audit |
| 11 | `MarkorTranscribeVideo` | 0 / `model_answer` | 14 / 14 | 5 | evaluator-disconfirmed answer；不能仅由终止类型判断错误原因 |
| 12 | `OsmAndMarker` | 1.0 / `model_terminate_success` | 12 / 11 | 2 | R2 相对 A1 的新增成功，必须零损失保护 |
| 13 | `OsmAndTrack` | 0 / `max_steps` | 120 / 120 | 67 | 最高 recurrence-proxy 暴露；不能把 67 次刷新等同于 67 次同动作或无进展 |
| 14 | `RecipeAddMultipleRecipesFromImage` | 0 / `max_steps` | 60 / 60 | 1 | 需审计多义务遗漏、视觉读取和提交确认 |
| 15 | `RecipeAddMultipleRecipesFromMarkor` | 0 / `model_terminate_success` | 29 / 28 | 1 | evaluator-disconfirmed success termination |
| 16 | `RecipeAddMultipleRecipesFromMarkor2` | 0 / `max_steps` | 60 / 60 | 1 | 需审计未确认义务和跨页面状态 |
| 17 | `SaveCopyOfReceiptTaskEval` | 0 / `model_terminate_success` | 11 / 10 | 2 | evaluator-disconfirmed success termination |
| 18 | `SportsTrackerActivitiesOnDate` | 0 / `model_answer` | 7 / 7 | 1 | evaluator-disconfirmed answer |
| 19 | `SportsTrackerTotalDistanceForCategoryOverInterval` | 0 / `model_answer` | 8 / 8 | 0 | evaluator-disconfirmed answer；无 refresh 不代表没有错误 completion belief |

上述任务级字段来自 R2 scored artifact；其作用是界定审计对象，而不是替代 raw trace 标注。

## 2.3 现阶段可以报告的跨任务下界

### evaluator-disconfirmed terminal proposals

至少有三个 episode 的 executor 以 `terminate(success)` 结束，但正式 reward 为 0：

1. `ExpenseAddMultipleFromGallery`；
2. `RecipeAddMultipleRecipesFromMarkor`；
3. `SaveCopyOfReceiptTaskEval`。

这证明 R2 中存在“模型成功声明与正式 evaluator 结果不一致”的跨任务现象，但不证明一个只看截图的 judge 在终止时能够识别它们。某些任务可能依赖后台持久化、列表中未显示的对象或 evaluator 特有的完整性条件。

### answer 不是统一的负信号

R2 有四个 `model_answer` episode：

- 1 个成功：`SportsTrackerTotalDurationForCategoryThisWeek`；
- 3 个失败：`MarkorTranscribeVideo`、`SportsTrackerActivitiesOnDate`、`SportsTrackerTotalDistanceForCategoryOverInterval`。

因此，任何“所有 answer 都需要 verifier 批准”或“answer 不能作为终止”的方案都会直接制造已知 preservation 风险。

### same-state refresh 只是触发代理

130 次 same-state refresh 中，`MarkorMergeNotes` 和 `OsmAndTrack` 合计 94 次。它们适合用来寻找“同一开放声明长期未被证据关闭”的候选片段，但它们不是 semantic no-progress 标签：

- 不是同屏幕的充分条件；
- 不是相同动作的充分条件；
- 不是义务未完成的充分条件；
- 成功任务中也有 refresh。

R2 实现中的 refresh 表示 compact memory 状态被相同内容重新提交，不是环境 outcome 的认证。

## 2.4 请求中的七类问题目前分别能知道什么

| 问题类型 | 当前正式证据 | 仍缺少什么 |
|---|---|---|
| Unsupported continuation | A1/A2 报告存在过早前进、错误完成信念；R2 有失败和 stale refresh 代理 | R2 每个事件在当时截图上的直接证据等级 |
| False terminal claim | 至少 3 个 `terminate(success)` 被 evaluator 判 0 | 当时是否直接可见矛盾、不可判定，或其实局部证据充分但全局任务不完整 |
| Unconfirmed obligation | A1 的正向内核是保留未确认删除；R2 仍有 pending/refresh | R2 中义务何时被清除、替换或遗忘 |
| Repeated ineffective commitment | 长失败任务有高 refresh；A2 guard 只捕获极窄的 byte-identical repeat | “语义相同的 commitment”与“合理重试”之间的独立标签 |
| 证据不足却继续 | controller 在下一次 executor 调用前可获得 action 后截图 | executor 是否在下一响应中把效果当成已完成 |
| 截图无法判断 outcome | 协议已明确 pixel transition 不是 progress | 哪些具体事件属于 backend、off-screen、aggregate、transient 或 illegible |
| 成功任务反例 | 六个成功中有 terminate、answer、refresh 和多步骤任务 | 新机制在这些事件上的 false-reject 风险 |

controller 已经保存 action 前后 RGB、截图文件哈希和原始像素哈希；同时还记录 hidden UI/activity 等 audit-only 字段。新组件只能使用 RGB 路径，必须通过序列化测试证明 audit-only 字段未进入请求。现有 protocol 也明确不允许把 pixel transition 当作 semantic progress。

## 2.5 必须保持 UNCERTAIN 的判断

“UNCERTAIN”在本设计中不是 runtime 的全局三值 verdict，而是一类 **不可被当前 RGB 闭合的声明片段**。至少以下情况必须保留不可判定：

- 操作是否已经写入后台数据库，但屏幕只显示原表单；
- 目标对象是否存在于当前屏幕之外的列表区域；
- 多项任务是否全部完成，但当前帧只显示其中一项；
- toast、动画或瞬时提示已消失；
- 地图或画布发生大范围像素移动，但目标语义对象不可辨认；
- 总和、区间统计或完整列表所需数据没有同时出现在可见区域；
- 文本过小、被遮挡、截断或视觉模型无法可靠读取；
- 当前画面与成功、失败两种后台状态均相容。

这些场景中，正确行为不是让 judge 猜测 `SUPPORTED` 或 `UNSUPPORTED`，而是：

1. 不把该声明片段写成“已由可见证据确认”；
2. 保留其开放状态；
3. 允许 executor 自己决定是否进行额外观察、继续、回答或再次终止；
4. 终止最多被延迟一次，不能由 judge 无限阻断。

---

# 3. 候选机制比较与最终唯一推荐

| 候选方向 | 核心做法 | 优点 | 主要问题 | 裁决 |
|---|---|---|---|---|
| **A. 每动作后独立 VOV** | 每次 action 后用 before/after 图输出一个 outcome verdict | 覆盖面大，概念直接 | 高频调用和 prompt 干扰；A2/A6 没有正向先验；容易把 pixel change 语义化；六成功损失风险最高 | **否定** |
| **B. Terminal-only review** | 只检查 success termination 或 answer | 成本最低；直接针对至少三个 evaluator-disconfirmed terminate | 捕捉不到中途 forgotten obligation、unsupported continuation 和重复 commitment | **不作为最终方案** |
| **C. 每个风险步骤 dual-pass** | executor 先提动作，再由第二调用审查并让 executor 重生成 | 可在动作执行前纠正 | 近似 action override；调用成本高；actor-judge 相关；容易损害原本正确的 reactive 决策 | **否定** |
| **D. 纯确定性 evidence ledger** | 不调用模型，只保留 pending、attempted、transition | 成本低、可审计 | A1/R2 已表明 model-authored pending 会 stale；A6 表明 transition 日志不是 semantic outcome | **不足** |
| **E. 选择性声明—证据对账** | 仅在 pending 被关闭/替换、同状态复发或带开放义务终止时，对一个具体声明进行可见证据对账 | 稀疏；覆盖中途和终止；不阻断普通动作；可显式保留不可判定义务；容易做 matched generic control | 依赖 raw audit 证明触发覆盖；可能仍受同模型相关性和不可见 outcome 限制 | **唯一推荐** |

A2 的完整负结果说明不能继承“高频 progress memory + visible transition + guard”完整包；A6 的负结果说明增加 transition 描述本身不足以提高 accuracy。另一方面，A1 唯一 paired gain 支持“不要在没有确认时忘记重复操作义务”这一窄内核。因此，最小合理扩展应在 **声明关闭时核对证据**，而不是在所有像素变化后判定 progress。

---

# 4. 对初始 Sparse Visible-Outcome Verifier 假设的裁决

## 4.1 裁决：修改并替换原形

初始 VOV 中只有以下原语被保留：

- 判断调用应当稀疏；
- 判断角色与 executor request 隔离；
- 只使用正常运行中已有的 RGB；
- 可见证据不足时不得宣称已完成；
- 所有额外调用必须计费。

以下部分被明确否定：

- 逐动作调用；
- 使用 pixel-change 大小决定 semantic progress；
- 让一个全局 `SUPPORTED / UNSUPPORTED / UNCERTAIN` 覆盖复杂、多项任务；
- 让 verifier 推荐、屏蔽或替换动作；
- 把 verifier 输出写成“任务已经通过”；
- 让 verifier 的一次输出直接等同于组件有效；
- 只修改 verifier prompt，而不设计触发、生命周期、terminal policy、active control 和因果审计。

## 4.2 替换后的核心变化

VOV 被替换为 **Claim–Evidence Reconciler**：

- 判断对象从“刚才的 action 是否成功”改成“executor 正准备关闭、替换或忘记的具体声明是否有直接可见依据”；
- 输出从全局 verdict 改成声明片段与可见事实的映射；
- 普通动作的判断是 delayed confirmation，回执只影响下一次 request；
- terminal review 只提供一次重新考虑机会；
- 不可见的语义 outcome 保持开放，但不能无限阻止终止；
- 与 generic additional visual reasoning 做配置和资源匹配。

这不是 verifier prompt 的改写，而是判断位置、信息权限、状态对象、控制效应和实验合同的整体重构。

---

# 5. 系统名称、假设、父系统与新增组件

## 5.1 系统名称

**R2-SCER v1**

全称：

> **A1-R2 + Selective Claim–Evidence Reconciliation v1**

内部系统标识建议：

`a1r2_scer_v1`

## 5.2 可证伪假设

### H1：系统级正向假设

在不增加 native action-step budget、保持 R2 六成功 0 loss 的条件下，R2-SCER 将正式结果从 6/19、reward 6.5 提升到：

- 至少 7/19 full success；
- reward > 6.5。

### H2：机制假设

错误不是主要因为 agent 缺少更多一般视觉推理，而是因为：

1. executor 在缺少直接证据时关闭了自己先前的声明；
2. 未确认义务从 compact memory 中被清除或替换；
3. 同一开放声明反复出现却未被证据对账；
4. 带开放义务的 terminal claim 没有获得一次独立审视。

因此，专业化的 claim–evidence accounting 应当优于相同计算量的 generic visual reasoning。

### H3：preservation 假设

因为 SCER：

- no-trigger 时保持 R2 request 字节级不变；
- 不修改普通动作；
- 不注入 always-on prose；
- 不把 answer 一律阻断；
- 每个 episode 最多一次 mid-episode review 和一次 terminal review；

它应当比 A2/A6 式高频机制更能保护 R2 的六个成功任务。

### H4：因果假设

Full 不仅应优于 R2，还应：

- 至少比 resource-matched generic control 多 1 个 full success；
- 在 R2 六成功上 0 loss；
- 至少产生 2 个独立的 productive intervention。

否则只能说“额外计算或一次额外考虑机会可能有帮助”，不能说专业 outcome judgment 得到支持。该因果门与 composite component charter 一致。

## 5.3 父系统

选择 **R2 作为精确行为父系统**，不是因为 R2 已经证明因果最优，而是因为：

- 它是唯一完整达到 6/19 且相对 A1 0 loss 的纵向变体；
- 它降低了 token 和 latency；
- 它保留了 A1 的 positive kernel；
- 它没有额外 guard、额外模型调用或 action override；
- preservation 目标要求 no-trigger 轨迹尽可能保持不变。

## 5.4 新增的一个科学组件

SCER 在工程上有三个子模块，但在科学上只构成 **一个 outcome-judgment component**：

1. **Claim Boundary Scheduler**  
   确定何时一个声明即将被关闭、替换、复发或用于终止。

2. **Evidence Accountant**  
   独立辅助调用，把指定声明片段与 RGB 中的直接可见事实对账。

3. **Reconciliation Receipt State**  
   保存最新直接证据和仍开放片段，并以单一短回执影响下一次 executor request。

它们不是“判断 + 恢复 + 长程规划”三条轨道：

- scheduler 不判断任务成功；
- accountant 不推荐动作；
- receipt state 不分解新目标、不排序里程碑、不选择恢复路线。

## 5.5 为什么不继承 A2 完整包

不继承 A2 的高频 injection、model-authored verified-progress state 和 exact-repeat guard，原因是：

- A2 包级结果为 0/19；
- 所有 A1 成功任务均丢失；
- A2 的 `verified` 仍是模型自述；
- transition 分类只表示像素变化幅度；
- guard 只在一个失败任务上节省成本，没有 accuracy gain；
- 高频 memory read 和严格 writer format 自身成为干扰源。

SCER 只复用 controller 已经具备的 `before/after RGB + hash` 原语，不复用 A2 的 semantic interpretation，也不复用 guard。

---

# 6. 完整端到端工作流与组件权限

## 6.1 总体流程

```text
当前 RGB + 原始 R2 memory + 可选 SCER 短回执
                         │
                         ▼
                    R2 executor
                         │
             ┌───────────┴───────────┐
             │                       │
        普通 UI action          terminate / answer
             │                       │
       原动作照常执行          检查是否存在开放声明
             │                       │
       获得已有 after RGB       触发一次 terminal review
             │                       │
   记录 R2 memory 状态变化      有效回执后最多延迟一次
             │                       │
   若 T1/T3 触发，调用 SCER      下一次仍由 executor 自主决定
             │
   当前动作不修改，回执进入
      下一次 executor request
```

## 6.2 No-trigger 路径

没有触发 SCER 时：

- executor prompt、历史、R2 compact memory、action parser 和终止语义与 R2 相同；
- 不调用 auxiliary model；
- 不增加任何文本；
- 不改变 native action；
- 不改变 native step budget；
- 不运行 guard；
- 不保存额外长期状态。

preflight 必须做 byte-level request comparison，证明 no-trigger request 与冻结 R2 等价。

## 6.3 普通动作路径

在 native action step \(t\)：

1. executor 读取当前 screenshot 和 R2 memory；
2. executor 生成 action 以及可能的 R2 `verified/pending` 更新；
3. controller 按 R2 规则执行原动作；
4. controller 获取已经存在的 after RGB；
5. R2 memory 正常提交；
6. scheduler 记录该动作关联的 pending bundle 和 frame hashes；
7. 在下一次 executor response 暴露 T1 或 T3 时，才调用 Evidence Accountant；
8. 当前已生成的普通 action 不被修改或取消；
9. SCER 回执只进入再下一次 executor request。

这是一种 **post-decision delayed reconciliation**：允许 agent 保持 reactive，但在错误关闭义务之后仍可在后续数步内重新打开它。

## 6.4 Terminal 路径

现有 controller 对 `terminate` 会在没有 canonical action 的情况下直接结束，对 `answer` 会执行其 terminal canonical action 后结束。SCER 的唯一控制钩子位于这一正式终止边界。

当 executor 提议 `terminate(success)` 或 `answer` 且存在开放声明时：

1. 暂存 terminal proposal；
2. 调用一次 Evidence Accountant；
3. 若输出格式有效，更新 evidence receipt；
4. 给 executor 一次带回执的新 request；
5. 不执行额外 native action，除非 executor 自己在新 request 中选择；
6. 同一 terminal chain 最多延迟一次；
7. executor 再次终止时接受其提议，同时记录是否发生 immediate relapse。

这一次延迟是 pre-registered scheduler 行为，不是 auxiliary model 自己决定“允许/拒绝终止”。generic control 使用相同 terminal-delay 规则。

## 6.5 不触发的 terminal

以下情况不调用 SCER：

- `terminate(failure)`；
- 没有开放声明的 answer；
- terminal review slot 已使用；
- auxiliary request 构造失败；
- 输出无法解析；
- RGB 哈希或 provenance 不完整。

失败时采用 fail-open：保留日志，但不让辅助角色接管 episode。

## 6.6 权限矩阵

| 能力 | Executor | SCER Accountant | Scheduler / Controller |
|---|---:|---:|---:|
| 查看当前 RGB | 是 | 是，仅冻结输入中的 RGB | 是 |
| 查看 before/after RGB | 间接通过正常历史 | 是，最多两个去重帧 | 是 |
| 查看完整历史 | 是，按 R2 协议 | 否 | 只做日志 |
| 查看 literal task instruction | 是 | 是 | 是 |
| 查看 task name / app whitelist | 否 | 否 | 否 |
| 查看 hidden UI tree / accessibility | 否 | 否 | audit-only，禁止序列化 |
| 查看 package/activity | 否 | 否 | audit-only，禁止序列化 |
| 查看 evaluator/reward | 否 | 否 | 运行时否 |
| 使用 future frames | 否 | 否 | 运行时否 |
| 推荐动作 | 是 | 否 | 否 |
| 改写普通 action | — | 否 | 否 |
| 宣称 evaluator success | 可提出 terminal claim | 否 | 否 |
| 延迟 terminal | — | 否 | 最多一次 |
| 新增 native step | — | 否 | 否 |

---

# 7. 判断对象、触发原则、可见证据与不确定性

## 7.1 判断对象

SCER 不判断整个任务，也不判断“这个 app 是否处于成功状态”。每次只判断一个 **Open Claim Bundle**：

- 来源必须是 executor 已经写入的 R2 `pending`；
- 或者是 executor 正准备从 `pending` 移到 `verified` 的同一段声明；
- 不能由 SCER 自行创造新目标；
- 多项声明可以由 accountant 引用原字符串中的精确子串分别处理；
- accountant 不能扩展 literal task instruction 中没有的规则。

## 7.2 三个确定性触发器

### T1：Closure / Replacement Trigger

满足以下条件时触发：

- 上一个已接受 R2 state 有非空 `pending`；
- 当前 executor response 尝试：
  - 清除该 pending；
  - 用不同 pending 替换它；
  - 或把其规范化文本复制/吸收到 `verified`；
- 且该 bundle 尚无有效 direct-evidence receipt。

目的：审查“即将被忘记或宣布完成”的义务，而不是审查每个动作。

### T2：Terminal-with-Open-Claim Trigger

满足以下条件时触发：

- executor 提议 `terminate(success)` 或 `answer`；
- 当前至少有一个未由直接可见证据关闭的 claim span；
- terminal review slot 未使用。

目的：提供一次 terminal-claim review，而不是模仿 evaluator。

### T3：Exact Recurrence Trigger

满足以下条件时触发：

- R2 writer 对相同规范化 `verified + pending` 状态发生 same-state refresh；
- 自上次该 bundle 的 receipt 之后至少执行过一个 native action；
- 同一 claim 仍开放；
- mid-episode review slot 未使用。

T3 只把 exact recurrence 当作 **调用机会**，不把它解释为错误或 no progress。R2 的 130 次 refresh 提供了潜在暴露，但成功任务中的 refresh 要作为 false-positive 反例共同审计。

## 7.3 规范化规则

为了避免语义匹配器本身成为第二个模型组件，v1 只使用确定性低风险规范化：

- Unicode NFKC；
- lowercase；
- 连续空白折叠；
- 首尾标点和 markdown 装饰移除；
- 数字、实体词、对象名和次序信息全部保留；
- 不做 embedding 相似度；
- 不做 task-specific synonym map；
- 不根据 app 或任务名合并声明；
- 不能匹配的 paraphrase 计为 trigger false negative，不使用隐藏语义模型补救。

这会牺牲 recall，但优先保护 R2 六成功并保持机制最小。

## 7.4 Accountant 可见输入

每次调用只允许：

1. literal task instruction；
2. 一个 `claim_id`；
3. 完整 `open_claim_text`；
4. 当前触发类型 T1/T2/T3；
5. 最后一个已执行 canonical action 的中性文本表示；
6. 最多两个不同哈希的 RGB：
   - `BEFORE`；
   - `AFTER/CURRENT`；
7. RGB provenance：
   - screenshot SHA-256；
   - pixel SHA-256；
   - step index。

若 `AFTER` 与 `CURRENT` 哈希相同，只传一帧。pixel hash 仅用于 provenance 和去重，不作为 semantic evidence。

## 7.5 不允许作为支持证据的信号

以下信号单独出现时不能关闭任何 claim span：

- action 已经被 controller 执行；
- executor 写了 `verified`；
- 页面发生切换；
- pixel change 较大；
- 出现动画；
- 点击坐标不同；
- memory 被读取；
- verifier/accountant 输出了回执；
- executor 在下一步改变了动作；
- episode 更早结束。

## 7.6 可关闭声明的证据

只有 accountant 给出明确、可核验的直接可见事实时，相关 span 才可标为已建立。例如所需结构是：

- 哪一帧；
- 看到了什么对象、文本或状态；
- 该可见事实与 claim span 的关系；
- 证据是否清晰；
- 是否存在相反可见事实。

“屏幕变了”“似乎完成”“通常点击保存后会保存”均不合格。

## 7.7 不确定性的处理

SCER 不生成单个 `UNCERTAIN` verdict。它把不确定性定位到具体 span：

- `visibility_limited_spans`：当前 RGB 原理上不能判断；
- `conflicting_spans`：不同可见事实相互冲突；
- `unaddressed_spans`：模型没有合法覆盖；
- 低置信度 observation：记录但不能关闭。

这些 span 保持开放。普通动作路径中，它们只作为下一 request 的事实回执；terminal 路径中只提供一次重新考虑机会，不能无限阻断。

---

# 8. 主要状态对象及其生命周期

## 8.1 `R2CompactState`

保持现有 R2 语义：

- `verified`；
- `pending`；
- R2 的字符上限、读写 ticket、provenance 和 compact rendering；
- no-trigger 时不改变任何行为。

## 8.2 `OpenClaimBundle`

建议字段：

| 字段 | 含义 |
|---|---|
| `claim_id` | episode 内唯一 ID |
| `source_pending_text` | executor 原始 pending 字符串 |
| `normalized_hash` | 确定性规范化后的哈希 |
| `origin_step` | 首次出现位置 |
| `last_refresh_step` | 最近同状态 refresh |
| `open_spans` | 仍未由直接证据关闭的原文片段 |
| `established_spans` | 已由直接可见事实建立的片段 |
| `contradicted_spans` | 有直接相反可见事实的片段 |
| `visibility_limited_spans` | 当前 RGB 无法决定的片段 |
| `source_frame_hashes` | 最近对账使用的 RGB provenance |

## 8.3 `EvidenceReceipt`

每次合法 accountant 输出形成一份 receipt：

- 只保存最新且可追溯的直接事实；
- 每个事实必须绑定图像标签和哈希；
- 不保存 action recommendation；
- 不保存“task success”字段；
- 对同一 span 的新证据可以替换旧的低质量 observation；
- 历史 receipt 进入 audit log，但 prompt 中只渲染当前有效的一份。

## 8.4 `ReviewBudget`

每个 episode：

- `mid_episode_slot ∈ {unused, used}`；
- `terminal_slot ∈ {unused, used}`；
- `terminal_deferral ∈ {unused, consumed}`；
- 不重试 accountant；
- parse failure 也计入已调用成本，但不修改 claim state。

## 8.5 `TerminalReviewTicket`

绑定：

- terminal proposal hash；
- claim bundle hash；
- current screenshot hash；
- accountant call ID；
- 是否已提供重新考虑机会；
- executor 下一 proposal；
- 是否 immediate relapse。

## 8.6 生命周期规则

1. executor 写入非空 pending 时建立 bundle；
2. same-state refresh 只更新时间，不关闭；
3. pending 被清除或替换时，旧 bundle 在 T1 对账前不能静默消失；
4. accountant 只能关闭由直接事实建立的原文 span；
5. `visibility_limited` 不关闭；
6. 新 pending 可以建立新 bundle，但旧开放 bundle 仍保留；
7. 不使用固定 step TTL 让义务自动消失；
8. bundle 仅在以下情况下结束：
   - 所有 span 由直接证据关闭；
   - executor 明确 `terminate(failure)`；
   - episode 正式结束；
9. 不跨 episode 保存。

## 8.7 容量与溢出

运营容量不应凭空设为 3、6 或 8。零生成 19-trace audit 后冻结：

\[
C_{\text{bundle}}
=
\max_{\text{19 audited traces}}
\left(
\text{concurrent unresolved claim bundles}
\right)
\]

实现可设置硬安全上限 8。若审计发现任何 episode 需要超过 8 个并发开放 bundle，SCER v1 应判定 **NO-GO**，因为它已开始接近长程 coordination memory，而不再是最小 outcome-judgment component。

prompt 中只允许一个 SCER receipt block，长度上限建议与 R2 单字段上限一致，初始为 **450 characters**。超过上限不能无声截掉实体或数字；preflight 若无法无损表达冻结审计中的开放 span，同样 NO-GO。

---

# 9. 新角色的推荐完整 Prompt 模板

## 9.1 System prompt

```text
SYSTEM — SELECTIVE CLAIM–EVIDENCE RECONCILER

You are an evidence accountant for exactly one executor-authored claim.

You are NOT:
- the AndroidWorld evaluator,
- a task-completion oracle,
- a planner,
- an action selector,
- a recovery policy,
- a critic that recommends the next action.

You receive:
1. the literal task instruction;
2. one open claim written by the executor;
3. the trigger type;
4. the last executed action;
5. one or two RGB screenshots labeled BEFORE and AFTER/CURRENT.

Your job is only to map directly visible facts in the supplied RGB images
to exact text spans of the supplied open claim.

Mandatory rules:

1. Executing an action is not evidence that its intended effect occurred.
2. A click, page change, animation, or pixel difference is not by itself
   semantic progress.
3. The executor's words "verified", "done", "saved", "deleted", or similar
   are claims, not evidence.
4. Do not infer backend persistence, hidden database state, off-screen items,
   complete-list coverage, aggregate totals, or evaluator success unless the
   supplied pixels directly show the required fact.
5. When the images cannot decide a claim span, place that exact span under
   visibility_limited_spans. Do not guess.
6. When visible facts conflict, place the span under conflicting_spans.
7. Every established or contradicted span must cite at least one concise,
   image-specific visible fact.
8. Claim spans must be exact substrings of OPEN_CLAIM_TEXT. Do not create new
   obligations, task rules, app-specific requirements, or hidden success
   conditions.
9. Do not recommend, rank, block, or describe any next action.
10. Do not output a global SUPPORTED / UNSUPPORTED / UNCERTAIN verdict.
11. Do not say that the task passed or failed an evaluator.
12. Output exactly one JSON object and no additional prose.
```

## 9.2 User payload template

```text
LITERAL_TASK_INSTRUCTION:
{literal_task_instruction}

CLAIM_ID:
{claim_id}

OPEN_CLAIM_TEXT:
{open_claim_text}

TRIGGER_TYPE:
{closure_or_replacement | exact_recurrence | terminal_with_open_claim}

EXECUTOR_PROPOSAL_TYPE:
{ordinary_action | terminate_success | answer}

LAST_EXECUTED_ACTION:
{canonical_action_summary}

IMAGE PROVENANCE:
BEFORE screenshot_sha256={before_sha256}, pixel_sha256={before_pixel_sha256}
AFTER/CURRENT screenshot_sha256={after_sha256}, pixel_sha256={after_pixel_sha256}

Return the required JSON object.
```

## 9.3 推荐输出结构

```json
{
  "claim_id": "C7",
  "visible_facts": [
    {
      "fact_id": "F1",
      "image": "AFTER_CURRENT",
      "observation": "Concise literal description of what is visibly present.",
      "observation_confidence": "high"
    }
  ],
  "established_spans": [
    {
      "text": "exact substring from OPEN_CLAIM_TEXT",
      "fact_ids": ["F1"]
    }
  ],
  "contradicted_spans": [],
  "visibility_limited_spans": [
    {
      "text": "exact substring from OPEN_CLAIM_TEXT",
      "reason": "off_screen | backend_state | aggregate_not_shown | transient_or_illegible | other"
    }
  ],
  "conflicting_spans": [],
  "scope_note": "No task-level success judgment was made."
}
```

## 9.4 Parser 约束

- `claim_id` 必须匹配 request；
- 所有 span 必须是 `OPEN_CLAIM_TEXT` 的精确子串；
- 同一字符区间不能同时进入多个集合；
- `established_spans` 和 `contradicted_spans` 必须引用合法 `fact_id`；
- accountant 新增的任务条件一律丢弃；
- 含 action recommendation 的字段一律丢弃；
- `observation_confidence` 仅用于审计，不直接决定 terminal；
- 未覆盖、重叠、格式错误或低置信度 span 保持开放；
- 全局 “task complete” 文本不进入 ledger。

---

# 10. 输出如何影响 executor，同时避免 action override 或隐藏 evaluator

## 10.1 普通动作

T1/T3 在 executor 已经生成当前普通动作后触发：

- 当前动作照常执行；
- accountant 不能取消、替换或重排该动作；
- 回执进入下一次 executor request；
- executor 自行决定观察、重试、导航、继续或终止。

推荐注入文本：

```text
OUTCOME-EVIDENCE RECEIPT — not an evaluator result and not an action instruction

Directly visible:
{established_or_contradicted_facts}

Still open or not visually decidable:
{open_spans_and_visibility_limits}

The current screenshot is authoritative. Choose the next action yourself.
```

## 10.2 Terminal proposal

T2 发生时：

- terminal proposal 最多暂存一次；
- Full 与 generic active control 都得到同样的一次 review opportunity；
- accountant 输出改变的是下一 request 中的 evidence receipt 和开放义务状态；
- accountant 不输出“接受/拒绝终止”；
- 第二次 terminal proposal 不再被无限阻断；
- immediate re-termination 被记录为 relapse，但仍按冻结协议处理。

## 10.3 Answer proposal

`answer` 的内容本身不由 SCER 重新求解。SCER 只检查是否还有与 answer 之前的 UI 操作有关的开放 obligation：

- 无开放 obligation：按 R2 接受；
- 有开放 obligation：最多 review 一次；
- 不能因为截图无法展示完整计算过程就拒绝 answer；
- 不能增加专门的 arithmetic solver。

这样保护 `SportsTrackerTotalDurationForCategoryThisWeek` 的已知成功 answer，同时仍允许审计其他 answer 前是否存在被遗忘的 UI 义务。

## 10.4 Fail-open 行为

以下情况不形成控制：

- auxiliary call 异常；
- JSON 无法解析；
- span 非原文子串；
- 图像 provenance 不完整；
- 输出包含 action suggestion；
- 超出 token/call budget；
- receipt 无法在字符上限内无损表示。

普通路径不注入；terminal 路径接受原 proposal。所有异常单独计费和报告。

## 10.5 为什么这不是隐藏 evaluator

SCER：

- 不知道 reward；
- 不知道最终 task result；
- 不知道 task name 或 app whitelist；
- 不知道 hidden UI tree；
- 不建立 AndroidWorld success predicate；
- 不声称 task pass/fail；
- 只核对 executor 自己的一段声明；
- 即使 span 不可判定，也不能无限阻止终止；
- 最终是否成功仍完全由正式 evaluator 在 episode 结束后判定。

---

# 11. 初始调用、token、latency、capacity 与 expiry 预算

## 11.1 Auxiliary call 上限

每个有效 episode：

| 项目 | 初始硬上限 |
|---|---:|
| Mid-episode SCER calls | 1 |
| Terminal SCER calls | 1 |
| Auxiliary calls 合计 | 2 |
| 每次最大输出 | 256 tokens |
| 每次唯一 RGB 数量 | 2 |
| 每 episode auxiliary input + output | 8,192 tokens |
| Terminal deferral | 1 次 |
| Auxiliary retry | 0 |
| 新增 native action-step | 0 |
| 活跃 receipt 渲染长度 | 450 characters |
| 新增 episode latency ceiling | 60 秒 |

该预算位于 composite charter 建议的稀疏范围内，但只是预注册上限，不是性能证据。所有 realized tokens、GPU seconds、wall latency 和 executor re-request 都必须完整记录。

## 11.2 调用优先级

- mid-episode slot：T1 优先于 T3；
- terminal slot：仅供 T2；
- T1/T3 同时出现时只调用一次；
- 已使用 T1 后，后续 recurrence 只记录，不再调用；
- terminal slot 不被 mid-episode 调用占用；
- 不因模型输出“不确定”追加第二次 accountant reflection。

## 11.3 图像预算

- 只发送已有 RGB；
- 相同 pixel hash 的 `AFTER` 与 `CURRENT` 去重；
- 不额外截屏；
- 不裁剪到 task-specific 区域；
- 不使用 OCR 生成额外文本输入；
- 可以使用冻结的统一缩放，但缩放方法和分辨率必须在首次 generation 前冻结，并对 Full/Generic 完全一致；
- 原始图像哈希仍保留用于 provenance。

## 11.4 Expiry

- 开放 obligation 不按 step TTL 自动过期；
- evidence receipt 在 claim 关闭、episode 结束或被更高质量同 claim 证据替换时失效；
- 离开原 UI 页面不会自动删除已建立的直接证据；
- “当前无法判断”的 receipt 可被后来截图更新，但不能自行变成支持；
- 所有状态 episode-local，不跨任务或 seed。

## 11.5 成本必须分项报告

至少报告：

- executor calls；
- auxiliary calls；
- terminal deferral 导致的额外 executor calls；
- executor prompt/completion/image tokens；
- SCER prompt/completion/image tokens；
- native actions；
- triggers、skipped triggers、parse failures；
- GPU seconds；
- auxiliary latency、episode wall time；
- active receipt characters；
- 每新增一个 full success 的增量成本。

---

# 12. 主要代码模块、接口方向与集成风险

## 12.1 建议模块

### `claim_boundary_scheduler.py`

职责：

- 读取 R2 memory transition；
- 计算 T1/T2/T3；
- 管理两个 call slots；
- 不读取 reward、hidden UI 或 task name；
- 不进行视觉判断；
- 不选择动作。

### `scer_state.py`

职责：

- `OpenClaimBundle`；
- `EvidenceReceipt`；
- `ReviewBudget`；
- `TerminalReviewTicket`；
- 精确子串 span 生命周期；
- receipt compact rendering。

### `scer_accountant_client.py`

职责：

- 构造独立 auxiliary request；
- 绑定 RGB hashes；
- 调用冻结模型；
- 记录 token、GPU time、latency；
- 不含 executor action tool schema。

### `scer_contract.py`

职责：

- prompt 常量；
- 输出 parser；
- provenance 检查；
- scope violation 检查；
- fail-open 规则。

### `a1r2_scer_adapter.py`

职责：

- 组合原始 R2 memory 与 SCER receipt；
- no-trigger 时保持 R2 prompt 等价；
- 不修改 `a1r2_compact_verified_pending.py` 的原历史身份。

### `controller.py` 最小 hook

只增加：

- 普通 action 后 claim candidate 记录；
- 下一 response 的 T1/T3 检查；
- terminal proposal 暂存；
- auxiliary call accounting；
- receipt 注入。

controller 已有 before/after screenshot、文件哈希和 raw-pixel hash，因此不需要 A6 式重新定义 transition memory。

### `protocol.py`

executor 的 tool grammar 和 parser 原则上保持不变。auxiliary prompt/parser 必须与 executor protocol 分离，避免 A2 式严格格式要求污染主模型生成。

## 12.2 接口方向

逻辑接口应保持单向：

\[
\text{Executor state}
\rightarrow
\text{Scheduler}
\rightarrow
\text{Accountant request}
\rightarrow
\text{Evidence receipt}
\rightarrow
\text{Next executor context}
\]

禁止反向接口：

- accountant 不能调用 action executor；
- accountant 不能修改 canonical action；
- accountant 不能查询 evaluator；
- scheduler 不能把 receipt 转换为 hard-coded recovery action；
- ledger 不能直接调用 terminate。

## 12.3 主要集成风险

1. **No-trigger 不再等价于 R2**  
   新 renderer、空字段或不同 system prompt 也可能扰动模型。

2. **历史重复注入重新出现**  
   receipt 如果同时写入当前 memory 和 history，会复现 A1 的膨胀问题。

3. **Terminal deferral 计数错误**  
   必须区分 executor generation、native action 和 controller loop iteration。

4. **Answer 语义被错误改写**  
   `answer` 在 protocol 中是 terminal canonical action，不能当普通 UI action。

5. **隐藏字段泄漏**  
   controller 日志中已有 UI/activity audit 字段，序列化白名单必须严格。

6. **RGB 时序错位**  
   claim 必须与产生它的 before/after/current hashes 绑定，不能误用未来帧。

7. **Parse failure 形成隐形策略**  
   所有格式错误都必须 fail-open 且计入组件质量。

8. **Generic control 不再资源匹配**  
   调用模型、图像、触发器、解码或最大输出任一不同都会破坏因果比较。

9. **状态容量把机制推成长程 planner**  
   若需要大量并发义务、复杂依赖图或跨页面计划，SCER v1 应失败，而不是继续扩展。

10. **同模型 actor-judge 相关性**  
    auxiliary role 可能重复 executor 的错误信念，因此必须用独立人工 audit 和 generic control 检验，而不能把回执自证为正确。

---

# 13. Base、Full、resource-matched active control 与机制消融

## 13.1 实验臂

| Arm | 系统 | Auxiliary 调用 | Terminal review | 持久 evidence ledger |
|---|---|---:|---:|---:|
| **Base** | 冻结历史 R2 | 0 | 0 | 否 |
| **Full** | R2-SCER v1 | T1/T2/T3，最多 2 | 最多一次 | 是 |
| **Generic Active Control** | R2 + matched generic visual reasoning | 与 Full 相同 scheduler 和预算 | 与 Full 相同 | 否，只保留普通 note |
| **Ablation: SCER-NoCarry** | 同一 specialist prompt 和调用，但 receipt 只注入一次 | 与 Full 相同 | 与 Full 相同 | 否 |

## 13.2 Base

Base 使用已经冻结的 R2 正式结果，不重跑、不覆盖：

- 6/19；
- reward 6.5；
- 603 calls；
- 595 actions；
- 2,685,730 tokens；
- 六成功集合固定。

如独立审查要求 contemporaneous no-component control，它必须创建新系统身份和新结果文件，不能冒充或覆盖历史 R2；本蓝图的主比较仍以冻结 R2 为 Base。

## 13.3 Full

Full 使用：

- 同一 R2 executor；
- T1/T2/T3；
- Evidence Accountant；
- episode-local open-claim state；
- 一次性 terminal review；
- 下一 request 的结构化 evidence receipt。

## 13.4 Generic Active Control

Generic arm 必须匹配：

- 同一 checkpoint 和 revision；
- 同一 auxiliary system role 长度级别；
- 同一 trigger scheduler；
- 同一 literal goal、claim text 和 action summary；
- 同一 RGB 及哈希；
- 同一图像处理；
- 同一 decoding 参数；
- 同一 max output tokens；
- 同一 call slots；
- 同一 terminal-delay 上限；
- 同一注入位置和字符上限。

其 prompt 只要求：

> 对所给屏幕做一段额外、简洁的一般视觉推理，指出可能相关的可见变化与模糊处；不要采用声明片段—证据对账规则，不要维护开放义务账目，不要推荐动作。

Generic note 会进入与 Full receipt 相同的位置，但不产生 `established/open/contradicted` 的持久状态。

Live 轨迹在第一次行为分歧后不可能继续拥有完全相同的未来 RGB。因此：

- **共同分歧前**检查 call/input 精确匹配；
- **分歧后**不伪造 step alignment；
- 在冻结 R2 raw traces 上另做 exact same-frame offline paired judgment，比较 specialist 与 generic 的判断质量；
- live accuracy 使用完整 episode 结果，不做虚假的逐步配对。

## 13.5 SCER-NoCarry 消融

该消融保留：

- specialist prompt；
- specialist calls；
- 相同 RGB；
- terminal review；
- 一次 receipt 注入。

但在下一 executor response 后丢弃 receipt，不把仍开放 span 持续带入后续步骤。

它检验：

> 改进来自一次额外专业视觉判断，还是来自“未得到直接证据的义务持续保留”这一状态机制？

## 13.6 结果解释合同

### Full 优于 Base，但不优于 Generic

结论只能是：

- 额外视觉计算；
- 一次额外考虑机会；
- 或 prompt 扰动

可能产生收益。

**不得声称专业 outcome judgment 或 claim–evidence accounting 有因果价值。**

### Full 优于 Generic，但不优于 SCER-NoCarry

可支持专业 visual accounting，但不支持持久开放义务 ledger 的必要性。

### Full 优于 Base 和 Generic，但没有 productive intervention

不能把 success 差异归因于已设计的判断路径；可能是随机轨迹扰动或 silent success。

### Full 的成功 episode 中组件未触发

记为系统成功，但组件 causal credit 为 0。

### 组件触发、输出回执或改变动作

这些只证明 activation，不证明 benefit。

---

# 14. Zero-generation audit、offline replay、preflight 与反泄漏检查

## 14.1 当前 live NO-GO 的直接原因

Git 中没有 R2 的完整 raw suite tree，因此现阶段不能诚信地给出请求中七类错误的准确数量，也不能确定 T1/T2/T3 对六个成功任务和十三个非成功任务的暴露率。正式 scored artifact 已经提供 episode 身份与 JSON hashes，足以支持后续物化验证，但不能代替逐步 RGB 审计。

## 14.2 零生成物化

目标 suite：

`official_qwen_20260814T145307_50081981`

步骤：

1. 从原实验机、只读归档或对象存储中取回完整 suite root；
2. 不启动模型 server，不连接 generation API，不使用 GPU；
3. 对每个文件记录：
   - relative path；
   - byte size；
   - SHA-256；
4. 生成递归 source manifest 和 manifest SHA-256；
5. 验证 19 个有效 episode ID；
6. 验证每个 episode JSON SHA-256 与 scored result 一致；
7. 保留 infrastructure-invalid attempt 及其 replacement linkage；
8. 对每个 referenced screenshot 验证：
   - PNG 文件 SHA-256；
   - decode 后 RGB byte hash；
   - shape；
   - dtype；
9. 缺少任一必要文件、hash mismatch 或无法解释的重复路径均立即 NO-GO；
10. materializer 强制 `generation_calls = 0`，模型客户端入口被替换为抛错 stub。

## 14.3 Visible-only 审计包

从验证后的 raw tree 生成只读 annotation packet。每个事件只包含：

- literal task instruction；
- executor response；
- canonical action；
- R2 verified/pending state；
- 截至该事件可用的 before/after/current RGB；
- RGB hashes；
- step index；
- terminal proposal。

明确移除：

- reward；
- evaluator result；
- success/failure summary；
- hidden UI tree；
- accessibility；
- package/activity；
- task-name shortcut；
- future frames；
- A10–A12 diagnostic labels；
- 本设计的 SCER trigger/output。

## 14.4 独立标注顺序

### Pass A：事件时点可见证据标注

两名独立标注者只看事件时点已有信息，标注：

- 直接可见建立；
- 直接可见矛盾；
- 可见事实冲突；
- 截图无法判断；
- executor 是否在无直接证据时关闭声明；
- 是否遗忘仍开放义务；
- 是否以未确认效果为前提继续；
- 是否重复同一 commitment 而没有新的区分性证据。

标注者看不到机制 prompt，也不知道推荐方向。

### Pass B：短窗行为标注

在 Pass A 锁定后，允许查看事件后的：

- 3 个 native actions：判断是否出现 visible correction；
- 再后 4 个 native actions：判断是否 relapse。

这些 future frames 只用于 post-hoc audit，绝不进入 runtime accountant。

### Pass C：结果连接

所有 visible-only 标签、分歧和 adjudication 完成并哈希锁定后，才连接：

- 正式 reward；
- full success；
- termination reason；
- R2 success/failure stratum。

这样可以区分：

1. **visible-evidence unsupported claim**；
2. **evaluator-disconfirmed claim**。

二者不能互相替代。

## 14.5 独立事件定义

### Unsupported continuation

executor 在当前决策中把某一效果当作已成立，且：

- 截至当前帧没有直接可见支持；
- 该效果不再保留为开放 obligation；
- 后续 action 或计划依赖该效果已完成。

### False terminal claim

分两列报告：

- `visible_unsupported_terminal`：终止时没有直接可见支持，或存在直接矛盾；
- `evaluator_disconfirmed_terminal`：锁定标签后连接正式 reward，发现成功声明未获 evaluator success。

### Unconfirmed obligation

literal goal 或 executor 自己已经建立的 obligation：

- 尚无直接可见 closure；
- 未被明确取消；
- 却从最新 working state 中消失、被替换或被 terminal claim 覆盖。

### Repeated ineffective commitment

同一语义 commitment 再次出现，且在两次之间：

- 没有新的区分性可见证据；
- 没有明确改变目标对象；
- 没有完成确认。

人工审计使用语义标签；runtime T3 仍只使用 conservative exact recurrence。

### Screenshot-indistinguishable outcome

成功与失败两种语义状态均与当前 RGB 相容。标注必须保持不可判定，不能用最终 reward 倒推事件时点证据。

## 14.6 审计输出

至少量化：

- 每类事件数；
- 每类涉及 episode 数；
- 六成功与其余十三题分别的比例；
- 每个 T1/T2/T3 的 exposure；
- trigger precision/recall；
- success-task false-positive risk；
- failure-task false-negative risk；
- 必须保持不可判定的事件数；
- 标注者原始一致率；
- adjudicated 结果；
- 按 episode 聚类的 bootstrap interval；
- 未能分类的事件。

## 14.7 机制不得自己定义标签

审计 rubric、annotation manual、source manifest 和标注结果必须在以下内容之前锁定：

- SCER prompt；
- generic prompt；
- trigger normalizer；
- call capacity；
- terminal policy；
- live code/config。

否则会形成“机制定义自己的正确标签，再证明自己正确”的循环。

## 14.8 零生成 scheduler replay

在任何模型 generation 前：

- 对全部 19 条 R2 trace 重放 T1/T2/T3；
- 记录每个 trigger 的 source state；
- 验证不访问 reward/future/hidden fields；
- 验证 no-trigger prompt 等价；
- 验证最多两个 calls/episode；
- 验证六成功任务的触发暴露；
- 验证第一个 gate task 是否存在预注册 intervention opportunity；
- 验证容量和 receipt 字符预算。

该 replay 仍然不能预测行为改变后的 accuracy。

## 14.9 冻结后的 auxiliary offline replay

只有所有行为决策和 hashes 已冻结后，才允许第一次辅助模型 generation：

- specialist 与 generic 对同一 R2 audit event 使用完全相同 RGB；
- 不与 AndroidWorld 交互；
- 不使用 future frame；
- 记录所有 tokens、GPU time 和 latency；
- 不根据输出修改 prompt、触发器或阈值；
- 输出失败即作为正式 offline failure 保留；
- 只能验证 schema、判断质量和资源暴露；
- 不能声称 live accuracy gain。

## 14.10 反泄漏检查

必须建立自动 sentinel tests：

1. 在 episode JSON 中注入假的 `reward=1`、`evaluator_success=true`、package/activity 和 UI tree sentinel；
2. 序列化 auxiliary request；
3. 逐字检查 sentinel 不存在；
4. 检查 task path 和 filename 不含可识别 task-name shortcut；
5. 检查 RGB 只来自当前或过去；
6. 检查 source step index 不大于 decision step；
7. 检查 Full 与 Generic 的可见输入字段相同；
8. 检查 pixel-diff 数值没有进入 accountant prompt；
9. 检查 no-trigger executor request 与 R2 一致；
10. 独立审查者签署 leakage matrix。

---

# 15. 六题保持门、后十三题释放、停止与 resume 规则

## 15.1 Audit GO 门

进入任何 generation 前必须同时满足：

- 19/19 valid R2 raw episodes 全部物化；
- 所有 committed episode hashes 匹配；
- screenshot file/pixel hashes 匹配；
- annotation 完成并锁定；
- T1/T2/T3 的跨任务 exposure 已量化；
- 至少两个非同一任务的目标事件能够被 trigger 覆盖；
- 六成功 counterexamples 已审计；
- `ExpenseDeleteMultiple2` 存在至少一个冻结 trigger opportunity；
- 无 evaluator/hidden/future 泄漏；
- state capacity ≤8；
- receipt 能在冻结长度内无损表示。

任一不满足：**NO-GO，不通过扩大机制补救。**

## 15.2 第一题门

第一题固定：

`ExpenseDeleteMultiple2`

先运行：

1. Full；
2. Generic Active Control。

顺序、seed、模型、环境 snapshot 和配置在首次 generation 前冻结。

Full 必须同时：

- 正式 success；
- 至少发生一次有效 SCER activation；
- 下一次 executor decision 发生可审计差异；
- 3 个 native actions 内出现 visible correction 或直接 evidence closure；
- 之后 4 个 native actions 内无 relapse。

若 Full 成功但组件完全 silent，只能报告 preservation success，不能通过 productive-intervention 门。Composite charter 对首任务的 protection 与 productive intervention 要求应保留。

## 15.3 其余五个成功任务门

固定顺序：

1. `RetroSavePlaylist`
2. `SimpleCalendarAddOneEvent`
3. `SportsTrackerTotalDurationForCategoryThisWeek`
4. `RecipeDeleteMultipleRecipesWithConstraint`
5. `OsmAndMarker`

释放条件：

- Full 在六题上 6/6；
- Generic primary control 同样完成六题而无 infrastructure ambiguity；
- 所有成本在预注册上限内；
- 没有泄漏或协议偏移。

Full 任一 loss：

- 立即停止 Full；
- 不运行剩余十三题；
- 不改 prompt；
- 不改 trigger；
- 不重跑；
- 正式结论为 preservation gate failure。

## 15.4 Ablation 门

`SCER-NoCarry` 在主 Full/Generic 六题门完成后运行自己的六题保持门：

- 任一 loss 停止该 arm；
- 不影响已经完成的 Full 事实；
- 但不能在缺少 ablation 全套结果时宣称持久 ledger 是必要组件。

## 15.5 后十三题释放

只有 Full 与 Generic 均通过 6/6，才释放剩余十三题的主比较。

每个 passing arm：

- 使用同一固定任务顺序；
- 不根据前一任务结果调参；
- 不重置行为决策；
- 不选择性跳过困难任务；
- 不因一次有效科学失败重跑。

## 15.6 停止条件

立即停止相应 arm：

- Full 丢失任一 R2 成功任务；
- hidden/evaluator/future leakage；
- native action budget 增加；
- auxiliary call 超限；
- source hash mismatch；
- prompt/config 与 frozen manifest 不一致；
- 有效任务被人为取消或重跑；
- generic control 资源配置不匹配；
- receipt 被用于 action override；
- accountant 输出被解释为 evaluator success。

## 15.7 Infrastructure-invalid 与 resume

只有明确的 infrastructure invalidity 才允许 replacement：

- emulator crash；
- model server 不可达；
- screenshot 文件损坏；
- runner 未执行既定 action；
- evaluator 未返回有效记录。

resume/replacement 必须：

- 保留无效 attempt；
- 给出 invalidity 证据；
- 使用完全相同代码/config/model；
- 从该任务的合法初始状态重新开始；
- 不从中间轨迹恢复；
- 不因 reward 低、模型犯错或 mechanism failure 重新运行。

---

# 16. Accuracy、cost、judgment quality 与 causality 判据

## 16.1 Accuracy

对每个 arm 报告：

\[
S_{\text{arm}}
=
\sum_{i=1}^{19}
\mathbf{1}\left[\text{full success}_i\right]
\]

\[
R_{\text{arm}}
=
\sum_{i=1}^{19}
\text{reward}_i
\]

以及：

- 任务级 reward；
- termination reason；
- 对 R2 的 win/loss/tie；
- 六成功 preservation；
- 剩余十三题新增 full success；
- partial reward 变化。

Full 的最低正向门：

\[
S_{\text{Full}} \ge 7
\]

\[
R_{\text{Full}} > 6.5
\]

\[
\text{Losses on R2 six} = 0
\]

## 16.2 Cost

单独报告：

\[
\Delta C_{\text{calls}}
=
C_{\text{Full}} - C_{\text{R2}}
\]

\[
\Delta T_{\text{tokens}}
=
T_{\text{Full}} - T_{\text{R2}}
\]

\[
\Delta L_{\text{wall}}
=
L_{\text{Full}} - L_{\text{R2}}
\]

并拆分：

- executor vs auxiliary；
- text vs image tokens；
- GPU seconds；
- terminal reconsideration calls；
- native actions；
- per-success incremental cost；
- p50/p95 auxiliary latency。

Accuracy pass 不能自动覆盖 cost failure；cost saving 也不能代替 accuracy gain。

## 16.3 Judgment quality

以锁定的人类 visible-only audit 为参考，报告：

- direct-establishment precision；
- direct-establishment recall；
- contradiction precision/recall；
- visibility-limit identification；
- false closure rate；
- false reopen/retain rate；
- parse failure rate；
- claim-span coverage；
- 六成功上的 false-reject；
- 十三题上的 missed-target false-negative；
- specialist 与 generic 在完全相同 frozen frames 上的差异。

`observation_confidence` 只做描述性校准：

- high/medium/low 各自对应的人工正确率；
- 不声称 held-out calibration；
- 不根据这 19 题生成后的结果重新调阈值。

## 16.4 Productive intervention

一次 intervention 必须同时满足：

\[
\text{Productive}
=
\text{Activated}
\land
\text{NextDecisionChanged}
\land
\text{VisibleCorrection}_{\le 3}
\land
\neg \text{Relapse}_{\le 4}
\]

其中：

- `Activated`：trigger、合法 call、合法 receipt、实际进入 executor context；
- `NextDecisionChanged`：下一 proposal 相对触发时的 terminal/commitment 或重复 action family 出现可审计差异；
- `VisibleCorrection≤3`：三次 native action 内出现独立审计认可的直接证据、矛盾消除或重新打开义务；
- `NoRelapse≤4`：之后四次 native action 内不重新出现同一 unsupported closure、terminal 或 commitment。

三步纠正和四步 relapse 窗口沿用 A12 diagnostic 的审计思想，但这里只作为 prospective、预注册的因果判据，不能追认 A12 正式有效。

## 16.5 专业组件因果门

只有同时满足以下条件，才可说“专业 outcome judgment 获得支持”：

1. Full 达到系统级正向门；
2. Full 比 Generic 至少多 1 个 full success；
3. R2 六成功 0 loss；
4. 至少 2 个不同 episode 出现 productive intervention；
5. productive interventions 不是只发生在 silent success 或无法匹配的后验故事中；
6. 资源匹配审计通过。

## 16.6 Full 优于 Base 但不优于 Generic

必须写成：

> 结果支持“额外视觉推理或额外一次 executor reconsideration 可能有帮助”，但不支持 claim–evidence specialist 相对 generic reasoning 的独立因果价值。

不得通过挑选 judge 输出、展示成功案例或强调 action change 来弱化该解释。

## 16.7 所有任务已观察的限制

19 个任务和 seed 均已被观察，因此：

- 不声称 held-out generalization；
- 不声称统计总体上的泛化提升；
- 不把 bootstrap interval 解释为新任务置信区间；
- 结果只说明冻结 AndroidWorld Hard packet 上的 prospective comparison；
- 后续真正的 generalization 需要新的、未用于设计的任务包或 seed，但不属于本轮。

---

# 17. False accept、false reject、uncertain、纠正与 relapse 审计

## 17.1 False accept

分三层报告：

### Judgment false accept

SCER 把某 span 记为 established，但独立 visible-only audit 认为：

- 无直接证据；
- 当前不可判定；
- 或存在直接矛盾。

### Behavioral false accept

SCER receipt 没有保留开放义务，executor 随后继续或终止，并依赖该效果已完成。

### Outcome false accept

锁定 visible-only 标签后连接 evaluator，发现 episode 的 success claim 未获正式 success。

第三类不能倒过来证明第一类：有些 evaluator failure 可能不是当前 RGB 可识别的。

## 17.2 False reject

SCER 保留、重开或强调某 span，但独立审计认为该 span 已被直接可见证据建立。

重点单列：

- 是否发生在六个成功任务；
- 是否导致额外无效动作；
- 是否把原成功变成 failure；
- 是否来自 accountant 错误；
- 是否来自 scheduler 的一次 terminal delay；
- 是否来自 stale receipt。

## 17.3 Uncertain

不可判定事件不进入普通二值 confusion matrix，而单独报告：

- 总数；
- episode 覆盖；
- 成功/失败分层；
- accountant 是否正确保持开放；
- executor 是否在一次 reconsideration 后仍终止；
- 最终 evaluator result；
- 是否存在 silent success。

不可判定后终止成功，不代表 accountant 应该提前判定成功；不可判定后终止失败，也不代表 accountant 应判失败。

## 17.4 Trigger false positive

scheduler 触发了 review，但独立审计认为：

- claim 已有直接可见支持；
- refresh 是合理状态保持；
- replacement 不构成义务遗忘；
- terminal 没有开放 obligation。

六成功中的此类事件是 preservation 风险核心。

## 17.5 Trigger false negative

独立审计发现：

- unsupported closure；
- forgotten obligation；
- repeated ineffective commitment；
- 带开放义务的错误终止；

但 T1/T2/T3 未触发。

由于 v1 不使用语义 embedding，paraphrase miss 必须作为 false negative 诚实报告，不能 post-hoc 加 synonym rule。

## 17.6 Visible correction

只在 post-hoc audit 中使用未来三步，且必须观察到：

- 原开放对象的直接状态证据；
- 原矛盾消失；
- executor 明确恢复未确认义务；
- 或 terminal claim 被撤回并完成可见确认。

单纯动作变化、页面变化或更多 token 不算 correction。

## 17.7 Relapse

以下任一发生即为 relapse：

- 再次无证据关闭同一 claim；
- 再次提出相同 success terminal；
- 再次重复同一 commitment 且没有新证据；
- receipt 仍在 prompt 中，但 executor 明确忽略并恢复原错误信念。

## 17.8 Silent success

episode 成功但：

- 无 trigger；
- 未调用 accountant；
- receipt 未进入 executor；
- 或行为差异发生在组件激活前。

记为系统 success，组件 credit 为 0。

## 17.9 无法匹配的轨迹

Full 与 Generic 一旦产生不同动作，后续 screenshot 不再强行逐步匹配：

- episode-level accuracy/cost 继续比较；
- intervention-level causal audit 在各自轨迹内完成；
- exact same-frame judgment quality 使用冻结 R2 offline event；
- 不使用“看起来类似的后续步骤”构造伪 counterfactual。

---

# 18. R2 六个成功任务逐题 preservation 与风险分析

以下分析只用于审计和保护，不进入 runtime task whitelist。运行时 scheduler 不得读取任务名。

| 任务 | 已知 R2 路径 | 主要风险 | SCER preservation 规则 |
|---|---|---|---|
| `ExpenseDeleteMultiple2` | success；terminate；5 refresh | T3 可能对合理重试过度触发；错误 reopen 已完成删除 | 首题 raw audit 必须确认触发点；普通 action 不阻断；只有直接可见反证或不可判定 span 进入 receipt |
| `RetroSavePlaylist` | success；terminate；0 refresh | 多个目标对象可能不在同一屏幕；terminal review 可能要求不可能的全屏证据 | 允许分片 direct receipts；不能要求所有对象同时可见；不可见部分只保持开放一次，不无限阻断 |
| `SimpleCalendarAddOneEvent` | success；terminate；1 refresh | 保存后可能离开表单；当前屏幕未必持续展示 event | 已见的直接 confirmation 可以保留；离开页面不自动撤销；不能凭表单消失判成功或失败 |
| `SportsTrackerTotalDurationForCategoryThisWeek` | success；`model_answer`；1 refresh | blanket answer review 会直接造成 false reject | 无开放 UI obligation 时 answer 不触发；SCER 不重新计算答案，不要求 evaluator-level proof |
| `RecipeDeleteMultipleRecipesWithConstraint` | success；terminate；2 refresh | 新 judge 可能破坏 A1 唯一正向内核，或把局部页面变化当删除确认 | 重复删除义务在没有直接证据时继续开放；点击、返回和 pixel change 均不能自行关闭 |
| `OsmAndMarker` | success；terminate；2 refresh | 地图平移产生大像素变化，但不等于 marker semantic success | 地图运动不能关闭 claim；只有直接可辨认的 marker/label/state 事实可用；不可判定时只给一次 review |

任务级终止方式和 refresh 来自 R2 正式结果；`RecipeDeleteMultipleRecipesWithConstraint` 是 A1 唯一 paired gain，`OsmAndMarker` 是 R2 相对 A1 的新增 win。

## 18.1 首题特殊要求

`ExpenseDeleteMultiple2` 有 5 次 same-state refresh，因此很可能暴露 T3，但只有 raw trace 能确定：

- refresh 前后是否对应同一 obligation；
- 是否有新的可见证据；
- 是否属于合理重复操作；
- SCER receipt 是否有机会改变下一决策；
- 是否会破坏原成功。

若 zero-generation audit 发现这五次 refresh 均不构成合法 intervention opportunity，则当前设计无法满足首题 productive-intervention gate，必须在 live 前判定 NO-GO，而不能临时扩大触发器。

## 18.2 RecipeDelete 的保护原则

A1 的唯一 paired gain 不是“模型知道删除成功”，而是“模型没有在未确认时忘记重复删除义务”。SCER 必须继承这一原则：

- pending 本身不是完成证据；
- action receipt 不是完成证据；
- 同一删除操作仍未确认时不能静默移入 verified；
- 但 SCER 也不能因为无法看到完整后台状态而无限阻止终止。

## 18.3 SportsTracker answer 的保护原则

这一路径说明 task completion 与 terminal format 不能绑定：

- 成功可以来自 answer；
- 失败也可以来自 answer；
- outcome judgment 应检查开放 UI obligation，而不是重新扮演求解器；
- 如果没有开放 obligation，额外 terminal verifier 只会增加 false-reject 风险。

---

# 19. 预期收益、失败模式与明确 falsification

## 19.1 为什么 SCER 值得成为唯一推荐

### 它对应 A1 的唯一正向内核

A1 的可辩护收益来自“不把重复操作过早视为已确认”。SCER 将这一原则从 executor 自述的 pending 提升为：

- pending 即将被关闭时检查直接证据；
- 不可判定时保留 span；
- 不要求每一步都进行判断。

### 它直接针对 R2 的已知终止错配

R2 至少有三个 evaluator-disconfirmed `terminate(success)`，说明 terminal proposal 是高价值审计边界。SCER 不声称能够识别全部三例，但提供了一次专门、低频的 claim review。

### 它避开 A2/A6 的完整负先验

- 不 always-on；
- 不注入每步 transition；
- 不用 pixel threshold；
- 不使用 guard；
- 不强制主 executor 输出新格式；
- no-trigger 路径保持 R2。

### 它允许严格 active control

specialist 与 generic 可以使用：

- 同一触发；
- 同一模型；
- 同一 RGB；
- 同一调用；
- 同一 token 上限；
- 同一 terminal reconsideration opportunity。

因此可以区分“专业 evidence accounting”和“多做一次一般视觉推理”。

## 19.2 主要失败模式

1. **Actor-judge correlated error**  
   同一 checkpoint 可能重复 executor 的错误信念。

2. **Outcome 原理上不可见**  
   backend、off-screen 和 aggregate 状态无法由两帧 RGB 判断。

3. **Trigger recall 不足**  
   exact normalization 会漏掉 paraphrase 或 invalid-prefix 路径。

4. **Receipt 干扰成功轨迹**  
   即使不改当前 action，下一 request 也可能被 stale concern 带偏。

5. **一次 terminal delay 不足**  
   executor 可能立即重复同一 terminal claim。

6. **一次 terminal delay 本身有害**  
   原本正确的 executor 可能在第二次 request 中采取不必要动作。

7. **多项 obligation 无法紧凑表达**  
   450 characters 或容量上限可能不足。

8. **Generic reasoning 同样有效**  
   收益可能来自额外视觉计算，而不是专业判断。

9. **Specialist 判断好但不改变行为**  
   judgment quality 与 task accuracy 可以脱钩。

10. **状态开始承担 long-horizon coordination**  
    若需要复杂目标图、顺序或多页面依赖，SCER v1 边界被突破。

## 19.3 明确 falsification 条件

| 观察结果 | 科学裁决 |
|---|---|
| Raw R2 traces 无法物化或 hash 不匹配 | 整体 NO-GO |
| 独立审计未发现跨任务目标现象 | SCER 问题假设被削弱，NO-GO |
| T1/T2/T3 不能覆盖至少两个非同一任务的目标事件 | Trigger 设计被 falsify |
| 首题没有合法 intervention opportunity | 不进入 live |
| Full 丢失任一 R2 成功任务 | Preservation falsified，立即停止 |
| Full ≤6/19 | 无 accuracy gain |
| Full reward ≤6.5 | 未达到正向目标 |
| Full 优于 Base 但不优于 Generic | 只支持 generic extra reasoning，不支持专业组件 |
| Productive interventions <2 | 专业组件因果门失败 |
| Full 不优于 SCER-NoCarry | 持久 ledger 的必要性未获支持 |
| 收益全部来自 silent success | 无组件 causal credit |
| Accountant 大量把不可见状态判为 established | Judgment mechanism falsified |
| 六成功出现可见证据已充分但被错误 reopen 并导致 loss | False-reject failure |
| 只有借助 task rule、evaluator、hidden UI、future frame 或额外 native steps 才有效 | 协议无效 |
| 调用或 latency 超预算 | Cost failure，不能被 accuracy 自动覆盖 |
| 有效失败后调 prompt 或重跑 | 结果失去预注册资格 |

## 19.4 当前科学状态

**设计推荐：GO。**

- 允许按本文接口开展零生成物化、独立审计和实现规划；
- 允许编写不调用模型的单元测试与 scheduler replay。

**Live generation：NO-GO。**

解除 NO-GO 的唯一最小证据补全是：

1. 物化并哈希绑定 R2 全 19 题 raw traces；
2. 完成 visible-only 独立 audit；
3. 冻结触发暴露、成功反例、容量和 prompt；
4. 通过 anti-leak 与 resource-match preflight。

不能用进一步 prompt brainstorming、diagnostic output 或模型自评替代这一步。

---

# 20. 分阶段实现、独立审查、offline 验证与 live 路线图

## Phase 0：零生成证据补全

- 物化 R2 suite；
- 验证 episode/screenshot hashes；
- 生成 visible-only packet；
- 双人独立标注；
- adjudication；
- 结果锁定后连接 reward；
- 量化 T1/T2/T3 暴露；
- 形成 GO/NO-GO。

输出是审计事实，不是新系统结果。

## Phase 1：行为合同冻结

冻结：

- 父系统身份；
- trigger rules；
- normalization；
- prompt；
- parser；
- state lifecycle；
- capacity；
- receipt renderer；
- terminal/answer policy；
- generic control；
- ablation；
- resource ceilings；
- task/arm order；
- stop/resume rules。

此阶段结束后，任何模型 generation 都不能再用于调设计。

## Phase 2：最小实现与静态测试

实现：

- scheduler；
- SCER state；
- accountant client；
- controller hooks；
- prompt serializer；
- resource logger；
- generic arm；
- NoCarry ablation。

静态测试：

- no-trigger request byte equivalence；
- span parser；
- malformed output fail-open；
- terminal ticket；
- no duplicate history injection；
- native action counter；
- task/app/evaluator sentinel leakage。

## Phase 3：零生成完整 replay

在 19 条 R2 trace 上：

- 重放 triggers；
- 验证 call upper bound；
- 验证首题 exposure；
- 验证六成功风险；
- 验证容量；
- 生成 frozen behavior manifest；
- 独立 reviewer 签字。

仍然不调用模型。

## Phase 4：冻结后的 auxiliary offline replay

- specialist 与 generic 使用同一 R2 event；
- 完整计费；
- 不与环境交互；
- 不调 prompt；
- 评估 judgment quality；
- 验证 JSON parse 和 receipt rendering；
- 若发生科学 failure，保留并停止，不用第二版 prompt 覆盖。

## Phase 5：Live preservation gates

1. `ExpenseDeleteMultiple2`：Full + Generic；
2. productive-intervention 门；
3. 其余五个 R2 successes；
4. Full/Generic 6/6；
5. NoCarry 六题；
6. 只有通过的主比较释放剩余十三题。

## Phase 6：完整 prospective comparison

对释放的 arm：

- 按固定顺序运行十三题；
- 不调参；
- 不重跑有效失败；
- 完整保存 calls、tokens、RGB hashes、receipts、actions 和 latency；
- evaluator 只在正式流程中评分，不进入 runtime component。

## Phase 7：独立结果审计

分四份逻辑面板报告，而不是混成一个“有效/无效”结论：

1. Accuracy；
2. Judgment quality；
3. Resource cost；
4. Component causality。

同时报告：

- silent successes；
- unmatched trajectories；
- false accepts/rejects；
- uncertain cases；
- corrections；
- relapses；
- protocol invalidities；
- stopped arms。

任何 post-hoc diagnostic 只能追加为 diagnostic，不能改写正式状态。

---

# 21. 实现前仍需冻结的关键决策

以下决策必须在第一次 auxiliary generation 前形成 hash-bound manifest：

1. **Raw source identity**
   - suite root；
   - 19 个 valid episode hashes；
   - invalid attempt linkage；
   - screenshot manifest。

2. **独立 audit rubric**
   - unsupported continuation；
   - false terminal；
   - unconfirmed obligation；
   - repeated ineffective commitment；
   - visibility-limited outcome；
   - correction；
   - relapse。

3. **Annotation protocol**
   - 标注者身份；
   - blind fields；
   - disagreement/adjudication；
   - future-window 使用边界；
   - reward join 顺序。

4. **Claim normalization**
   - Unicode、空白、标点规则；
   - 不做 synonym/embedding；
   - exact substring 验证。

5. **T1/T2/T3 精确定义**
   - pending clear/replace；
   - verified absorption；
   - same-state refresh；
   - terminal-with-open-claim；
   - 多 trigger 冲突优先级。

6. **Call budget**
   - 1 mid + 1 terminal；
   - output 256 tokens；
   - episode total 8,192 tokens；
   - no retry；
   - latency ceiling。

7. **图像输入**
   - 使用哪两个 frame；
   - hash 去重；
   - 是否统一缩放；
   - 缩放算法和分辨率。

8. **State capacity**
   - 由 19-trace audit 得到的并发 bundle 数；
   - 硬上限 8；
   - overflow 行为；
   - 450-character receipt 是否足够。

9. **State lifecycle**
   - span closure；
   - contradiction；
   - visibility limit；
   - replacement；
   - episode-end cleanup；
   - no TTL。

10. **Accountant 模型配置**
    - checkpoint；
    - revision；
    - tokenizer/image processor；
    - decoding；
    - seed；
    - max output；
    - precision。

11. **Accountant prompt 与 parser**
    - system prompt hash；
    - user template hash；
    - output contract；
    - scope violation；
    - malformed fail-open。

12. **Terminal policy**
    - `terminate(success)`；
    - `terminate(failure)`；
    - `answer`；
    - 一次 deferral；
    - immediate relapse；
    - parse failure。

13. **Executor receipt**
    - 注入位置；
    - no-trigger byte identity；
    - 历史剥离；
    - 单一活跃 block；
    - 字符上限。

14. **Generic Active Control**
    - prompt；
    - 相同输入字段；
    - 相同 call schedule；
    - 相同图像处理；
    - 相同 terminal opportunity；
    - resource-match 验证方法。

15. **NoCarry 消融**
    - receipt 保留一轮的精确定义；
    - trigger scheduler 是否共享；
    - terminal ticket 是否共享。

16. **实验顺序**
    - 首题；
    - 六题固定顺序；
    - 十三题顺序；
    - arm 顺序；
    - 是否允许 interleaving。

17. **停止与 invalidity**
    - success loss；
    - resource violation；
    - leakage；
    - infrastructure invalid；
    - replacement receipt。

18. **Productive intervention**
    - next-decision difference；
    - 3-action correction；
    - 4-action relapse；
    - independent audit procedure。

19. **Cost instrumentation**
    - executor/auxiliary calls；
    - image tokens；
    - GPU seconds；
    - wall latency；
    - terminal re-request；
    - native actions。

20. **结果解释合同**
    - Full vs Base；
    - Full vs Generic；
    - Full vs NoCarry；
    - silent success；
    - unmatched trace；
    - no held-out claim。

21. **代码与配置 hashes**
    - parent R2 code；
    - SCER modules；
    - controller/protocol；
    - prompts；
    - model/config；
    - runner；
    - preflight report。

---

# 最终科学结论

本轮不推荐原始的逐动作、固定三值 Sparse Visible-Outcome Verifier。A2 和 A6 已经表明，高频 progress/transition 注入与像素变化记录没有形成正向 accuracy 先验；A1 的唯一 paired gain 则支持一个更窄的原则：**在没有直接确认时，不要忘记仍待完成的重复操作义务。**

因此，唯一推荐是：

> **R2-SCER v1：在 R2 的 compact verified+pending 之上，只在声明即将关闭、替换、精确复发或被用于终止时，进行一次独立的可见声明—证据对账；把不可见或矛盾的声明片段继续保持为开放义务，并以短回执影响下一次 executor request，而不覆盖普通动作、不模仿 evaluator、不引入 recovery policy 或长程 planner。**

该方案当前只获得 **设计推荐**，没有获得实验有效性认证。

在 R2 raw trace 尚未完成 zero-generation、hash-bound、visible-only 独立审计之前，正式状态必须保持：

> **LIVE NO-GO。**

解除 NO-GO 后，R2-SCER 只有在同时达到以下条件时才构成正向结果：

- R2 六成功 6/6；
- 至少 7/19；
- reward > 6.5；
- Full 比 matched Generic 至少多 1 个 full success；
- 至少 2 个独立 productive interventions；
- 无 evaluator、hidden UI、future frame、task whitelist 或额外 native-step 泄漏；
- accuracy、judgment quality、resource cost 和 component causality 分别通过审计。