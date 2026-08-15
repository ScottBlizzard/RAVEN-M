# Prompt for GPT Pro — A1-R3-v2 Clean Redesign from Frozen R2

你现在进入一个全新的研究设计任务，没有任何既有对话上下文。请先完整审计指定 GitHub 提交，再设计一条从冻结 A1-R2 重新分叉的纯记忆实验臂。不要沿用历史 A1-R3–R12 的实现栈，不要凭一般印象给方案，也不要把长文或复杂状态机当作严谨性。

仓库：<https://github.com/ScottBlizzard/RAVEN-M>

指定分支：`a2-verified-progress-audit-20260810`

冻结审计提交：`83c0de5bed18740719b46b5bdd1fccf7904ba0cb`

请首先核对分支和 commit。该 commit 是本轮设计唯一事实边界。后续提交、对话中的口头概括以及你自己的先验都不能替代仓库证据。

## 任务定义

请设计一个新的 `A1-R3-v2`（最终名称可以更严谨，但必须明确是新 prospective identity），目标是在保留 A1-R2 六个成功任务的前提下，从 6/19 提升到至少 7/19，并进一步降低或至少不增加 A1-R2 的系统成本。

历史 `A1-R3 SRPL` 已经是冻结且终止的实验身份。不得覆盖、修改、续跑或把新设计仍称为同一个 R3。所谓“重新设计 R3”，是从 A1-R2 重新分叉一个新版本，而不是修改历史证据。

## 必须核验的事实

同一 19 个 AndroidWorld Hard 实例、task seed `20260806`：

| Arm | Full success | Reward | Calls | Actions | Total tokens | Valid elapsed |
|---|---:|---:|---:|---:|---:|---:|
| A0 | 4/19 | 4.5 | 329 | 316 | 1,273,361 | 6,541.82 s |
| A1 | 5/19 | 5.5 | 603 | 596 | 3,464,267 | 14,595.49 s |
| A1-R2 | **6/19** | **6.5** | 603 | 595 | **2,685,730** | **11,230.18 s** |

A1-R2 相对 A1：1 win、0 loss、18 ties；新增成功是 `OsmAndMarker`；保留了 A1 的五个成功任务；tokens 减少 778,537，elapsed 减少 3,365.31 秒，calls 相同。R2 accuracy verdict 为 PASS，严格 cost verdict 因 calls 没有小于 603 而 FAIL，mechanism causality 因缺少 matched ablation 而未建立。

A1-R1 BPR-v2 并不是正结果：它首题 0/1。你可以审计其 bounded receipt、expiry、one-copy 等思想，但不能把 R1 当成功先验。可执行的正向 parent 必须是 A1-R2。

A1-R3 到 A1-R12 都只运行了固定首题 `ExpenseDeleteMultiple2`，并且都是有效的 reward-0、0/1 gate failure；它们不是 0/19。最重要的方法学事实是：R3–R12 是一条高度依赖的串行补丁谱系，而不是十个独立方案。R3 的新生命周期完全未激活；R4 修复 writer 后，R5–R12 继续继承已回归的 R4 底座，并越来越针对同一条 Expense 轨迹局部修补。不要继承这条实现链。

## 必读材料

至少阅读并在文档中引用具体仓库路径和证据：

1. `evidence/a1/A1_R1_R2_POSITIVE_AND_R3_R12_FAILURE_AUDIT_2026-08-15.md`
2. `evidence/a1r2/A1R2_CVP_SCORED_RESULT_2026-08-14.md`
3. `evidence/a1r2/A1R2_CVP_SCORED_RESULT_2026-08-14.json`
4. `evidence/a1r2/A1R2_CVP_OFFLINE_REPLAY_REPORT.json`
5. `protocols/A1R2_COMPACT_VERIFIED_PENDING_PREREG_2026-08-14.md`
6. `implementation/src/raven_m/official_qwen_mobile/a1r2_compact_verified_pending.py`
7. `implementation/src/raven_m/official_qwen_mobile/a1r2_contract.py`
8. `implementation/configs/a1r2_compact_verified_pending_hard_seed20260806.json`
9. `evidence/a1r1_v2/A1R1_BPR_V2_PRIMARY_GATE_RESULT_2026-08-14.md`
10. `implementation/src/raven_m/official_qwen_mobile/a1r1_bpr_v2.py`
11. `evidence/a1r3/` 到 `evidence/a1r12/` 的 primary gate result、offline replay 和 preflight
12. `implementation/src/raven_m/official_qwen_mobile/a1r3_stale_resistant_pending.py` 到 R12 的实现继承关系
13. `implementation/src/raven_m/official_qwen_mobile/controller.py`
14. `implementation/src/raven_m/official_qwen_mobile/protocol.py`
15. `implementation/src/raven_m/official_qwen_mobile/working_memory.py`
16. `evidence/a2/A0_A1_PAIRED_REFERENCE_20260810.json`
17. `HANDOFF_2026-08-13.md`

如果 GitHub 中缺少完成设计所需的 raw screenshot/step trace，不得脑补。请明确列出缺失证据，并把一个 zero-generation、只读、可物化并哈希绑定的 trace audit 作为设计冻结前的必要步骤。不得根据已知 reward 在运行时决策。

## 设计方法要求

先独立审计完整 R2 19 题，而不是只分析 `ExpenseDeleteMultiple2`。至少找出三类跨任务候选缺陷，并分别量化：

- 在 R2 的 6 个成功任务中出现多少；
- 在 13 个失败任务中出现多少；
- 是否与额外 calls/tokens、同状态刷新、错误循环或未完成事项丢失相关；
- 是否存在反例；
- 为什么某个缺陷适合由 episode-local memory 修复，而不是需要 planner、verifier、grounder 或更多推理。

完成比较后只能冻结**一条首选机制**。不要给十个菜单式方案。每一个新增字段、阈值、trigger 和 renderer token 都必须对应跨任务 R2 证据，并说明为什么更简单的规则不够。

优先级是：保持 R2 的成功行为 > 稀疏地修复跨任务缺陷 > 降低成本 > 增加复杂度。新机制在未触发时必须尽可能与冻结 R2 等价。

## 运行时硬约束

1. 仍使用同一个 official Qwen3-VL-32B mobile controller、model revision、截图输入、system prompt、sampling、action schema、19 个任务实例、task seed `20260806`、generation seed `3407` 和 native step budgets。
2. parent 必须是冻结的 `a1r2_compact_verified_pending_v1`。不得从 R3–R12 subclass 或复制累计 prompt stack。
3. 只允许一个 episode-local deterministic memory path，这是唯一干预。
4. 零额外模型调用；禁止 planner、critic、verifier、RAG、retriever、额外 agent、OCR、额外截图、视觉模型、训练或微调。
5. 禁止 hidden UI tree/accessibility、activity/package、AndroidWorld evaluator、reward、future trace、数据库、跨 episode donor、task name/app whitelist、坐标或 screen-hash 特判。
6. 记忆只能使用 goal、模型自己已经生成的文本/动作、当前及过去模型可见 RGB 的确定性统计。
7. 当前截图永远覆盖旧记忆；记忆不得声明 evaluator success/failure。
8. 记忆只能通过下一次正常模型请求中的 bounded context 影响动作；不得 block、override、repair、retry 或 force termination，不得增加 native action budget。
9. ordinary action history 保留其正常动作语义；同一结构化记忆不得同时存在于 history 与 memory block 两份。
10. 禁止 always-on writer reminder、每步重复完整 goal、通用坐标教程以及 R3–R12 的累积 recovery 文本，除非你用跨任务 R2 证据证明某个最小片段不可替代；即使保留也必须重新设计而不是继承代码。
11. 冻结单次字符/UTF-8/token上限、episode 总注入预算、最大非空 reads、cooldown/expiry、存储容量、CPU P95/P99 和 audit 上限。
12. 不得从 R3–R12 的首题失败结果事后拟合 task-specific trigger。

## 必须解决的关键问题

### Writer fragility

R3 的 34 个 Action 全部不符合 inherited `MEMORY[...]` prefix，导致机制完全不运行。请决定新设计是否继续依赖 model-authored memory syntax。若继续，必须给出为什么 R2 的成功证据足够，以及如何 fail-closed；若取消依赖，必须证明 controller-authored update 不会引入 task parser、hidden state 或新的策略组件。

### R2 causality

R2 的六个成功 episode 都有 read，但这不证明 read 导致成功。请设计最小 matched ablation。首选是同一新实现的 read-enabled 与 read-disabled/content-neutralized projection，而不是换 controller。说明哪些 paired opportunities 可以 exact-match，哪些只能记为 unresolved。

### Cross-task rather than single-task optimization

你的首选机制必须由至少多个 R2 task traces 支撑。若证据只支持修复 Expense，则不得把它注册为通用 R3-v2。

### Preservation

新机制在六个 R2 成功任务上必须有明确 preservation argument。请列出每个成功任务的潜在触发机会、风险和预期 silent/no-op 行为。不能只写“应该不影响”。

## 实验纪律

固定 capability gate 顺序：

1. `ExpenseDeleteMultiple2`
2. `RetroSavePlaylist`
3. `SimpleCalendarAddOneEvent`
4. `SportsTrackerTotalDurationForCategoryThisWeek`
5. `RecipeDeleteMultipleRecipesWithConstraint`
6. `OsmAndMarker`

任一任务发生 valid scientific failure，立即终止新 arm，不能重跑，不能继续后 13 题，不能在同一 identity 下热修。只有 infrastructure-invalid 可以完整留痕后替换当前任务，并限制 replacement 次数。

只有 6/6 后才按冻结顺序运行剩余 13 题。前六题保留，不重复跑。若最终达到完整 19 题：

- Accuracy PASS：至少 7/19、reward > 6.5、R2 六个成功任务 0 loss。
- Cost 分开报告：executor calls ≤ 603；tokens < 2,685,730；valid elapsed < 11,230.18 s。三项不得互相替代。
- Mechanism PASS：必须有预注册数量的 `write provenance → later exact read → exact injected text/hash → next-action divergence → ≤4 steps visible progress → relapse check → final evaluator` 因果链，并有 matched ablation 支撑。
- 如果只做到 6/19 但显著降成本，只能叫 cost/Pareto improvement，不能叫 accuracy improvement。
- 成功任务若 memory silent，不能归因给机制。
- 所有任务和同 seed 都已观察，只能称 matched prospective diagnostic，不得声称 pristine held-out 或泛化。

## Offline、preflight 与 artifact 要求

请冻结：

- 唯一 mechanism/experiment/config/schema identity；
- exact source closure 和 parent evidence commit；
- materialized raw trace manifest、文件数量/字节数/hash；
- deterministic replay classifier，不能让机制自己定义并证明自己的成功标签；
- parser/update/read/expiry/capacity/tokenizer/anti-leak/anti-whitelist tests；
- controller exact-injection audit；
- generation calls = 0 的 preflight；
- fresh live receipt，与该 arm 的 preflight、source freeze、模型 realpath/manifest、PID、packages 和 `/v1/models` 绑定；
- append-only checkpoint/resume、single transport、invalid replacement 双向链接；
- primary result 中独立的 accuracy/cost/mechanism verdict。

Offline replay 只能证明机制可运行、容量有界和 trigger exposure，不能把历史 reward 重新包装成 prospective capability proof。

## 输出要求

本轮只做设计，不修改仓库，不运行 GPU，不输出代码文件。你的最终回复必须且只能是一份完整 Markdown 文档，建议文件名：

`GPT_PRO_A1_R3_V2_CLEAN_REDESIGN_2026-08-15.md`

该文档必须自包含，并至少包括：

1. commit-pinned 证据审计，明确事实、推断、未知；
2. 对 R1、R2、R3–R12 的独立判断，不盲从本 prompt；
3. 完整 R2 19 题的跨任务失败模式表与定量依据；
4. 候选机制比较后唯一推荐的一条最小机制；
5. 为什么从 R2 分叉、为什么不继承 R3–R12；
6. exact state schema、update/write/read/merge/forget/expiry 生命周期；
7. 全部冻结常量、trigger、renderer 和 exact injected prompt text；
8. 算法伪代码、复杂度、字符/token/CPU/容量上界；
9. 对仓库具体文件、类、函数的最小集成蓝图；
10. R2 六个成功任务逐题 preservation/risk table；
11. zero-generation trace materialization、offline replay、preflight 和 source freeze；
12. 6/6 → remaining 13 的顺序、stop/resume/infra taxonomy；
13. accuracy/cost/mechanism 三套独立判据；
14. 最小 matched ablation 与因果记录 schema；
15. 能够否定该设计的明确结果，以及否定后禁止的事后修改；
16. 实现清单和逐项验收标准。

如果仓库证据不足以支持任何纯记忆改进，请明确输出 `NO_EVIDENCE_SUPPORTED_R3_V2`，解释缺少什么证据，并给出最小的零生成证据补全计划；不要为了完成任务而发明复杂机制。

所有输出只放在这一份 Markdown 中。
