# GPT_PRO_A11_STANDALONE_MEMORY_DESIGN_2026-08-12.md

> **文档性质**：A11 唯一规范性机制设计、实现绑定、zero-generation 资格门与前瞻性实验预注册  
> **文档日期**：2026-08-12  
> **父证据分支**：`a2-verified-progress-audit-20260810`  
> **父证据提交**：`4548b932bc3b189507e1442e312c73c8f35dbdb8`  
> **原 A10-v1 文档**：`GPT_PRO_A10_STANDALONE_MEMORY_DESIGN_2026-08-12.md`  
> **A10-v1 正式回放报告**：`evidence/a10/A10_OFFLINE_REPLAY_REPORT.json`  
> **A10-v1 正式裁定**：`PROTOCOL QUALIFICATION FAILURE — LIVE GENERATION NOT AUTHORIZED`  
> **A11 机制名称**：确认式路线收缩义务—分支前沿记忆  
> **英文名称**：Confirmed Route-Contraction Evidence-Calibrated Obligation–Branch Frontier Memory  
> **缩写**：CRC-ECOBF  
> **Mechanism ID**：`a11_confirmed_route_contraction_ecobf_v1`  
> **Experiment ID**：`A11_CRC_ECOBF_QWEN3VL32B_AW_HARD_T20260806_G3407_V1`  
> **Audit schema**：`a11_crc_ecobf_audit_v1`  
> **Offline replay schema**：`a11_offline_replay_report_v1`  
> **Preflight schema**：`a11_zero_generation_preflight_v1`  
> **Live receipt schema**：`a11_live_server_receipt_v1`

---

## 0. 规范性语言

本文中的以下词语具有强制含义：

- **必须 / MUST**：实现和实验不得偏离。
- **不得 / MUST NOT**：违反即构成 protocol invalid。
- **应当 / SHALL**：与 MUST 同等约束。
- **可以 / MAY**：只表示本文明确允许的行为，不代表实现者可自行选择影响实验结果的参数。
- 所有阈值、容量、顺序、正则表达式、评分权重、读取次数和失败条件均在本文冻结。
- Codex 不得自行补充新的触发器、白名单、阈值、语义解析器或例外规则。
- 任何影响模型输入或记忆决策的修改都必须创建新的机制版本，不得继续使用本文的 Mechanism ID 和 Experiment ID。

---

# 1. A10-v1 的正式裁定

## 1.1 实现与证据完整性裁定

A10-v1 已完成实际机制实现、controller 集成、测试、真实 RGB 轨迹物化和 zero-generation replay。正式报告验证了 27 个 episode、1,668 个冻结文件、442,138,413 bytes，所有文件哈希校验通过，`generation_calls=0`；A6 qualifying loop activation 为 22/23，即 95.65%。因此，A10-v1 当前失败不能归因为文件损坏、伪造回放、缺失 RGB、额外模型调用或 replay 基础设施异常。

正式报告的最终状态为：

```text
status = fail
errors = [
  "a0_success_silence_gate_failed",
  "a1_recipe_sentinel_or_trace_evidence_failed"
]
generation_calls = 0
verification.status = pass
```

这两项是正式、不可覆盖的协议失败。

实现绑定文件明确规定：A10-v1 不得为了历史成功轨迹静默而偷偷削弱 T2；如果成功轨迹真实满足一次 no-gain closed route，则机制必须按原公式创建并可能检索 T2，随后由静默门公开失败。该绑定同时明确规定，在正式 real-RGB replay 全部通过前不得启动 live generation。

因此，对 A10-v1 的正式裁定是：

```text
A10-v1:
  implementation_integrity = PASS
  trace_integrity = PASS
  zero_generation = PASS
  protocol_consistency = FAIL
  offline_qualification = FAIL
  live_generation_authorized = FALSE
```

它不是 infrastructure invalid，也不能通过重写报告、删除失败项、把失败称为“预期现象”或仅凭 95.65% A6 activation 获得放行。

---

## 1.2 第一处内部冲突：单次 closed route 与绝对静默

A10-v1 的实现忠实执行了以下规则：

- 一次 4 个动作内返回的 no-gain route 即可产生 `CLOSED_ROUTE_WITHOUT_ADVANCE`；
- 近似视觉匹配满足原阈值时可检索；
- `Score >= 0.68` 即可读取；
- 三次近期 frontier visit、两条已解析 receipt、无 trusted escape 且无 anchor gain 时，T3 可以成熟。

与此同时，原协议又要求四条 A0 历史成功轨迹全部满足：

```text
nonempty_read_count == 0
delivered_trigger_count == 0
max_rendered_chars == 0
```

真实回放结果为：

| A0 历史成功任务 | Replayed actions | A10-v1 reads |
|---|---:|---:|
| `ExpenseDeleteMultiple2` | 17 | 0 |
| `RetroSavePlaylist` | 31 | 2 |
| `SimpleCalendarAddOneEvent` | 16 | 1 |
| `SportsTrackerTotalDurationForCategoryThisWeek` | 3 | 0 |

Retro 的第一条读取来自 `FRONTIER_COLLAPSE`，第二条来自一次 exact closed-route 读取；Calendar 的读取发生在一次长度为 2、anchor gain 为 0 的 closed route 之后。

这证明原协议同时要求了：

\[
\text{同一确定性轨迹必须读取}
\]

和：

\[
\text{同一确定性轨迹绝对不得读取}
\]

两者无法同时成立。

### 正式裁定

该冲突不是“实现需要微调”，而是原 v1 规范内部不相容。A11 必须修改机制和历史 replay gate，不能继续使用 v1 identity。

---

## 1.3 第二处内部冲突：冻结 parser 与 Recipe gate

冻结 query 是：

```text
Delete the recipes from Broccoli app that use zucchini in the directions.
```

A10-v1 parser 只接受：

- quoted literal；
- colon-list；
- marker-list；
- numeric/date/time；
- temporal literal。

该 query 不含任何上述结构，因此严格实现得到：

```text
anchor_count = 0
```

并进入 sentinel fallback。冻结 query 和 A10-v1 parser 的边界均在仓库中明确可审计。

但原 replay gate 又要求该 query 抽取“多个显式目标或约束”。正式 A1 Recipe replay 的实际结果是 `anchor_count=0`，从而触发第二项 protocol failure。

### 正式裁定

这同样是逻辑矛盾：

```text
frozen parser(query) == []
```

和：

```text
gate requires len(parser(query)) >= 2
```

不能同时满足。

A11 将增加确定性的 relational constraint grammar，并把 A1 Recipe gate 改为要求一个结构化约束 anchor，而不是虚构多个目标条目。

---

# 2. A11 的设计决策

## 2.1 核心问题重述

A10-v1 将以下事件过早视为策略失败：

```text
leave a visual frontier
→ return within four actions
→ no anchor confidence gain
```

但在 GUI agent 中，同一事件结构还可能对应：

- 打开 Settings 并返回；
- 打开 Backup & Restore 并返回；
- 修改开始时间后回到事件编辑页；
- 修改结束时间后回到事件编辑页；
- 进入子表单、选择值、保存并回到父页面；
- 一次正常探索后发现该入口不是最终出口；
- 多阶段工作流中的必要页面往返。

因此：

\[
\text{closed route}
\not\Rightarrow
\text{strategy contraction}
\]

A11 只在 closed route 获得第二项独立不利证据后，才把它升级为可读取的“路线陷阱”。

---

## 2.2 新的一句话因果假设

> **第一次进入并返回一个新路线应获得导航探索信用；只有当同一状态条件下的动作分支或路线核心被再次使用，并且两次都没有产生目标耦合工作、可见工作、目标切换或义务证据增益时，才说明局部策略空间正在收缩。此时注入“仍开放的义务/约束 + 已确认重复的不利分支证据”，有可能在完整循环形成前诱导策略分化。**

该假设是前瞻性、可证伪假设，不是性能保证。

---

## 2.3 A11 的最小证据单元

A11 的读取对象为：

\[
\boxed{
\text{unresolved obligation or persistent constraint}
\land
\text{matching visible frontier}
\land
\text{at least two independent adverse supports}
\land
\neg\text{normal-navigation/workflow exemption}
}
\]

单次普通页面往返不满足该条件。

---

# 3. A10-v1 与 A11 的逐项差异

| 设计项 | A10-v1 | A11 |
|---|---|---|
| Identity | `a10_evidence_calibrated_obligation_branch_frontier_v1` | `a11_confirmed_route_contraction_ecobf_v1` |
| Parent evidence | `ee6df0...` | `4548b932...` |
| Constraint parser | 无 relational constraint | 固定 grammar 抽取 predicate/value/scope |
| Recipe anchor | 0 anchor | 1 个 persistent constraint anchor |
| T2 | 一次 no-gain closed route 即成熟 | 第一次 route 只记为 provisional；第二项独立不利证据后成熟 |
| T3 | 3 visits、2 resolved receipts 即可 | 4 visits、3 resolved、adverse mass、分支收缩和重复坏证据同时成立 |
| Route return 权重 | 所有 qualifying return 都可作为不利证据 | 一次正常探索 return 不增加 bad confidence |
| Normal navigation | 无显式信用 | 冻结 novelty/workflow credit |
| Candidate state | 创建后直接可检索 | `PROVISIONAL → MATURE → DELIVERED/EXPIRED` |
| Near retrieval | \(D_V\le0.055\) 即可 | 更严格 near 阈值，且必须已有至少 2 项成熟支持 |
| Score threshold | 0.68 | 0.70 |
| Score | 无 workflow penalty | 包含 contraction 与 workflow-credit penalty |
| Constraint completion | 不适用 | constraint 始终 persistent-open，不声称所有匹配项已完成 |
| A0 historical gate | 四条绝对 0 read | 稀疏、成熟、无单次路线误报门 |
| A1 Recipe gate | 要求多个 anchor | 要求一个字段完全正确的 structured constraint |
| A6 gate | 23 个 v1 qualifying segments | 使用独立的 v2 branch/route-confirmation classifier |
| v1 evidence reuse | 可作为设计证据 | 只能作为历史证据，不可拼接为 v2 结果 |
| Live arm | A10-v1 | 全新 fresh A11 19-task arm |

---

# 4. 冻结实验身份与比较边界

## 4.1 模型与采样

A11 必须使用与 A0/A1 相同的冻结设置：

```text
model_id:
  Qwen/Qwen3-VL-32B-Instruct

revision:
  0cfaf48183f594c314753d30a4c4974bc75f3ccb

task_seed:
  20260806

generation_seed:
  3407

temperature:
  0.7

top_p:
  0.8

top_k:
  20

presence_penalty:
  1.5

repetition_penalty:
  1.0

max_tokens:
  32768

official_system_prompt_sha256:
  9d060af15f62acb31b9fb197649ec001d4096491d7fb102de929316944b3e26d
```

这些设置已由当前 A10 contract 和 arm config 冻结。

## 4.2 禁止改变的比较条件

A11 不得改变：

- AndroidWorld Hard 19 个实例；
- 任务参数；
- native max steps；
- task order；
- evaluator；
- RGB 截图观察；
- action schema；
- official system prompt；
- 模型 revision；
- vLLM BF16 后端；
- 采样参数；
- task seed；
- generation seed；
- 成功标准；
- A0/A1 paired reference。

---

# 5. 严格因果边界

## 5.1 允许输入

A11 的决策函数只能读取：

```text
task query
before["pixels"]
after["pixels"]
executed canonical action
policy-authored action summary
source_step
```

其中：

- `before["pixels"]` 和 `after["pixels"]` 必须是模型可见 RGB；
- canonical action 必须已经由 policy 生成并由 controller 执行；
- action summary 必须是同一次 policy response 中的原始 summary；
- `source_step` 只用于时间、顺序和衰减。

## 5.2 禁止输入

以下内容不得进入任何写入、更新、触发、评分、检索或渲染分支：

```text
evaluator reward
success flag
task ground truth
hidden task database
UI tree
accessibility tree
UI element bounds
foreground package
activity
app package name
OCR model output
future screenshot
future action
another episode's trajectory
task-name-specific rule
screen-hash whitelist
```

## 5.3 禁止组件

A11 不得引入：

```text
planner
critic
verifier
second model
summarization model
retrieval model
OCR model
reward model
action guard
action filter
action blocker
action override
forced termination
extra model call
```

## 5.4 纯记忆证明条件

对每个 step 必须满足：

```text
policy_canonical_action == executed_canonical_action
memory_added_model_calls == 0
guard_enabled == false
action_override_count == 0
forced_termination_count == 0
```

---

# 6. 形式化定义

在 step \(t\)：

- \(q\)：task query；
- \(I_t\)：执行动作前的可见 RGB；
- \(a_t\)：已执行 canonical action；
- \(u_t\)：policy-authored action summary；
- \(I_{t+1}\)：执行后可见 RGB；
- \(M_t\)：episode-local memory state。

更新函数：

\[
M_{t+1}
=
U(M_t,q,I_t,a_t,u_t,I_{t+1})
\]

读取函数：

\[
m_t
=
R(M_t,q,I_t)
\]

\(U\) 和 \(R\) 必须是确定性函数。

---

# 7. 完整 memory state schema

## 7.1 顶层状态

| 字段 | 类型 | 硬上限 | 含义 |
|---|---|---:|---|
| `mechanism_id` | `str` | 常量 | A11 identity |
| `goal_sha256` | `str[64]` | 1 | query 哈希 |
| `operation_class` | enum | 1 | 固定 lexicon 得到的任务操作类 |
| `anchors` | `list[GoalAnchor]` | 8 | item/value/constraint anchors |
| `phase_id` | `int` | native steps 内 | 当前阶段 |
| `item_open_mask` | `int` | 8 bits | 非 persistent anchor 的开放状态 |
| `constraint_mask` | `int` | 8 bits | persistent constraints |
| `frontiers` | ordered map | 16 | 视觉决策前沿 |
| `attempt_receipts` | deque | 32 | 已执行动作证据 |
| `pending_routes` | list | 4 | 尚未解析的 departure |
| `closed_routes` | deque | 12 | 已闭合路线证据 |
| `post_return_watches` | list | 4 | 等待回返后重复证据 |
| `escape_watches` | list | 2 | T0 部分义务逃离监视 |
| `typed_value_records` | ordered map | 12 keys | T4 输入历史 |
| `trigger_candidates` | list | 8 | provisional/mature candidates |
| `delivered_signatures` | deque | 12 | one-shot signatures |
| `screen_trace` | deque | 17 | 近期 descriptor hashes |
| `read_events` | list | 5 | 非空读取事件 |
| `phase_switch_events` | deque | 8 | 阶段变化 |
| `counters` | fixed dict | 固定字段 | 容量、触发、淘汰等统计 |

---

## 7.2 `GoalAnchor`

| 字段 | 类型 | 上限 |
|---|---|---:|
| `anchor_id` | `str` | 24 chars |
| `role` | `ITEM / VALUE / CONSTRAINT` | 1 |
| `literal` | `str` | 64 chars |
| `normalized` | `str` | 64 chars |
| `source_kind` | enum | 1 |
| `source_offset` | `int` | 1 |
| `specificity_weight` | `int` | 2–5 |
| `predicate` | enum or null | 1 |
| `constraint_value` | `str` | 48 chars |
| `constraint_scope` | enum or null | 1 |
| `negated` | `bool` | 1 |
| `persistent_open` | `bool` | 1 |
| `confidence` | `float` | [0,1] |
| `status` | enum | 1 |
| `last_evidence_step` | `int or None` | 1 |
| `evidence_events` | list | 6 |
| `contradiction_count` | saturating int | 255 |

Constraint anchor 的 `persistent_open` 必须为 `true`。它可以进入 `ENGAGED` 或 `LOCALLY_APPLIED`，但不得从 obligation mask 中移除。

---

## 7.3 `FrontierRecord`

| 字段 | 类型 | 上限 |
|---|---|---:|
| `frontier_id` | `str` | 32 chars |
| `phase_id` | `int` | 1 |
| `item_open_mask` | `int` | 8 bits |
| `constraint_mask` | `int` | 8 bits |
| `visual_exemplars` | list | 3 |
| `first_step` | `int` | 1 |
| `last_visit_step` | `int` | 1 |
| `recent_visit_steps` | deque | 8 |
| `visit_count` | saturating int | 255 |
| `branches` | ordered map | 5 |
| `confirmed_return_count` | saturating int | 255 |
| `benign_return_count` | saturating int | 255 |
| `durable_departure_count` | saturating int | 255 |
| `anchor_confidence_at_first_visit` | tuple | 8 floats |
| `read_count_in_phase` | int | 0–2 |

一次 physical screen 在下一次 `read()` 中只登记为一次 decision visit。不得同时因“前一步 destination”和“下一步 source”重复增加 visit count。

---

## 7.4 `BranchRecord`

| 字段 | 类型 | 上限 |
|---|---|---:|
| `branch_id` | `str` | 32 chars |
| `canonical_family` | tuple | 固定 |
| `intent_class` | enum | 1 |
| `target_anchor_mask` | `int` | 8 bits |
| `label` | `str` | 40 chars |
| `latest_intent_excerpt` | `str` | 56 chars |
| `first_step` | `int` | 1 |
| `last_step` | `int` | 1 |
| `attempt_count` | saturating int | 255 |
| `raw_no_progress_count` | saturating int | 255 |
| `raw_local_change_count` | saturating int | 255 |
| `confirmed_adverse_return_count` | saturating int | 255 |
| `benign_return_count` | saturating int | 255 |
| `raw_durable_count` | saturating int | 255 |
| `failure_confidence` | `float` | [0,1] |
| `escape_confidence` | `float` | [0,1] |
| `canonical_action_sha256s` | deque | 3 |

一次未确认的普通 route return 只能增加 `benign_return_count` 或保留为 provisional，不能增加 `confirmed_adverse_return_count`。

---

## 7.5 `PendingRoute`

| 字段 | 类型 | 上限 |
|---|---|---:|
| `attempt_id` | str | 1 |
| `source_step` | int | 1 |
| `source_frontier_id` | str | 1 |
| `entry_branch_id` | str | 1 |
| `phase_id` | int | 1 |
| `item_open_mask` | int | 1 |
| `constraint_mask` | int | 1 |
| `source_descriptor_ref` | str | 1 |
| `base_anchor_confidences` | tuple | 8 |
| `entry_target_mask` | int | 1 |
| `entry_bad_confidence` | float | 1 |
| `entry_attempt_count_before` | int | 1 |
| `route_hops` | list | 4 |
| `max_anchor_gain` | float | 1 |
| `phase_masks_unchanged` | bool | 1 |
| `target_progress` | bool | 1 |

---

## 7.6 `RouteHop`

| 字段 | 类型 |
|---|---|
| `source_step` | int |
| `branch_family_digest` | str[16] |
| `intent_class` | enum |
| `target_anchor_mask` | int |
| `source_descriptor_hash` | str[16] |
| `destination_descriptor_hash` | str[16] |
| `immediate_outcome` | enum |
| `visible_work` | bool |
| `goal_coupled` | bool |

最多保留 departure 起点到 return 之间的 4 个 hop。

---

## 7.7 `ClosedRouteRecord`

| 字段 | 类型 |
|---|---|
| `route_id` | str |
| `source_frontier_id` | str |
| `entry_branch_id` | str |
| `phase_id` | int |
| `item_open_mask` | int |
| `constraint_mask` | int |
| `start_step` | int |
| `return_step` | int |
| `route_length` | int，1–4 |
| `route_length_bucket` | `ONE / TWO / THREE_FOUR` |
| `return_branch_family_digest` | str[16] |
| `route_core_signature` | str[64] |
| `route_full_signature` | str[64] |
| `anchor_gain` | float |
| `goal_coupled` | bool |
| `visible_work` | bool |
| `target_progress` | bool |
| `entry_novel` | bool |
| `route_core_novel` | bool |
| `novelty_workflow_credit` | float |
| `residual_work_credit` | float |
| `classification` | enum |
| `confirmation_step` | int or null |
| `support_receipt_ids` | list，最多 3 |

Route classification：

```text
WORKFLOW_ADVANCE
NOVEL_EXPLORATION_RETURN
PROVISIONAL_ADVERSE_RETURN
CONFIRMED_ADVERSE_RETURN
LATE_BENIGN_RETURN
LATE_CONFIRMED_ADVERSE_RETURN
```

---

## 7.8 `TriggerCandidate`

| 字段 | 类型 |
|---|---|
| `trigger_id` | str |
| `kind` | enum |
| `state` | `PROVISIONAL / MATURE / DELIVERED / EXPIRED / INVALIDATED` |
| `created_step` | int |
| `maturity_step` | int or null |
| `expires_step` | int |
| `phase_id` | int |
| `item_open_mask` | int |
| `constraint_mask` | int |
| `query_frontier_id` | str |
| `expected_descriptor_ref` | str |
| `support_count` | int |
| `support_receipt_ids` | list，最多 4 |
| `evidence_strength` | float |
| `contraction_confidence` | float |
| `anchor_gain` | float |
| `workflow_credit` | float |
| `evidence_signature` | str[64] |
| `evidence_payload` | bounded struct |
| `delivered` | bool |

只有 `state == MATURE` 的 candidate 才能参与 retrieval。

---

# 8. Query anchor 与 constraint parser

## 8.1 预处理

```python
text = unicodedata.normalize("NFKC", goal)
folded = text.casefold()
folded = re.sub(r"\s+", " ", folded).strip()
```

保留原始字符偏移。

基础 Unicode token：

```python
WORD = r"[^\W_]+(?:[-’'][^\W_]+)*"
```

该表达式使用 Python 标准库 `re` 的 Unicode 规则，不需要外部 NLP 库。

---

## 8.2 Constraint predicate lexicon

```python
PREDICATE_MAP = {
    "use": "USE",
    "uses": "USE",
    "contain": "CONTAIN",
    "contains": "CONTAIN",
    "include": "INCLUDE",
    "includes": "INCLUDE",
    "have": "HAVE",
    "has": "HAVE",
    "take": "TAKE",
    "takes": "TAKE",
    "last": "LAST",
    "lasts": "LAST",
    "cost": "COST",
    "costs": "COST",
    "match": "MATCH",
    "matches": "MATCH",
    "equal": "EQUAL",
    "equals": "EQUAL",
}
```

Generic task verbs such as `delete`、`add`、`open`、`save`、`create`、`copy` 不属于 constraint predicate。

---

## 8.3 Scope field lexicon

```python
FIELD_MAP = {
    "direction": "DIRECTIONS",
    "directions": "DIRECTIONS",
    "ingredient": "INGREDIENTS",
    "ingredients": "INGREDIENTS",
    "title": "TITLE",
    "titles": "TITLE",
    "name": "NAME",
    "names": "NAME",
    "description": "DESCRIPTION",
    "descriptions": "DESCRIPTION",
    "note": "NOTES",
    "notes": "NOTES",
    "category": "CATEGORY",
    "categories": "CATEGORY",
    "date": "DATE",
    "dates": "DATE",
    "time": "TIME",
    "times": "TIME",
    "duration": "DURATION",
    "durations": "DURATION",
    "distance": "DISTANCE",
    "distances": "DISTANCE",
    "amount": "AMOUNT",
    "amounts": "AMOUNT",
    "location": "LOCATION",
    "locations": "LOCATION",
    "filename": "FILENAME",
    "filenames": "FILENAME",
    "content": "CONTENT",
    "contents": "CONTENT",
}
```

固定 purpose mapping：

```python
PURPOSE_SCOPE = {
    "prepare": "PREPARATION_DURATION",
    "cook": "PREPARATION_DURATION",
    "complete": "COMPLETION_DURATION",
}
```

---

## 8.4 App span 排除

生产代码必须识别并排除以下结构中的 app span：

```python
APP_SCOPE_RE = re.compile(
    rf"\b(?:from|in|into|to|using|via)\s+"
    rf"(?:the\s+)?"
    rf"(?P<app>{WORD}(?:\s+{WORD}){{0,3}})"
    rf"\s+(?:app|application)\b",
    re.IGNORECASE | re.UNICODE,
)
```

不得再运行左端贪婪的 `BARE_APP_RE`。它会在规范正例
`that use zucchini from Broccoli app` 中吞入 `use zucchini from Broccoli`，与
`zucchini` value 重叠并错误拒绝正例。app span 只由上面的 `APP_SCOPE_RE` 产生；
不存在介词引导的 bare `X app` 不参与 constraint value 排除。

与 `APP_SCOPE_RE` app span 有字符重叠的 constraint value candidate 必须拒绝。

Scope field 不能是 `app` 或 `application`。

---

## 8.5 Relative constraint grammar

Head：

```python
REL_HEAD_RE = re.compile(
    r"\b(?P<relative>that|which)\s+"
    r"(?:(?P<negation>do\s+not|does\s+not|don't|doesn't|not)\s+)?"
    r"(?P<predicate>"
    r"use|uses|contain|contains|include|includes|have|has|"
    r"take|takes|last|lasts|cost|costs|match|matches|equal|equals"
    r")\b",
    re.IGNORECASE | re.UNICODE,
)
```

### 8.5.1 `USE/CONTAIN/INCLUDE/HAVE/MATCH/EQUAL`

Head 后的 token parser 必须按下列规则执行：

1. 最多读取 6 个 value tokens；
2. 遇到以下结构时停止 value：
   - 标点：`, . ; : ! ? ( )`
   - clause word：`and, or, but, then`
   - destination word：`from, to, into, using, via`
3. 遇到：

```text
in|within|inside|under|on
[optional "the"]
FIELD
```

时：

- 介词前 token 为 `constraint_value`；
- FIELD 通过 `FIELD_MAP` 映射为 `constraint_scope`；
- field token 本身不属于 value。

4. 如果没有合法 field scope，则允许无 scope 的 value；
5. value 必须通过 §8.9 的内容检查。

对于：

```text
that use zucchini in the directions
```

结果必须是：

```json
{
  "role": "CONSTRAINT",
  "predicate": "USE",
  "constraint_value": "zucchini",
  "constraint_scope": "DIRECTIONS",
  "negated": false,
  "persistent_open": true
}
```

### 8.5.2 `TAKE/LAST/COST`

固定 scalar tail：

```python
SCALAR_TAIL_RE = re.compile(
    r"^\s*"
    r"(?P<value>"
    r"\d+(?:\.\d+)?"
    r"(?:\s*(?:h|hr|hrs|hour|hours|min|mins|minute|minutes|"
    r"km|m|meter|meters|dollar|dollars))?"
    r")"
    r"(?:\s+to\s+(?P<purpose>prepare|cook|complete))?"
    r"\b",
    re.IGNORECASE | re.UNICODE,
)
```

例如：

```text
that take 2 hrs to prepare
```

必须抽取：

```json
{
  "predicate": "TAKE",
  "constraint_value": "2 hrs",
  "constraint_scope": "PREPARATION_DURATION"
}
```

嵌套在该 structured constraint 内的普通 numeric anchor `2 hrs` 必须被 overlap 去重规则抑制。

---

## 8.6 Attribute constraint grammar

```python
ATTRIBUTE_HEAD_RE = re.compile(
    rf"\b(?:with|whose)\s+"
    rf"(?:the\s+)?"
    rf"(?P<field>{'|'.join(sorted(FIELD_MAP, key=len, reverse=True))})\s+"
    r"(?P<predicate>"
    r"is|are|equal|equals|contain|contains|include|includes|have|has"
    r")\b",
    re.IGNORECASE | re.UNICODE,
)
```

Head 后按最多 6 个 value token 解析。该 grammar 产生：

```text
scope = FIELD_MAP[field]
predicate = normalized predicate
value = parsed tail
```

---

## 8.7 Legacy anchor grammar

A11 保留以下 v1 规则。

### Quoted literal

支持：

```text
"..."
'...'
`...`
“...”
‘...’
```

内容长度 2–64。

### Colon-list

取最后一个冒号后的第一个句子，按：

```text
comma
semicolon
newline
```

拆分。至少有两个有效项才产生 anchors。

### Marker-list

固定 marker：

```text
following
these
named
called
titled
containing
```

marker 后直到句末，按逗号、分号、换行和 `and` 拆分。至少两个有效项才产生 anchors。

### Numeric/time

```python
NUMERIC_RE = re.compile(
    r"\b(?:"
    r"\d{1,4}(?:[-/:.]\d{1,4})+|"
    r"\d+(?:\.\d+)?"
    r"(?:\s*(?:am|pm|km|mins?|minutes?|h|hrs?|hours?))?"
    r")\b",
    re.IGNORECASE,
)
```

### Temporal lexicon

```text
today
tomorrow
yesterday
this week
last week
monday ... sunday
january ... december
```

---

## 8.8 角色与优先级

| Source kind | Role | Priority |
|---|---|---:|
| relational/attribute constraint | `CONSTRAINT` | 5 |
| quoted | `ITEM` | 4 |
| colon-list | `ITEM` | 3 |
| marker-list | `ITEM` | 3 |
| numeric/time | `VALUE` | 2 |
| temporal | `VALUE` | 2 |

排序：

```text
priority descending
source_offset ascending
source_span_length descending
normalized key ascending
```

最多保留 8 个 anchors。

---

## 8.9 Constraint value 内容检查

固定 generic stop set：

```python
GENERIC_VALUE_TOKENS = {
    "a", "an", "the", "any", "all", "some", "each", "every",
    "this", "that", "these", "those",
    "it", "them", "they", "one", "ones",
    "app", "application",
    "item", "items", "entry", "entries", "record", "records",
    "file", "files", "note", "notes", "recipe", "recipes",
    "expense", "expenses", "song", "songs",
    "activity", "activities", "event", "events",
    "playlist", "playlists", "transaction", "transactions",
    "use", "uses", "contain", "contains", "include", "includes",
    "have", "has", "take", "takes", "last", "lasts",
    "cost", "costs", "match", "matches", "equal", "equals",
    "in", "on", "at", "from", "to", "into", "within",
    "inside", "under", "using", "via",
    *FIELD_MAP.keys(),
}
```

Candidate 必须同时满足：

```text
1 <= token_count <= 6
2 <= normalized_character_count <= 48
not overlap APP_SCOPE span
no token is "app" or "application"
first token not a preposition
last token not a preposition
at least one token not in GENERIC_VALUE_TOKENS
```

---

## 8.10 去重与 overlap

每个 candidate 生成：

```text
semantic_key
```

Constraint key：

```text
constraint|predicate|normalized_value|scope|negated
```

Simple anchor key：

```text
simple|normalized_literal
```

规则：

1. semantic key 完全相同只保留最早 candidate；
2. 两个 candidate 源 span overlap 比例大于等于 0.8 时，保留 priority 更高者；
3. structured constraint 完整包含 lower-priority numeric/time candidate 时，只保留 constraint；
4. quoted/list items 即使 value 文本相同，只要来源 span 不重叠，仍按 normalized key 去重；
5. scope field 不单独生成 anchor；
6. predicate verb 不单独生成 anchor；
7. app name 不生成 anchor。

---

## 8.11 正例

| Query fragment | 预期 |
|---|---|
| `that use zucchini in the directions` | `USE / zucchini / DIRECTIONS` |
| `which contain pineapple in the content` | `CONTAIN / pineapple / CONTENT` |
| `that do not include tax in notes` | `INCLUDE / tax / NOTES / negated=true` |
| `that take 2 hrs to prepare` | `TAKE / 2 hrs / PREPARATION_DURATION` |
| `whose filename contains report` | `CONTAIN / report / FILENAME` |
| `with title equal Project X` | `EQUAL / Project X / TITLE` |

---

## 8.12 负例

| Query fragment | 结果 |
|---|---|
| `from Broccoli app` | 无 constraint |
| `to the Broccoli recipe app` | 无 constraint |
| `use Simple Gallery Pro` | 无 constraint；缺少 relative/attribute grammar |
| `delete the recipes` | 无 constraint |
| `in Downloads` | 无 constraint |
| `for skiing activities` | 无 relational constraint |
| `that use in the directions` | 拒绝；value 为空 |
| `that use the directions` | 拒绝；value 全为 generic/field token |
| `that use app in directions` | 拒绝；value 为 app |
| `that use Broccoli app in directions` | 拒绝；与 app span 重叠 |

---

## 8.13 对抗样例

实现必须测试：

```text
that use extra virgin olive oil in the ingredients
```

产生 4-token value。

```text
that use one two three four five six seven in the directions
```

因超过 6 tokens 拒绝。

```text
that use zucchini from Broccoli app
```

允许抽取 `zucchini`，但不得抽取 `Broccoli` 或 `app`。

```text
that use "zucchini" in directions
```

structured constraint 优先于内部 quoted duplicate。

```text
that take 2 hours to prepare into the Broccoli app
```

只保留 structured duration constraint，不把 app 作为义务。

---

# 9. Target anchor mask

## 9.1 Simple anchors

对 `ITEM` 和 `VALUE` anchor：

```python
pattern = rf"(?<!\w){re.escape(anchor.normalized)}(?!\w)"
```

若 pattern 出现在：

- normalized action summary；或
- normalized `type_text.text`

则置位。

---

## 9.2 Constraint anchors

Constraint bit 只在以下任一条件成立时置位：

1. 完整 normalized `constraint_value` 以 token-bounded 形式出现在 action summary；
2. 完整 normalized `constraint_value` 出现在 `type_text.text`；
3. summary 中出现 predicate alias，并且在其后 64 个字符内出现完整 value。

以下内容单独出现时不得置位：

- scope field；
- predicate；
- app name；
- generic object noun；
- task verb。

对于 Recipe query：

```text
summary = "Search for zucchini"
```

必须匹配 constraint。

```text
summary = "Open directions"
```

不得仅因 `directions` 匹配 constraint。

```text
summary = "Open Broccoli app"
```

不得匹配 constraint。

---

# 10. Visual descriptor

A11 复用 v1 的非学习型 RGB descriptor。

## 10.1 RGB 校验

允许：

```text
ndim == 3
height >= 25
width >= 8
channels >= 3
integer dtype
all values in [0,255]
```

RGBA 只使用前 3 个 channel。

以下输入必须抛出 `A11VisibleInputError`：

```text
float RGB
NaN
negative values
values > 255
channels < 3
height < 25
width < 8
```

---

## 10.2 Crop 与 exact hash

裁掉顶部、底部各 4%：

\[
I^{crop}
=
I[
\lfloor0.04H\rfloor:
\lceil0.96H\rceil
]
\]

Exact fingerprint：

\[
h^{exact}
=
SHA256(shape\Vert dtype\Vert RGB\ bytes)
\]

---

## 10.3 Coarse descriptor

固定划分为 \(9\times16\) cells。

每个 cell：

\[
Y=\frac{77R+150G+29B}{256}
\]

\[
q_{r,c}
=
\left\lfloor \frac{Y_{r,c}}{16}\right\rfloor
\]

亮度距离：

\[
D_L
=
\frac{1}{144\cdot15}
\sum_{r,c}|q_{r,c}-q'_{r,c}|
\]

横向和纵向 edge bits 共 263 位。

\[
D_E
=
\frac{\operatorname{Hamming}(E,E')}{263}
\]

\[
D_V
=
0.7D_L+0.3D_E
\]

---

## 10.4 三类视觉匹配

### Standard state match

用于 frontier matching 和 route return detection：

```text
exact hash equal
OR
DL <= 0.06
DE <= 0.12
DV <= 0.055
```

### Frontier merge

```text
DV <= 0.035
```

并且：

```text
phase_id equal
item_open_mask equal
constraint_mask equal
```

### Near retrieval match

非 exact candidate retrieval 必须满足：

```text
DL <= 0.05
DE <= 0.10
DV <= 0.045
candidate.support_count >= 2
candidate.state == MATURE
```

因此 A11 仍允许 near retrieval，但单次路线证据不能借 near match 直接进入 prompt。

---

# 11. Canonical action、intent 与 branch

## 11.1 Intent class

固定优先级：

```text
COMMIT
OPEN_OR_SELECT
INPUT_OR_SEARCH
INSPECT
RECOVER
SCROLL
WAIT
ANSWER
OTHER
```

固定 verb lexicon：

```python
COMMIT = {
  "delete", "remove", "add", "create", "save", "send",
  "share", "submit", "confirm", "merge", "copy", "mark",
  "export"
}

OPEN_OR_SELECT = {
  "open", "launch", "navigate", "select", "choose"
}

INPUT_OR_SEARCH = {
  "type", "enter", "fill", "search"
}

INSPECT = {
  "inspect", "check", "view", "read", "find", "calculate"
}

RECOVER = {
  "back", "return", "close", "cancel"
}

SCROLL = {
  "scroll", "swipe"
}
```

---

## 11.2 Canonical family

### Tap / long press

\[
x_{bin}=\min(11,\lfloor12x\rfloor)
\]

\[
y_{bin}=\min(23,\lfloor24y\rfloor)
\]

```text
(type, x_bin, y_bin)
```

Long press duration：

```text
short  < 700 ms
medium 700–1500 ms
long   > 1500 ms
```

### Swipe

方向按 dominant axis。

长度：

```text
short  < 0.25
medium 0.25–0.55
long   >= 0.55
```

起点采用 \(3\times4\) grid。

```text
("swipe", direction, length_bucket, start_x_bin, start_y_bin)
```

### Type text

```text
(
  "type_text",
  SHA256(NFKC(text)),
  length_bucket,
  clear_text
)
```

### Wait / system / answer

保留固定类型与 bounded duration/text digest。

---

## 11.3 Branch key

\[
BKey
=
SHA256(
canonical\_family,
intent\_class,
target\_anchor\_mask
)
\]

因此：

- 相同坐标、不同目标 anchor 是不同 branch；
- 相同 text、不同 `clear_text` 是不同 branch；
- 相同 swipe、不同 phase/frontier 不会合并为同一个决策前沿；
- scope field 单独出现不会改变 constraint target mask。

---

# 12. Immediate transition outcome

像素变化：

\[
P_t
=
\frac{1}{HW}
\sum_{i,j}
\mathbf 1
[
\max_c|I_t-I_{t+1}|>5
]
\]

| 条件 | Outcome |
|---|---|
| RGB 完全一致 | `NO_PROGRESS_EXACT` |
| \(P_t\le0.001\) | `NO_PROGRESS_NEGLIGIBLE` |
| \(P_t>0.001\) 且 destination match source frontier | `LOCAL_VISIBLE_CHANGE` |
| destination 不 match source | `DEPARTURE_PENDING` |

`LOCAL_VISIBLE_CHANGE` 不等于任务进展。

---

# 13. Route 定义与正常导航信用

## 13.1 Route closure

一次 departure 从 source frontier \(F\) 开始。

若在后续 1–4 个 executed actions 内再次 standard-match \(F\)，则：

```text
outcome = RETURNED
```

若 4 个动作内未返回：

```text
outcome = DURABLE_DEPARTURE
```

若第 5–8 个动作返回：

```text
outcome = LATE_RETURN
```

Late return 必须修订先前 durable 记录，不得双重计数。

---

## 13.2 Route signature

### Route length bucket

```text
1       -> ONE
2       -> TWO
3 or 4  -> THREE_FOUR
```

### Core signature

```python
route_core_signature = sha256_json({
    "source_frontier_id": source_frontier_id,
    "phase_id": phase_id,
    "item_open_mask": item_open_mask,
    "constraint_mask": constraint_mask,
    "entry_branch_key": entry_branch_key,
    "return_branch_family": return_branch_family,
    "route_length_bucket": route_length_bucket,
})
```

### Full signature

在 core fields 基础上增加最多 4 个 ordered route-hop family digests，仅用于审计和更细粒度比较。

两个 route 被视为“同一核心路线”，只要求 `route_core_signature` 相同。

---

## 13.3 Route 证据变量

对一条 closed route 定义：

### Entry novelty

\[
n_e
=
\mathbf1[
entry\ branch\ 在 route 开始前未在该 frontier 被尝试
]
\]

### Route novelty

\[
n_r
=
\mathbf1[
同一 route\_core\_signature 在当前 phase/masks 中尚未出现
]
\]

### Goal-coupled action

\[
c
=
\mathbf1[
route 中任一 action 的 target\_anchor\_mask\neq0
]
\]

### Visible work

\[
v
=
\mathbf1[
route 中存在 intent\in\{COMMIT,INPUT\_OR\_SEARCH\}
\land P_t>0.001
]
\]

单纯 `OPEN_OR_SELECT`、`SCROLL`、`RECOVER` 或 `WAIT` 的页面变化不构成 visible work。

### Target progression

\[
z
=
\mathbf1[
route 中出现此前未涉及的 open item target
]
\]

### Anchor gain

\[
g
=
\max_a
(C_a(return)-C_a(start))
\]

---

## 13.4 Navigation novelty/workflow credit

\[
X
=
0.30n_e
+
0.25n_r
+
0.20c
+
0.15v
+
0.10z
\]

\[
0\le X\le1
\]

第一次进入一个新 branch 和一条新 route core，仅凭 novelty 即可获得：

\[
X=0.55
\]

---

## 13.5 Residual work credit

为了在第二次重复时移除“第一次探索新路线”的信用，定义：

\[
W
=
0.40c
+
0.35v
+
0.25z
\]

\(W\) 不包含 novelty。

---

## 13.6 Normal-navigation exemption

一次 closed route 满足以下任一条件时，不作为 adverse return：

### Workflow advance

```text
anchor_gain >= 0.10
OR phase changed
OR item_open_mask changed
OR target_progress == true
OR residual_work_credit >= 0.35
```

分类：

```text
WORKFLOW_ADVANCE
```

### Novel navigation

若：

```text
X >= 0.50
entry_branch.failure_confidence < 0.55
```

分类：

```text
NOVEL_EXPLORATION_RETURN
```

### 关键约束

```text
A single closed route MUST NOT create a mature T2.
```

无论其 \(X\) 高低，第一次 route 最多创建 provisional route evidence。

---

## 13.7 Confirmed adverse return

一条 route 只有通过以下任一确认路径，才升级为：

```text
CONFIRMED_ADVERSE_RETURN
```

### Route recurrence confirmation

当前 route 与一条前 12 个动作内的旧 route 满足：

```text
same route_core_signature
same phase
same item_open_mask
same constraint_mask
both anchor_gain < 0.10
both residual_work_credit < 0.35
neither has target_progress
```

两条 route 同时在当前 confirmation step 被标为 confirmed adverse evidence。

以前已经发生的 read audit 不得被改写为“当时已经知道确认结果”。

### Post-return reversion confirmation

第一次 route 返回后建立 watch。

若 return 后的前 2 个 source actions 中，出现：

```text
source frontier matches
same entry branch
OR branch.failure_confidence >= 0.55
```

并且该 action 最终解析为：

```text
NO_PROGRESS_EXACT
NO_PROGRESS_NEGLIGIBLE
RETURNED
LATE_RETURN
```

且从 route return 到该解析时：

```text
anchor_gain < 0.10
phase/masks unchanged
```

则 route 与该坏 branch 共同构成两项独立 adverse supports。

若第二个 source action 产生 departure，其 route resolution 可晚于 watch 的 action window；只要该 source action 本身发生于 return 后 2 个动作内，resolution 最迟允许在 return 后 6 个动作内完成。

---

# 14. Anchor evidence 与 confidence

## 14.1 Simple item/value evidence

正证据：

| Event | Weight |
|---|---:|
| `ACTION_MENTION` | +0.20 |
| `TYPE_EXACT` | +0.25 |
| `COMMIT_INTENT` | +0.20 |
| `MATERIAL_VISIBLE_CHANGE` | +0.10 |
| `DURABLE_ROUTE_DEPARTURE` | +0.15 |
| `INDEPENDENT_SECOND_SUPPORT` | +0.15 |

负证据：

| Event | Weight |
|---|---:|
| `NO_PROGRESS_COMMIT` | -0.20 |
| `CONFIRMED_ROUTE_RETURN` | -0.25 |
| `REVERSAL_OR_FAILURE_PROSE` | -0.45 |
| `LATER_REOPEN_ATTEMPT` | -0.30 |

未确认的 one-off route return 不产生 `CONFIRMED_ROUTE_RETURN`。

---

## 14.2 Constraint evidence

| Event | Weight |
|---|---:|
| `CONSTRAINT_VALUE_MENTION` | +0.20 |
| `CONSTRAINT_TYPE_EXACT` | +0.25 |
| `PREDICATE_AND_VALUE_MENTION` | +0.20 |
| `CONSTRAINT_VISIBLE_CHANGE` | +0.10 |
| `CONSTRAINT_DURABLE_ROUTE` | +0.10 |
| `INDEPENDENT_SECOND_SUPPORT` | +0.15 |
| `NO_PROGRESS_CONSTRAINT_ACTION` | -0.20 |
| `CONFIRMED_CONSTRAINT_ROUTE_RETURN` | -0.25 |
| `REVERSAL_OR_FAILURE_PROSE` | -0.45 |

Constraint evidence 只能表示该筛选条件被模型处理或使用，不能表示“所有满足该约束的对象都已完成”。

---

## 14.3 Confidence 衰减

普通正证据：

\[
\lambda=0.97
\]

Durable/independent support：

\[
\lambda=0.995
\]

负证据：

\[
\lambda=0.99
\]

\[
C_a(s)
=
clip
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

同一：

```text
(anchor_id, source_step, event_kind)
```

只允许写入一次。

---

## 14.4 Simple anchor status

| 条件 | Status |
|---|---|
| \(C<0.35\) | `OPEN` |
| \(0.35\le C<0.60\) | `TOUCHED` |
| \(0.60\le C<0.80\) | `PROVISIONAL` |
| \(C\ge0.80\) 且通过 hard support | `LOCALLY_SUPPORTED` |
| supported 后出现强负证据 | `REOPENED` |

Hard support：

```text
at least ACTION_MENTION or TYPE_EXACT
AND at least COMMIT_INTENT
AND:
  DURABLE_ROUTE_DEPARTURE
  OR two material/support events from different steps
```

---

## 14.5 Constraint status

| 条件 | Status |
|---|---|
| \(C<0.35\) | `OPEN` |
| \(0.35\le C<0.80\) | `ENGAGED` |
| \(C\ge0.80\) 且 hard constraint support | `LOCALLY_APPLIED` |
| applied 后出现强负证据 | `REOPENED` |

Hard constraint support：

```text
value mention or exact type
AND predicate/value or commit/filter intent
AND visible change or durable route
```

即使进入 `LOCALLY_APPLIED`：

```text
persistent_open = true
constraint bit remains set
```

---

# 15. Branch confidence

当前 step \(s\)，对每个 outcome event：

\[
d(e,s)
=
0.85^{
\left\lfloor
\frac{s-e.step}{8}
\right\rfloor
}
\]

定义：

\[
N
=
\sum_{\text{NO_PROGRESS}}d
\]

\[
R
=
\sum_{\text{CONFIRMED_ADVERSE_RETURN}}1.25d
+
\sum_{\text{LATE_CONFIRMED_ADVERSE_RETURN}}0.75d
\]

\[
L
=
\sum_{\text{LOCAL_VISIBLE_CHANGE}}0.5d
\]

\[
D
=
\sum_{\text{DURABLE_DEPARTURE}}d
\]

普通 one-off benign return 不进入 \(R\)。

\[
A=N+R+L+D
\]

\[
p_{bad}
=
\frac{1+N+R}{2+N+R+L+D}
\]

\[
s_{evidence}
=
1-e^{-0.7A}
\]

\[
C_{bad}
=
p_{bad}s_{evidence}
\]

\[
C_{escape}
=
\frac{1+D}{2+N+R+L+D}
s_{evidence}
\]

Trusted bad：

```text
C_bad >= 0.55
AND:
  two no-progress receipts
  OR one no-progress + one confirmed adverse return
  OR two confirmed adverse returns
```

Trusted escape：

```text
C_escape >= 0.55
AND raw_durable_count >= 1
```

---

# 16. Phase 与 masks

## 16.1 Masks

```text
item_open_mask:
  ITEM/VALUE anchors whose status is not LOCALLY_SUPPORTED

constraint_mask:
  every CONSTRAINT anchor, regardless of status
```

Frontier key：

```text
phase_id
item_open_mask
constraint_mask
visual state
```

---

## 16.2 Phase switch

`phase_id` 在以下条件下递增：

1. `item_open_mask` 发生变化；
2. 某 nonpersistent anchor 进入或离开 `LOCALLY_SUPPORTED`；
3. query 没有 nonpersistent anchors，且一个 `COMMIT` branch：
   - 产生 `LOCAL_VISIBLE_CHANGE`；
   - 离开 source frontier；
   - 4 个动作内没有返回。

Constraint confidence/status 的变化不单独切换 phase。

Phase switch 后：

```text
expire all old-phase candidates
reset phase read count
reset read cooldown
preserve historical receipts for audit
do not merge old and new phase frontiers
```

---

# 17. Trigger 规范

A11 保留 T0、T1、T4，并重写 T2、T3。

---

## 17.1 T0 — `PARTIAL_OBLIGATION_ESCAPE`

### Hard conditions

1. 至少两个 nonpersistent `ITEM` anchors；
2. 一个 item 在最近一次 `COMMIT` 后 confidence 增加至少 0.20；
3. 至少另一个 item 仍在 `item_open_mask`；
4. commit source frontier 后连续两个已观察 decision screens 均不 match source；
5. 两个 decision steps 内其他 open item 最大 confidence gain 小于 0.10；
6. 没有 phase/mask mismatch；
7. 相同 evidence signature 未读取。

### Candidate

```text
state = MATURE
support_count = 2
expiry = maturity_step + 6
```

---

## 17.2 T1 — `BAD_BRANCH_REPEAT`

### Adverse support

同一：

```text
frontier
phase
item_open_mask
constraint_mask
branch key
```

内：

```text
N >= 1.70
OR
N >= 0.85 AND R >= 1.00
```

并且：

```text
C_bad >= 0.55
max open-anchor gain since first support < 0.15
```

### Wait 特例

`WAIT` branch 必须至少有 3 次 no-progress receipts，不能仅凭两次 wait 触发。

### Retry exemptions

以下任一成立时不得创建 T1：

```text
current type_text has clear_text=true
explicit clear/erase input intent occurred in previous 2 actions
target_anchor_mask changed
previous attempt is still DEPARTURE_PENDING
previous attempt produced anchor gain >= 0.10
exact screen hash changed since previous attempt while coarse state remains matched
branch is WAIT and no-progress count < 3
```

### Candidate

```text
state = MATURE
support_count >= 2
expiry = maturity_step + 8
```

---

## 17.3 T2 — `CONFIRMED_ROUTE_TRAP`

### 第一次 closed route

第一次 route 只能：

```text
write ClosedRouteRecord
possibly create PostReturnWatch
state remains provisional
no mature trigger
no prompt read
```

### Maturity path A：route recurrence

同一 `route_core_signature` 在前 12 个动作内第二次闭合，并满足：

```text
both anchor_gain < 0.10
both residual_work_credit < 0.35
same phase
same item_open_mask
same constraint_mask
no target_progress
```

### Maturity path B：post-return reversion

满足 §13.7 的 post-return reversion confirmation。

### Route evidence confidence

令：

- \(k\)：同一 route core 的 confirmed occurrence count，至少 2；
- \(q\)：是否有 post-return reversion；
- \(b\)：相关 entry/return branch 的最大 \(C_{bad}\)；
- \(W_{max}\)：支持路线的最大 residual work credit。

\[
E_{route}
=
clip
\left(
0.50
+
0.20\min(2,k-1)
+
0.20q
+
0.15b
-
0.20W_{max},
0,
1
\right)
\]

成熟要求：

\[
E_{route}\ge0.75
\]

Contraction confidence：

\[
C_{route}
=
clip
\left(
0.60
+
0.20\mathbf1[k\ge2]
+
0.20q,
0,
1
\right)
\]

### Candidate

```text
state = MATURE
support_count >= 2
workflow_credit = max residual work credit
expiry = maturity_step + 8
```

---

## 17.4 T3 — `CONTRACTED_FRONTIER`

T3 不再由“3 visits + 2 resolved”直接产生。

### Window

当前 step \(s\) 的窗口：

\[
W_s=[s-7,s]
\]

### Hard conditions

```text
decision visits to frontier in W_s >= 4
resolved source attempts in W_s >= 3
no phase switch in W_s
max open-anchor gain in W_s < 0.15
no pending route from this frontier
no trusted escape branch
```

### Adverse mass

\[
A_F
=
1.0N_{raw}
+
1.0R_{confirmed}
+
0.75R_{late-confirmed}
\]

只统计窗口内 receipt。

要求：

\[
A_F\ge2.5
\]

一次 provisional/benign route return 的权重为 0。

### Branch contraction

设窗口内 attempts 共 \(m\) 个，unique branch 数为 \(K\)，最大 branch 比例为 \(p_{max}\)。

\[
C_F
=
0.5p_{max}
+
0.5
\left(
1-\min\left(1,\frac{K-1}{3}\right)
\right)
\]

要求：

```text
K <= 2
C_F >= 0.55
```

并且窗口最后两个 branch 在各自出现前都已经在该窗口出现过，即：

```text
no new branch among the last two attempts
```

还必须满足：

```text
at least one trusted bad branch
OR at least one route_core_signature confirmed twice
```

### Workflow exclusion

窗口内用于 adverse mass 的支持 receipts 必须满足：

```text
residual_work_credit < 0.35
```

### Candidate

\[
E_F=\min(1,A_F/3)
\]

```text
state = MATURE
support_count >= 3
contraction_confidence = C_F
expiry = maturity_step + 8
```

---

## 17.5 T4 — `VALUE_REENTRY_AFTER_BAD_OUTCOME`

### Hard conditions

1. 同一 normalized nonempty `type_text` 在 12 个动作内第二次出现；
2. phase、item mask、constraint mask 相同；
3. 当前 source frontier 与首次 source exact/near match；
4. 首次输入对应：
   - no-progress；或
   - confirmed adverse return；或
   - source frontier 被重新进入，且 anchor gain 小于 0.15；
5. 中间没有 clear evidence；
6. 若中间有 clear，则只有再次回到同一坏 frontier 时才允许触发。

### Candidate

```text
state = MATURE
support_count = 2
evidence_strength >= 0.65
expiry = maturity_step + 8
```

---

# 18. Candidate maturity、失效、one-shot

## 18.1 状态机

```text
PROVISIONAL
  ├─ enough independent evidence -> MATURE
  ├─ phase/mask change -> INVALIDATED
  ├─ anchor gain >= 0.15 -> INVALIDATED
  ├─ trusted escape -> INVALIDATED
  └─ expiry -> EXPIRED

MATURE
  ├─ selected -> DELIVERED
  ├─ phase/mask change -> INVALIDATED
  ├─ evidence contradicted -> INVALIDATED
  └─ expiry -> EXPIRED
```

T1、T3、T4 在创建时已经具有多项支持，可直接 `MATURE`。

T2 第一次路线记录不是 mature trigger。

---

## 18.2 Evidence signature

```python
evidence_signature = sha256_json({
    "kind": kind,
    "phase_id": phase_id,
    "item_open_mask": item_open_mask,
    "constraint_mask": constraint_mask,
    "frontier_id": frontier_id,
    "support_receipt_ids": sorted(support_receipt_ids),
    "evidence_revision": evidence_revision,
})
```

同一 signature 整个 episode 最多读取一次。

新增独立 evidence 可以形成新的 signature，但仍受 cooldown、phase cap 和 episode cap 约束。

---

## 18.3 Expiry

| Trigger | Expiry |
|---|---:|
| T0 | maturity + 6 actions |
| T1 | maturity + 8 actions |
| T2 | maturity + 8 actions |
| T3 | maturity + 8 actions |
| T4 | maturity + 8 actions |

Phase switch 立即使旧 phase candidate 失效。

---

# 19. Retrieval hard eligibility

Candidate 必须同时满足：

```text
state == MATURE
phase_id == current phase
item_open_mask == current item_open_mask
constraint_mask == current constraint_mask
evidence_signature not delivered
current_step <= expires_step
episode nonempty reads < 5
phase nonempty reads < 2
current_step - last_nonempty_read_step >= 4
```

视觉条件：

```text
exact match
OR strict near retrieval match
```

Strict near：

```text
DL <= 0.05
DE <= 0.10
DV <= 0.045
support_count >= 2
```

T2/T3 额外要求：

```text
workflow_credit < 0.35
contraction_confidence >= 0.55
support_count >= 2
```

Candidate 在成熟后若产生：

```text
anchor gain >= 0.15
trusted durable escape
phase/mask change
```

必须在评分前失效。

---

# 20. Retrieval score

## 20.1 Visual match component

\[
M=
\begin{cases}
1.00,& exact\\
0.85,& strict\ near\\
0,& otherwise
\end{cases}
\]

## 20.2 Evidence strength

\[
E\in[0,1]
\]

由各 trigger 规则给出：

- T0：partial obligation evidence；
- T1：\(C_{bad}\)；
- T2：\(E_{route}\)；
- T3：\(E_F\)；
- T4：最大 bad evidence，最低 0.65。

## 20.3 Contraction confidence

\[
C\in[0,1]
\]

- T0：0.75；
- T1：同一 branch 重复时取 1.0；
- T2：\(C_{route}\)；
- T3：\(C_F\)；
- T4：0.70。

## 20.4 Obligation relevance

设：

- open nonpersistent anchor 的 specificity 总和为 \(W_o\)；
- persistent constraint 的 specificity 总和为 \(W_c\)；
- 所有 anchors specificity 总和为 \(W_{all}\)。

\[
O=
\begin{cases}
1,& W_{all}=0\\
\min\left(
1,
\frac{W_o+0.75W_c}{W_{all}}
\right),& otherwise
\end{cases}
\]

## 20.5 No-gain

\[
G
=
1-\min\left(1,\frac{anchor\_gain}{0.15}\right)
\]

## 20.6 Freshness

\[
F
=
e^{-(step-maturity\_step)/8}
\]

## 20.7 Workflow penalty

\[
X=workflow\_credit
\]

对 T0、T1、T4，若无 route workflow，则 \(X=0\)。

## 20.8 Final score

\[
Score
=
M
\left(
0.32E+
0.28C+
0.18O+
0.12G+
0.10F
\right)
-
0.08X
\]

读取阈值：

\[
\boxed{Score\ge0.70}
\]

---

## 20.9 排序

候选按以下顺序排序：

1. Score 降序；
2. trigger priority：
   - T0 = 5
   - T2 = 4
   - T1 = 3
   - T4 = 2
   - T3 = 1
3. exact 优先于 near；
4. visual distance 升序；
5. maturity step 降序；
6. trigger ID 字典序。

一次 `read()` 最多输出一个 memory block。

---

# 21. Rendering template

## 21.1 固定模板

```text
A11 frontier; past visible evidence only, current screen wins.
Open: {OPEN}. Constraint: {CONSTRAINT}. Evidence: {EVIDENCE}.
Confirmed by 2+ adverse observations after navigation credit. Reassess another action family or target; retry is allowed. Nothing is blocked or selected.
```

---

## 21.2 动态字段预算

| 字段 | Max chars | Max UTF-8 bytes |
|---|---:|---:|
| `OPEN` | 40 | 96 |
| `CONSTRAINT` | 44 | 112 |
| `EVIDENCE` | 72 | 160 |
| 完整 block | 420 | 720 |

若第一次渲染超限，使用 fallback：

```text
OPEN <= 28 chars
CONSTRAINT <= 32 chars
EVIDENCE <= 52 chars
```

若 fallback 仍超限，抛出 `A11IntegrityError`，不得静默截掉固定边界句。

---

## 21.3 Open rendering

最多显示两个 unresolved nonpersistent anchors：

```text
"Bike Repairs", "Public Transit" (+1)
```

若没有：

```text
task completion is not established
```

---

## 21.4 Constraint rendering

最多显示一个 constraint：

```text
use "zucchini" in directions
```

若多于一个：

```text
use "zucchini" in directions (+1)
```

若无 constraint：

```text
none
```

---

## 21.5 Evidence rendering

### T0

```text
"Tuition Fees" gained local support; another item stayed open after leaving
```

### T1

```text
tap lower-middle had no/negligible screen change 2x
```

### T2

```text
the same route closed 2x without goal-coupled or visible work
```

或：

```text
a closed route was followed by the same bad branch without goal gain
```

### T3

```text
4 visits/8 actions; 3 adverse receipts; two branches repeated
```

### T4

```text
the same text was re-entered after a confirmed bad outcome
```

---

## 21.6 禁止文本

Memory block 不得包含：

```text
completed
success
verified by evaluator
must click
do not click
blocked
forbidden
terminate now
the correct action is
```

固定尾句中的：

```text
Nothing is blocked or selected.
```

是边界声明，允许出现。

---

# 22. 更新、合并、衰减与淘汰

## 22.1 Frontier merge

只有同时满足：

```text
same phase
same item_open_mask
same constraint_mask
DV <= 0.035
```

才合并。

若多个候选：

```text
smallest DV
then most recent
then frontier_id lexicographic
```

每个 frontier 最多 3 个 exemplar。新 descriptor 与全部 exemplar 的 \(D_V>0.02\) 才加入。

---

## 22.2 Branch merge

只有以下字段完全相同才合并：

```text
canonical_family
intent_class
target_anchor_mask
```

---

## 22.3 Route revision

第一次 route：

```text
PROVISIONAL_ADVERSE_RETURN
OR NOVEL_EXPLORATION_RETURN
OR WORKFLOW_ADVANCE
```

后续 confirmation 可以把旧 provisional route 修订为 confirmed adverse。

修订发生在 confirmation step，不能回写旧 read 的知识状态。

---

## 22.4 Anchor event eviction

每个 anchor 超过 6 个 event：

1. 保留最新负证据；
2. 计算当前绝对衰减贡献；
3. 淘汰贡献最小者；
4. 平局淘汰最旧；
5. 再按 event kind 字典序。

---

## 22.5 Branch eviction

超过 5 个 branch：

\[
U_b
=
2C_{bad}
+
C_{escape}
+
0.5\mathbf1[target\ mask\ intersects\ current\ obligation]
+
e^{-(s-last)/8}
\]

淘汰最小 \(U_b\)，平局按最旧、再按 ID。

---

## 22.6 Frontier eviction

超过 16：

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

- \(A_f=1\)：当前 frontier；
- \(J_f\)：与当前 masks 的 weighted Jaccard；
- \(E_f\)：有效 evidence strength；
- \(T_f=1\)：存在 mature undelivered trigger。

淘汰最低值。

---

## 22.7 Closed route eviction

超过 12：

\[
U_r
=
2\mathbf1[confirmed]
+
1.5\mathbf1[post\ return\ watch]
+
evidence\_strength
+
e^{-(s-return\_step)/8}
\]

淘汰最低值；平局最旧。

---

## 22.8 Trigger eviction

超过 8：

\[
U_t
=
evidence\_strength
+
contraction\_confidence
+
O
+
e^{-(s-maturity)/8}
+
B_{kind}
\]

```text
T0 0.25
T2 0.20
T1 0.15
T4 0.10
T3 0.05
```

优先淘汰：

```text
PROVISIONAL
then lowest utility
then oldest
then trigger_id
```

---

# 23. `read(context)` 伪代码

```python
def read(self, context=None):
    context = context or {}

    step = self.read_count
    self.read_count += 1

    goal = str(context.get("goal") or "")
    self._initialize_goal_once(goal)

    # Whitelist: only model-visible pixels.
    before = dict(context.get("before") or {})
    pixels = visible_rgb_only(before)
    descriptor = describe_visual_state(pixels)

    self._register_decision_visit(
        descriptor=descriptor,
        step=step,
        phase_id=self.phase_id,
        item_open_mask=self.item_open_mask(),
        constraint_mask=self.constraint_mask(),
    )

    self._refresh_anchor_confidences(step)
    self._refresh_branch_confidences(step)

    current_item_mask = self.item_open_mask()
    current_constraint_mask = self.constraint_mask()

    self._invalidate_stale_candidates(
        step=step,
        phase_id=self.phase_id,
        item_open_mask=current_item_mask,
        constraint_mask=current_constraint_mask,
    )

    if self.nonempty_read_count >= 5:
        return "", read_audit(reason="episode_read_cap")

    if self.phase_nonempty_read_count >= 2:
        return "", read_audit(reason="phase_read_cap")

    if (
        self.last_nonempty_read_step is not None
        and step - self.last_nonempty_read_step < 4
    ):
        return "", read_audit(reason="cooldown")

    ranked = []

    for candidate in self.trigger_candidates:
        if candidate.state != "MATURE":
            continue

        if candidate.phase_id != self.phase_id:
            continue

        if candidate.item_open_mask != current_item_mask:
            continue

        if candidate.constraint_mask != current_constraint_mask:
            continue

        if candidate.evidence_signature in self.delivered_signatures:
            continue

        if step > candidate.expires_step:
            continue

        match_kind, distance = retrieval_visual_match(
            candidate.expected_descriptor_ref,
            descriptor,
            support_count=candidate.support_count,
        )

        if match_kind == "NONE":
            continue

        if candidate.kind in {"CONFIRMED_ROUTE_TRAP", "CONTRACTED_FRONTIER"}:
            if candidate.support_count < 2:
                continue
            if candidate.workflow_credit >= 0.35:
                continue
            if candidate.contraction_confidence < 0.55:
                continue

        frontier = self.frontiers.get(candidate.query_frontier_id)
        if frontier is not None and frontier.read_count_in_phase >= 2:
            continue

        score, components = retrieval_score(
            candidate=candidate,
            match_kind=match_kind,
            current_step=step,
            anchors=self.anchors,
        )

        if score < 0.70:
            continue

        ranked.append(
            (
                -score,
                -TRIGGER_PRIORITY[candidate.kind],
                0 if match_kind == "EXACT" else 1,
                distance,
                -candidate.maturity_step,
                candidate.trigger_id,
                candidate,
                components,
            )
        )

    if not ranked:
        return "", read_audit(reason="no_eligible_candidate")

    ranked.sort(key=lambda item: item[:6])
    selected = ranked[0][6]
    components = ranked[0][7]
    score = -ranked[0][0]

    rendered = render_a11(
        selected,
        anchors=self.anchors,
        max_chars=420,
        max_utf8_bytes=720,
    )

    assert len(rendered) <= 420
    assert len(rendered.encode("utf-8")) <= 720

    selected.state = "DELIVERED"
    selected.delivered = True

    self.nonempty_read_count += 1
    self.phase_nonempty_read_count += 1
    self.last_nonempty_read_step = step

    self.delivered_signatures.append(selected.evidence_signature)
    self.delivered_signatures = self.delivered_signatures[-12:]

    frontier = self.frontiers.get(selected.query_frontier_id)
    if frontier is not None:
        frontier.read_count_in_phase += 1

    event = create_read_event(
        step=step,
        candidate=selected,
        score=score,
        components=components,
        rendered=rendered,
    )
    self.read_events.append(event)
    self.read_events = self.read_events[-5:]

    return rendered, read_audit(
        reason="selected",
        selected=selected,
        score=score,
        components=components,
        rendered=rendered,
    )
```

---

# 24. `observe_step(...)` 伪代码

```python
def observe_step(self, **kwargs):
    self.write_attempt_count += 1

    step = int(kwargs["source_step"])
    if step != self.last_observed_step + 1:
        raise A11IntegrityError("non-monotonic source_step")

    # Strict input whitelist.
    before_pixels = visible_rgb_only(dict(kwargs.get("before") or {}))
    after_pixels = visible_rgb_only(dict(kwargs.get("after") or {}))
    action = validate_canonical_action(
        dict(kwargs.get("canonical_action") or {})
    )
    summary = compact_text(
        kwargs.get("action_summary") or "",
        limit=256,
    )

    before_desc = describe_visual_state(before_pixels)
    after_desc = describe_visual_state(after_pixels)
    changed_fraction = changed_pixel_fraction(
        before_pixels,
        after_pixels,
    )

    self._refresh_anchor_confidences(step)
    self._refresh_branch_confidences(step)

    old_item_mask = self.item_open_mask()
    old_constraint_mask = self.constraint_mask()

    source = self._match_or_create_frontier(
        descriptor=before_desc,
        phase_id=self.phase_id,
        item_open_mask=old_item_mask,
        constraint_mask=old_constraint_mask,
        step=step,
    )

    intent = classify_intent(summary, action)
    target_mask = target_anchor_mask(
        summary,
        action,
        self.anchors,
    )

    branch_key = canonicalize_branch(
        action=action,
        intent_class=intent,
        target_anchor_mask=target_mask,
    )

    branch, branch_created = source.get_or_create_branch(
        branch_key,
        step=step,
    )

    outcome = classify_immediate_outcome(
        before_pixels,
        after_pixels,
        before_desc,
        after_desc,
        changed_fraction,
    )

    receipt = create_attempt_receipt(
        step=step,
        source=source,
        branch=branch,
        outcome=outcome,
        action=action,
        target_mask=target_mask,
    )

    self.attempt_receipts.append(receipt)
    self.attempt_receipts = self.attempt_receipts[-32:]

    if outcome == "DEPARTURE_PENDING":
        self.pending_routes.append(
            create_pending_route(
                receipt=receipt,
                source=source,
                branch=branch,
                source_descriptor=before_desc,
                base_anchor_confidences=current_anchor_confidences(),
                entry_attempt_count_before=branch.attempt_count - 1,
                entry_bad_confidence=branch.failure_confidence,
            )
        )
        self._enforce_pending_route_capacity()
    else:
        self._record_immediate_outcome(
            branch,
            outcome,
            step,
        )

    anchor_events = derive_anchor_events(
        step=step,
        summary=summary,
        action=action,
        target_mask=target_mask,
        intent=intent,
        outcome=outcome,
    )
    self._apply_anchor_events(anchor_events)

    self._append_hop_to_open_routes(
        step=step,
        branch=branch,
        intent=intent,
        target_mask=target_mask,
        outcome=outcome,
        before_desc=before_desc,
        after_desc=after_desc,
    )

    route_resolutions = self._resolve_routes(
        current_step=step,
        current_after_descriptor=after_desc,
    )

    closed_route_records = []

    for resolution in route_resolutions:
        route = self._build_closed_route_record(resolution)

        route.goal_coupled = any(
            hop.goal_coupled for hop in route.route_hops
        )
        route.visible_work = any(
            hop.visible_work for hop in route.route_hops
        )
        route.target_progress = detect_target_progress(route)
        route.entry_novel = (
            route.entry_attempt_count_before == 0
        )
        route.route_core_novel = (
            no_prior_route_core(route.route_core_signature)
        )

        route.novelty_workflow_credit = (
            0.30 * int(route.entry_novel)
            + 0.25 * int(route.route_core_novel)
            + 0.20 * int(route.goal_coupled)
            + 0.15 * int(route.visible_work)
            + 0.10 * int(route.target_progress)
        )

        route.residual_work_credit = (
            0.40 * int(route.goal_coupled)
            + 0.35 * int(route.visible_work)
            + 0.25 * int(route.target_progress)
        )

        route.classification = classify_initial_route(
            route=route,
            entry_branch=branch_for_route(route),
        )

        self.closed_routes.append(route)
        self.closed_routes = self.closed_routes[-12:]
        closed_route_records.append(route)

        if route.classification not in {
            "WORKFLOW_ADVANCE",
            "NOVEL_EXPLORATION_RETURN",
        }:
            self._create_post_return_watch(route)

    # Confirmation can revise provisional route evidence.
    route_confirmations = self._confirm_repeated_route_cores(
        current_step=step,
    )
    route_confirmations += self._resolve_post_return_watches(
        current_step=step,
        current_source=source,
        current_branch=branch,
        current_outcome=outcome,
    )

    for confirmation in route_confirmations:
        self._mark_routes_confirmed_adverse(confirmation)
        self._add_confirmed_return_to_branches(confirmation)
        self._apply_confirmed_route_anchor_events(confirmation)

    self._refresh_anchor_confidences(step)
    self._refresh_branch_confidences(step)

    new_item_mask = self.item_open_mask()
    new_constraint_mask = self.constraint_mask()

    phase_switch = self._should_switch_phase(
        old_item_mask=old_item_mask,
        new_item_mask=new_item_mask,
        intent=intent,
        outcome=outcome,
        before_descriptor=before_desc,
        after_descriptor=after_desc,
        step=step,
    )

    if phase_switch:
        self.phase_id += 1
        self.phase_nonempty_read_count = 0
        # episode-global cooldown 不随 phase 重置
        self._invalidate_old_phase_candidates()

    destination = self._match_or_create_frontier(
        descriptor=after_desc,
        phase_id=self.phase_id,
        item_open_mask=self.item_open_mask(),
        constraint_mask=self.constraint_mask(),
        step=step + 1,
    )

    new_candidates = []

    t0 = self._evaluate_t0(step, destination)
    if t0 is not None:
        new_candidates.append(t0)

    t1 = self._evaluate_t1(
        step=step,
        frontier=source,
        branch=branch,
        action=action,
    )
    if t1 is not None:
        new_candidates.append(t1)

    for confirmation in route_confirmations:
        t2 = self._evaluate_t2(
            step=step,
            confirmation=confirmation,
        )
        if t2 is not None:
            new_candidates.append(t2)

    t3 = self._evaluate_t3(
        step=step,
        frontier=source,
    )
    if t3 is not None:
        new_candidates.append(t3)

    t4 = self._evaluate_t4(
        step=step,
        frontier=source,
        action=action,
        branch=branch,
    )
    if t4 is not None:
        new_candidates.append(t4)

    enqueued = []
    for candidate in new_candidates:
        if self._enqueue_if_novel(candidate):
            enqueued.append(candidate.trigger_id)

    self._invalidate_contradicted_candidates(step)
    evictions = self._enforce_capacities(step)

    self._update_post_read_behavior(
        step=step,
        source_frontier=source,
        branch=branch,
        branch_created=branch_created,
        after_descriptor=after_desc,
    )

    self.last_observed_step = step

    written = any([
        branch_created,
        anchor_events,
        route_resolutions,
        route_confirmations,
        phase_switch,
        enqueued,
        evictions,
    ])

    if written:
        self.write_success_count += 1

    return {
        "written": bool(written),
        "source_step": step,
        "source_frontier_id": source.frontier_id,
        "destination_frontier_id": destination.frontier_id,
        "branch_id": branch.branch_id,
        "immediate_outcome": outcome,
        "route_resolutions": audit_routes(route_resolutions),
        "route_confirmations": audit_confirmations(route_confirmations),
        "anchor_events": audit_anchor_events(anchor_events),
        "phase_switch": phase_switch,
        "phase_id_after": self.phase_id,
        "trigger_ids_enqueued": enqueued,
        "evictions": evictions,
    }
```

---

# 25. `audit_record()` schema

必须记录：

```text
schema
mechanism_id
experiment_id
parent_evidence_commit
implementation_commit

parameters
  all capacities
  all thresholds
  all score weights
  route horizons
  near/exact thresholds
  parser grammar version

decision_boundary
  allowed_inputs
  ignored_snapshot_fields
  model_calls_added
  evaluator_used_for_decision
  hidden_ui_used_for_decision
  future_information_used
  guard_enabled
  action_override_count
  forced_termination_count
  history_summary_method

goal
  goal_sha256
  operation_class
  anchor_count
  item_anchor_count
  value_anchor_count
  constraint_anchor_count
  anchors
  excluded_app_spans

phase
  current_phase_id
  item_open_mask
  constraint_mask
  phase_switch_count
  phase_switch_events

frontiers
  current_count
  maximum_observed
  merge_count
  eviction_count
  records

branches
  current_count
  maximum_observed
  confirmed_adverse_return_count
  benign_return_count

attempts
  retained_count
  raw_outcome_counts
  receipts

routes
  pending_count
  closed_count
  workflow_advance_count
  novel_exploration_return_count
  provisional_adverse_count
  confirmed_adverse_count
  post_return_confirmation_count
  route_recurrence_confirmation_count
  records

triggers
  candidate_count
  provisional_count
  mature_count
  delivered_count
  invalidated_count
  expired_count
  duplicate_suppressed_count
  created_counts_by_kind
  delivered_counts_by_kind
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
  max_rendered_chars
  max_rendered_utf8_bytes
  max_rendered_tokens
  serialized_audit_bytes
```

---

# 26. 每条 read 的审计字段

```text
read_id
step
trigger_id
trigger_kind
candidate_state_before_read
maturity_step
support_count
support_receipt_ids
frontier_id
phase_id
item_open_mask
constraint_mask
visual_match_kind
visual_distance
score
score_components
workflow_credit
contraction_confidence
evidence_signature
rendered_text
rendered_sha256
rendered_chars
rendered_utf8_bytes
rendered_tokens
retrieved_anchor_ids
retrieved_constraint_ids
retrieved_branch_ids
retrieved_route_ids

next_action_branch_id
next_action_was_novel
escaped_frontier_within_3
returned_within_4
anchor_confidence_delta_within_4
constraint_confidence_delta_within_4
```

后五项只能在对应后续 step 已真实发生后更新。

---

# 27. Controller 与 runner 集成

## 27.1 新实现文件

```text
implementation/src/raven_m/official_qwen_mobile/
  a11_confirmed_route_contraction.py
  a11_contract.py

implementation/scripts/
  replay_a11_offline_traces.py
  preflight_a11.py
  qualify_a11_live_server.py
  start_a11_server.sh

implementation/configs/
  a11_confirmed_route_contraction_hard_seed20260806.json

implementation/tests/official_qwen_mobile/
  test_a11_anchor_parser.py
  test_a11_route_contraction.py
  test_a11_retrieval.py
  test_a11_controller_integration.py
  test_a11_contract.py
  test_a11_offline_replay.py
  test_a11_adversarial.py
```

## 27.2 Arm

Runner 增加：

```text
--arm a11
```

不得覆盖 `--arm a10`。

## 27.3 Memory construction

```python
memory = ConfirmedRouteContractionECOBFMemory(
    max_anchors=8,
    max_anchor_events=6,
    max_frontiers=16,
    max_visual_exemplars=3,
    max_branches_per_frontier=5,
    max_attempt_receipts=32,
    max_pending_routes=4,
    max_closed_routes=12,
    max_post_return_watches=4,
    max_escape_watches=2,
    max_typed_value_keys=12,
    max_trigger_candidates=8,
    max_delivered_signatures=12,
    max_nonempty_reads=5,
    max_reads_per_phase=2,
    read_cooldown_steps=4,
    max_chars=420,
    max_utf8_bytes=720,
    retrieval_score_threshold=0.70,
)
```

## 27.4 Controller

```python
OfficialQwenMobileController(
    client=client,
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

A11 不实现：

```text
history_summary()
record_protocol()
action_filter()
guard()
override()
```

Memory block 只进入当前 user turn，不写入后续官方 action-summary history。

---

# 28. 不泄漏证明

## 28.1 白名单抽取

`read()` 只能访问：

```python
context["goal"]
context["before"]["pixels"]
```

`observe_step()` 只能访问：

```python
source_step
action_summary
canonical_action
before["pixels"]
after["pixels"]
source_response_sha256  # audit only
source_screenshot_sha256  # audit only
```

Controller 提供的 `transition` 字典必须完全忽略。

## 28.2 Hidden-field invariance

对任意相同：

\[
(q,I_t,a_t,u_t,I_{t+1})
\]

但不同隐藏字段 \(H_1,H_2\)，必须满足：

\[
U(M,\ldots,H_1)=U(M,\ldots,H_2)
\]

\[
R(M,\ldots,H_1)=R(M,\ldots,H_2)
\]

测试必须比较：

```text
read text
read score
trigger IDs
route classifications
serialized decision state
```

全部完全相同。

## 28.3 无未来信息

- Route return 只有在返回截图实际出现后才能记录；
- route recurrence 只有第二条 route 实际闭合后才能确认；
- post-return reversion 只有后续坏 branch outcome 实际解析后才能确认；
- 旧 read audit 不得因未来确认而重写。

---

# 29. 有界性、复杂度与成本

## 29.1 状态上界

最多：

```text
8 anchors
48 anchor events
16 frontiers
48 visual exemplars
80 branches
32 attempt receipts
4 pending routes
16 route hops
12 closed routes
4 post-return watches
2 escape watches
12 typed-value keys
24 typed-value occurrences
8 trigger candidates
12 delivered signatures
17 screen trace entries
5 read events
8 phase events
```

## 29.2 Serialized audit

正式测试必须构造最大状态并断言：

```text
len(
  json.dumps(
    audit_record,
    ensure_ascii=True,
    sort_keys=True,
    separators=(",", ":"),
  ).encode("utf-8")
) <= 131072
```

即：

```text
serialized audit <= 128 KiB
```

任何越界都是 preflight failure。

## 29.3 时间复杂度

RGB descriptor 和 pixel diff：

\[
O(HW)
\]

每 step 最多比较：

```text
16 frontiers × 3 exemplars
```

每次 descriptor comparison 是固定的：

```text
144 luma cells + 263 edge bits
```

其余处理上限：

```text
8 anchors
80 branches
32 receipts
12 closed routes
8 triggers
```

因此每 step：

\[
O(HW)+O(1)
\]

其中 \(O(1)\) 的常数由本文容量硬限制。

## 29.4 Prompt 成本

单 read：

```text
<= 420 chars
<= 720 UTF-8 bytes
<= 192 frozen-tokenizer tokens
```

单 episode：

```text
<= 5 reads
<= 2,100 memory characters
<= 960 memory tokens
```

完整 19 题理论上界：

```text
<= 39,900 memory characters
<= 18,240 memory tokens
```

额外模型调用：

```text
0
```

---

# 30. A11 是否要求 A0 四条历史成功轨迹绝对 0 read

## 30.1 正式答案

**不再要求绝对 0 read。**

A11 将绝对静默门替换为：

```text
competent-trajectory sparse-and-mature gate
```

## 30.2 科学理由

绝对 0 read 只检验“历史 action sequence 上没有 prompt perturbation”，但不能检验：

- 读取是否有害；
- 读取是否会改变 live policy；
- 一条成熟、合理的早期循环证据是否应该被完全禁止；
- 新机制是否只因对四条已知轨迹过拟合而静默。

Offline replay 使用的是冻结 action sequence。模型并不会看到新 memory 后重新采样，所以 replay 无法直接证明 prompt intervention 无害。真正的能力保持必须由 fresh live 4/4 gate 检验。

因此 v2 使用两级保护：

1. 历史 competent trajectories 上要求严格稀疏、成熟、无单次 route 误报；
2. fresh live generation 上要求真正 4/4。

---

## 30.3 新 competent-trajectory gate

冻结的四条 A0 历史成功轨迹共有 67 个 replayed actions：17、31、16、3。

A11 必须满足：

```text
per_episode_nonempty_reads <= 1
total_nonempty_reads_across_four <= 2
total_read_density <= 0.04
total_rendered_chars_across_four <= 840
```

并且：

```text
immature_candidate_delivery_count == 0
single_closed_route_delivery_count == 0
first_route_core_delivery_count == 0
normal_navigation_exemption_violation_count == 0
support_count_below_two_delivery_count == 0
same_signature_redelivery_count == 0
```

每个 read 必须满足：

```text
candidate.state == MATURE
candidate.support_count >= 2
```

A11 在这四条轨迹上得到 0 read、1 read 或 2 reads 均可能通过；超过上述任一上限则失败。

该门是全局公式门，不得按任务名、app 名、页面名或 screen hash 设置例外。

---

# 31. Zero-generation real-trace replay

## 31.1 轨迹来源

A11 使用与 v1 相同的 27 个真实 episode 来源：

```text
5 A0 episodes
1 A1 Recipe episode
19 A6 episodes
1 A8-v2 Expense episode
1 A9 Retro episode
```

源规范已冻结这些 episode 和 suite provenance。

A11 可以复用原始 trace bytes 和 manifest，但必须：

- 重新验证全部 1,668 个文件；
- 重新验证 442,138,413 bytes；
- 使用新的 replay script；
- 生成新的 `A11_OFFLINE_REPLAY_REPORT.json`；
- 不覆盖 A10-v1 report；
- 不把 v1 trigger/read 结果拼接为 v2 结果；
- `generation_calls=0`。

---

## 31.2 独立 loop qualification classifier

Replay script 必须实现一个与 memory trigger 创建逻辑分离的 deterministic classifier。

它只能使用：

```text
query
real RGB
canonical actions
action summaries
step order
```

不得读取：

```text
task reward
final success
A10-v1 trigger
A11 trigger
task-specific whitelist
```

### Branch-pair segment

满足：

```text
same matched frontier
same branch key
same phase/masks
two adverse no-progress receipts
anchor gain < 0.15
```

Deadline：

```text
the read immediately after the second adverse receipt,
and before a third same-branch attempt
```

### Route-pair segment

满足：

```text
same route_core_signature closes twice within 12 actions
both anchor gain < 0.10
both residual work credit < 0.35
same phase/masks
```

Deadline：

```text
the read immediately after the second route closure
```

### Post-return segment

满足：

```text
one closed route
followed within 2 source actions by same/trusted-bad branch
resolved adverse
no anchor gain
```

Deadline：

```text
the first read after adverse resolution
```

重叠 segment 按：

```text
frontier
branch or route core
phase
masks
```

去重。

---

# 32. Real-trace replay 资格门

## 32.1 File integrity gate

必须：

```text
verified_file_count == 1668
verified_total_bytes == 442138413
verification_errors == []
generation_calls == 0
```

若源 manifest 因平台路径表示方式变化，只允许 canonical JSON hash；原始内容 SHA 不得变化。最新父提交已经将 A10 provenance 改为平台稳定的 canonical JSON 绑定。

---

## 32.2 A0 competent gate

使用四条历史成功轨迹。

必须满足 §30.3 全部条件。

不再要求绝对 0 read。

---

## 32.3 A6 activation gate

要求：

```text
independent_qualifying_segments >= 20
qualified_segments / qualifying_segments >= 0.80
```

一个 segment qualified 当且仅当：

```text
a mature candidate exists by its frozen deadline
AND an eligible read occurs by the deadline
AND before the third repeated bad branch where applicable
```

还必须满足：

```text
each episode nonempty reads <= 5
each phase reads <= 2
cooldown >= 4
no single-route T2 delivery
```

A10-v1 的 22/23 只作为设计证据；A11 必须重新计算，不得继承该通过率。A10-v1 的 95.65% 表明重复坏 branch 证据在冻结轨迹中确实存在，因此 v2 可以提高 T2/T3 精度，而不必依赖单次 route 维持全部 activation。

---

## 32.4 A8-v2 Expense gate

必须：

```text
independent_qualifying_segments >= 1
first mature candidate <= earliest qualifying deadline
first eligible read <= earliest qualifying deadline + 1
first eligible read step <= floor(0.75 * native_max_steps)
nonempty reads <= 5
```

还必须：

```text
single-route delivery count == 0
all delivered candidates support_count >= 2
```

A8-v2 原 live 轨迹曾发生 14 次非空读取并最终失败，因此 v2 必须在保持及时性的同时显著低于该暴露次数。

---

## 32.5 A9 Retro gate

必须：

```text
independent_qualifying_segments >= 1
first mature candidate <= earliest qualifying deadline
first eligible read <= earliest qualifying deadline + 1
first eligible read <= original A9 first canary step + 2
nonempty reads <= 5
```

冻结 A9 Retro report 中原 canary 首次读取 step 由 source evidence 读取，不能传给 memory，只能由 replay evaluator 事后比较。

若 A11 因确认式 T2 延迟，但 T1 已在更早的第二次 no-progress 成熟，则以最早 qualifying segment 为准。

---

## 32.6 A1 Recipe constraint gate

对 query：

```text
Delete the recipes from Broccoli app that use zucchini in the directions.
```

parser 必须得到：

```text
constraint_anchor_count == 1
```

该 anchor 必须完全满足：

```json
{
  "role": "CONSTRAINT",
  "predicate": "USE",
  "constraint_value": "zucchini",
  "constraint_scope": "DIRECTIONS",
  "negated": false,
  "persistent_open": true
}
```

并且：

```text
no anchor contains "Broccoli"
no anchor contains "app"
no generic verb-only anchor
no scope-only anchor
```

该 replay gate 不再要求“多个目标”，也不强制成功轨迹必须触发 memory。

额外稀疏要求：

```text
nonempty_reads <= 2
single_route_delivery_count == 0
all delivered candidates support_count >= 2
```

这消除了 v1 的 parser/gate 矛盾。

---

## 32.7 不过拟合门

Production memory module 必须通过静态扫描：

```text
no 19 task class names
no episode IDs
no frozen screen hashes
no frozen goal hashes
no literal "zucchini"
no literal "Broccoli"
no literal "RetroSavePlaylist"
no literal "SimpleCalendarAddOneEvent"
```

允许：

- 通用 field lexicon 中的 `directions`；
- 通用 predicate `use`；
- contract/runner 中用于 task order 的 task class 名；
- test fixtures 中的正例文本。

Replay role、reward 和 task name 不得传入 memory。

---

# 33. 对抗性测试矩阵

## 33.1 Parser tests

| ID | 测试 | 断言 |
|---|---|---|
| P01 | exact Recipe query | 1 个正确 structured constraint |
| P02 | `that take 2 hrs to prepare` | TAKE constraint，numeric duplicate 被抑制 |
| P03 | quoted constraint value | structured constraint 优先 |
| P04 | negated constraint | `negated=true` |
| P05 | app span | app name 不成为 anchor |
| P06 | scope-only | 拒绝 |
| P07 | predicate-only | 拒绝 |
| P08 | 7-token value | 拒绝 |
| P09 | 6-token value | 接受 |
| P10 | Unicode/hyphen value | 稳定解析 |
| P11 | same semantic constraint twice | 去重 |
| P12 | constraint plus list | priority/order 固定 |
| P13 | generic prepositional phrase | 不生成 constraint |
| P14 | `for skiing activities` | 不生成 relational constraint |
| P15 | `in Downloads` | 不生成 constraint |
| P16 | `use Simple Gallery Pro` | 无 relative head，不生成 |
| P17 | app overlap | 拒绝 value |
| P18 | target mask value match | 置位 |
| P19 | target mask scope-only | 不置位 |
| P20 | target mask app-only | 不置位 |

---

## 33.2 Route tests

| ID | 测试 | 断言 |
|---|---|---|
| R01 | first novel closed route | 无 mature T2 |
| R02 | first route \(X=0.55\) | `NOVEL_EXPLORATION_RETURN` |
| R03 | route with anchor gain | `WORKFLOW_ADVANCE` |
| R04 | route with target progression | `WORKFLOW_ADVANCE` |
| R05 | route with type/commit visible work | residual work \(\ge0.35\)，不确认 |
| R06 | same route closes twice | T2 mature |
| R07 | different route core | 不确认同一 T2 |
| R08 | same route after 13 actions | 不构成 12-step recurrence |
| R09 | post-return same bad branch | T2 mature |
| R10 | post-return novel productive branch | 不成熟 |
| R11 | late return revision | 不双计数 |
| R12 | first benign return | 不增加 branch bad confidence |
| R13 | second confirmed return | 两条 route 当前时刻升级 |
| R14 | future information | 首次 route read 前不可见 confirmation |
| R15 | route capacity | 最低 utility 正确淘汰 |

---

## 33.3 Normal navigation tests

必须构造不含真实 task name/page hash 的通用轨迹。

### Settings-like

```text
main page
→ open settings
→ open subsection
→ press back
→ main page
```

第一次 route：

```text
no mature T2
no T3
read == ""
```

### Calendar-like multi-stage

```text
edit form
→ open start-time picker
→ change value
→ return edit form
→ open end-time picker
→ change value
→ return edit form
```

必须：

```text
visible work or target progression detected
no confirmed adverse route
no T2
no T3
```

### Repeated unproductive settings route

同一 settings route 第二次完整重复，且无 goal-coupled action、visible work 或 target progress：

```text
T2 matures on second closure
```

---

## 33.4 T1/T3 tests

| ID | 测试 | 断言 |
|---|---|---|
| C01 | two tap no-progress | T1 mature |
| C02 | one no-progress | 不成熟 |
| C03 | two waits | 不成熟 |
| C04 | three waits | 可成熟 |
| C05 | clear and retype | retry exemption |
| C06 | target mask change | normal repeat |
| C07 | anchor gain after retry | 不成熟 |
| C08 | 3 visits/2 receipts | T3 不成熟 |
| C09 | 4 visits/3 adverse/1 branch | T3 mature |
| C10 | 4 visits/3 receipts but 3 unique branches | T3 不成熟 |
| C11 | 4 visits but local visible work | 不成熟 |
| C12 | trusted escape | T3 不成熟 |
| C13 | ABAB adverse cycle | K=2，满足 contraction 时成熟 |
| C14 | ABC exploration | K=3，不成熟 |
| C15 | last two branches new | 不成熟 |

---

## 33.5 Retrieval tests

| ID | 测试 | 断言 |
|---|---|---|
| Q01 | provisional candidate | 不可读取 |
| Q02 | mature exact | 可评分 |
| Q03 | mature near/support=2 | 可评分 |
| Q04 | near/support=1 | 不可读取 |
| Q05 | DV > 0.045 | 不可读取 |
| Q06 | score 0.699999 | 不读取 |
| Q07 | score 0.700000 | 读取 |
| Q08 | same signature | one-shot |
| Q09 | cooldown 3 | 不读取 |
| Q10 | cooldown 4 | 可读取 |
| Q11 | phase cap 2 | 第 3 次不读 |
| Q12 | episode cap 5 | 第 6 次不读 |
| Q13 | phase switch | old candidate invalid |
| Q14 | workflow credit >=0.35 for T2/T3 | hard ineligible |
| Q15 | candidate ranking | 冻结 tie-break |

---

## 33.6 RGB tests

必须覆盖：

```text
invalid dimensions
invalid channels
float
NaN
negative integer
>255
RGBA
non-contiguous array
all black
all white
top/bottom 4% only change
minor animation
keyboard appearance
loading spinner
same global brightness/different layout
```

---

## 33.7 Leakage tests

对相同 visible input，分别注入不同：

```text
evaluator_reward
task_success
ui_tree
accessibility_nodes
foreground
activity
package
database_state
ground_truth
```

必须得到完全相同：

```text
read text
scores
triggers
routes
serialized decision state
```

---

## 33.8 No-extra-call tests

- Production module AST 禁止 import：

```text
requests
urllib
httpx
openai
transformers
vllm
socket
```

- monkeypatch 所有 `.generate()`、HTTP 和 socket 调用为抛错；
- 运行 parser、route、replay；
- 必须无调用；
- audit：

```text
model_calls_added == 0
```

Tokenizer 只允许在 preflight 外部检查脚本使用，不能在 memory runtime 使用。

---

## 33.9 Action boundary tests

必须断言：

```text
controller.cost_guard is None
controller.source_document_coverage_gate is None
action_override_count == 0
forced_termination_count == 0
model action == executed action
```

---

## 33.10 Capacity tests

| 对象 | 溢出测试 |
|---|---|
| anchors | 第 9 个按冻结排序丢弃 |
| anchor events | 第 7 个按贡献淘汰 |
| frontiers | 第 17 个按 utility 淘汰 |
| branches | 第 6 个按 utility 淘汰 |
| receipts | 第 33 个 FIFO |
| pending routes | 第 5 个先解析/再淘汰最旧 |
| closed routes | 第 13 个按 route utility |
| post-return watches | 第 5 个按 expiry |
| triggers | 第 9 个按 trigger utility |
| reads | 第 6 次空 |
| serialized state | <=128 KiB |

---

# 34. Source freeze

## 34.1 Parent evidence

```text
PARENT_EVIDENCE_COMMIT =
4548b932bc3b189507e1442e312c73c8f35dbdb8
```

## 34.2 Implementation commit

A11 实现完成并生成正式 replay report 后，创建一个 clean commit：

```text
A11_IMPLEMENTATION_COMMIT = <exact 40-hex git SHA>
```

Preflight 必须拒绝：

```text
missing
placeholder
non-40-hex
not current HEAD
parent commit not ancestor
dirty worktree
```

## 34.3 Source closure

至少包含：

```text
GPT_PRO_A11_STANDALONE_MEMORY_DESIGN_2026-08-12.md

implementation/configs/
  androidworld_hard_v2_instances.json
  a11_confirmed_route_contraction_hard_seed20260806.json

implementation/src/raven_m/official_qwen_mobile/
  a11_confirmed_route_contraction.py
  a11_contract.py
  controller.py
  protocol.py
  __init__.py

implementation/scripts/
  run_official_qwen_mobile.py
  run_a678_arm.py
  replay_a11_offline_traces.py
  preflight_a11.py
  qualify_a11_live_server.py
  start_a11_server.sh

implementation/src/raven_m/models/
  vllm_client.py

implementation/src/raven_m/env/
  androidworld_adapter.py

implementation/src/raven_m/multi_framework_benchmark/
  task_instances.py

implementation/tests/official_qwen_mobile/
  all A11 test files
  all adjacent official controller tests

evidence/a11/
  A11_FROZEN_QUERY_SET.json
  A11_OFFLINE_TRACE_SOURCE_SPEC.json
  A11_OFFLINE_TRACE_MANIFEST.json
  A11_OFFLINE_REPLAY_REPORT.json
  A11_TEST_MANIFEST.json

historical immutable inputs:
  evidence/a10/A10_OFFLINE_REPLAY_REPORT.json
  evidence/a10/A10_OFFLINE_TRACE_MANIFEST.json
  evidence/a10/A10_OFFLINE_TRACE_SOURCE_SPEC.json
  evidence/a2/A0_A1_PAIRED_REFERENCE_20260810.json
  evidence/a678/A8_V2_OFFLINE_TRACE_AUDIT_2026-08-11.json
  evidence/a678/A89_INITIAL_GATE_RESULTS_2026-08-12.json
```

A10-v1 report 必须作为 immutable historical input 记录哈希，但不能被修改为 pass。

---

# 35. Zero-generation preflight

新脚本：

```text
implementation/scripts/preflight_a11.py
```

输出：

```text
evidence/a11/A11_ZERO_GENERATION_PREFLIGHT.json
```

## 35.1 必查项目

### Identity

```text
HEAD == A11_IMPLEMENTATION_COMMIT
PARENT_EVIDENCE_COMMIT is ancestor
worktree clean including untracked files
```

### Config

```text
mechanism ID exact
experiment ID exact
model exact
revision exact
seeds exact
sampling exact
system prompt hash exact
task count 19
native max steps unchanged
```

### Causal boundary

```text
extra_model_calls = 0
guard = false
action_override = false
forced_termination = false
evaluator_input = false
hidden_ui_input = false
future_input = false
```

### Tests

- 运行全部 `official_qwen_mobile` tests；
- 运行全部新增 A11 tests；
- `failed=0`；
- `errors=0`；
- `deselected=0`；
- collected node IDs 与 `A11_TEST_MANIFEST.json` 完全一致。

不得只运行新测试子集而忽略 adjacent controller tests。

### Runtime canaries

必须证明：

```text
single closed route -> no read
two no-progress branches -> mature read
second unproductive route -> mature T2
Recipe query -> one structured constraint
hidden fields invariant
audit <=128 KiB
```

### Real replay

```text
A11_OFFLINE_REPLAY_REPORT.status == pass
generation_calls == 0
all gates pass
```

### Tokenizer

使用冻结本地 Qwen tokenizer。

必须覆盖：

- 所有 19 个 query；
- 所有 trigger templates；
- ASCII；
- CJK；
- accented text；
- emoji；
- 最大字段长度。

要求：

```text
max_added_tokens_per_read <= 192
max_added_tokens_per_episode <= 960
```

缺失 tokenizer 只能用于本地诊断，不能正式 pass。当前 A10-v1 preflight 也明确将 missing frozen tokenizer 视为 formal error。

### Static no-overfit scan

按 §32.7 执行。

### Generation counter

```text
generation_calls == 0
```

## 35.2 Preflight 状态

```text
PASS
SCIENTIFIC_PREFLIGHT_FAILURE
PROTOCOL_INVALID
INFRASTRUCTURE_PREFLIGHT_FAILURE
```

### `PROTOCOL_INVALID`

以下情况必须标为 protocol invalid：

- 同一 synthetic trace 被规范同时要求 read 和 no-read；
- 同一 query 被规范同时要求 0 anchor 和非零 anchor；
- 某 trigger 的 hard maturity 条件在数学上不可能达到；
- score threshold 与所有合法成熟 candidate 的理论最大 score 冲突；
- source freeze 出现循环依赖且无法稳定生成；
- 任一 required gate 无确定性实现；
- 需要任务名/page hash 白名单才能通过；
- 需要 evaluator/future 信息才能满足。

Protocol invalid 时不得启动 GPU live generation。

---

# 36. Live server receipt

A11 必须创建全新 receipt，不得复用 A10/A678/A89 receipt。

## 36.1 Launch intent

```text
schema = a11_server_launch_intent_v1
status = launch_pending_live_qualification
```

绑定：

```text
preflight SHA256
source freeze SHA256
implementation commit
model ID
model realpath
model manifest
port
packages
exact process command
```

## 36.2 Live qualification

新脚本必须验证：

```text
preflight.status == pass
preflight.generation_calls == 0
launch intent hash exact
source freeze hash exact
process alive
/proc PID command exact
served model IDs == [frozen model ID]
runtime package versions exact
model realpath exact
model manifest exact
```

Receipt 必须包含：

```text
schema
status
generation_calls = 0
a11_preflight_sha256
a11_source_freeze_sha256
launch_intent_sha256
launch_intent_path
implementation_commit
served_model_id
model_realpath
model_manifest_sha256
pid
process_pid
process_cmdline
host
port
packages
vllm_version
torch_version
transformers_version
served_model_ids_observed
qualification_timestamp
```

Receipt 资格时间不得早于当前时间 60 秒以上，也不得超过 12 小时。现有 A10 contract 已采用 process-alive、command binding、served-model 和 12-hour freshness 检查；A11 保留这一审计模式。

---

# 37. Live generation 启动条件

只有以下全部成立才允许第一条 live generation：

```text
1. A11 implementation commit frozen
2. worktree clean
3. source freeze pass
4. all tests pass
5. real-RGB replay pass
6. parser gate pass
7. competent sparse gate pass
8. A6 activation gate pass
9. A8 timing gate pass
10. A9 timing gate pass
11. tokenizer budget pass
12. no-overfit scan pass
13. preflight.status == pass
14. preflight.generation_calls == 0
15. fresh live receipt.status == pass
16. launch receipt bound to same preflight/source freeze
```

缺少任一项：

```text
live_generation_authorized = false
```

---

# 38. Fresh prospective 4/4 gate

A11 必须使用全新的 suite ID 和 episode IDs。

前四个 valid episodes 依次为：

1. `ExpenseDeleteMultiple2`
2. `RetroSavePlaylist`
3. `SimpleCalendarAddOneEvent`
4. `SportsTrackerTotalDurationForCategoryThisWeek`

每题要求：

```text
evaluator_reward == 1.0
```

任一 scientific failure：

```text
suite_status = stopped_capability_gate_failure
remaining_15_released = false
scientific_rerun = forbidden
```

四题 gate 构成正式 19 题 suite 的前四个 valid episodes；通过后不得再次运行这四题并挑选更好版本。当前 contract 同样冻结了这四题顺序和 fail-fast 逻辑。

---

# 39. Gate 后剩余 15 题顺序

1. `BrowserMultiply`
2. `ExpenseAddMultipleFromGallery`
3. `ExpenseAddMultipleFromMarkor`
4. `MarkorCreateNoteAndSms`
5. `MarkorMergeNotes`
6. `MarkorTranscribeVideo`
7. `OsmAndMarker`
8. `OsmAndTrack`
9. `RecipeAddMultipleRecipesFromImage`
10. `RecipeAddMultipleRecipesFromMarkor`
11. `RecipeAddMultipleRecipesFromMarkor2`
12. `RecipeDeleteMultipleRecipesWithConstraint`
13. `SaveCopyOfReceiptTaskEval`
14. `SportsTrackerActivitiesOnDate`
15. `SportsTrackerTotalDistanceForCategoryOverInterval`

该顺序与当前冻结 contract 一致。

不得根据中间结果调整顺序。

---

# 40. Infrastructure invalid 与 resume

## 40.1 Infrastructure invalid

仅以下情况可标记：

```text
vLLM process crash
HTTP transport fails before complete response
transport_attempts != 1
ADB disconnect
emulator crash
UIAutomator state acquisition failure
task reset/initialization exception
invalid or corrupt screenshot
evaluator exception
evaluator non-finite/missing result
frozen source/config/model receipt mismatch
artifact write corruption before evaluator result is committed
```

## 40.2 Scientific failure

以下不得标 infrastructure invalid：

```text
reward 0
partial reward below success
max_steps
model loop
wrong app
wrong object
wrong field
wrong canonical action
invalid model response format
model terminate
model answer error
memory misleads model
memory never activates
memory activates but behavior does not improve
```

## 40.3 Resume 规则

### Episode 间基础设施中断

若前一 valid episode 已完整写入 evaluator result 和 hashes：

```text
resume from next frozen task
do not rerun completed valid episodes
```

### Episode 中基础设施中断

```text
preserve invalid attempt artifacts
mark infrastructure_invalid
restart same task from clean task initialization
same seeds
same source/model/config
link replacement episode to invalid attempt
```

### 重试上限

每个 task 最多允许：

```text
2 infrastructure-invalid attempts
```

即最多第 3 次 attempt 可以成为 valid episode。

第三次仍 infrastructure invalid：

```text
suite_status = infrastructure_incomplete
live result not scientifically closed
```

### Scientific failure

不得重跑，不得 resume 为第二个 policy sample。

### 代码或环境变化

以下任一改变必须创建新 experiment：

```text
mechanism code
threshold
parser
descriptor
capacity
template
model
revision
sampling
prompt
task seed
generation seed
task manifest
native max steps
```

---

# 41. Exact 19/19 closure

正式完整结果必须满足：

```text
exactly 19 valid episodes
exact frozen order
one valid episode per task
unique episode IDs
task_seed == 20260806 for all
finite evaluator reward for all
transport_attempts == 1 for every valid model call
all invalid attempts have exact resolution links
no unresolved lifecycle error
```

已完成 valid episode 不得与 replication suite 或旧 arm episode 拼接。

---

# 42. Result schema

```json
{
  "schema": "a11_crc_ecobf_result_v1",
  "mechanism_id": "a11_confirmed_route_contraction_ecobf_v1",
  "experiment_id": "A11_CRC_ECOBF_QWEN3VL32B_AW_HARD_T20260806_G3407_V1",
  "parent_evidence_commit": "4548b932bc3b189507e1442e312c73c8f35dbdb8",
  "implementation_commit": "<40-hex>",
  "source_freeze_sha256": "<sha256>",
  "preflight_sha256": "<sha256>",
  "live_receipt_sha256": "<sha256>",
  "historical_a10v1_report_sha256": "<sha256>",
  "task_seed": 20260806,
  "generation_seed": 3407,
  "gate": {
    "status": "pass|fail",
    "valid_episode_count": 4,
    "success_count": 4,
    "required": 4
  },
  "closure": {
    "status": "exact_19_closed|not_released|infrastructure_incomplete",
    "valid_episode_count": 19,
    "invalid_attempt_count": 0,
    "ordered_tasks_exact": true
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
    "provisional_route_count": 0,
    "confirmed_route_count": 0,
    "normal_navigation_exemption_count": 0,
    "trigger_count": 0,
    "mature_trigger_count": 0,
    "nonempty_read_count": 0,
    "active_success_count": 0,
    "productive_divergence_count": 0,
    "max_reads_per_episode": 0,
    "rendered_chars_total": 0,
    "rendered_tokens_total": 0,
    "model_calls_added": 0,
    "guard_enabled": false,
    "action_override_count": 0,
    "forced_termination_count": 0
  },
  "pairwise": {
    "versus_a0": {},
    "versus_a1": {}
  },
  "episodes": [],
  "invalid_attempts": [],
  "errors": []
}
```

---

# 43. Per-task schema

```text
task_index
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
provisional_route_count
confirmed_route_count
normal_navigation_exemption_count
mature_trigger_count
memory_nonempty_read_count
first_nonempty_read_step
memory_rendered_chars
memory_rendered_tokens
phase_switch_count
frontier_eviction_count
branch_eviction_count
route_eviction_count

model_calls_added
guard_enabled
action_override_count
forced_termination_count
hidden_ui_used
evaluator_used
future_used
```

---

# 44. 性能验收

A11 overall performance pass 必须同时满足：

```text
gate = 4/4
valid tasks = 19/19
success_count >= 6
reward_sum > 5.5
success_count > A0 success_count
success_count > A1 success_count
```

并且：

```text
extra model calls = 0
guard = 0
override = 0
forced termination = 0
```

---

# 45. Active-memory success 与 productive divergence

## 45.1 Active-memory success

至少一个成功 episode：

```text
reward == 1.0
nonempty_read_count >= 1
```

始终静默后恰好得到 6/19 不满足 A11 机制验收。

## 45.2 Productive divergence

一条 read 只有同时满足以下条件，才计为 productive divergence：

1. read 基于 mature candidate；
2. support count 至少 2；
3. 接下来 2 个 actions 内，模型选择了该 frontier 先前未尝试的 branch；
4. 3 个 actions 内离开该 frontier；
5. 离开后 4 个 actions 内没有返回；
6. 满足以下之一：
   - open-anchor confidence 增加至少 0.15；
   - constraint confidence 增加至少 0.15；
   - episode 最终 reward 为 1.0。

至少一个 productive divergence 必须发生在 successful active-memory episode 中。

---

# 46. 逐 read 因果分析格式

每条 read 生成：

```text
task
episode_id
read_step
trigger_kind
candidate_maturity_step
support_count
support_receipt_ids
open_items_before_read
constraints_before_read
matching_frontier
visual_match_kind
prior_branches
prior_branch_outcomes
prior_routes
route_workflow_credit
route_confirmation_path
contraction_confidence
score
score_components
exact_injected_text
rendered_sha256

next_action
next_branch_id
next_branch_was_novel
escaped_frontier_within_3
returned_within_4
anchor_delta_within_4
constraint_delta_within_4
episode_reward
final_success
productive_divergence
```

## 46.1 允许的因果表述

> 在 step \(t\)，A11 基于两项以上已经观察到的不利证据发出读取；下一次或第二次动作选择了此前未在该 frontier 尝试的 branch，轨迹随后没有返回该 frontier，并产生新的义务证据或最终成功。因此，该读取可能促成了策略分化。

## 46.2 禁止的表述

```text
A11 proved the correct action.
The memory caused success.
The route was impossible.
The task was verified complete.
```

固定单 seed、单轨迹只能支持 trace-grounded causal hypothesis，不能证明必然因果。

---

# 47. Falsification criteria

以下任一成立，A11 不能获得 overall pass。

## 47.1 Protocol / boundary

```text
extra model call
guard
override
forced termination
evaluator input
hidden UI input
future information
task/page whitelist
system prompt change
seed drift
sampling drift
native max-step drift
```

## 47.2 Preflight

```text
real replay status != pass
single closed route creates delivered T2
constraint parser fails exact Recipe gate
A6 activation < 80%
A8 timing failure
A9 timing failure
competent sparse gate failure
token budget exceeded
audit > 128 KiB
tests incomplete
dirty source freeze
```

## 47.3 Live capability

```text
any of four gate tasks fails
```

## 47.4 Full performance

```text
success < 6
reward <= 5.5
not strictly better than A1
```

## 47.5 Mechanism evidence

```text
all successful tasks are memory-inactive
no successful active-memory episode
no productive divergence hypothesis
all reads occur after 75% of native steps
more than half of reads are followed by same bad branch
```

最后一项的精确定义：

```text
same_bad_branch_within_2
AND no anchor/constraint gain >= 0.15
```

若该比例大于 0.5，则机制的策略分化假设失败，即使总分偶然提高。

---

# 48. Final verdict taxonomy

## 48.1 `PROTOCOL_INVALID`

规范存在不可满足条件、隐藏依赖或需要非法信息。

```text
live generation forbidden
```

## 48.2 `SCIENTIFIC_PREFLIGHT_FAILURE`

规范自洽，但实现或真实 replay 未达到冻结资格门。

```text
live generation forbidden
```

## 48.3 `INFRASTRUCTURE_PREFLIGHT_FAILURE`

缺文件、损坏、环境或 tokenizer 不可用。

```text
repair infrastructure only
do not change mechanism
```

## 48.4 `LIVE_NOT_AUTHORIZED`

Preflight 或 live receipt 缺失、过期或不匹配。

## 48.5 `GATE_SCIENTIFIC_FAILURE`

四题 gate 小于 4/4。

## 48.6 `SUITE_INFRASTRUCTURE_INCOMPLETE`

超过 invalid retry 上限或无法形成 exact 19 closure。

## 48.7 `A11_SCIENTIFIC_FAILURE`

19 题完成，但未达到性能或机制条件。

## 48.8 `PERFORMANCE_PASS_MECHANISM_EVIDENCE_FAIL`

达到至少 6/19 和 reward 目标，但没有 successful active-memory episode 或 productive divergence。

## 48.9 `A11_OVERALL_PASS`

必须同时满足：

```text
preflight pass
fresh live receipt pass
4/4 gate
exact 19/19 closure
success >= 6
reward > 5.5
strictly better than A0
strictly better than A1
zero extra calls
zero guard
zero override
zero forced termination
at least one active-memory success
at least one productive divergence
all capacity and prompt bounds
```

---

# 49. 从 A10-v1 到 A11 的代码迁移

## 49.1 可以复用

以下纯函数或框架可复制后重新绑定 v2 identity：

```text
RGB input validation
4% crop
exact screenshot SHA
9×16 luma descriptor
edge-bit descriptor
visual distance
pixel-change calculation
canonical action validation
tap/long-press/swipe/type family
basic intent classifier
bounded audit utilities
saturating counters
UTF-8-safe compact renderer
controller input whitelist pattern
post-read behavioral receipt framework
source-freeze hashing utilities
live-server qualification framework
exact 19-task closure framework
```

复用必须发生在新的 v2 module 中，不得通过修改 v1 class 后继续使用 v1 ID。

## 49.2 必须重新实现

```text
GoalAnchor schema
constraint grammar
app-span exclusion
overlap/dedup
constraint target mask
persistent constraint status
item/constraint masks
route-hop capture
route core/full signature
navigation novelty credit
residual work credit
normal-navigation exemption
confirmed route recurrence
post-return reversion
route evidence revision
T2
T3
candidate maturity state machine
strict near retrieval
new score
new renderer fields
v2 replay qualification classifier
competent sparse gate
A1 Recipe gate
source freeze
preflight
live receipt
result schema
```

## 49.3 不允许的迁移方式

```text
only change threshold 0.68 to another number
only change max read count
add Retro/Calendar exemptions
add Settings-page hashes
add task-name if-statements
edit v1 replay report to pass
reuse v1 mechanism ID
reuse v1 experiment ID
reuse old live receipt
stitch v1 episodes into v2 suite
```

---

# 50. A11 可能引入的新失败模式

| 风险 | 原因 | 冻结缓解 |
|---|---|---|
| T2 太保守 | 需要第二项证据 | T1 仍在第二次 no-progress 时触发；post-return reversion 可提前确认 |
| 合法路线重复两次被误判 | 用户工作流可能需要重复设置 | residual work、target progression、anchor gain 排除 |
| Route signature 太严格 | 路径中间动作轻微变化 | core signature 不包含全部中间 hop |
| Route signature 太宽 | entry/return 相同但中间任务不同 | full signature 审计；phase/masks 和 source frontier 必须相同 |
| Constraint persistent 导致 O 偏高 | 无法知道所有满足约束的对象是否已处理 | score 仍需多项 adverse supports；constraint 不单独触发 |
| Summary 不提 constraint value | target mask 为 0 | query constraint 仍保留在 prompt relevance；不使用自由语义猜测 |
| Grammar 漏掉其他自然语言约束 | 固定 grammar 有限 | 这是可证伪限制；不得临时扩展 |
| Near threshold 漏掉动画页面 | retrieval 更严格 | route recording 仍使用 standard match；exact path 保留 |
| T3 无法捕获三分支循环 | K 必须 <=2 | 这是有意限制以降低 false positive；A6 gate 检验代价 |
| Prompt 仍可能扰动成功轨迹 | 即使成熟 evidence 也可能不必要 | 历史 sparse gate + fresh live 4/4 |
| 新 branch 不一定更好 | memory 只促进多样性 | 不 override；productive-divergence 分析要求实际逃离和增益 |
| 固定 seed 随机差异 | 单 arm 不能完全归因 | paired comparison、active-success 和逐 read 分析 |

---

# 51. 最终逻辑裁定

## 51.1 A11 是否逻辑自洽

**是。**

A11 不再要求单次 qualifying closed route 同时“必须读取”和“绝对不得读取”。

新规则是：

```text
single closed route:
  record only
  never mature T2
  never directly read

second independent adverse support:
  may mature T2
```

历史 competent gate 也不再要求所有轨迹绝对静默，而是要求：

```text
sparse
mature
at least two supports
no single-route delivery
no normal-navigation exemption violation
```

因此第一项内部冲突已在规范层面消除。

---

## 51.2 是否解决 constraint parser 冲突

**是。**

Recipe query 必须产生一个、且仅一个结构化 constraint：

```text
USE / zucchini / DIRECTIONS
```

v2 gate 同样只要求这个结构化 constraint，不再要求冻结 grammar 无法产生的“多个目标”。

因此第二项内部冲突已消除。

---

## 51.3 何时允许 zero-generation preflight pass

只有以下全部成立：

```text
spec consistency witnesses pass
all tests pass
all 1,668 files and 442,138,413 bytes reverify
generation_calls = 0
competent sparse gate pass
A6 >= 80% with >=20 qualifying segments
A8 timing gate pass
A9 timing gate pass
Recipe constraint gate pass
no-overfit scan pass
tokenizer <=192 tokens/read
audit <=128 KiB
source freeze clean and exact
no causal-boundary violation
```

才允许：

```text
A11_ZERO_GENERATION_PREFLIGHT.status = pass
```

如果真实 replay 未通过，只能标：

```text
SCIENTIFIC_PREFLIGHT_FAILURE
```

不得为了放行 live generation临时更改阈值。

---

## 51.4 何时允许开始 live generation

必须已经存在：

```text
formal preflight pass
fresh live receipt pass
same implementation commit
same source freeze
same model process
clean worktree
```

否则：

```text
live_generation_authorized = false
```

---

## 51.5 若仍存在不可满足条件

实现阶段若发现：

- 本文任一规则在相同输入上要求相反输出；
- parser 与 gate 再次不一致；
- mature candidate 理论最高 score 低于阈值；
- replay gate 只能依靠 task/page whitelist；
- 必须使用 evaluator、future、UI tree 或额外模型才能通过；
- source freeze 无法无循环地形成；
- 无法同时满足容量和审计要求；

则必须输出：

```text
A11_PROTOCOL_INVALID
LIVE_GENERATION_FORBIDDEN
```

不得继续消耗 GPU。

---

# 52. 最终研究裁决

A10-v1 的主要问题不是 detection 不够强，而是把一次普通 closed route 直接解释为局部策略失败。真实成功轨迹证明，GUI 任务中的正常设置、子页面操作和多阶段工作流也会产生完全相同的浅层结构。A11 因而将核心干预对象从：

```text
one no-gain closed route
```

改为：

```text
confirmed local strategy contraction
```

确认必须来自：

```text
same route repeated
OR
closed route followed by bad-branch reversion
OR
same branch repeatedly produces no progress
OR
a low-diversity frontier accumulates multiple adverse receipts
```

同时，constraint parser 不再要求模型自由总结，也不调用额外语义模型，而是通过固定 predicate/value/scope grammar 将：

```text
that use zucchini in the directions
```

转化为一个 persistent constraint anchor。

A11 保持了原 A 类实验最重要的因果边界：

```text
one deterministic controller-authored memory
zero extra model calls
zero planner
zero critic
zero verifier
zero guard
zero override
zero forced termination
visible RGB only
past executed actions only
```

本文提出的是一个逻辑自洽、可实现、可审计、可证伪的新实验臂。它尚未获得 live 性能结果，也不保证达到 6/19。只有正式 A11 实现、fresh real-RGB replay、严格 preflight 和 live receipt 全部通过后，才允许启动 4/4 fail-fast gate；只有通过 4/4、完成 exact 19/19、达到至少 6/19、reward 大于 5.5，并出现 successful active-memory productive divergence，才允许裁定：

```text
A11_OVERALL_PASS
```

---

## 53. 非调参式实现勘误与确定性绑定

本节只修复硬冲突并冻结未定义函数，不改变 T0–T4、score、阈值或 replay gate。
完整字段、公式、枚举、指标算法与淘汰键位于
`protocols/A11_CRC_ECOBF_IMPLEMENTATION_BINDING_2026-08-12.md`；该 binding 与本文共同
构成 A11 规范。

1. attribute predicate 中 `is` / `are` 固定映射为 `EQUAL`。
2. episode-global `last_nonempty_read_step` 永不因 phase switch 清空；phase switch
   只清 `phase_nonempty_read_count`。
3. 新增 capacity=4 的 `LateRouteWatch`，保存 source packed descriptor、route core、
   entry branch key/intent 与 receipt id，在第 5–8 步支持 durable-to-late-return 原位
   修订，禁止正负双计数。
4. `PendingRoute` 内嵌 source descriptor、entry branch key/intent、source exact hash、
   phase baseline masks 与 targeted-mask baseline；任何被 pending/watch/candidate 引用的
   descriptor 都必须内嵌或 pin，不能悬空引用已淘汰 frontier。
5. decision visit 只由 `read()` 登记；`observe_step()` 的 source/destination 匹配不增加
   visit count。T1 exact-hash retry exemption 使用 receipt 保存的 source exact hash。
6. constraint-only COMMIT 只在对应 pending route 解析为 DURABLE 时携带原 intent 触发。
7. branch confidence 仅从 retained 32 receipts 依冻结衰减公式重算；T3
   `workflow_credit` 为支持性 receipts 的最大 residual credit。
8. 禁止词只禁止机制自行声称成功/失败/完成；合法动态 anchor 值必须逐字保留并做边界
   转义，不能因值恰含 `success` 或 `completed` 而删除任务约束。
9. source freeze 不包含其自身生成的 replay/preflight/live/result 输出；这些 evidence
   绑定 source commit、source-freeze manifest 与生成器 SHA256，避免 commit/hash 自引用。
10. `operation_class`、`specificity_weight`、failure prose、T0/T4 evidence strength、
    target-progress baseline、对象 schema 与 replay metric 算法全部按 binding 固定，禁止
    在真实 replay 后以同一 mechanism ID 修改。
