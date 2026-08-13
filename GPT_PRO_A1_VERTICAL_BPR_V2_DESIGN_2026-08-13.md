# GPT_PRO_A1_VERTICAL_BPR_V2_DESIGN_2026-08-13.md

> **Repository**：`https://github.com/ScottBlizzard/RAVEN-M`  
> **Branch**：`a2-verified-progress-audit-20260810`  
> **唯一冻结审计 commit**：`3f1de08f3f936f1283ff4868a2be83cc211a63db`  
> **审计日期**：2026-08-13  
> **设计类型**：A1-R1 BPR v1 的严格窄幅 v2 修订  
> **Mechanism ID**：`a1r1_bounded_pending_receipt_v2`  
> **Primary experiment ID**：`A1R1_BPRV2_QWEN3VL32B_AW_HARD_T20260806_G3407_V1`  
> **Empty-read experiment ID**：`A1R1_BPRV2_EMPTYREAD_QWEN3VL32B_AW_HARD_T20260806_G3407_V1`  
> **Normative bundle SHA-256**：`61adeb079ac1b0ff286c5dff5e15ef258f3465ccbf9a888e161569d0e547fcb4`  
> **本轮执行边界**：仓库写入 `0`；GPU/model generation `0`；额外模型调用 `0`

---

## 0. 最终裁定

### 0.1 Commit 核验

已通过完整 commit URL 与 commit-pinned raw 文件核对，审计快照的完整 SHA **严格等于**：

```text
3f1de08f3f936f1283ff4868a2be83cc211a63db
```

该提交标题为 `evidence: audit BPR v1 against raw A1 traces`，父提交为 `43617f5`，提交中新增或更新的五个文件为：

1. `ARTIFACT_MANIFEST.md`
2. `GPT_PRO_A1_VERTICAL_BPR_V2_REVISION_REQUEST_2026-08-13.md`
3. `HANDOFF_2026-08-13.md`
4. `evidence/a1r1/A1R1_V1_DESIGN_AUDIT_2026-08-13.md`
5. `evidence/a1r1/A1R1_V1_RAW_TRACE_AUDIT_2026-08-13.json`

本文只把该 commit 及其明确引用的冻结历史证据作为仓库事实边界。未提交的本机原始树只通过已提交的哈希绑定审计结果被引用；本文不把未提交内容扩写成新的仓库事实。

### 0.2 三层版本裁定

| 对象 | 裁定 | 含义 |
|---|---|---|
| 冻结 v1：`a1r1_bounded_pending_receipt_v1` | **`A1R1_OFFLINE_QUALIFICATION_FAIL`，永久保持** | v1 R3 被完整 A1 原始树确定性击穿。不得修改 48 chars/72 bytes 后继续沿用 v1 mechanism、experiment、schema 或 artifact 身份。 |
| 新 v2 设计 | **`BPR_V2_DESIGN_FREEZE_GO`** | BPR 因果内核保留，只按新证据修改 cap、renderer budget、R3、R5 与所有受影响身份/哈希。 |
| 在审计 commit 上直接启动 live generation | **`NO-GO`** | 本轮没有 v2 implementation commit、source-freeze instance、v2 offline replay instance、zero-generation preflight instance 或 live receipt。设计完成不等于获准运行。 |

v2 的 `NO-GO` 不是对 BPR 机制的否定，而是对实验纪律的要求：未来实现只有在本文冻结的 source-freeze、replay 和 preflight 全部通过后，才可创建 live receipt 并按固定五题门运行。

### 0.3 唯一推荐机制

> **A1-R1 BPR v2 只保存一个由同一策略模型写出的“已经尝试、但仍未得到可见确认的任务状态改变”，以及一个能在当前 RGB 截图上确认该改变的可见事实；该 receipt 只在 source+1 至 source+4 的短窗口内最多注入两次，episode 最多八次，重复写不续期，同一 RGB 不重复注入，并把有效 `PEND[...]` 前缀从 ordinary history 精确剥离。**

v2 不是新机制。它没有 frontier、route、branch、failure signature、action-family recurrence、maturity score、planner、critic、verifier、RAG、额外模型调用或动作控制。与 v1 相比，运行时状态机、TTL、read cap、cooldown、same-RGB suppression、tombstone 和因果归因规则保持不变。

### 0.4 不允许的结论捷径

本文明确冻结以下解释边界：

- `memory read > 0` **不等于** memory 有效。
- memory-silent 的成功 **不得**归因给 memory。
- A1 RecipeDelete 的 source+1 时间关系是**结构性历史支持**，不是反事实有效性证明。
- A10-v2、A11、A12 的六题结果是 post-hoc diagnostic，不是 held-out evidence，也不修复 formal qualification failure。
- v2 R5 在 live 前保持 `PROSPECTIVE_UNKNOWN_PRELIVE`；不得用人工标签、任务规则、LLM/VLM 分类或合成 proof 把它伪装成 PASS。
- Accuracy、Cost、Mechanism 三种结论必须分别判定，任何一种都不能替代另外两种。

---

## 1. Source / evidence freeze

### 1.1 强制审计源

下表中的 `[S#]` 是本文内部引用标识；所有仓库路径均固定到 commit `3f1de08f3f936f1283ff4868a2be83cc211a63db`，历史 A1 实现另按其已冻结 commit `fbc25dc` 解释。

| ID | 路径或对象 | 作用 | 证据类别 |
|---|---|---|---|
| S0 | commit `3f1de08f3f936f1283ff4868a2be83cc211a63db` | 唯一审计快照与文件变更边界 | 冻结仓库事实 |
| S1 | `GPT_PRO_A1_VERTICAL_BPR_V2_REVISION_REQUEST_2026-08-13.md` | v2 必改项、禁止项、输出边界 | 冻结设计请求 |
| S2 | `evidence/a1r1/A1R1_V1_RAW_TRACE_AUDIT_2026-08-13.json` | 原始树哈希、514 条 pending 分布、success-tail、v1 gate verdict | 零生成、哈希绑定正式审计 |
| S3 | `evidence/a1r1/A1R1_V1_DESIGN_AUDIT_2026-08-13.md` | v1 failure、保留 BPR core、R5 不可识别边界 | 正式设计审计 |
| S4 | `evidence/diag6/A11_A12_DIAGNOSTIC6_RESULTS_2026-08-13.md` | A11/A12 六题终局与 read-causality | post-hoc diagnostic |
| S5 | `HANDOFF_2026-08-13.md` | 当前研究状态、A0/A1/A2、横向实验边界 | 冻结状态总表 |
| S6 | `ARTIFACT_MANIFEST.md` | 证据入口及 artifact 分类 | 冻结 manifest |
| S7 | `evidence/baseline/official_qwen32b_full_hard_combined_corrected_final.md` | A0 19 题基线 | 正式结果 |
| S8 | `evidence/a1/A1_ACTION_WORKING_MEMORY_RESULTS_2026-08-10.md` | A1 19 题结果与成本 | 正式结果 |
| S9 | `protocols/A1_ACTION_WORKING_MEMORY_PREREG_2026-08-10.md` | A1 预注册与 runtime identity | 正式协议 |
| S10 | `evidence/a2/A0_A1_PAIRED_REFERENCE_20260810.json` | A0/A1 逐任务配对 ledger 与 episode hashes | 冻结 reference |
| S11 | `implementation/src/raven_m/official_qwen_mobile/working_memory.py` | A1 六记录、duplicate refresh、无 TTL/read cap 的代码事实 | 冻结实现 |
| S12 | `implementation/src/raven_m/official_qwen_mobile/controller.py` | read-before-call、write-after-action、history hook | 冻结实现 |
| S13 | `implementation/src/raven_m/official_qwen_mobile/protocol.py` | official prompt、A1 prompt、action parser | 冻结实现 |
| S14 | A10-v2、A11、A12 design/binding/formal replay/reference/preflight | 三条横向机制的正式资格边界 | formal fail / protocol invalid |
| S15 | `protocols/ENRICHED_MEMORY_DIAGNOSTIC6_PROTOCOL_2026-08-13.md` | 六题 post-hoc 诊断定义 | post-hoc protocol |
| S16 | `evidence/diag6/A10V2_DIAGNOSTIC6_RESULT_2026-08-13.md` | A10-v2 六题结果 | post-hoc diagnostic |
| S17 | 本轮前一份 v1 文档 | SHA-256 `e248b8dbdeaaf49fd3d49dea6fd7270ea8f57443df8e080203c487942f2cfcbd`，69,820 bytes | 被审计设计，不是新仓库事实 |

### 1.2 已提交并冻结的正式事实

#### A0/A1 配对结果

| Arm | Full success | Reward | Calls | Total tokens | Elapsed |
|---|---:|---:|---:|---:|---:|
| A0 official baseline | 4/19 | 4.5 | 329 | 1,273,361 | 6,541.82036 s |
| A1 Action Working Memory | 5/19 | 5.5 | 603 | 3,464,267 | 14,595.491996 s |

A1 相对 A0：一题 paired gain、零 paired loss、18 ties；唯一新增 full success 为 `RecipeDeleteMultipleRecipesWithConstraint`。A1 冻结实现 commit 为 `fbc25dc`。A1 共记录：

```text
model calls                 = 603
executed actions            = 596
successful memory writes    = 515
non-empty memory reads      = 580
prompt tokens               = 3,376,888
completion tokens           = 87,379
reward                      = 5.5
```

这些数字只说明 A1 的结果与成本；不能由 580 次 read 推导出 580 次有效干预。

#### 原始 A1 树物化

[S2] 已提交的零生成审计冻结：

```text
suite_id                         = official_qwen_20260810T122419_26573d7c
aggregate_sha256                 = 7a4ebaad754802fcf3350e83ca13032a16de609f2904c96c7b5ecd0efc006f51
ledger_aggregate_sha256          = 7a4ebaad754802fcf3350e83ca13032a16de609f2904c96c7b5ecd0efc006f51
episode_directories              = 19
episode_json_files               = 19
episode_json_hash_mismatches     = 0
png_files                        = 1,199
all_files                        = 2,440
all_bytes                        = 381,429,354
raw_tree_committed               = false
generation_calls                 = 0
```

因此，“原始树不存在”已经不再是问题。需要保持的边界是：大树仍为本地、未提交；仓库中正式可引用的是其紧凑、哈希绑定审计结果。

### 1.3 v1 的确定性失败

[S2][S3] 对 514 条从有效 A1 `MEMORY[...]` 前缀抽取的 non-`none` `pending` 值给出：

| 统计 | 值 |
|---|---:|
| N | 514 |
| 同时满足 v1 `≤48 chars`、`≤72 UTF-8 bytes` | 365 |
| 覆盖率 | 71.011673% |
| chars P50 | 45 |
| chars P75 | 57 |
| chars P90 | 100 |
| chars P95 | 100 |
| chars P99 | 100 |
| chars max | 122 |
| UTF-8 bytes P95 | 100 |
| UTF-8 bytes max | 122 |

v1 R3 要求至少 P95 可装入 48 chars/72 bytes；实际只有 71.011673%。因此 v1 必须保持：

```text
A1R1_OFFLINE_QUALIFICATION_FAIL
live_generation_authorized = false
```

该失败否定的是 v1 cap 与 qualification binding，不是单 receipt 因果内核。

### 1.4 五个 A1 成功任务的 tail evidence

| Task | Step | Historical A1 pending | Chars/bytes | 冻结解释 |
|---|---:|---|---:|---|
| ExpenseDeleteMultiple2 | 17 | `confirm deletion of Bike Repairs` | 32/32 | success-tail payload |
| RecipeDeleteMultipleRecipesWithConstraint | 24 | `confirm deletion` | 16/16 | step 25 下一普通 call，terminal success，reward 1.0 |
| RetroSavePlaylist | 26 | `save playlist to Downloads directory` | 36/36 | success-tail payload |
| SimpleCalendarAddOneEvent | 33 | `dismiss disclaimer and save the event` | 37/37 | success-tail payload |
| SportsTrackerTotalDurationForCategoryThisWeek | 6 | `find weekly summary of mountain biking activities` | 49/49 | success-tail payload |

RecipeDelete 的关键事实严格写为：

```text
source step 24 historical pending
→ source+1 ordinary call at step 25 receives pending state
→ terminal success
→ final reward 1.0
```

这支持“短 source+1 机会在历史结构上存在”，但不证明未来 BPR `op/proof` 文本导致成功，也不证明同一 seed 下 no-read 会失败。

### 1.5 R5 的真实边界

旧 A1 `pending` 是自由 prose，并不等于未来 BPR 的：

```text
op=<one attempted state-changing operation>
proof=<one visible confirmation condition>
```

旧输出混合了导航、打开页面、等待、搜索、任务状态改变等内容。若要从旧 trace 重建未来 BPR write schedule，必须引入语义判断或反事实模型。以下方法全部禁止：

- 人工逐条标注；
- task/app-specific 规则；
- LLM/VLM 分类；
- 合成 `proof`；
- 把每条旧 pending 都当 BPR write；
- 乐观删除“看起来不重要”的 pending。

因此 v1 R5 不能 PASS。v2 将其冻结为：

```text
R5 = PROSPECTIVE_UNKNOWN_PRELIVE
```

并由固定五题 live gate 做前瞻性证伪。

### 1.6 A10-v2、A11、A12 的证据边界

| Arm | Formal status | Post-hoc six-task result | Actual reads | Productive divergence | Success attribution |
|---|---|---:|---:|---:|---|
| A10-v2 | formal offline qualification failure | 2/6 | 6 | 0 | 两个成功均 memory-silent |
| A11 | formal offline qualification failure | 2/6；reward 2.0；128 calls；489,910 tokens；3,147.675261 s | 4，位于两个失败 episode | 0 | RecipeDelete 与 Retro 成功，均 memory-silent |
| A12 | `A12_PROTOCOL_INVALID`，独立有效 reference 11/23 < 20/23 | 1/6；reward 1.0；158 calls；629,936 tokens；4,131.601948 s | 3，位于两个失败 episode | 0 | 唯一 Retro 成功 memory-silent |

A11 首个 `OsmAndTrack` attempt 是完整留痕的 infrastructure-invalid，随后用 fresh replacement；它不计科学结果。A11 顶层 `memory_active_episode_count=0` 是聚合 schema 未读取 nested mechanism record 的已知错误，原生 nested records 与 causal audit 恢复出四次真实 read；修正计数不改变结论。

联合结论只能是：

> A10-v2/A11/A12 能在部分 episode 注入 memory，但没有一个产生预注册 productive-divergence 信号；所有 read-active A11/A12 episode 失败，所有成功 memory-silent。

这正是 v2 必须使用完整因果链、而不能把 activation 当 effectiveness 的原因。

### 1.7 事实、推断、未知

| 陈述 | 分类 | 本文处理 |
|---|---|---|
| A1 原始树 19/19 episode hashes 匹配 aggregate | 已提交正式事实 | 可作为 v2 source material |
| v1 R3 失败 | formal qualification failure | 不可重命名为通过 |
| RecipeDelete source+1 opportunity | 结构性历史事实 | 只支持短窗口，不支持因果有效性 |
| A11/A12 六题结果 | post-hoc diagnostic | 不修复 formal arm，不是 held-out |
| BPR v2 的未来 op/proof write schedule | 未知 | live 前不得合成 |
| episode read cap=8 是否会提前耗尽 | prospective unknown | 五题 live gate 证伪 |
| BPR v2 是否使 calls/tokens/time 低于 A1 | 未知 | 完整 19 题后单独判 Cost |
| BPR v2 是否提高 accuracy | 未知 | 完整 19 题后单独判 Accuracy |
| BPR v2 某次 read 是否有效 | 未知，需 trace chain | 用第 15 节 productive-read 定义判定 |

---

## 2. v1 → v2 精确 delta table

除本表列出的变化外，v1 状态机和实验规则全部保持不变。

| 项目 | v1 冻结值 | v2 冻结值 | 新证据强制原因 |
|---|---|---|---|
| 审计 parent commit | `e1ba0b069011c54be902db5679cfa205d460435c` | `3f1de08f3f936f1283ff4868a2be83cc211a63db` | 新 commit 提交原始树审计与 A11/A12 终局 |
| v1 verdict | 当时待原始树资格验证 | **永久 `A1R1_OFFLINE_QUALIFICATION_FAIL`** | 365/514，仅 71.011673%，违反自身 R3 |
| Mechanism ID | `a1r1_bounded_pending_receipt_v1` | `a1r1_bounded_pending_receipt_v2` | 禁止静默调阈值 |
| Primary experiment | `A1R1_BPR_QWEN3VL32B_AW_HARD_T20260806_G3407_V1` | `A1R1_BPRV2_QWEN3VL32B_AW_HARD_T20260806_G3407_V1` | 新机制身份 |
| Empty-read experiment | `A1R1_BPR_EMPTYREAD_QWEN3VL32B_AW_HARD_T20260806_G3407_V1` | `A1R1_BPRV2_EMPTYREAD_QWEN3VL32B_AW_HARD_T20260806_G3407_V1` | 新机制身份 |
| `op` chars/bytes | 48 / 72 | **100 / 128** | committed chars P95=P99=100；v1 cap 明显过窄 |
| `proof` chars/bytes | 48 / 72 | **100 / 128** | 旧 pending 不能语义分配给 op/proof，故对称、无语义猜测 |
| cap 选择原则 | v1 未获原始分布支持 | chars 取 committed P95/P99 plateau 100；bytes 取覆盖 observed max 122 的 128 hard ceiling | 排除少量 >100-char prose，同时不让 UTF-8 byte bound 低于 observed max |
| renderer template | 不变 | **不变** | 模板不是 v1 failure 来源 |
| renderer template SHA | `007f...a01` | **相同** | 字节未变 |
| max rendered chars/read | 240 | **340** | `140 + 100 + 100` |
| max bytes/read | 320 | **396** | `140 + 128 + 128` |
| max tokens/read | 320 | **396** | tokenizer certificate：actual tokens ≤ UTF-8 bytes |
| max episode chars | 1,920 | **2,720** | 8 × 340 |
| max episode bytes/tokens | 2,560 / 2,560 | **3,168 / 3,168** | 8 × 396 |
| v1 suffix bytes/SHA | 681 / `1463f2a725fbfa1d672090d5c5a95e08bdef48d285dbf9f276e8e7fe7f58a0bb` | 686 / `6d399443083139e0aad8241cc0e4a949e311348a09d68c032397104e163d610b` | title 与 cap 文本新身份 |
| combined prompt bytes/SHA | 4,149 / `7da0fa69616a8fa0f56cfda3d671044d6b0c642c9eea740a2c0293dedca7618f` | 4,154 / `1692b3c67248307c6e0dc962e6f1ad65a5c3c4934ff1835a79681c34f0b8842e` | suffix 改动 |
| R3 | P95 必须 fit 48/72 | **在固定 N=514 上，`fit_count(≤100 chars ∧ ≤128 bytes) ≥489`**；并要求五个 success-tail 全 fit | 明确 denominator 与 integer pass threshold，禁止 percentile 实现歧义 |
| R3 当前状态 | FAIL | **尚未执行 v2 exact joint recount；不得预写 PASS** | committed summary 没有直接给 `100/128` joint fit count |
| R4 | Recipe key receipt source+1..+4 | **不变；已有 source+1 structural support** | 新证据支持短窗口 |
| R5 | 试图从旧 A1 映射未来 cap consumption | **`PROSPECTIVE_UNKNOWN_PRELIVE`；由固定 5 题 live gate 证伪** | 旧 pending ≠ 未来 op/proof schedule |
| A11/A12 状态 | v1 文档中尚在运行/未完成 | **A11 2/6、4 reads、productive 0；A12 1/6、3 reads、productive 0** | 新终局证据 |
| artifact identity | v1 路径/隐式 schema | **全部使用 `a1r1_v2/` 与 `a1r1_bpr_v2_*` 新身份** | 防止证据混用 |
| TTL/read/cooldown/same-RGB/tombstone | v1 values | **完全不变** | 新证据没有要求改动 |
| runtime components | 单 memory path | **完全不变** | 禁止无关扩展 |

为什么不是 48→122 chars 全覆盖：122 是 observed max，但 P95 与 P99 均为 100。v2 采用 100-char plateau 作为更紧的 bounded field，并用显式 95% integer gate 检查是否保留足够历史 payload envelope；超过 100 的少量长 prose 不自动获得运行时预算。UTF-8 byte cap 设为 128，覆盖 observed byte max 122，并保持硬上界。若 exact recount 低于 489，v2 直接 offline fail，不得再调到 122 并沿用 v2 身份。

---

## 3. 规范性 runtime boundary

BPR v2 必须保持：

- 模型：`Qwen/Qwen3-VL-32B-Instruct`
- model revision：`0cfaf48183f594c314753d30a4c4974bc75f3ccb`
- task seed：`20260806`
- generation seed：`3407`
- temperature：`0.7`
- top-p：`0.8`
- top-k：`20`
- presence penalty：`1.5`
- repetition penalty：`1.0`
- max output tokens：`32768`
- 同一 19 个 AndroidWorld Hard task instances、goal hashes、native step budgets
- current RGB screenshot only；context images 为空
- 每个普通决策恰好一次原模型 request
- transport attempt maximum `1`
- episode-local fresh memory state

BPR v2 唯一允许影响 action 的路径：

```text
deterministic episode-local BPR state
→ exact bounded renderer text
→ next ordinary user prompt
→ original Qwen model call
→ model selects ordinary mobile action
```

严格禁止：

- planner、critic、verifier、retriever、RAG、database、额外 agent；
- 额外模型调用、OCR、UI tree、accessibility tree、额外 screenshot 或 wait-for-observation；
- hidden evaluator、reward、future screenshot、future action；
- task name、app name、package name、foreground activity 白名单或分支；
- cross-episode donor 或 persistent memory；
- action override、block、guard、repair、forced termination；
- 增加 step budget；
- 训练、微调、在线阈值学习。

当前 RGB 永远覆盖旧 receipt。Receipt 是提醒，不是任务完成证明。

---

## 4. v2 identity、canonicalization 与哈希冻结

### 4.1 核心身份

```text
mechanism_id       = a1r1_bounded_pending_receipt_v2
prefix_id          = a1r1_bpr_v2_pend_prefix_v1
renderer_id        = a1r1_bpr_v2_renderer_v1
state_schema       = a1r1_bpr_v2_state_schema_v1
config_id          = a1r1_bpr_v2_qwen32b_aw_hard_t20260806_g3407_v1
primary_experiment = A1R1_BPRV2_QWEN3VL32B_AW_HARD_T20260806_G3407_V1
empty_read_arm     = A1R1_BPRV2_EMPTYREAD_QWEN3VL32B_AW_HARD_T20260806_G3407_V1
```

### 4.2 JSON canonicalization

所有 contract 和未来 JSON artifact 使用：

```text
encoding       = UTF-8
BOM            = forbidden
ensure_ascii   = false
sort_keys      = true
separators     = (",", ":")
instance file  = canonical JSON + exactly one trailing LF
self hash      = hash canonical object after omitting self_sha256
```

不得把 pretty-printed bytes 的 hash 与 canonical hash 混用。

### 4.3 已可冻结的 exact hashes

| 对象 | Canonical/UTF-8 bytes | SHA-256 |
|---|---:|---|
| official system prompt | 3468 | `9d060af15f62acb31b9fb197649ec001d4096491d7fb102de929316944b3e26d` |
| BPR v2 suffix | 686 | `6d399443083139e0aad8241cc0e4a949e311348a09d68c032397104e163d610b` |
| official + BPR v2 prompt | 4154 | `1692b3c67248307c6e0dc962e6f1ad65a5c3c4934ff1835a79681c34f0b8842e` |
| renderer literal template | 151 | `007f0000c3003ea452093b2fbfbcaacd3e0f4c326da85daf9e81a4d682427a01` |
| action-prefix contract | 779 | `881598942996eb546f0716b1a03be93518c3dae2333834ecfbf8d18418f26ad9` |
| renderer contract | 728 | `8320c69ef32dd0db42e7f05b5cad54dbf24b8c0bb3f89cd3e4ba68af83c37271` |
| state-schema contract | 1694 | `c715490277ea7a5e261709399d26ffa9c7b755c92562e4a43b33b75e66044f05` |
| mechanism contract | 2085 | `e3b7fa1ecd59a9a9c21eed21822fdf9c334b8b0d39bcd1a883bdc8e263ebd6bc` |
| task-manifest contract | 1145 | `0f1c31dd9924bf0eaa649063e6696d830413d2b9469d164522b15f8d3ce76206` |
| config contract | 1774 | `80de362d5a90bd5e3afed2f197131514fc10bbd8efc8c792873967c5d4341881` |
| artifact registry | 2241 | `0097d2a4720a073c85370672c71fc6a3dad05547422e85b7569e3c4044d3474f` |
| normative bundle | 1234 | `61adeb079ac1b0ff286c5dff5e15ef258f3465ccbf9a888e161569d0e547fcb4` |

### 4.4 未来 artifact hash 的诚实边界

source-freeze、offline replay、preflight、live receipt、checkpoint、result 和 causal-read 的**schema contract hashes**在本文冻结；它们未来的**instance SHA-256**必须等 exact bytes 真实生成后计算。本文不会伪造尚不存在的 instance hash。

| Artifact | Schema | Schema contract SHA-256 | 未来路径 |
|---|---|---|---|
| Source freeze | `a1r1_bpr_v2_source_freeze_v1` | `abd397ac57f6bbf392e7952a7decc804ebb1f88e189debe850db58633f02cf1a` | `evidence/a1r1_v2/A1R1_BPR_V2_SOURCE_FREEZE.json` |
| Offline replay | `a1r1_bpr_v2_offline_replay_v1` | `ac6ac093a7d084fe3869fc1d3acd8ee187eafb235c6bcfef44ecaf5f2cb577c5` | `evidence/a1r1_v2/A1R1_BPR_V2_OFFLINE_REPLAY_REPORT.json` |
| Preflight | `a1r1_bpr_v2_zero_generation_preflight_v1` | `040ed9e73e86b04ee104325855d146dfd318454f2269c9a43b6ceaff1c269a16` | `evidence/a1r1_v2/A1R1_BPR_V2_ZERO_GENERATION_PREFLIGHT.json` |
| Live receipt | `a1r1_bpr_v2_live_receipt_v1` | `31597dc608f39c7ab68c5657e7bb36635c43a630dd292ad352f264f45d2f2045` | `evidence/a1r1_v2/A1R1_BPR_V2_LIVE_RECEIPT.json` |
| Checkpoint | `a1r1_bpr_v2_checkpoint_v1` | `deaab57d63b52092c7d3dc0e34cc98528ee14eed758bf5ae34b763fe86f0221d` | `evidence/a1r1_v2/checkpoints/A1R1_BPR_V2_CHECKPOINT_<ordinal>.json` |
| Result | `a1r1_bpr_v2_result_v1` | `45f84c7000607172e8d86b5a20be1928789e82b35f410ac5d3a69358742c76a4` | `evidence/a1r1_v2/A1R1_BPR_V2_<PRIMARY|EMPTYREAD>_RESULT.json` |
| Causal reads | `a1r1_bpr_v2_causal_read_v1` | `ffcc20e4865c294e3a272d8ba65a59f20b661b2f045c34b40b25f3b24cea9d42` | `evidence/a1r1_v2/A1R1_BPR_V2_CAUSAL_READS.json` |

---

## 5. BPR v2 完整机制规范

### 5.1 Action prefix

每个 `Action:` 句子，包括 answer/terminate，必须以：

```text
PEND[op=<one still-unconfirmed operation or none>;proof=<one visible fact that would confirm it or none>] | <one concise UI imperative>
```

开头。

字段语义：

- `op`：本 Action 正在尝试、或此前已经尝试但尚未得到可见确认的**一个任务状态改变**。
- `proof`：当前或后续 RGB 截图中，能够直接确认 `op` 已生效的**一个可见事实**。
- `op=none;proof=none`：清除 active receipt。
- exactly-one-`none`：invalid pair；action 正常执行，history 只保留 imperative，memory state 不变。
- 导航、打开页面、等待、搜索本身不应建立 receipt；这条语义由模型提示约束，不由 controller semantic classifier 执行。

`proof` 不是 evaluator、verifier 或 reward。Controller 不判断 proof 是否满足。

### 5.2 Exact system suffix

以下文本开头恰好两个 LF，末尾恰好一个 LF：

```text


# A1-R1 bounded pending receipt v2

Begin every Action sentence, including answer or terminate steps, with exactly:
PEND[op=<one still-unconfirmed operation or none>;proof=<one visible fact that would confirm it or none>] | <one concise UI imperative>

Rules:
- Use non-none only for one task-state change attempted by this Action or still awaiting visible confirmation. Carry the same pair until confirmed; op=none;proof=none clears it.
- Each field: at most 100 characters and 128 UTF-8 bytes; no ], ;, |, or line break. Keep exact names and values.
- A click or page change is not proof.
- The current screenshot overrides the receipt. Never repeat solely because it says pending.
```

冻结：

```text
suffix bytes  = 686
suffix SHA-256 = 6d399443083139e0aad8241cc0e4a949e311348a09d68c032397104e163d610b
combined bytes = 4154
combined SHA-256 = 1692b3c67248307c6e0dc962e6f1ad65a5c3c4934ff1835a79681c34f0b8842e
```

### 5.3 Parser 与 normalization

Exact full-match regex：

```regex
^PEND\[op=(?P<op>[^\]\;\|\r\n]+);proof=(?P<proof>[^\]\;\|\r\n]+)\] \| (?P<imperative>\S(?:.*\S)?)$
```

对 `op` 和 `proof` 依次：

1. Unicode NFKC；
2. 全部 whitespace runs 折叠为一个 ASCII space；
3. strip；
4. 非空；
5. `len(codepoints) ≤ 100`；
6. `len(utf8_bytes) ≤ 128`；
7. 禁止 `]`、`;`、`|`、CR、LF、NUL 和 Unicode control characters。

Operation identity：

```text
op_key_sha256 =
SHA256(NFKC(op) → whitespace-collapse → strip → casefold → UTF-8)
```

禁止 stemming、embedding、同义词匹配、action-family normalization 或 task-specific parser。

### 5.4 Ordinary-history exact stripping

| Parse situation | Ordinary history | Memory state |
|---|---|---|
| valid non-none/non-none | 仅 `imperative` | 正常 write/update |
| valid none/none | 仅 `imperative` | clear |
| valid exactly-one-none | 仅 `imperative` | unchanged |
| invalid prefix/field/cap/empty imperative | 原始 `action_summary` | unchanged |

任何被接受、更新或用于 clear 的有效 `PEND[...]` 前缀不得进入 ordinary history。Memory renderer text也不得被复制进 ordinary history。这样直接消除 A1 同一内容在 history 与 injection 双重出现的问题。

### 5.5 Episode-local state

#### Active receipt：最多一个

| Field | Type | Rule |
|---|---|---|
| `receipt_id` | string | `bpr2_<first_source_step>_<op_key[:12]>` |
| `op` | string | ≤100 codepoints，≤128 UTF-8 bytes |
| `proof` | string | ≤100 codepoints，≤128 UTF-8 bytes |
| `op_key_sha256` | 64 hex | same-operation identity |
| `first_source_step` | int | duplicate 永不修改 |
| `expiry_before_read_step` | int | 固定 `first_source_step + 5` |
| `read_count` | 0..2 | 只统计 exact non-empty injection |
| `last_read_step` | int/null | 上次真实 read |
| `last_read_pixel_sha256` | hex/null | same-RGB suppression |
| `text_version_event_id` | string | provenance only |

#### Tombstone：最多一个

```text
op_key_sha256
retired_step
reason ∈ {
  explicit_clear,
  replacement,
  expiry,
  read_cap,
  episode_budget
}
```

Tombstone 不保存 op/proof 文本，不是 failure cache，不含 route、screen signature 或 action family。唯一作用：防止刚退休的 stale operation 被下一步原样写回并立即恢复注入。

#### Bounded counters

```text
read_call_count
nonempty_read_count
last_nonempty_read_step
injected_chars
injected_utf8_bytes
injected_model_token_upper_bound
write_attempt_count
write_accept_count
same_op_no_refresh_count
same_op_text_update_count
explicit_clear_count
replacement_count
expiry_count
same_rgb_suppression_count
cooldown_suppression_count
receipt_read_cap_count
episode_budget_suppression_count
refractory_reject_count
invalid_prefix_count
invalid_pair_count
```

State 内禁止无界 event list。完整 provenance 流式写入 episode log，不进入 resident memory。

### 5.6 Write lifecycle

Write 只在原普通 action 已执行且 controller 已拥有 before/after snapshot 后发生；不得为 write 增加 screenshot。

#### New operation

若 valid non-none pair 的 `op_key` 与 active 不同：

1. 若等于 tombstone key 且 `source_step - retired_step < 4`：memory write 被拒绝，action 不受影响。
2. 若有 active：旧 active 退休，reason=`replacement`。
3. 建立新 receipt：
   - `first_source_step = source_step`
   - `expiry_before_read_step = source_step + 5`
   - `read_count = 0`

#### Same op、same normalized text

```text
same_op_no_refresh
```

不改变 receipt ID、first source、TTL、read count、last-read fields 或 tombstone。

#### Same op、different proof/op surface text

允许更新 display text 与 `text_version_event_id`，但：

```text
first_source_step unchanged
expiry unchanged
read_count unchanged
receipt_id unchanged
```

这阻止模型用轻微改写 stale pending 来续命。

#### none/none

有 active 则退休为 tombstone，reason=`explicit_clear`；无 active 则 no-op clear。Controller 不判断 clear 是否正确；错误 clear 是科学行为。

#### Merge

不存在 merge。Different op 永远 replacement。不得形成列表、graph、frontier 或 multi-obligation state。

### 5.7 Read eligibility

在普通模型请求 step `r` 前，exact non-empty read 当且仅当：

```text
read_enabled == true
active exists
r < active.expiry_before_read_step
active.read_count < 2
episode.nonempty_read_count < 8
last_nonempty_read_step is None
    OR r - last_nonempty_read_step >= 2
active.last_read_pixel_sha256 is None
    OR current_rgb_sha256 != active.last_read_pixel_sha256
renderer fits remaining char/byte/token budgets
```

冻结解释：

- 首次机会可为 `source+1`。
- Receipt 只在 `source+1, +2, +3, +4` 四个普通请求中存活；在 `source+5` read 前过期。
- 两次 non-empty read 之间至少有一个 ordinary call 不注入 memory。
- 同一 receipt 在相同 current RGB hash 上不得再次注入。
- suppression 不延长 TTL。
- 只有 text 实际追加到下一 ordinary prompt 后，才消费 read count 与预算。
- 第二次真实 read 后立即退休，reason=`read_cap`。
- episode 达到八次后，active 退休，reason=`episode_budget`；后续 write 仍按 tombstone/reentry 规则处理，但不能再产生 non-empty read。

### 5.8 Renderer 与严格预算

Exact renderer：

```text
PENDING, NOT PROOF: {op}
VISIBLE PROOF NEEDED: {proof}
Current screenshot overrides this. Check it first; do not repeat solely because this is pending.
```

```text
template SHA-256 = 007f0000c3003ea452093b2fbfbcaacd3e0f4c326da85daf9e81a4d682427a01
fixed non-field chars/bytes = 140
```

Hard bounds：

```text
per-read chars  ≤ 140 + 100 + 100 = 340
per-read bytes  ≤ 140 + 128 + 128 = 396
per-read tokens ≤ 396
episode chars   ≤ 8 × 340 = 2,720
episode bytes   ≤ 8 × 396 = 3,168
episode tokens  ≤ 8 × 396 = 3,168
```

Token cap 不允许 runtime 调服务器 tokenizer。Zero-generation preflight 必须针对冻结 tokenizer revision 证明：

```text
actual_model_tokens(renderer_text, add_special_tokens=False)
≤ len(renderer_text.encode("utf-8"))
```

若该证书不能成立，preflight FAIL；不得现场调高 token cap。

### 5.9 全部冻结常量

| Constant | Value |
|---|---:|
| `MAX_ACTIVE_RECEIPTS` | 1 |
| `MAX_TOMBSTONES` | 1 |
| `OP_MAX_CODEPOINTS` | 100 |
| `OP_MAX_UTF8_BYTES` | 128 |
| `PROOF_MAX_CODEPOINTS` | 100 |
| `PROOF_MAX_UTF8_BYTES` | 128 |
| `MAX_RENDERED_CHARS_PER_READ` | 340 |
| `MAX_RENDERED_UTF8_BYTES_PER_READ` | 396 |
| `MAX_RENDERED_MODEL_TOKENS_PER_READ` | 396 |
| `MAX_NONEMPTY_READS_PER_RECEIPT` | 2 |
| `MAX_NONEMPTY_READS_PER_EPISODE` | 8 |
| `READ_COOLDOWN_ORDINARY_CALLS` | 1 intervening call |
| `RECEIPT_WINDOW` | source+1..source+4 |
| `EXPIRY_BEFORE_READ_STEP` | source+5 |
| `SAME_RGB_REINJECTION_PER_RECEIPT` | 0 |
| `REENTRY_ADMIT_DISTANCE` | `new_source-retired ≥4` |
| `MAX_EPISODE_INJECTED_CHARS` | 2,720 |
| `MAX_EPISODE_INJECTED_UTF8_BYTES` | 3,168 |
| `MAX_EPISODE_INJECTED_MODEL_TOKENS` | 3,168 |
| `MAX_CANONICAL_RESIDENT_STATE_BYTES` | 8,192 |
| `MAX_INCREMENTAL_HEAP_AFTER_WARMUP` | 65,536 |
| `READ_OR_OBSERVE_CPU_P99` | ≤2.0 ms |
| `READ_OR_OBSERVE_CPU_ABSOLUTE_MAX` | ≤10.0 ms |
| `ADDITIONAL_MODEL_CALLS` | 0 |
| `ADDITIONAL_SCREENSHOTS` | 0 |
| `ADDITIONAL_OCR_UI_TREE_CALLS` | 0 |

### 5.10 每个字段、阈值与观察问题的绑定

| 设计项 | 已观察 A1 问题 | 为什么更简单规则不够 |
|---|---|---|
| 一个 active receipt | A1 六条 recency records 与 3,000-char read path 扩张 context | 零 receipt 会删除 A1 唯一合理内核；多 receipt 重引入排序与累积 |
| `op` | 需要标识哪个 attempted state change 仍未确认 | 无 identity 无法 duplicate-no-refresh、expiry 或 tombstone |
| `proof` | stale pending 没有“看到什么才算完成”的显式条件 | 只存 op 会继续留下无清除语义的待办；controller verifier 又被禁止 |
| 100-char cap | v1 48-char 只覆盖 71.011673%；committed P95/P99=100 | 保持 48 必然失败；直接采用 max122 会为极少长 prose 永久扩大 char envelope |
| 128-byte cap | observed byte max122 | 72 已失败；只用 char cap 无法控制 UTF-8 与 token 上界 |
| duplicate no-refresh | A1 duplicate payload 会重建 source step，stale 可无限续命 | 只限制 slot 数但刷新 TTL，仍会长期强化 |
| same-op text update no-refresh | 模型可轻微改 proof 绕过 exact duplicate | 完全禁止更新会锁死错误 proof；文本可改但生命周期不变是最小折中 |
| source+1..+4 TTL | RecipeDelete 有 source+1 structural support；归因 horizon 为3/4步 | TTL=1 可能错过一次中间 UI；>4 不能获得短期机制 credit |
| 2 reads/receipt | 一次提醒可能被动态页错过；A1 近连续 read 明显过量 | 1 过脆；3+ 缺少正证据且加重强化 |
| 1-call cooldown | A1 580/603 接近逐调用注入 | cooldown=0 保留连续强化；更长可能使第二次机会落出 TTL |
| same-RGB suppression | stale loop 常表现为同屏重复 | 仅 TTL 仍允许同一截图收到两次相同 memory |
| 8 reads/episode | A1 平均 30.53 reads/episode；仅 per-receipt cap 可被新 op 绕过 | 无 episode cap 仍可不断 replacement |
| one tombstone, distance4 | expiry 后模型可能下一步原样重建 | 无 tombstone 可立即复活；永久 blacklist 又会破坏多对象任务 |
| exact history stripping | A1 `MEMORY[...]` 同时在 ordinary history 与 injection | 仅缩短 renderer 无法删除逐步累积的第二份副本 |
| 8 KiB / 2 ms | 本 arm 的主张是最小低成本 | 不冻结 resource ceiling 会允许隐性复杂组件 |
| zero added calls | A1 成本已大幅增加；用户禁止 extra agent/model | 只报告少调用而不 hard bind 无法归因 |

---

## 6. Normative pseudocode

```python
def normalize_field(text: str) -> str:
    value = unicode_nfkc(text)
    value = collapse_all_whitespace_to_ascii_space(value).strip()
    if not value:
        raise InvalidPrefix
    if len(value) > 100:
        raise InvalidPrefix
    if len(value.encode("utf-8")) > 128:
        raise InvalidPrefix
    if contains_forbidden_delimiter_or_control(value):
        raise InvalidPrefix
    return value


def parse_pend(action_summary: str):
    m = FROZEN_FULLMATCH_REGEX.fullmatch(action_summary)
    if m is None:
        return Parse(valid=False, history=action_summary)

    imperative = m["imperative"].strip()
    if not imperative:
        return Parse(valid=False, history=action_summary)

    try:
        op = normalize_field(m["op"])
        proof = normalize_field(m["proof"])
    except InvalidPrefix:
        return Parse(valid=False, history=action_summary)

    op_none = (op == "none")
    proof_none = (proof == "none")

    if op_none != proof_none:
        return Parse(
            valid=True,
            pair_valid=False,
            history=imperative,
        )

    return Parse(
        valid=True,
        pair_valid=True,
        clear=op_none,
        op=op,
        proof=proof,
        history=imperative,
    )


def history_summary(action_summary: str) -> str:
    return parse_pend(action_summary).history
```

```python
def observe_step(source_step, action_summary, canonical_action,
                 before, after, source_call_id, source_response_sha256):
    counters.write_attempt_count += 1
    parsed = parse_pend(action_summary)

    if not parsed.valid:
        counters.invalid_prefix_count += 1
        audit("invalid_prefix_state_unchanged")
        return

    if not parsed.pair_valid:
        counters.invalid_pair_count += 1
        audit("invalid_pair_state_unchanged")
        return

    if parsed.clear:
        retire_active_if_any(source_step, "explicit_clear")
        audit("explicit_clear")
        return

    key = sha256(canonicalize_for_op_key(parsed.op))

    if tombstone is not None and key == tombstone.op_key_sha256:
        if source_step - tombstone.retired_step < 4:
            counters.refractory_reject_count += 1
            audit("refractory_reject_state_unchanged")
            return

    if active is not None and key == active.op_key_sha256:
        if parsed.op == active.op and parsed.proof == active.proof:
            counters.same_op_no_refresh_count += 1
            audit("same_op_same_text_no_refresh")
            return

        active.op = parsed.op
        active.proof = parsed.proof
        active.text_version_event_id = fresh_event_id()
        counters.same_op_text_update_count += 1
        audit("same_op_text_update_no_refresh")
        return

    if active is not None:
        retire_active(source_step, "replacement")

    active = PendingReceipt(
        receipt_id=f"bpr2_{source_step}_{key[:12]}",
        op=parsed.op,
        proof=parsed.proof,
        op_key_sha256=key,
        first_source_step=source_step,
        expiry_before_read_step=source_step + 5,
        read_count=0,
        last_read_step=None,
        last_read_pixel_sha256=None,
        text_version_event_id=fresh_event_id(),
    )
    counters.write_accept_count += 1
    audit("new_receipt")
```

```python
def read(context, *, read_enabled: bool) -> str:
    r = counters.read_call_count
    current_rgb = context["before"]["pixel_sha256"]
    counters.read_call_count += 1

    # All goal/task/app/evaluator/future fields are ignored.

    if active is not None and r >= active.expiry_before_read_step:
        retire_active(r, "expiry")

    if not read_enabled:
        audit_read("empty_read_ablation")
        return ""
    if active is None:
        audit_read("no_active_receipt")
        return ""
    if active.read_count >= 2:
        audit_read("receipt_read_cap")
        return ""
    if counters.nonempty_read_count >= 8:
        retire_active(r, "episode_budget")
        audit_read("episode_read_cap")
        return ""
    if (
        counters.last_nonempty_read_step is not None
        and r - counters.last_nonempty_read_step < 2
    ):
        counters.cooldown_suppression_count += 1
        audit_read("cooldown")
        return ""
    if active.last_read_pixel_sha256 == current_rgb:
        counters.same_rgb_suppression_count += 1
        audit_read("same_rgb")
        return ""

    text = FROZEN_RENDERER.format(op=active.op, proof=active.proof)
    chars = len(text)
    bytes_ = len(text.encode("utf-8"))
    token_upper = bytes_

    if chars > 340 or bytes_ > 396 or token_upper > 396:
        raise ImplementationInvalid("renderer_bound_violation")
    if counters.injected_chars + chars > 2720:
        audit_read("episode_char_budget")
        return ""
    if counters.injected_utf8_bytes + bytes_ > 3168:
        audit_read("episode_byte_budget")
        return ""
    if counters.injected_model_token_upper_bound + token_upper > 3168:
        audit_read("episode_token_budget")
        return ""

    event = audit_exact_injection(
        receipt_id=active.receipt_id,
        text_version_event_id=active.text_version_event_id,
        exact_injected_text=text,
        exact_injected_text_sha256=sha256(text.encode("utf-8")),
        chars=chars,
        utf8_bytes=bytes_,
        model_token_upper_bound=token_upper,
        current_rgb_sha256=current_rgb,
    )

    active.read_count += 1
    active.last_read_step = r
    active.last_read_pixel_sha256 = current_rgb
    counters.last_nonempty_read_step = r
    counters.nonempty_read_count += 1
    counters.injected_chars += chars
    counters.injected_utf8_bytes += bytes_
    counters.injected_model_token_upper_bound += token_upper

    if active.read_count == 2:
        retire_active(r, "read_cap")

    return text


def reset_at_episode_boundary():
    active = None
    tombstone = None
    counters = zeroed_counters()
```

同一 episode 内禁止 reset 来绕过 cap、TTL 或 tombstone。

---

## 7. 静态成本边界

### 7.1 可证明的 memory-path 上界

A1 实测 non-empty reads 为 580。BPR v2 完整 19 题即使每题打满：

```text
19 × 8 = 152 non-empty reads maximum
580 - 152 = 428 fewer read events minimum
relative reduction = 73.793103%
```

Controller-authored memory injection 全套理论最大：

```text
chars  ≤ 19 × 2,720 = 51,680
bytes  ≤ 19 × 3,168 = 60,192
tokens ≤ 19 × 3,168 = 60,192  # conservative upper bound
```

与 A1 configured 3,000 chars/read 比较，v2 340 chars/read hard cap 低 88.666667%。BPR v2 suffix 为 686 bytes，A1 suffix 为 863 bytes，静态少 177 bytes，即 20.509849%。

额外运行时开销冻结为：

```text
additional model calls          = 0
additional screenshots          = 0
additional OCR/UI-tree calls    = 0
resident canonical state        ≤ 8,192 bytes
incremental heap after warmup    ≤ 65,536 bytes
read/observe CPU p99            ≤ 2.0 ms
read/observe CPU absolute max   ≤ 10.0 ms
```

### 7.2 不能静态预声明的成本结论

以下只能由完整 19 题 primary arm 实测：

- calls 是否 `<603`
- total tokens 是否 `<3,464,267`
- wall time 是否 `<14,595.491996 s`

Memory injection 上界更小不等于完整 Cost PASS，因为模型可能仍产生更多普通 calls、history 或 completion。任何预先声称“成本必然下降”的写法都不合格。

---

## 8. v2 zero-generation offline qualification

### 8.1 当前状态

[S2] 已证明原始 A1 source materialization 本身可用；但本文没有创建 v2 implementation 或 replay artifact。因此当前应写：

```text
v1_status = A1R1_OFFLINE_QUALIFICATION_FAIL
v2_offline_replay_status = NOT_EXECUTED
v2_live_generation_authorized = false
R5 = PROSPECTIVE_UNKNOWN_PRELIVE
```

不能把 committed P95/P99=100 自动写成 v2 R3 PASS，因为 exact joint count `chars≤100 AND bytes≤128` 尚未在 v2 artifact 中输出。

### 8.2 决定性 gate

未来 `A1R1_BPR_V2_OFFLINE_REPLAY_REPORT.json` 必须逐项报告：

| Gate | Type | Exact pass condition |
|---|---|---|
| R0 | decidable | `generation_calls == 0` |
| R1 | decidable | 19 episode dirs、19 JSON、0 mismatch；aggregate SHA 精确为 `7a4e...006f51`；重建 A1 calls/actions/writes/reads/tokens/reward |
| R2 | decidable | 五个 success-tail pending 全部满足 `≤100 chars ∧ ≤128 bytes`；基于 committed audit 预期为 5/5，但 replay 必须重算 |
| R3-v2 | decidable | denominator 固定为全部 514 historical non-none pending；`fit(v)=chars(v)≤100 ∧ utf8(v)≤128`；要求 `fit_count ≥ ceil(0.95×514)=489` |
| R4 | decidable | RecipeDelete step24→step25 source+1 opportunity 精确重建；只标 `STRUCTURAL_HISTORICAL_SUPPORT` |
| R5-v2 | **prospective** | 必须精确输出 `PROSPECTIVE_UNKNOWN_PRELIVE`；不得计入 offline PASS/FAIL；不得建立旧 A1→未来 BPR semantic mapping |
| R6 | decidable engineering | synthetic state-machine tests：duplicate no-refresh、source+5 expiry、2-read cap、same-RGB suppression、reentry distance4、episode cap8 全 PASS |
| R7 | decidable engineering | renderer ≤340 chars/396 bytes/396 tokens；episode ≤2720/3168/3168；tokenizer certificate PASS |
| R8 | decidable engineering | 每 episode theoretical reads ≤8；19题 ≤152 |
| R9 | decidable | valid prefix 只留 imperative；invalid prefix 保持 raw；non-memory action semantics 不变 |
| R10 | decidable | replay/implementation 不读取 task/app/hidden UI/evaluator/future data；无额外模型调用 |
| R11 | decidable | exact identities、prompt hashes、contract hashes、source hashes 全匹配本文 |

Offline status function：

```text
PASS iff:
  every decidable gate R0,R1,R2,R3,R4,R6,R7,R8,R9,R10,R11 passes
  AND R5 is exactly PROSPECTIVE_UNKNOWN_PRELIVE
  AND errors == []
```

`R5=PASS` 反而是 protocol error，因为 live 前没有合法证据把它判为 PASS。

若 R3 `fit_count<489`：`A1R1_BPR_V2_OFFLINE_QUALIFICATION_FAIL`；不得把 cap 改为 101、122 或其他值后沿用 v2 identity。

### 8.3 R5 的 live falsification

固定前五题共同承担 prospective operational adequacy 检验：

```text
Gate 1: A0 四个成功任务必须 4/4
Gate 2: RecipeDelete 必须成功
```

状态更新：

- 五题全部 valid 且 5/5：`R5_NOT_FALSIFIED_ON_GATE5`
- 任一 valid scientific failure：`R5_FALSIFIED_ON_GATE5`，停止，不运行剩余14题
- infrastructure-invalid：按第 13 节替代，不更新 R5
- 5/5 不等于“R5 已被证明普适”，只说明本预注册五题未证伪

同时报告每题：

```text
write attempts / accepted writes
duplicate no-refresh
receipt expiry
same-RGB suppression
cooldown suppression
nonempty reads
episode cap suppression
field-cap invalid prefixes
```

不得在看到这些计数后调 cap、TTL 或 read budget。

### 8.4 Source+1 的使用边界

RecipeDelete 的 source+1 事实只用于 R4。它不能用于：

- 声称 read 导致 terminal success；
- 声称 future BPR 会写同一 receipt；
- 声称 empty-read 会失败；
- 调整 task-specific TTL；
- 给 RecipeDelete 白名单或特殊 renderer。

---

## 9. Source freeze、preflight 与 artifact pipeline

### 9.1 新 implementation source freeze

未来实现 commit 必须：

1. 以 `3f1de08f3f936f1283ff4868a2be83cc211a63db` 为 ancestry boundary；
2. working tree clean；
3. 不修改冻结 A1 commit `fbc25dc` 的历史身份；
4. 冻结 design、binding、BPR module、protocol suffix、controller integration、runner/config、tests、replay script 的 exact path/bytes/SHA；
5. 冻结本文 normative bundle SHA：
   `"61adeb079ac1b0ff286c5dff5e15ef258f3465ccbf9a888e161569d0e547fcb4"`；
6. 冻结 raw A1 aggregate SHA：
   `7a4ebaad754802fcf3350e83ca13032a16de609f2904c96c7b5ecd0efc006f51`；
7. `generation_calls=0`；
8. source manifest 不包含正在生成的 source-freeze JSON 本身。

Source-freeze instance 未生成前，不能创建 preflight 或 live receipt。

### 9.2 Zero-generation preflight

Preflight 必须全部通过：

#### Identity

- implementation commit、source-freeze SHA、offline replay SHA 匹配；
- model/revision、sampling、task/generation seeds 匹配；
- task instance/goal hashes、native step budgets 匹配；
- official prompt、suffix、combined prompt hashes匹配；
- primary/empty-read experiment IDs匹配；
- transport maximum=1。

#### Static/unit

- 第 10 节 test matrix 全 PASS；
- prefix/renderer/state/mechanism/config/task/artifact-registry hashes匹配；
- tokenizer certificate PASS；
- exact field boundary tests PASS；
- source+5 expiry、duplicate no-refresh、same-RGB、cooldown、read caps PASS；
- history stripping PASS；
- fresh episode reset PASS。

#### Runtime isolation

- fake model client 证明每 ordinary step 恰好一个 `generate()`；
- additional model calls=0；
- additional screenshot/OCR/UI-tree calls=0；
- current RGB hash 是唯一外部 read eligibility 输入；
- mutation task/app/goal/evaluator/hidden fields 不改变 state、read text 或 hash；
- memory 不修改 canonical action、mapped action、执行顺序或 terminal；
- AST/import scan 无 planner、critic、verifier、retriever、database、guard；
- no cross-episode serialization。

#### Resource benchmark

建议固定：

```text
warmup operations   = 1,000
measured operations = 10,000
serialized state    ≤ 8,192 UTF-8 bytes
incremental heap    ≤ 65,536 bytes
p99 read/observe    ≤ 2.0 ms
absolute max        ≤ 10.0 ms
```

Benchmark 失败即 preflight FAIL，不得以“相比模型调用很小”忽略。

### 9.3 Live receipt

必须在第一次 generation 前写入并哈希：

```text
implementation_commit
source_freeze_sha256
offline_replay_sha256
preflight_sha256
config_sha256
task_manifest_sha256
model_id / model_revision / server_model_id
sampling and seeds
system_prompt_sha256
mechanism_id
experiment_id
read_enabled
additional_model_calls=0
transport_attempt_max=1
created_before_first_generation=true
```

任何 mismatch：fail-closed。

### 9.4 Checkpoint 与 resume

每完成一个 valid episode 或记录一个 infrastructure-invalid attempt 后创建 append-only checkpoint。Checkpoint 必须保存 attempt hash chain、valid ordinals、invalid attempts、gate state、aggregate-so-far、source hashes 和 stop reason。

Resume 仅在以下完全相同的前提下允许：

```text
implementation/source/preflight/config/model/server/sampling/seeds/task manifest
```

Valid scientific episode 永不替代。Resume 不能绕过已经触发的 gate stop。

### 9.5 Result artifact

Primary result 必须在完整19题或预注册 stop 后冻结；empty-read result 单独冻结。Result 不能把 ablation 成本并入 primary 19题成本，也不能把 memory-silent success 计入 mechanism credit。

---

## 10. Test matrix

### 10.1 Prefix/parser/history

| Test | Expected |
|---|---|
| 100 ASCII chars field | accept |
| 101 ASCII chars | reject |
| 128 UTF-8 bytes | accept |
| 129 UTF-8 bytes | reject |
| NFKC 后超 cap | reject after normalization |
| `] ; | CR LF NUL control` | reject |
| exactly one `none` | valid prefix, invalid pair, imperative-only history, state unchanged |
| none/none | imperative-only history, clear |
| missing prefix | raw history, state unchanged |
| valid prefix | `PEND[...]` bytes absent from ordinary history |
| empty imperative | invalid, raw history |
| case-only op change | same op key; no lifetime refresh |
| whitespace-only op change | same op key; no lifetime refresh |

### 10.2 Lifecycle

| Test | Expected |
|---|---|
| first new pair at source s | active, expiry=s+5, read_count=0 |
| exact duplicate at s+1 | source/expiry/read budget unchanged |
| same op, changed proof | text version changes only |
| different op | old becomes tombstone, new active |
| reentry distance 0..3 | reject memory write |
| reentry distance 4 | admit |
| read at s+1 | eligible if other conditions pass |
| read at s+5 | expired before read |
| second nonempty read | returned then retire |
| third read attempt | empty |
| same RGB after first read | empty; no TTL extension |
| cooldown next ordinary call | empty |
| eight episode reads | exact max |
| ninth opportunity | empty, episode-budget reason |
| episode reset | active/tombstone/counters zero |

### 10.3 Renderer/budget/token

- Template SHA exact。
- Empty placeholders fixed portion 140 chars/bytes。
- Max legal fields produce ≤340 chars and ≤396 bytes。
- No legal renderer output is truncated。
- Episode sum cannot exceed 2720/3168/3168。
- Frozen tokenizer exhaustive/boundary corpus verifies tokens≤bytes。
- Runtime code performs no tokenizer network/model call。

### 10.4 Source replay

- 19/19 episode JSON hash match。
- aggregate SHA exact。
- 514 denominator exact。
- `fit_count_100_128` exact integer output。
- required threshold exact integer 489。
- five success-tail strings and source steps exact。
- Recipe step24→25 exact。
- No hand labels or semantic mapping field exists。
- R5 literal status equals `PROSPECTIVE_UNKNOWN_PRELIVE`。

### 10.5 Controller integration

- `read()` exactly once before each ordinary model request。
- `observe_step()` only after executed ordinary action。
- memory text only appended to ordinary prompt。
- valid prefix stripped before history accumulation。
- canonical action identical with/without memory path when model response bytes identical。
- read-disabled arm differs only in returned injection text and resulting prompt hash。
- task/app/hidden/evaluator mutation leaves memory output unchanged。
- additional calls/screens/OCR/UI-tree all zero。

### 10.6 Artifact integrity

- 每个 schema contract hash 匹配第4节。
- 每个 future instance self hash 按 omission rule 重算。
- checkpoint attempt chain 无断裂。
- result task order精确等于 task manifest。
- live receipt 早于首个 generation timestamp。
- v1 artifact 不得被 v2 覆盖或改写。

---

## 11. 固定 live 运行顺序与停止规则

### 11.1 Primary Gate 1：必须 4/4

1. `ExpenseDeleteMultiple2`
2. `RetroSavePlaylist`
3. `SimpleCalendarAddOneEvent`
4. `SportsTrackerTotalDurationForCategoryThisWeek`

四个 valid episode 必须全部 full success。任一 scientific failure：

```text
stop immediately
do not run RecipeDelete
do not run remaining 14
do not retune
```

### 11.2 Primary Gate 2：必须保住 A1 唯一 gain

5. `RecipeDeleteMultipleRecipesWithConstraint`

必须 full success。失败则立即停止，不运行剩余14题。

### 11.3 剩余 14 题

只有前五题 5/5 才按以下顺序运行：

6. `BrowserMultiply`
7. `ExpenseAddMultipleFromGallery`
8. `ExpenseAddMultipleFromMarkor`
9. `MarkorCreateNoteAndSms`
10. `MarkorMergeNotes`
11. `MarkorTranscribeVideo`
12. `OsmAndMarker`
13. `OsmAndTrack`
14. `RecipeAddMultipleRecipesFromImage`
15. `RecipeAddMultipleRecipesFromMarkor`
16. `RecipeAddMultipleRecipesFromMarkor2`
17. `SaveCopyOfReceiptTaskEval`
18. `SportsTrackerActivitiesOnDate`
19. `SportsTrackerTotalDistanceForCategoryOverInterval`

不得按早期结果重排。

### 11.4 Scientific failure 不得重跑

以下均为 valid scientific outcome：

- reward 0；
- wrong model action；
- parse error；
- premature terminate；
- max-step exit；
- memory silent；
- valid read 但 action 不变；
- divergence 后无 progress；
- field cap 使模型 prefix invalid；
- 模型错误 clear 或 stale write。

这些都不允许 replacement。

### 11.5 Infrastructure-invalid replacement

只有满足完整留痕的基础设施异常才可 fresh replacement，例如：

- emulator/device reset 失败；
- transport connection reset，导致调用结果是否返回不可判；
- server crash；
- episode log/checkpoint 损坏到无法判定动作或 evaluator；
- external harness failure。

必须保存 invalid attempt 的全部可得证据，记录：

```text
attempt_id
task ordinal
failure timestamp
last confirmed call/action
transport records
episode path/hash
reason
replacement_attempt_id
bidirectional link
scientific_score = null
```

整个 primary arm 最多允许 **2 次** infrastructure replacements。第三次 invalid：`RUN_INFRASTRUCTURE_ABORT`。已有有效 scientific episode 永不替代。

### 11.6 Protocol/implementation invalid

发现下列任一项立即关闭整个 arm：

- prompt/config/source hash 漂移；
- hidden/future/task/app branching；
- extra model/screenshot/OCR/UI-tree call；
- memory action control；
- cap、TTL、read/cooldown/same-RGB 实现不符；
- valid prefix 仍进入 ordinary history；
- state 跨 episode 泄漏；
- live receipt 不存在或晚于首个 generation；
- result/checkpoint hash chain 损坏。

修复必须新 implementation/source freeze；若改变本文 normative contract，则必须新 mechanism version。

---

## 12. Failure taxonomy

| Label | 定义 | 是否重跑 | 是否计科学结果 |
|---|---|---:|---:|
| `SCIENTIFIC_FAILURE` | 有效环境/模型执行下 reward0或任务失败 | 否 | 是 |
| `INFRASTRUCTURE_INVALID` | 外部执行/transport/log失效，科学结果不可判 | 仅按规则替代 | 否 |
| `IMPLEMENTATION_INVALID` | BPR 实现违反 frozen contract | 否；停止 arm | 否 |
| `PROTOCOL_INVALID` | 运行顺序、identity、gate、artifact 等违反协议 | 否；停止 arm | 否 |
| `SOURCE_MATERIALIZATION_FAIL` | source hashes/aggregate不能重建 | 否；live NO-GO | 否 |
| `A1R1_OFFLINE_QUALIFICATION_FAIL` | 某 frozen v1/v2 decidable replay gate失败 | 否；该版本关闭 | 否 |
| `PROSPECTIVE_UNKNOWN` | live 前无法无语义猜测判定的未来行为 | 不适用 | 不是 PASS/FAIL |
| `MECHANISM_CENSORED` | read 后窗口因 episode终止/infra失效不足以判因果 | 否 | 不计 productive |
| `MEMORY_SILENT_SUCCESS` | 成功 episode 无 nonempty read | 否 | Accuracy 可计；Mechanism 不计 |
| `ACTIVATION_WITHOUT_PRODUCTIVE_DIVERGENCE` | 有 read，但完整 productive chain不成立 | 否 | 不能称 memory有效 |
| `PARETO_COST_ONLY` | 5/19且成本显著低于A1，无 accuracy gain | 否 | 只称成本/Pareto改善 |

---

## 13. 完整因果归因链

每次候选 productive read 必须有：

```text
write provenance
→ later exact nonempty read
→ exact injected text/hash
→ next action divergence
→ visible escape/progress within 3/4 steps
→ relapse check
→ final evaluator
```

### 13.1 Write provenance

必须记录：

```text
write_event_id
receipt_id
text_version_event_id
source_step
source_call_id
source_response_sha256
source_action_summary_sha256
source_prefix_sha256
source_canonical_action_sha256
source_before_pixel_sha256
source_after_pixel_sha256
normalized_op
normalized_proof
op_key_sha256
write_kind
state_sha256_before
state_sha256_after
```

### 13.2 Later exact nonempty read

必须链接同一 `receipt_id` 与正确 `text_version_event_id`，并记录：

```text
read_step / call_id
exact_injected_text
exact_injected_text_sha256
chars / utf8_bytes / actual_model_tokens
prompt_sha256
ordinary_history_sha256
current_rgb_sha256
receipt read_count before/after
all suppression/budget counters
```

只记录 state 被 read 不够；必须证明 exact nonempty bytes 进入该 normal request。

### 13.3 Next action divergence

Primary read 后的下一 model decision 必须与 exact matched empty-read counterfactual 不同，或者在没有 exact match 时，只能标记：

```text
DIVERGENCE_UNRESOLVED
```

不得用与历史 A0/A1“看起来不同”的动作代替 exact match。Divergence 比较至少包含：

```text
raw response hash
canonical decision hash
canonical action
terminal status
```

### 13.4 Visible escape within 3

若 read 前存在 exact repeated loop，read 后最多三个 executed actions 内必须离开该 exact loop。Exact loop 只能由已记录的 pixel/action hashes定义，不得由人工“感觉卡住”定义。

### 13.5 Visible proof/progress within 4

read 后最多四个 executed actions 内，当前 RGB 必须提供任务相关、可见且 trace-grounded 的进展或 proof。它不能来自 hidden evaluator，也不能把任意 page transition 叫 progress。

事后审计可由两名独立审计者按 frozen visible-evidence rubric 编码；分歧则该 read 不计 productive。该人工审计只用于结果归因，不参与 runtime、write/read eligibility 或 action。

### 13.6 Relapse check

在 progress 后接下来的最多四个 executed actions 内：

- 不回到同一 exact loop；
- 不重新建立同一 stale receipt 并重复原动作；
- 若 episode 更早正常结束，则检查至结束。

窗口不完整且无法判定时：`MECHANISM_CENSORED`。

### 13.7 Final evaluator

必须报告 episode final reward/full success，但 final success 本身不能把缺失的 divergence/progress 链补齐。相反，productive divergence 后最终失败也必须如实报告。

### 13.8 `trace_grounded_productive_read` 定义

一个 read 只有在以下全部满足时计数：

1. implementation chain 完整；
2. exact nonempty injection 已证明；
3. next action divergence 已由 exact counterfactual 支持；
4. `visible_escape_within_3` 或 `visible_progress_or_proof_within_4` 成立；
5. relapse check PASS；
6. 非 censored；
7. 若只依赖 exact escape，则该 episode final full success；
8. 证据不来自 future runtime information。

Read、write、screen change 或成功中的任何单项均不够。

### 13.9 Mechanism PASS threshold

完整 primary 19题与 ablation 完成后：

```text
productive_read_count                    ≥ 3
productive_episode_count                 ≥ 2
productive_read_from_full_success_episode ≥ 1
exact_matched_empty_read_support_count    ≥ 1
```

四项必须同时满足。该阈值保持 v1 不变。

---

## 14. Minimal no-read / empty-read ablation

### 14.1 唯一差异

Ablation 使用：

```text
same v2 mechanism implementation
same system prompt and PEND output contract
same parser/write/update/clear
same ordinary-history stripping
same TTL/cooldown/same-RGB/tombstone/counters
same model/revision/sampling/seeds/task instances
read_enabled = false
```

`read()` 每个 ordinary call 仍执行 deterministic state maintenance，但永远返回 empty string。它不增加 runtime component 或模型调用。

### 14.2 运行时机与任务

只有 primary 完整运行19题后，才允许按固定顺序运行五题 empty-read：

1. ExpenseDeleteMultiple2
2. RetroSavePlaylist
3. SimpleCalendarAddOneEvent
4. SportsTrackerTotalDurationForCategoryThisWeek
5. RecipeDeleteMultipleRecipesWithConstraint

Ablation 的 calls/tokens/wall 单独报告，不并入 primary Cost。

### 14.3 Exact matched pre-call opportunity

要称 exact matched，primary 与 empty-read 在目标 call 前必须一致：

```text
task instance and goal hash
task/generation seeds
model/revision/sampling/system prompt
ordinary call ordinal
current RGB SHA-256
ordinary history SHA-256
prior canonical action sequence hash
active BPR state SHA-256
source implementation/config hashes
```

唯一差异：

```text
primary prompt appends exact memory renderer
empty-read prompt appends empty string
```

若任何字段不同：

```text
MATCH_UNAVAILABLE
```

禁止 nearest-screen、语义相似或人工挑选近似 trace。

### 14.4 Matched counterfactual support

一个 matched pair 支持 causal read，当且仅当：

- primary next decision/action diverges；
- primary read 满足 productive-read chain；
- empty-read 没有同样的3/4步 visible progress，或 relapse，或最终失败；
- 两侧均非 infrastructure/protocol invalid。

该 ablation 不改变 primary 运行，也不允许逐步在线配对或额外调用。

---

## 15. 三种独立结论

### 15.1 Accuracy

只在 primary 完整19题后判定：

```text
full_successes ≥ 6        # strictly >5/19
reward > 5.5
A1 five successful tasks all remain full successes
```

A1 五个必须无 paired loss：

- ExpenseDeleteMultiple2
- RetroSavePlaylist
- SimpleCalendarAddOneEvent
- SportsTrackerTotalDurationForCategoryThisWeek
- RecipeDeleteMultipleRecipesWithConstraint

任何一项不满足：Accuracy FAIL。

### 15.2 Cost

只在 primary 完整19题后判定：

```text
calls      < 603
tokens     < 3,464,267
wall time  < 14,595.491996 seconds
```

三项全部严格低于 A1 才是 Cost PASS。静态 renderer 上界不能替代。

### 15.3 Mechanism

只按第13节数量门判定。Accuracy PASS 不自动带来 Mechanism PASS；Cost PASS 也不自动带来 Mechanism PASS。

### 15.4 合法组合用语

| Accuracy | Cost | Mechanism | 允许结论 |
|---|---|---|---|
| PASS | PASS | PASS | accuracy、cost 与 trace-grounded mechanism 均改善 |
| PASS | PASS | FAIL | 结果与成本改善，但 BPR 因果解释未被支持 |
| PASS | FAIL | 任意 | accuracy improvement only；成本主张失败 |
| FAIL，恰5/19 | PASS | 任意 | **Pareto/cost improvement only**，不得称 accuracy improvement |
| FAIL，<5/19或 A1 paired loss | 任意 | 任意 | accuracy 退化/未保留 A1 |
| 任意 | 任意 | PASS | 只说明达到预注册 productive-read 证据；不能代替 accuracy/cost |

---

## 16. 显式可证伪条件

### 16.1 Live 前否定 v2

任一成立即 v2 offline fail：

- R3 exact count `<489/514`；
- 五个 success-tail 任一不 fit；
- Recipe source+1 timeline不能重建；
- tokenizer certificate失败；
- duplicate refresh、same-RGB、TTL、cap、history stripping任一单测失败；
- extra call/hidden/task/app/future leakage；
- resource ceiling失败；
- source/prompt/config/schema hash不匹配；
- replay把 R5 写成 PASS 或使用 semantic mapping。

### 16.2 五题门否定前瞻性可用性

- Gate1 非4/4；
- RecipeDelete失败；
- 任一 A1 成功任务出现 paired loss。

Valid failure不得重跑。出现即停止。

### 16.3 完整19题否定 Accuracy/Cost

- full success≤5；
- reward≤5.5；
- A1五成功任一 loss；
- calls≥603；
- tokens≥3,464,267；
- wall≥14,595.491996 s。

### 16.4 否定 Mechanism

任一即可使 Mechanism FAIL：

- productive reads<3；
- productive episodes<2；
- 无 full-success episode productive read；
- 无 exact matched empty-read support；
- 所有成功 memory-silent；
- read-active episode无 productive divergence；
- 只有 activation，没有完整链；
- 证据依赖未来信息或近似匹配。

A11/A12 已经展示“有真实 read、但 productive=0”的可行失败模式，v2 必须允许该结果，而不能修改归因定义。

---

## 17. 最终冻结结论

### 17.1 机制

冻结且仅冻结：

```text
A1-R1 BPR v2
= one active receipt
+ at most one short tombstone
+ model-authored op/proof
+ duplicate no-refresh
+ source+1..+4 TTL
+ max 2 reads/receipt
+ max 8 reads/episode
+ one-call cooldown
+ same-RGB suppression
+ exact history stripping
+ prompt-only influence
+ zero extra model calls
```

### 17.2 本次仅有的实质修订

```text
48 chars / 72 bytes
→ 100 chars / 128 bytes

R3 ambiguous percentile fit
→ fixed N=514, exact joint fit count ≥489

R5 unverifiable replay claim
→ PROSPECTIVE_UNKNOWN_PRELIVE
→ fixed five-task live falsification

all affected IDs/hashes/artifact schemas
→ new v2 identities
```

没有其他机制扩展。

### 17.3 当前行动状态

```text
v1:
  A1R1_OFFLINE_QUALIFICATION_FAIL
  immutable
  no live

v2 design:
  BPR_V2_DESIGN_FREEZE_GO

v2 live at commit 3f1de08:
  NO-GO
  reason:
    no v2 implementation commit
    no v2 source-freeze instance
    no v2 offline replay instance
    no v2 zero-generation preflight instance
    no live receipt
```

未来只有在所有 decidable offline gates通过、R5诚实保持 prospective unknown、preflight授权后，才可按固定五题顺序开始 primary live run。

---

## Appendix A. Canonical contracts

### A.1 Action-prefix contract

```json
{
  "field_caps": {
    "op_max_unicode_codepoints": 100,
    "op_max_utf8_bytes": 128,
    "proof_max_unicode_codepoints": 100,
    "proof_max_utf8_bytes": 128
  },
  "forbidden": [
    "]",
    ";",
    "|",
    "CR",
    "LF",
    "NUL",
    "unicode_control"
  ],
  "normalization": [
    "unicode_nfkc",
    "collapse_all_whitespace_to_single_ascii_space",
    "strip"
  ],
  "ordinary_history": {
    "invalid_prefix": "raw_action_summary",
    "valid_prefix": "imperative_only",
    "valid_prefix_invalid_pair": "imperative_only_state_unchanged"
  },
  "pair_rules": {
    "exactly_one_none": "invalid_pair_state_unchanged",
    "non_none_non_none": "candidate_write",
    "none_none": "clear_active"
  },
  "prefix_id": "a1r1_bpr_v2_pend_prefix_v1",
  "regex": "^PEND\\[op=(?P<op>[^\\]\\;\\|\\r\\n]+);proof=(?P<proof>[^\\]\\;\\|\\r\\n]+)\\] \\| (?P<imperative>\\S(?:.*\\S)?)$",
  "schema": "a1r1_bpr_v2_action_prefix_schema_v1"
}
```

SHA-256：

```text
881598942996eb546f0716b1a03be93518c3dae2333834ecfbf8d18418f26ad9
```

### A.2 Renderer contract

```json
{
  "encoding": "utf-8",
  "field_caps": {
    "op_max_unicode_codepoints": 100,
    "op_max_utf8_bytes": 128,
    "proof_max_unicode_codepoints": 100,
    "proof_max_utf8_bytes": 128
  },
  "rendered_caps": {
    "max_model_tokens_per_read": 396,
    "max_unicode_codepoints_per_read": 340,
    "max_utf8_bytes_per_read": 396
  },
  "renderer_id": "a1r1_bpr_v2_renderer_v1",
  "schema": "a1r1_bpr_v2_renderer_contract_v1",
  "template": "PENDING, NOT PROOF: {op}\nVISIBLE PROOF NEEDED: {proof}\nCurrent screenshot overrides this. Check it first; do not repeat solely because this is pending.",
  "template_sha256": "007f0000c3003ea452093b2fbfbcaacd3e0f4c326da85daf9e81a4d682427a01",
  "token_bound": "frozen_tokenizer_actual_tokens<=utf8_bytes;zero_generation_certificate_required",
  "truncation": "forbidden"
}
```

SHA-256：

```text
8320c69ef32dd0db42e7f05b5cad54dbf24b8c0bb3f89cd3e4ba68af83c37271
```

### A.3 State-schema contract

```json
{
  "active_receipt": {
    "cardinality": "0_or_1",
    "fields": {
      "expiry_before_read_step": {
        "duplicate_mutable": false,
        "formula": "first_source_step+5",
        "type": "nonnegative_int"
      },
      "first_source_step": {
        "duplicate_mutable": false,
        "type": "nonnegative_int"
      },
      "last_read_pixel_sha256": {
        "type": "null_or_lowercase_hex64"
      },
      "last_read_step": {
        "type": "null_or_nonnegative_int"
      },
      "op": {
        "max_unicode_codepoints": 100,
        "max_utf8_bytes": 128,
        "type": "string"
      },
      "op_key_sha256": {
        "type": "lowercase_hex64"
      },
      "proof": {
        "max_unicode_codepoints": 100,
        "max_utf8_bytes": 128,
        "type": "string"
      },
      "read_count": {
        "counts": "exact_nonempty_injections_only",
        "type": "int_0_to_2"
      },
      "text_version_event_id": {
        "audit_only": true,
        "type": "string"
      }
    },
    "receipt_id": "bpr2_<first_source_step>_<op_key_sha256_prefix12>"
  },
  "canonical_resident_state_max_utf8_bytes": 8192,
  "manager_counters": [
    "read_call_count",
    "nonempty_read_count",
    "last_nonempty_read_step",
    "injected_chars",
    "injected_utf8_bytes",
    "injected_model_token_upper_bound",
    "write_attempt_count",
    "write_accept_count",
    "same_op_no_refresh_count",
    "same_op_text_update_count",
    "explicit_clear_count",
    "replacement_count",
    "expiry_count",
    "same_rgb_suppression_count",
    "cooldown_suppression_count",
    "receipt_read_cap_count",
    "episode_budget_suppression_count",
    "refractory_reject_count",
    "invalid_prefix_count",
    "invalid_pair_count"
  ],
  "mechanism_id": "a1r1_bounded_pending_receipt_v2",
  "reset": "fresh_state_at_episode_start_only",
  "schema": "a1r1_bpr_v2_state_schema_v1",
  "scope": "episode_local_deterministic",
  "tombstone": {
    "cardinality": "0_or_1",
    "fields": [
      "op_key_sha256",
      "retired_step",
      "reason"
    ],
    "reason_enum": [
      "explicit_clear",
      "replacement",
      "expiry",
      "read_cap",
      "episode_budget"
    ],
    "retains_text": false
  },
  "unbounded_event_list": "forbidden"
}
```

SHA-256：

```text
c715490277ea7a5e261709399d26ffa9c7b755c92562e4a43b33b75e66044f05
```

### A.4 Mechanism contract

```json
{
  "action_override_block_guard_forced_termination": "forbidden",
  "additional_model_calls": 0,
  "additional_ocr_ui_tree_calls": 0,
  "additional_screenshots": 0,
  "budgets": {
    "canonical_resident_state_max_utf8_bytes": 8192,
    "episode_max_model_tokens": 3168,
    "episode_max_unicode_codepoints": 2720,
    "episode_max_utf8_bytes": 3168,
    "incremental_heap_after_warmup_max_bytes": 65536,
    "per_read_max_model_tokens": 396,
    "per_read_max_unicode_codepoints": 340,
    "per_read_max_utf8_bytes": 396,
    "read_or_observe_cpu_absolute_max_ms": 10.0,
    "read_or_observe_cpu_p99_ms": 2.0
  },
  "components": {
    "prefix_contract_sha256": "881598942996eb546f0716b1a03be93518c3dae2333834ecfbf8d18418f26ad9",
    "renderer_contract_sha256": "8320c69ef32dd0db42e7f05b5cad54dbf24b8c0bb3f89cd3e4ba68af83c37271",
    "state_schema_sha256": "c715490277ea7a5e261709399d26ffa9c7b755c92562e4a43b33b75e66044f05"
  },
  "cross_episode_state": "forbidden",
  "history": {
    "accepted_memory_text_may_coexist_in_ordinary_history": false,
    "invalid_prefix": "store_raw_action_summary",
    "valid_memory_prefix": "remove_exactly_store_imperative_only"
  },
  "influence_path": "prompt_context_on_next_ordinary_model_request_only",
  "mechanism_id": "a1r1_bounded_pending_receipt_v2",
  "observation_precedence": "current_rgb_screenshot_overrides_receipt",
  "planner_critic_verifier_retriever_database": "forbidden",
  "read": {
    "cooldown": "at_least_one_intervening_ordinary_call",
    "expiry_before": "source_plus_5",
    "max_nonempty_reads_per_episode": 8,
    "max_nonempty_reads_per_receipt": 2,
    "read_enabled_empty_read_ablation": false,
    "read_enabled_primary": true,
    "same_rgb_reinjection_per_receipt": 0,
    "window": "source_plus_1_through_source_plus_4"
  },
  "schema": "a1r1_bpr_v2_mechanism_contract_v1",
  "task_or_app_branching": "forbidden",
  "truncation": "forbidden",
  "write": {
    "accepted_pair": "non_none_op_and_non_none_visible_proof",
    "author": "same_policy_model_action_prefix",
    "different_op": "replace_active_and_retire_old",
    "duplicate_same_op_changed_text": "text_only_update_no_ttl_or_read_budget_refresh",
    "duplicate_same_op_same_text": "state_unchanged_no_refresh",
    "none_none": "clear_active",
    "reentry_admit_condition": "new_source_step-retired_step>=4"
  }
}
```

SHA-256：

```text
e3b7fa1ecd59a9a9c21eed21822fdf9c334b8b0d39bcd1a883bdc8e263ebd6bc
```

### A.5 Task-manifest contract

```json
{
  "gates": {
    "expansion": {
      "authorized_only_after_gate1_and_gate2": true,
      "ordinals": [
        6,
        7,
        8,
        9,
        10,
        11,
        12,
        13,
        14,
        15,
        16,
        17,
        18,
        19
      ]
    },
    "gate1": {
      "ordinals": [
        1,
        2,
        3,
        4
      ],
      "required_full_successes": "4_of_4"
    },
    "gate2": {
      "ordinals": [
        5
      ],
      "required_full_successes": "1_of_1"
    }
  },
  "require_exact_task_instance_and_goal_hash_match": true,
  "run_order": [
    "ExpenseDeleteMultiple2",
    "RetroSavePlaylist",
    "SimpleCalendarAddOneEvent",
    "SportsTrackerTotalDurationForCategoryThisWeek",
    "RecipeDeleteMultipleRecipesWithConstraint",
    "BrowserMultiply",
    "ExpenseAddMultipleFromGallery",
    "ExpenseAddMultipleFromMarkor",
    "MarkorCreateNoteAndSms",
    "MarkorMergeNotes",
    "MarkorTranscribeVideo",
    "OsmAndMarker",
    "OsmAndTrack",
    "RecipeAddMultipleRecipesFromImage",
    "RecipeAddMultipleRecipesFromMarkor",
    "RecipeAddMultipleRecipesFromMarkor2",
    "SaveCopyOfReceiptTaskEval",
    "SportsTrackerActivitiesOnDate",
    "SportsTrackerTotalDistanceForCategoryOverInterval"
  ],
  "schema": "a1r1_bpr_v2_task_manifest_v1",
  "source": "evidence/a2/A0_A1_PAIRED_REFERENCE_20260810.json",
  "source_a1_aggregate_sha256": "7a4ebaad754802fcf3350e83ca13032a16de609f2904c96c7b5ecd0efc006f51",
  "suite": "AndroidWorld_Hard_frozen_first_seed",
  "task_seed": 20260806
}
```

SHA-256：

```text
0f1c31dd9924bf0eaa649063e6696d830413d2b9469d164522b15f8d3ce76206
```

### A.6 Config contract

```json
{
  "a1_frozen_commit": "fbc25dc",
  "additional_model_calls": 0,
  "additional_ocr_ui_tree_calls": 0,
  "additional_screenshots": 0,
  "audit_commit": "3f1de08f3f936f1283ff4868a2be83cc211a63db",
  "combined_system_prompt_sha256": "1692b3c67248307c6e0dc962e6f1ad65a5c3c4934ff1835a79681c34f0b8842e",
  "config_id": "a1r1_bpr_v2_qwen32b_aw_hard_t20260806_g3407_v1",
  "context_images": "empty",
  "empty_read_experiment_id": "A1R1_BPRV2_EMPTYREAD_QWEN3VL32B_AW_HARD_T20260806_G3407_V1",
  "mechanism_contract_sha256": "e3b7fa1ecd59a9a9c21eed21822fdf9c334b8b0d39bcd1a883bdc8e263ebd6bc",
  "mechanism_id": "a1r1_bounded_pending_receipt_v2",
  "model": {
    "id": "Qwen/Qwen3-VL-32B-Instruct",
    "revision": "0cfaf48183f594c314753d30a4c4974bc75f3ccb"
  },
  "native_step_budget": "unchanged",
  "observation": "current_rgb_screenshot_only",
  "official_system_prompt_sha256": "9d060af15f62acb31b9fb197649ec001d4096491d7fb102de929316944b3e26d",
  "prefix_contract_sha256": "881598942996eb546f0716b1a03be93518c3dae2333834ecfbf8d18418f26ad9",
  "primary_experiment_id": "A1R1_BPRV2_QWEN3VL32B_AW_HARD_T20260806_G3407_V1",
  "read_enabled_by_arm": {
    "A1R1_BPRV2_EMPTYREAD_QWEN3VL32B_AW_HARD_T20260806_G3407_V1": false,
    "A1R1_BPRV2_QWEN3VL32B_AW_HARD_T20260806_G3407_V1": true
  },
  "renderer_contract_sha256": "8320c69ef32dd0db42e7f05b5cad54dbf24b8c0bb3f89cd3e4ba68af83c37271",
  "sampling": {
    "generation_seed": 3407,
    "max_output_tokens": 32768,
    "presence_penalty": 1.5,
    "repetition_penalty": 1.0,
    "temperature": 0.7,
    "top_k": 20,
    "top_p": 0.8
  },
  "schema": "a1r1_bpr_v2_config_v1",
  "state_schema_sha256": "c715490277ea7a5e261709399d26ffa9c7b755c92562e4a43b33b75e66044f05",
  "system_suffix_sha256": "6d399443083139e0aad8241cc0e4a949e311348a09d68c032397104e163d610b",
  "task_manifest_sha256": "0f1c31dd9924bf0eaa649063e6696d830413d2b9469d164522b15f8d3ce76206",
  "task_seed": 20260806,
  "transport_attempt_max": 1
}
```

SHA-256：

```text
80de362d5a90bd5e3afed2f197131514fc10bbd8efc8c792873967c5d4341881
```

### A.7 Artifact registry

```json
{
  "arm_ids": {
    "empty_read": "A1R1_BPRV2_EMPTYREAD_QWEN3VL32B_AW_HARD_T20260806_G3407_V1",
    "primary": "A1R1_BPRV2_QWEN3VL32B_AW_HARD_T20260806_G3407_V1"
  },
  "canonicalization": {
    "bom": false,
    "encoding": "utf-8",
    "ensure_ascii": false,
    "self_hash_rule": "compute canonical object with self_sha256 omitted",
    "separators": [
      ",",
      ":"
    ],
    "sort_keys": true,
    "trailing_lf_for_instance_files": true
  },
  "future_instance_hash_policy": "UNBOUND_UNTIL_EXACT_ARTIFACT_BYTES_EXIST;never_fabricate",
  "mechanism_id": "a1r1_bounded_pending_receipt_v2",
  "schema": "a1r1_bpr_v2_artifact_registry_v1",
  "schemas": {
    "causal_read": {
      "path": "evidence/a1r1_v2/A1R1_BPR_V2_CAUSAL_READS.json",
      "schema": "a1r1_bpr_v2_causal_read_v1",
      "schema_contract_bytes": 982,
      "schema_contract_sha256": "ffcc20e4865c294e3a272d8ba65a59f20b661b2f045c34b40b25f3b24cea9d42"
    },
    "checkpoint": {
      "path": "evidence/a1r1_v2/checkpoints/A1R1_BPR_V2_CHECKPOINT_<ordinal>.json",
      "schema": "a1r1_bpr_v2_checkpoint_v1",
      "schema_contract_bytes": 621,
      "schema_contract_sha256": "deaab57d63b52092c7d3dc0e34cc98528ee14eed758bf5ae34b763fe86f0221d"
    },
    "live_receipt": {
      "path": "evidence/a1r1_v2/A1R1_BPR_V2_LIVE_RECEIPT.json",
      "schema": "a1r1_bpr_v2_live_receipt_v1",
      "schema_contract_bytes": 745,
      "schema_contract_sha256": "31597dc608f39c7ab68c5657e7bb36635c43a630dd292ad352f264f45d2f2045"
    },
    "offline_replay": {
      "path": "evidence/a1r1_v2/A1R1_BPR_V2_OFFLINE_REPLAY_REPORT.json",
      "schema": "a1r1_bpr_v2_offline_replay_v1",
      "schema_contract_bytes": 802,
      "schema_contract_sha256": "ac6ac093a7d084fe3869fc1d3acd8ee187eafb235c6bcfef44ecaf5f2cb577c5"
    },
    "preflight": {
      "path": "evidence/a1r1_v2/A1R1_BPR_V2_ZERO_GENERATION_PREFLIGHT.json",
      "schema": "a1r1_bpr_v2_zero_generation_preflight_v1",
      "schema_contract_bytes": 834,
      "schema_contract_sha256": "040ed9e73e86b04ee104325855d146dfd318454f2269c9a43b6ceaff1c269a16"
    },
    "result": {
      "path": "evidence/a1r1_v2/A1R1_BPR_V2_<PRIMARY|EMPTYREAD>_RESULT.json",
      "schema": "a1r1_bpr_v2_result_v1",
      "schema_contract_bytes": 683,
      "schema_contract_sha256": "45f84c7000607172e8d86b5a20be1928789e82b35f410ac5d3a69358742c76a4"
    },
    "source_freeze": {
      "path": "evidence/a1r1_v2/A1R1_BPR_V2_SOURCE_FREEZE.json",
      "schema": "a1r1_bpr_v2_source_freeze_v1",
      "schema_contract_bytes": 708,
      "schema_contract_sha256": "abd397ac57f6bbf392e7952a7decc804ebb1f88e189debe850db58633f02cf1a"
    }
  }
}
```

SHA-256：

```text
0097d2a4720a073c85370672c71fc6a3dad05547422e85b7569e3c4044d3474f
```

### A.8 Normative bundle

```json
{
  "R5_status": "PROSPECTIVE_UNKNOWN_PRELIVE",
  "audit_commit": "3f1de08f3f936f1283ff4868a2be83cc211a63db",
  "component_hashes": {
    "artifact_registry_sha256": "0097d2a4720a073c85370672c71fc6a3dad05547422e85b7569e3c4044d3474f",
    "combined_system_prompt_sha256": "1692b3c67248307c6e0dc962e6f1ad65a5c3c4934ff1835a79681c34f0b8842e",
    "config_sha256": "80de362d5a90bd5e3afed2f197131514fc10bbd8efc8c792873967c5d4341881",
    "mechanism_contract_sha256": "e3b7fa1ecd59a9a9c21eed21822fdf9c334b8b0d39bcd1a883bdc8e263ebd6bc",
    "prefix_contract_sha256": "881598942996eb546f0716b1a03be93518c3dae2333834ecfbf8d18418f26ad9",
    "renderer_contract_sha256": "8320c69ef32dd0db42e7f05b5cad54dbf24b8c0bb3f89cd3e4ba68af83c37271",
    "state_schema_sha256": "c715490277ea7a5e261709399d26ffa9c7b755c92562e4a43b33b75e66044f05",
    "system_suffix_sha256": "6d399443083139e0aad8241cc0e4a949e311348a09d68c032397104e163d610b",
    "task_manifest_sha256": "0f1c31dd9924bf0eaa649063e6696d830413d2b9469d164522b15f8d3ce76206"
  },
  "mechanism_id": "a1r1_bounded_pending_receipt_v2",
  "schema": "a1r1_bpr_v2_normative_bundle_v1",
  "v1_immutable_verdict": "A1R1_OFFLINE_QUALIFICATION_FAIL",
  "v2_design_status": "DESIGN_FREEZE_GO",
  "v2_live_status_at_audit_commit": "NO_GO_PENDING_NEW_IMPLEMENTATION_SOURCE_FREEZE_REPLAY_PREFLIGHT"
}
```

SHA-256：

```text
61adeb079ac1b0ff286c5dff5e15ef258f3465ccbf9a888e161569d0e547fcb4
```

---

## Appendix B. Future artifact minimum fields

### B.1 Source freeze

```json
{
  "artifact_id": "A1R1_BPR_V2_SOURCE_FREEZE",
  "invariants": [
    "audit_commit_exact",
    "implementation_commit_descends_from_audit_commit",
    "working_tree_clean_true",
    "generation_calls_zero",
    "raw_a1_aggregate_sha256_exact",
    "all_source_file_sha256_present",
    "self_hash_omits_self_sha256_field"
  ],
  "path": "evidence/a1r1_v2/A1R1_BPR_V2_SOURCE_FREEZE.json",
  "required_fields": [
    "schema",
    "artifact_id",
    "created_at_utc",
    "audit_commit",
    "implementation_commit",
    "working_tree_clean",
    "a1_frozen_commit",
    "design_file",
    "design_sha256",
    "normative_bundle_sha256",
    "source_files",
    "task_manifest_sha256",
    "system_prompt_sha256",
    "config_sha256",
    "raw_a1_source_manifest",
    "generation_calls",
    "self_sha256"
  ],
  "schema": "a1r1_bpr_v2_source_freeze_v1"
}
```

### B.2 Offline replay

```json
{
  "artifact_id": "A1R1_BPR_V2_OFFLINE_REPLAY",
  "invariants": [
    "generation_calls_zero",
    "R3_denominator_514",
    "R3_fit_count_at_least_489_under_100_chars_128_bytes",
    "R5_exactly_PROSPECTIVE_UNKNOWN_PRELIVE",
    "no_semantic_mapping_of_a1_pending_to_future_bpr_writes",
    "status_pass_only_if_all_decidable_gates_pass_and_no_errors",
    "self_hash_omits_self_sha256_field"
  ],
  "path": "evidence/a1r1_v2/A1R1_BPR_V2_OFFLINE_REPLAY_REPORT.json",
  "required_fields": [
    "schema",
    "artifact_id",
    "source_freeze_sha256",
    "generation_calls",
    "source_reconstruction",
    "historical_pending_envelope",
    "success_tail",
    "recipe_source_plus_one",
    "synthetic_lifecycle_tests",
    "history_dedup_tests",
    "renderer_tests",
    "tokenizer_certificate",
    "decidable_gates",
    "prospective_unknowns",
    "errors",
    "status",
    "self_sha256"
  ],
  "schema": "a1r1_bpr_v2_offline_replay_v1"
}
```

### B.3 Zero-generation preflight

```json
{
  "artifact_id": "A1R1_BPR_V2_ZERO_GENERATION_PREFLIGHT",
  "invariants": [
    "generation_calls_zero",
    "all_required_tests_pass",
    "additional_model_calls_zero",
    "additional_screenshots_zero",
    "additional_ocr_ui_tree_calls_zero",
    "no_task_app_or_future_information_branching",
    "live_generation_authorized_true_iff_no_errors",
    "self_hash_omits_self_sha256_field"
  ],
  "path": "evidence/a1r1_v2/A1R1_BPR_V2_ZERO_GENERATION_PREFLIGHT.json",
  "required_fields": [
    "schema",
    "artifact_id",
    "source_freeze_sha256",
    "offline_replay_sha256",
    "generation_calls",
    "source_identity",
    "runtime_identity",
    "prompt_hashes",
    "config_hashes",
    "unit_tests",
    "integration_tests",
    "tokenizer_certificate",
    "resource_benchmark",
    "forbidden_dependency_scan",
    "empty_read_differential_test",
    "errors",
    "live_generation_authorized",
    "self_sha256"
  ],
  "schema": "a1r1_bpr_v2_zero_generation_preflight_v1"
}
```

### B.4 Live receipt

```json
{
  "artifact_id": "A1R1_BPR_V2_LIVE_RECEIPT",
  "invariants": [
    "created_before_first_generation_true",
    "all_hashes_match_preflight",
    "additional_model_calls_zero",
    "transport_attempt_max_one",
    "self_hash_omits_self_sha256_field"
  ],
  "path": "evidence/a1r1_v2/A1R1_BPR_V2_LIVE_RECEIPT.json",
  "required_fields": [
    "schema",
    "artifact_id",
    "arm",
    "experiment_id",
    "implementation_commit",
    "source_freeze_sha256",
    "offline_replay_sha256",
    "preflight_sha256",
    "config_sha256",
    "task_manifest_sha256",
    "model_id",
    "model_revision",
    "server_model_id",
    "sampling",
    "task_seed",
    "generation_seed",
    "system_prompt_sha256",
    "mechanism_id",
    "read_enabled",
    "additional_model_calls",
    "transport_attempt_max",
    "created_before_first_generation",
    "self_sha256"
  ],
  "schema": "a1r1_bpr_v2_live_receipt_v1"
}
```

### B.5 Checkpoint

```json
{
  "artifact_id": "A1R1_BPR_V2_CHECKPOINT",
  "invariants": [
    "append_only_attempt_chain",
    "valid_episode_never_replaced",
    "scientific_failure_never_rerun",
    "infrastructure_replacements_at_most_two",
    "self_hash_omits_self_sha256_field"
  ],
  "path_pattern": "evidence/a1r1_v2/checkpoints/A1R1_BPR_V2_CHECKPOINT_<ordinal>.json",
  "required_fields": [
    "schema",
    "artifact_id",
    "arm",
    "experiment_id",
    "checkpoint_ordinal",
    "completed_attempts",
    "valid_episode_ordinals",
    "infrastructure_invalid_attempts",
    "gate_state",
    "aggregate_so_far",
    "attempt_hash_chain_head",
    "resume_source_hashes",
    "stop_reason",
    "self_sha256"
  ],
  "schema": "a1r1_bpr_v2_checkpoint_v1"
}
```

### B.6 Result

```json
{
  "artifact_id": "A1R1_BPR_V2_RESULT",
  "invariants": [
    "three_verdicts_independent",
    "memory_silent_success_not_attributed",
    "read_not_equated_with_effectiveness",
    "full19_required_for_accuracy_and_cost",
    "self_hash_omits_self_sha256_field"
  ],
  "path_pattern": "evidence/a1r1_v2/A1R1_BPR_V2_<PRIMARY|EMPTYREAD>_RESULT.json",
  "required_fields": [
    "schema",
    "artifact_id",
    "arm",
    "experiment_id",
    "live_receipt_sha256",
    "task_results_in_frozen_order",
    "attempt_ledger",
    "aggregate",
    "paired_vs_a1",
    "read_write_counts",
    "injection_costs",
    "failure_taxonomy_counts",
    "accuracy_verdict",
    "cost_verdict",
    "mechanism_verdict",
    "prospective_R5_verdict",
    "protocol_validity",
    "self_sha256"
  ],
  "schema": "a1r1_bpr_v2_result_v1"
}
```

### B.7 Causal reads

```json
{
  "artifact_id": "A1R1_BPR_V2_CAUSAL_READS",
  "invariants": [
    "read_alone_not_productive",
    "future_information_forbidden",
    "matched_trace_requires_exact_precall_state",
    "self_hash_omits_self_sha256_field"
  ],
  "path": "evidence/a1r1_v2/A1R1_BPR_V2_CAUSAL_READS.json",
  "read_event_required_fields": [
    "write_provenance",
    "later_exact_nonempty_read",
    "receipt_id",
    "text_version_event_id",
    "exact_injected_text",
    "exact_injected_text_sha256",
    "chars",
    "utf8_bytes",
    "model_tokens",
    "prompt_sha256",
    "ordinary_history_sha256",
    "current_rgb_sha256",
    "next_action_divergence",
    "visible_escape_within_3",
    "visible_progress_or_proof_within_4",
    "relapse_check_within_4",
    "final_evaluator",
    "censored",
    "productive_read",
    "matched_empty_read_counterfactual"
  ],
  "required_fields": [
    "schema",
    "artifact_id",
    "experiment_id",
    "read_events",
    "productive_read_count",
    "productive_episode_count",
    "full_success_productive_read_count",
    "matched_empty_read_support_count",
    "mechanism_verdict",
    "self_sha256"
  ],
  "schema": "a1r1_bpr_v2_causal_read_v1"
}
```
