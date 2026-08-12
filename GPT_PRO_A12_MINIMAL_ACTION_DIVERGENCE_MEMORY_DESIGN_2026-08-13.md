# GPT_PRO_A12_MINIMAL_ACTION_DIVERGENCE_MEMORY_DESIGN_2026-08-13.md

> **文档状态**：A12 唯一规范性机制设计、实现合同与前瞻性实验预注册
> **审阅分支**：`a2-verified-progress-audit-20260810`
> **审阅提交**：`ee30db3692bd7797722b3ea29a70266eb6256c7e`
> **提交标题**：`Add A12 GPT Pro design handoff`
> **父证据提交**：`5009034fa050d2f065e4eb08ff1c8c394a0ac586`
> **设计日期**：2026-08-13
> **科学裁决**：`CONDITIONAL GO FOR IMPLEMENTATION AND ZERO-GENERATION QUALIFICATION`
> **当前 live 裁决**：`LIVE NO-GO UNTIL ALL A12 PREFLIGHT GATES PASS`
> **机制名称**：最小动作分歧记忆
> **英文名称**：Minimal Action-Divergence Memory
> **缩写**：MADM
> **Mechanism ID**：`a12_minimal_action_divergence_memory_v1`
> **Experiment ID**：`A12_MADM_QWEN3VL32B_AW_HARD_T20260806_G3407_V1`
> **Config schema**：`a12_madm_arm_v1`
> **Audit schema**：`a12_madm_audit_v1`
> **Reference-segment schema**：`a12_reference_segments_v1`
> **Offline replay schema**：`a12_offline_replay_report_v1`
> **Preflight schema**：`a12_zero_generation_preflight_v1`
> **Live receipt schema**：`a12_live_server_receipt_v1`
> **Checkpoint schema**：`a12_suite_checkpoint_v1`
> **Result schema**：`a12_madm_result_v1`

---

## 0. 规范性说明

本文是 A12 的完整最终规范，不是讨论稿。

本文中的：

- **必须 / MUST**：实现和实验不得偏离；
- **不得 / MUST NOT**：违反即构成 protocol invalid；
- **应当 / SHALL**：与 MUST 同等约束；
- **可以 / MAY**：只表示本文明确允许的行为，不授权实现者自行增加影响实验结果的规则。

任何改变下列内容的修改都属于行为变化：

```text
screen equivalence
no-progress threshold
canonical action family
repeat count
first-support lifetime
read timing
cooldown
one-shot rule
capacity
rendered text
token/character limits
reference-segment matching
live task order
success criterion
```

行为变化后不得继续使用本文的 Mechanism ID、Experiment ID、formal replay、preflight 或 live receipt。必须创建新的版本、重新冻结 source closure，并重新执行 zero-generation replay。

---

# 1. 仓库审阅范围与事实优先级

本设计以提交：

```text
ee30db3692bd7797722b3ea29a70266eb6256c7e
```

为最高代码和证据事实来源。该提交在父证据提交 `5009034...` 之上新增 A12 任务书和更新后的 handoff；旧对话中的推测若与该提交冲突，均以仓库为准。

本次审阅覆盖：

```text
GPT_PRO_A12_MINIMAL_MEMORY_DESIGN_REQUEST_2026-08-13.md
HANDOFF_2026-08-12.md

GPT_PRO_A10_V2_STANDALONE_MEMORY_DESIGN_2026-08-12.md
GPT_PRO_A11_STANDALONE_MEMORY_DESIGN_2026-08-12.md

protocols/A10_V2_EMOBF_IMPLEMENTATION_BINDING_2026-08-12.md
protocols/A11_CRC_ECOBF_IMPLEMENTATION_BINDING_2026-08-12.md

implementation/src/raven_m/official_qwen_mobile/
  a10_v2_obligation_branch_frontier.py
  a11_confirmed_route_contraction.py
  a10_obligation_branch_frontier.py
  controller.py
  working_memory.py
  a10_contract.py
  a11_contract.py

implementation/scripts/
  replay_a10_v2_offline_traces.py
  replay_a11_offline_traces.py
  replay_a10_offline_traces.py
  run_official_qwen_mobile.py
  run_a678_arm.py

evidence/a10_v2/A10_V2_OFFLINE_REPLAY_REPORT.json
evidence/a11/A11_OFFLINE_REPLAY_REPORT.json
evidence/a10/A10_OFFLINE_REPLAY_REPORT.json
evidence/a2/A0_A1_PAIRED_REFERENCE_20260810.json
evidence/a678/A8_V2_OFFLINE_TRACE_AUDIT_2026-08-11.json
evidence/a678/A89_INITIAL_GATE_RESULTS_2026-08-12.json

A0/A1/A6/A8-v2/A9 materialized episodes and screenshots
相关测试、contracts、manifests、source specifications
```

软件测试通过只证明实现满足软件断言，不证明机制有科学价值。任务书明确要求以真实轨迹回放中的成熟、eligible、实际非空读取为准，而不能把 candidate creation 当作机制成功。

---

# 2. 当前冻结事实

## 2.1 A0 与 A1

当前完整配对结果仍为：

| 指标 | A0 | A1 |
|---|---:|---:|
| Success | 4/19 | 5/19 |
| Reward sum | 4.5 | 5.5 |
| Executed actions | 316 | 596 |
| Model calls | 329 | 603 |
| Prompt tokens | 1,233,321 | 3,376,888 |
| Completion tokens | 40,040 | 87,379 |
| Total tokens | 1,273,361 | 3,464,267 |
| Valid elapsed seconds | 6,541.82 | 14,595.49 |
| Nonempty memory reads | 0 | 580 |
| Memory writes | 0 | 515 |

A1 相对 A0 只有 1 个任务胜出、0 个任务丢失和 18 个平局，但其 actions、calls、tokens 和 elapsed time 均大幅增加。

这说明：

1. 额外记忆文本确实有可能改变 policy 并带来一个新增成功；
2. 高频、长期、recency-based memory 的成本和污染风险非常高；
3. A12 不能通过复制 A1 的“几乎每步非空读取”来获得收益。

---

## 2.2 A6

A6 是完整 19 题的负对照：

```text
success = 0/19
executed actions = 625
total tokens = 2,674,422
```

A6 有 250 次写入发生在 changed-pixel fraction 小于 0.001 的转移后；其中 243 个位置随后发生非空读取，131 个位置又重复了相同 canonical action。也就是说，持续保存并回放近期 transition 并没有闭合：

```text
write
→ relevant retrieval
→ action divergence
→ task success
```

这条因果链。

---

## 2.3 A8-v2 与 A9

A8 的离线审计在 A6 的 628 个 executed steps 中发现：

```text
274 exact revisits
182 repeated exact state-action steps
117 repeated exact state-action no-progress steps
```

说明“重复同屏同动作且无进展”不是稀有现象，而是冻结失败轨迹中的真实、可观测信号。与此同时，宽松 exact-revisit prototype 在 OsmAndTrack 上可产生 76 次读取，证明单纯存在 recurrence 远远不够，必须限制实际 prompt exposure。

A8-v2 的初次 live gate 在 Expense 上：

```text
0/1
34 actions
14 nonempty reads
max_steps
```

A9 在 Expense 上保持静默并成功，但在 Retro 上发出 3 次 canary 后仍以 50 步失败。

因此：

```text
recurrence detection ≠ productive action divergence
memory activation ≠ causal benefit
```

---

## 2.4 A10-v2

A10-v2 的严格 replay 验证了：

```text
27 episodes
1,668 frozen files
442,138,413 bytes
generation_calls = 0
```

但在 23 个 A6 reference segments 上：

```text
timely eligible actual reads = 0/23
timely T1/T2 reads = 0/23
```

其 A0 四条 competent histories 全部保持 0 read，但这种精度是以完全失去及时召回为代价获得的。

A10-v2 report 中实际上存在大量 candidate creation。例如某些 A6 episode 创建了多条 `BAD_BRANCH_REPEAT` 或 route candidates，但严格 checker 不把这些 creation 计为 qualified read。这一差异正是 A12 必须永久保留的审计边界。

---

## 2.5 A11

A11 的严格结果为：

```text
A6 qualified segments = 5/23
qualification rate = 21.739%
```

成功历史 sparse gate 通过：

```text
total nonempty reads = 1
read density = 0.014925
rendered chars = 346
```

因此 A11 的主要问题不是 uncontrolled injection，而是：

```text
low recall
late maturity
read-time ineligibility
frontier/branch binding mismatch
```

A11 同时未通过 A8-v2 Expense 和 A9 Retro 的独立 segment gates。

A11 replay 的严格 checker 已经正确要求：

- read step 必须在 segment deadline 或 deadline + 1；
- read 必须绑定同一 frontier 和 branch；
- trigger kind 必须属于允许集合；
- support count 至少为 2；
- 必须存在实际 `read_event`。

Candidate creation 本身不会增加 qualified count。

A11 的 production implementation 达到 1,688 行，并同时维护 query anchors、constraints、frontiers、branches、pending routes、closed routes、post-return watches、typed-value records、phase masks、五类 trigger、score 和 retrieval gate。其复杂度提供了很多精度条件，也同时创造了多个可以阻止及时读取的交叉门。

---

# 3. 因果失败诊断

| Arm | 主要失败 | 次要失败 | 对 A12 的约束 |
|---|---|---|---|
| A1 | Prompt burden、上下文持续暴露 | 没有状态条件化失败证据 | 记忆必须稀疏、短、one-shot |
| A6 | Stale recent history；读取后仍重复原动作 | 成本膨胀 | 不保存完整 transition history |
| A8-v2 | 宽松 recurrence 导致高 exposure | 只报告失败，不促成替代动作 | 不使用 broad revisit trigger |
| A9 | Trigger 过晚且信息弱 | Canary 本身不能说明该改变什么 | 在第二次直接坏动作后立即读取 |
| A10-v2 | 0/23 timely eligible reads | 多层 score、phase、anchor、route gate | 删除 score、phase、义务图和 route maturity |
| A11 | 5/23，主要是 recall/timing 不足 | 346-char prompt 仍偏长 | 只保留一个布尔 trigger 和短模板 |

核心矛盾并不是：

```text
是否应当拥有记忆
```

而是：

```text
何时能以足够高的召回率，
在不污染 competent trajectory 的前提下，
向 policy 暴露最短、最直接的动作分歧信息。
```

---

# 4. A12 科学裁决

## 4.1 裁决

```text
DESIGN AND ZERO-GENERATION QUALIFICATION: GO
LIVE GENERATION NOW: NO-GO
```

A12 获得设计和实现 GO 的证据是：

1. A6 中存在 117 次 repeated exact state-action no-progress，说明直接动作失败信号真实存在；
2. 当前资格体系已经冻结了至少 23 个独立 A6 failure segments；
3. A10-v2/A11 的低召回主要来自信号之后的额外 gate，而不是信号不存在；
4. 四条 A0 competent histories 在 A10-v2 report 中没有 second-bad segments，说明“同屏同 canonical family 两次无进展”有希望比 route/navigation trigger 更精确；
5. 一个只绑定当前 screen 和 canonical action family 的机制可以完全避免 A10-v2/A11 的 query parser、phase、route graph、score 和 multi-trigger state machine。

这只足以授权：

```text
implementation
unit tests
independent reference freeze
zero-generation replay
preflight
```

在 A12 正式 replay 未达到本文全部门槛前：

```text
GPU live generation remains forbidden
```

---

## 4.2 一句话因果 thesis

> **当同一个 canonical action family 在同一个可见 screen context 中两次产生不超过 0.001 的像素变化，并且期间没有 material visible progress 或 screen-context loss 时，下一次 model call 前注入一次极短的“该动作在此屏已两次无可见进展，请尝试不同动作 family 或 target”提示，可能比 route reconstruction、obligation graph 或长历史摘要更及时地诱导 action divergence。**

---

## 4.3 A12 不试图解决的事情

A12 不保存或推断：

```text
任务阶段
目标完成状态
对象列表
约束语义
页面路线
应用名称
UI 控件
成功概率
任务 reward
正确下一动作
```

A12 只回答：

```text
On this currently visible screen,
has the same canonical action family already produced
no material visible progress twice?
```

---

# 5. A-class 因果边界

## 5.1 允许输入

运行时只允许：

```text
task query
before.pixels
after.pixels
executed canonical_action
policy-authored action_summary
source_step
```

其中：

- query 只用于 episode identity hash，不参与触发和渲染；
- action summary 只保存 SHA256 供审计，不参与动作匹配、screen matching、trigger 或 rendering；
- 所有行为决策仅由 RGB、canonical action family、step counter 和内部 bounded state 决定。

## 5.2 禁止输入

A12 不得读取：

```text
evaluator reward
task success
task ground truth
UI tree
accessibility hierarchy
foreground package
activity
hidden app database
OCR output
future screenshot
future action
episode role
task name
episode ID
A0/A1/A6/A8/A9 label
historical final reward
```

## 5.3 禁止干预

A12 不得：

```text
增加 model call
调用 planner
调用 critic
调用 verifier
调用 summarizer
调用 retrieval model
阻止 action
过滤 action
替换 action
修改 action
强制 retry
强制 terminate
修改 official system prompt
修改 official action history
```

Controller 已经在每次 model call 前调用 `memory.read()`，将返回文本附加到当前 user prompt，然后只执行一次 `client.generate()`；动作执行后再调用 `observe_step()`，evaluator 只在 episode 循环结束后运行且对 agent 不可见。A12 只利用这一现有接口。

---

# 6. 冻结模型和 benchmark 条件

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

backend:
  vLLM BF16

transport_attempts_per_model_step:
  exactly 1

task_count:
  19
```

不得改变 native max steps、任务参数、任务顺序、emulator setup 或 evaluator。

---

# 7. Step 与 off-by-one 语义

## 7.1 Controller 顺序

定义：

```text
read step r = 已经完成的 executed action 数量
source action step s = 当前将被 observe 的 action index
```

Episode 开始：

```text
read r=0
→ generate action s=0
→ execute s=0
→ observe s=0
→ read r=1
```

一般地：

```text
observe source_step=s
```

之后的即时读取为：

```text
read_step=s+1
```

## 7.2 Candidate 时序

若第二次 no-progress action 发生在：

```text
source_step = s2
```

则 candidate：

```text
maturity_step = s2
eligible_read_step = s2 + 1
expiry_read_step = s2 + 1
```

它只能在紧接着的下一次 `read()` 中被注入。

如果该次 read 因以下任一原因未注入：

```text
cooldown
episode read cap
screen mismatch
already delivered
integrity mismatch
```

candidate 必须立即进入：

```text
SUPPRESSED
```

不得在更晚 step 以 stale candidate 形式注入。

---

# 8. RGB 输入与 screen descriptor

## 8.1 合法 RGB

必须满足：

```text
ndim == 3
height >= 25
width >= 8
channels >= 3
integer dtype
all values in [0,255]
```

RGBA 只使用前三个 channels。

非法输入抛出：

```text
A12VisibleInputError
```

不得将非法 RGB 视为空 screen 或 no-progress。

---

## 8.2 Exact screen fingerprint

对 RGB 顶部和底部各裁去 4%：

\[
I^{crop}
=
I[
\lfloor 0.04H\rfloor:
\lceil 0.96H\rceil
]
\]

计算：

\[
h^{exact}
=
SHA256(
shape
\Vert
dtype
\Vert
I^{crop}.bytes
)
\]

---

## 8.3 Coarse descriptor

沿用已经审计过的 9×16 非学习型 RGB descriptor：

1. 将 crop 划分为 \(9\times16\) cells；
2. 每个 cell 计算 RGB 整数均值；
3. 转换亮度：

\[
Y=\frac{77R+150G+29B}{256}
\]

4. 量化：

\[
q_{r,c}
=
\left\lfloor\frac{Y_{r,c}}{16}\right\rfloor
\in\{0,\dots,15\}
\]

5. 生成 135 个水平 edge bits 和 128 个垂直 edge bits。

距离：

\[
D_L
=
\frac{1}{144\cdot15}
\sum_{r,c}|q_{r,c}-q'_{r,c}|
\]

\[
D_E
=
\frac{\operatorname{Hamming}(E,E')}{263}
\]

\[
D_V=0.7D_L+0.3D_E
\]

这些定义与 A10/A11 已实现的 visual descriptor 一致。

---

## 8.4 Screen equivalence

两个 screen descriptor 满足任一条件即等价：

### Exact

```text
exact_sha256 equal
```

### Conservative near match

\[
D_L\le0.06
\]

\[
D_E\le0.12
\]

\[
D_V\le0.055
\]

A12 不维护多个 frontiers。当前 episode 同一时刻只绑定一个 `ActiveScreenContext`。

---

## 8.5 禁止 context drift

Active context 始终与首次绑定的 representative descriptor 比较。

不得使用：

```text
current frame matches previous frame
```

的逐帧链式规则将页面逐渐漂移到远离最初 context 的状态。

如果新 screen 不再与 representative descriptor 等价：

```text
context loss
→ invalidate all active failure records
→ bind a fresh context
```

---

# 9. Material visible progress

## 9.1 Pixel-change fraction

使用完整 model-visible RGB，而不是 UI tree：

\[
P_t
=
\frac{1}{HW}
\sum_{i,j}
\mathbf1
\left[
\max_c
|I_t(i,j,c)-I_{t+1}(i,j,c)|>5
\right]
\]

若 before/after shape 不同：

\[
P_t=1
\]

现有 A10 utility 使用同样的 per-pixel max-channel difference 和阈值 5。

## 9.2 No material visible progress

动作 \(a_t\) 被视为 no-progress，当且仅当：

\[
NP_t
=
ScreenEquivalent(I_t,I_{t+1})
\land
P_t\le0.001
\]

阈值包含等号：

```text
P == 0.001 → no-progress
P > 0.001 → material visible progress
```

## 9.3 Material progress / context loss

以下任一成立即取消当前 screen 上所有未交付 failure evidence：

```text
P_t > 0.001
before/after screen not equivalent
before/after shape differs
next read screen no longer matches active context
```

A12 不声称该变化是 semantic task progress，只称其为：

```text
material visible progress or context change
```

---

# 10. Canonical action family

A12 使用 canonical action 本身，不使用 action summary 的自由文本语义。

## 10.1 Tap

\[
x_{bin}=\min(11,\lfloor12x\rfloor)
\]

\[
y_{bin}=\min(23,\lfloor24y\rfloor)
\]

```text
("tap", x_bin, y_bin)
```

## 10.2 Long press

```text
("long_press", x_bin, y_bin, duration_bucket)
```

Duration bucket：

```text
short  : duration_ms < 700
medium : 700 <= duration_ms <= 1500
long   : duration_ms > 1500
```

## 10.3 Swipe

令：

\[
dx=x_2-x,\quad dy=y_2-y
\]

方向：

```text
abs(dx) >= abs(dy):
  right if dx > 0 else left
otherwise:
  down if dy > 0 else up
```

长度：

\[
l=\sqrt{dx^2+dy^2}
\]

```text
short  : l < 0.25
medium : 0.25 <= l < 0.55
long   : l >= 0.55
```

起点网格：

```text
x: 3 bins
y: 4 bins
```

Family：

```text
("swipe", direction, length_bucket, start_x_bin, start_y_bin)
```

## 10.4 Type text

对 text 只执行 Unicode NFKC，不 casefold、不做语义归一化：

```text
(
  "type_text",
  SHA256(NFKC(text)),
  length_bucket,
  clear_text
)
```

长度：

```text
1-8
9-32
33-96
97+
```

## 10.5 Wait

```text
("wait", duration_bucket)
```

Duration bucket 与 long press 相同。

## 10.6 System actions

```text
("press_back",)
("press_home",)
("press_enter",)
("press_recents",)
```

## 10.7 Answer

```text
("answer", SHA256(NFKC(answer_text)))
```

这些 family 定义与现有经过测试的 A10 canonical-family utility 保持一致。

---

# 11. Action label

Memory 文本中的 action label 只根据 canonical family 生成。

| Family | Label |
|---|---|
| tap | `tap cell {x+1}/12,{y+1}/24` |
| long press | `long-press cell {x+1}/12,{y+1}/24 ({duration})` |
| swipe | `swipe {direction} ({length})` |
| type text | `enter the same text` |
| press back | `press Back` |
| press home | `press Home` |
| press enter | `press Enter` |
| press recents | `press Recents` |
| wait | `wait ({duration})` |
| answer | `submit the same answer` |

```text
MAX_ACTION_LABEL_CHARS = 48
```

Action summary 不进入 label。

---

# 12. A12 的唯一 trigger

```text
TRIGGER_KIND =
REPEATED_NO_PROGRESS_ACTION
```

A12 不得添加第二个 trigger family。

它没有：

```text
route trigger
navigation trigger
obligation trigger
phase trigger
text-reentry trigger
frontier-collapse trigger
completion trigger
```

---

# 13. 状态机

## 13.1 Failure-record 状态

```text
SEEN_ONCE
READY
DELIVERED
SUPPRESSED
EXPIRED
```

状态转移：

```text
no record
  └─ first same-screen/action no-progress
       → SEEN_ONCE

SEEN_ONCE
  ├─ second matching no-progress within 12 actions
  │    → READY
  ├─ material progress/context loss
  │    → EXPIRED
  ├─ first support older than 12 actions
  │    → replace with a new SEEN_ONCE
  └─ capacity eviction
       → EXPIRED

READY
  ├─ immediate next read eligible and nonempty
  │    → DELIVERED
  ├─ immediate next read blocked
  │    → SUPPRESSED
  ├─ screen mismatch
  │    → EXPIRED
  └─ read window passed
       → EXPIRED
```

`SUPPRESSED` record remains inert until active screen context is invalidated。它不得在更晚 read 重新成熟。

---

## 13.2 Repeat count

```text
REQUIRED_NO_PROGRESS_SUPPORTS = 2
```

第一次 no-progress 不产生 candidate。

第二次满足全部 matching 条件时，才创建并成熟 candidate。

A12 不使用 score 或 probabilistic confidence。

---

## 13.3 First-support lifetime

```text
FIRST_SUPPORT_MAX_GAP_ACTIONS = 12
```

第二次 support 必须满足：

\[
0 < s_2-s_1\le12
\]

若：

\[
s_2-s_1>12
\]

则旧 support 到期，当前 event 成为新的第一次 support。

---

# 14. Failure identity 与 one-shot

## 14.1 Semantic failure identity

一个 failure identity 由：

```text
screen representative descriptor
canonical action family
```

共同定义。

不同 action summary 不改变 identity。

## 14.2 Evidence signature

```python
evidence_signature = SHA256(canonical_json({
    "mechanism_id": MECHANISM_ID,
    "context_descriptor_sha256": active_context.descriptor_sha256,
    "action_family": canonical_family,
    "first_support_step": first_step,
    "second_support_step": second_step,
}))
```

该 signature 只用于审计本次证据。

## 14.3 One-shot delivered match

One-shot 不能只比较 evidence-signature 字符串，因为 near-equivalent screen 可能有不同 descriptor hash。

一个新的 candidate 被视为已经交付，当且仅当存在 `DeliveredFailureSignature` 满足：

```text
canonical action family exactly equal
AND screen representative descriptors are screen-equivalent
```

同一 episode 中，这类 matched failure identity 最多注入一次。

---

# 15. Persistent state schema

## 15.1 顶层

| 字段 | 类型 | 容量 |
|---|---|---:|
| `mechanism_id` | `str` | 常量 |
| `experiment_id` | `str` | 常量 |
| `goal_sha256` | `str[64]` | 1 |
| `active_context` | `ActiveScreenContext or None` | 1 |
| `failure_records` | ordered map | 8 |
| `delivered_failures` | list | 5 |
| `read_events` | list | 5 |
| `post_read_watches` | list | 5 |
| `descriptor_cache` | list | 2 |
| `counters` | fixed dict | 固定 |
| `last_observed_step` | int | 1 |
| `read_count` | int | 1 |
| `nonempty_read_count` | int | 0–5 |
| `last_nonempty_read_step` | int/None | 1 |

---

## 15.2 `ActiveScreenContext`

| 字段 | 类型 |
|---|---|
| `context_id` | str |
| `representative_descriptor` | VisualDescriptor |
| `created_read_step` | int |
| `last_matched_read_step` | int |
| `last_matched_source_step` | int |
| `context_epoch` | int |

`context_id`：

```python
SHA256({
  "context_epoch": epoch,
  "descriptor_sha256": representative.descriptor_sha256,
  "exact_sha256": representative.exact_sha256
})
```

---

## 15.3 `ActionFailureRecord`

| 字段 | 类型 |
|---|---|
| `record_id` | str |
| `context_id` | str |
| `action_family` | tuple |
| `action_key_sha256` | str |
| `action_label` | str<=48 |
| `state` | enum |
| `support_count` | 1 or 2 |
| `first_support_step` | int |
| `last_support_step` | int |
| `second_support_step` | int/None |
| `first_before_exact_sha256` | str |
| `first_after_exact_sha256` | str |
| `second_before_exact_sha256` | str/None |
| `second_after_exact_sha256` | str/None |
| `first_changed_fraction` | float |
| `second_changed_fraction` | float/None |
| `first_summary_sha256` | str |
| `second_summary_sha256` | str/None |
| `maturity_step` | int/None |
| `eligible_read_step` | int/None |
| `expiry_read_step` | int/None |
| `evidence_signature` | str/None |
| `suppression_reason` | str/None |

---

## 15.4 `DeliveredFailureSignature`

| 字段 | 类型 |
|---|---|
| `delivered_id` | str |
| `representative_descriptor` | VisualDescriptor |
| `action_family` | tuple |
| `action_key_sha256` | str |
| `evidence_signature` | str |
| `delivered_read_step` | int |

最多 5 条，因为 episode 最多 5 次非空读取。

---

## 15.5 `ReadEvent`

| 字段 | 类型 |
|---|---|
| `read_id` | str |
| `read_step` | int |
| `candidate_record_id` | str |
| `candidate_state_before_read` | str |
| `maturity_step` | int |
| `eligible_read_step` | int |
| `screen_match_kind` | `EXACT/NEAR` |
| `visual_distance` | float |
| `support_count` | int |
| `support_steps` | list[int] |
| `action_family` | tuple |
| `action_key_sha256` | str |
| `action_label` | str |
| `evidence_signature` | str |
| `all_hard_gates_passed` | bool |
| `actual_nonempty` | bool |
| `exact_injected_text` | str |
| `rendered_sha256` | str |
| `rendered_chars` | int |
| `rendered_utf8_bytes` | int |
| `rendered_tokens` | int/None |

Memory persistent audit 只保存实际非空 read events。每次空 read 的详细 eligibility audit 由 `read()` 返回给 controller/replay step record，不无限保存在 memory state 中。

---

## 15.6 `PostReadWatch`

该记录只做事后因果审计，不参与任何后续 memory decision。

| 字段 | 类型 |
|---|---|
| `watch_id` | str |
| `read_id` | str |
| `read_step` | int |
| `failed_screen_descriptor` | VisualDescriptor |
| `failed_action_family` | tuple |
| `next_action_step` | int/None |
| `next_action_family` | tuple/None |
| `next_action_diverged` | bool/None |
| `material_progress_within_2` | bool |
| `same_failed_action_within_4` | bool |
| `context_loss_within_2` | bool |
| `closed` | bool |
| `close_step` | int/None |

---

# 16. 容量

```text
MAX_ACTIVE_CONTEXTS = 1
MAX_FAILURE_RECORDS = 8
MAX_DELIVERED_FAILURES = 5
MAX_READ_EVENTS = 5
MAX_POST_READ_WATCHES = 5
MAX_DESCRIPTOR_CACHE = 2

MAX_NONEMPTY_READS_PER_EPISODE = 5
GLOBAL_COOLDOWN_EXECUTED_ACTIONS = 4
FIRST_SUPPORT_MAX_GAP_ACTIONS = 12
READY_READ_WINDOW = exactly 1 read

MAX_VISIBLE_CHARS_PER_READ = 240
MAX_UTF8_BYTES_PER_READ = 480
MAX_RENDERED_TOKENS_PER_READ = 100
MAX_RENDERED_TOKENS_PER_EPISODE = 500

MAX_AUDIT_JSON_BYTES = 131072
MAX_RESIDENT_STATE_DELTA_BYTES = 2097152
```

A12 没有 per-phase cap，因为它没有 phase。

---

# 17. Eviction

## 17.1 Failure records

超过 8 条时：

1. 不淘汰 `READY`；
2. 优先淘汰 `EXPIRED`；
3. 然后淘汰 `SUPPRESSED`；
4. 然后淘汰最旧 `SEEN_ONCE`；
5. tie-break：
   - `last_support_step` 升序；
   - `action_key_sha256` 字典序。

在合法 controller 顺序下，同一时刻最多一个 `READY`。

若实现观察到超过一个 `READY`：

```text
raise A12IntegrityError
```

不得自行选择多个 prompt。

## 17.2 Delivered failures

最多 5 条，不会在合法 episode 中溢出，因为 read cap 同为 5。

若发生第 6 次 insertion：

```text
raise A12IntegrityError
```

不得 FIFO 淘汰后重新允许旧 signature 触发。

## 17.3 Read events 与 post-read watches

都最多 5 条。

不得淘汰有效 read event 来绕过审计。

---

# 18. Candidate creation、eligibility 与实际读取

三个事件必须明确分离：

```text
candidate_matured
read_eligibility_checked
actual_nonempty_read
```

## 18.1 Candidate maturity

第二次 support 后：

```text
state = READY
support_count = 2
maturity_step = source_step
eligible_read_step = source_step + 1
expiry_read_step = source_step + 1
```

## 18.2 Hard eligibility

对 READY candidate \(c\) 和当前 read step \(r\)：

\[
Eligible(c,r)
=
\mathbf1[c.state=READY]
\cdot
\mathbf1[r=c.eligible\_read\_step]
\cdot
\mathbf1[r\le c.expiry\_read\_step]
\cdot
\mathbf1[ScreenEquivalent(current,context)]
\cdot
\mathbf1[\neg DeliveredEquivalent(c)]
\cdot
\mathbf1[nonempty\_reads<5]
\cdot
\mathbf1[CooldownPass]
\]

其中：

\[
CooldownPass
=
last\_read=\varnothing
\lor
r-last\_read\ge4
\]

没有 score，没有 threshold ranking。

## 18.3 Actual read

只有：

```text
Eligible == true
AND rendered_text is nonempty
AND exact text is returned by read()
```

才形成：

```text
actual_nonempty_read = true
```

Candidate creation、READY 状态、eligible 但 renderer 为空、错误 screen 上的 read、deadline 后的 read，都不能计为 actual read。

---

# 19. Rendering

## 19.1 唯一模板

```text
A12 memory: On this screen, {ACTION} produced no material visible change twice. Try a different action family or target. Retry is allowed; nothing is blocked.
```

## 19.2 字段

`{ACTION}` 使用 §11 的 canonical label。

最长 48 字符。

模板最大长度在最长合法 label 下不得超过：

```text
198 visible characters
```

实现硬上限仍为：

```text
240 visible characters
480 UTF-8 bytes
100 frozen-tokenizer tokens
```

## 19.3 禁止内容

不得出现：

```text
the task failed
the task succeeded
completed
verified
correct action
must click
do not click
terminate
evaluator
reward
```

该模板：

- 提供过去可见事实；
- 指明需要改变的维度；
- 不指定具体下一动作；
- 不阻止原动作；
- 不构成 planner、guard 或 override。

---

# 20. `reset()` 伪代码

```python
def reset(self) -> None:
    self.mechanism_id = MECHANISM_ID
    self.experiment_id = EXPERIMENT_ID

    self.goal_sha256 = ""

    self.active_context = None
    self.failure_records = {}
    self.delivered_failures = []
    self.read_events = []
    self.post_read_watches = []
    self.descriptor_cache = []

    self.context_epoch = 0
    self.last_observed_step = -1
    self.read_count = 0
    self.nonempty_read_count = 0
    self.last_nonempty_read_step = None

    self.counters = {
        "support_created_count": 0,
        "candidate_matured_count": 0,
        "eligibility_check_count": 0,
        "eligible_candidate_count": 0,
        "nonempty_read_count": 0,
        "context_loss_count": 0,
        "material_progress_reset_count": 0,
        "first_support_expiry_count": 0,
        "candidate_suppressed_count": 0,
        "candidate_expired_count": 0,
        "one_shot_suppressed_count": 0,
        "cooldown_suppressed_count": 0,
        "cap_suppressed_count": 0,
        "failure_record_eviction_count": 0,
    }
```

Runner 必须为每个 episode 创建全新 memory instance。

即使存在 `reset()`，不得在同一个 episode 中以 reset 方式清除 read cap 或 one-shot history。

---

# 21. `read(context)` 伪代码

```python
def read(self, context: dict | None = None) -> tuple[str, dict]:
    context = context or {}

    read_step = self.read_count
    self.read_count += 1

    goal = str(context.get("goal") or "")
    goal_sha = sha256(goal.encode("utf-8")).hexdigest()

    if not self.goal_sha256:
        self.goal_sha256 = goal_sha
    elif goal_sha != self.goal_sha256:
        raise A12IntegrityError("goal changed within episode")

    before = dict(context.get("before") or {})
    pixels = extract_visible_rgb_only(before)
    descriptor = describe_visual_state(pixels)

    if self.active_context is None:
        self._bind_new_context(descriptor, read_step)
        return "", self._read_audit(
            read_step=read_step,
            candidate_present=False,
            mature=False,
            eligible=False,
            actual_nonempty=False,
            reason="initial_context_bound",
        )

    match_kind, distance = compare_to_active_context(descriptor)

    if match_kind == "NONE":
        self._invalidate_active_context(
            reason="screen_context_loss",
            at_read_step=read_step,
        )
        self._bind_new_context(descriptor, read_step)

        return "", self._read_audit(
            read_step=read_step,
            candidate_present=False,
            mature=False,
            eligible=False,
            actual_nonempty=False,
            reason="context_reset",
        )

    self.active_context.last_matched_read_step = read_step
    self._expire_old_first_supports(
        current_source_step=self.last_observed_step,
    )

    ready = [
        record
        for record in self.failure_records.values()
        if record.state == "READY"
    ]

    if len(ready) > 1:
        raise A12IntegrityError("more than one READY record")

    if not ready:
        return "", self._read_audit(
            read_step=read_step,
            candidate_present=False,
            mature=False,
            eligible=False,
            actual_nonempty=False,
            reason="no_ready_candidate",
        )

    candidate = ready[0]
    self.counters["eligibility_check_count"] += 1

    gate = {
        "state_ready": candidate.state == "READY",
        "exact_immediate_read":
            read_step == candidate.eligible_read_step,
        "not_expired":
            read_step <= candidate.expiry_read_step,
        "screen_match":
            match_kind in {"EXACT", "NEAR"},
        "not_delivered":
            not self._delivered_equivalent(
                descriptor=self.active_context.representative_descriptor,
                action_family=candidate.action_family,
            ),
        "episode_cap":
            self.nonempty_read_count < 5,
        "cooldown":
            (
                self.last_nonempty_read_step is None
                or
                read_step - self.last_nonempty_read_step >= 4
            ),
    }

    eligible = all(gate.values())

    if not eligible:
        reason = deterministic_gate_failure_reason(gate)
        candidate.state = "SUPPRESSED"
        candidate.suppression_reason = reason
        self.counters["candidate_suppressed_count"] += 1

        if not gate["cooldown"]:
            self.counters["cooldown_suppressed_count"] += 1
        if not gate["episode_cap"]:
            self.counters["cap_suppressed_count"] += 1
        if not gate["not_delivered"]:
            self.counters["one_shot_suppressed_count"] += 1

        return "", self._read_audit(
            read_step=read_step,
            candidate=candidate,
            candidate_present=True,
            mature=True,
            eligible=False,
            actual_nonempty=False,
            reason=reason,
            hard_gates=gate,
            screen_match_kind=match_kind,
            visual_distance=distance,
        )

    rendered = render_memory(candidate.action_label)

    if len(rendered) > 240:
        raise A12IntegrityError("rendered char cap exceeded")

    if len(rendered.encode("utf-8")) > 480:
        raise A12IntegrityError("rendered byte cap exceeded")

    candidate.state = "DELIVERED"

    delivered = DeliveredFailureSignature(
        delivered_id=make_delivered_id(candidate, read_step),
        representative_descriptor=
            self.active_context.representative_descriptor,
        action_family=candidate.action_family,
        action_key_sha256=candidate.action_key_sha256,
        evidence_signature=candidate.evidence_signature,
        delivered_read_step=read_step,
    )
    self.delivered_failures.append(delivered)

    self.nonempty_read_count += 1
    self.last_nonempty_read_step = read_step
    self.counters["eligible_candidate_count"] += 1
    self.counters["nonempty_read_count"] += 1

    read_event = create_read_event(
        read_step=read_step,
        candidate=candidate,
        screen_match_kind=match_kind,
        visual_distance=distance,
        rendered=rendered,
        all_hard_gates_passed=True,
        actual_nonempty=True,
    )

    self.read_events.append(read_event)

    self.post_read_watches.append(
        create_post_read_watch(
            read_event=read_event,
            failed_screen_descriptor=
                self.active_context.representative_descriptor,
            failed_action_family=candidate.action_family,
        )
    )

    del self.failure_records[candidate.action_key_sha256]

    return rendered, self._read_audit(
        read_step=read_step,
        candidate=candidate,
        candidate_present=True,
        mature=True,
        eligible=True,
        actual_nonempty=True,
        reason="delivered",
        hard_gates=gate,
        screen_match_kind=match_kind,
        visual_distance=distance,
        exact_injected_text=rendered,
        read_event=read_event,
    )
```

---

# 22. `observe_step(...)` 伪代码

```python
def observe_step(self, **kwargs) -> dict:
    source_step = int(kwargs["source_step"])

    if source_step != self.last_observed_step + 1:
        raise A12IntegrityError("non-monotonic source_step")

    before_pixels = extract_visible_rgb_only(
        dict(kwargs.get("before") or {})
    )
    after_pixels = extract_visible_rgb_only(
        dict(kwargs.get("after") or {})
    )

    action = validate_canonical_action(
        dict(kwargs.get("canonical_action") or {})
    )
    action_family = canonical_action_family(action)
    action_key = sha256_canonical_json(action_family)
    action_label = render_action_label(action_family)

    action_summary = str(kwargs.get("action_summary") or "")
    summary_sha = sha256(action_summary.encode("utf-8")).hexdigest()

    before_desc = describe_visual_state(before_pixels)
    after_desc = describe_visual_state(after_pixels)

    # The current before frame must still match the active context.
    if self.active_context is None:
        self._bind_new_context(
            before_desc,
            read_step=self.read_count - 1,
        )
    elif not screen_equivalent(
        before_desc,
        self.active_context.representative_descriptor,
    ):
        self._invalidate_active_context(
            reason="before_context_loss",
            at_source_step=source_step,
        )
        self._bind_new_context(
            before_desc,
            read_step=self.read_count - 1,
        )

    changed_fraction = changed_pixel_fraction(
        before_pixels,
        after_pixels,
    )

    same_screen_after = screen_equivalent(
        before_desc,
        after_desc,
    )

    no_progress = (
        same_screen_after
        and changed_fraction <= 0.001
    )

    # Update existing post-read causal watches.
    self._update_post_read_watches(
        source_step=source_step,
        action_family=action_family,
        before_descriptor=before_desc,
        after_descriptor=after_desc,
        material_progress=not no_progress,
    )

    if not no_progress:
        invalidated_ids = self._invalidate_active_context(
            reason="material_visible_progress_or_context_change",
            at_source_step=source_step,
        )

        self.counters["material_progress_reset_count"] += 1

        # The next read binds after_desc as a new context.
        self.active_context = None
        self.last_observed_step = source_step

        return {
            "written": bool(invalidated_ids),
            "source_step": source_step,
            "action_family": action_family,
            "action_key_sha256": action_key,
            "changed_pixel_fraction": changed_fraction,
            "no_material_progress": False,
            "context_invalidated": True,
            "invalidated_record_ids": invalidated_ids,
            "support_created": False,
            "candidate_matured": False,
            "candidate_id": None,
        }

    # No-progress on the same screen.
    self.active_context.last_matched_source_step = source_step

    # One-shot semantic suppression.
    if self._delivered_equivalent(
        descriptor=self.active_context.representative_descriptor,
        action_family=action_family,
    ):
        self.counters["one_shot_suppressed_count"] += 1
        self.last_observed_step = source_step

        return {
            "written": False,
            "source_step": source_step,
            "action_family": action_family,
            "action_key_sha256": action_key,
            "changed_pixel_fraction": changed_fraction,
            "no_material_progress": True,
            "context_invalidated": False,
            "support_created": False,
            "candidate_matured": False,
            "candidate_id": None,
            "reason": "already_delivered_for_equivalent_screen_action",
        }

    record = self.failure_records.get(action_key)

    if record is None:
        record = ActionFailureRecord(
            record_id=make_record_id(
                self.active_context.context_id,
                action_key,
                source_step,
            ),
            context_id=self.active_context.context_id,
            action_family=action_family,
            action_key_sha256=action_key,
            action_label=action_label,
            state="SEEN_ONCE",
            support_count=1,
            first_support_step=source_step,
            last_support_step=source_step,
            second_support_step=None,
            first_before_exact_sha256=before_desc.exact_sha256,
            first_after_exact_sha256=after_desc.exact_sha256,
            second_before_exact_sha256=None,
            second_after_exact_sha256=None,
            first_changed_fraction=changed_fraction,
            second_changed_fraction=None,
            first_summary_sha256=summary_sha,
            second_summary_sha256=None,
            maturity_step=None,
            eligible_read_step=None,
            expiry_read_step=None,
            evidence_signature=None,
            suppression_reason=None,
        )

        self.failure_records[action_key] = record
        self.counters["support_created_count"] += 1
        self._enforce_failure_record_capacity()

        self.last_observed_step = source_step

        return {
            "written": True,
            "source_step": source_step,
            "action_family": action_family,
            "action_key_sha256": action_key,
            "changed_pixel_fraction": changed_fraction,
            "no_material_progress": True,
            "context_invalidated": False,
            "support_created": True,
            "support_count": 1,
            "candidate_matured": False,
            "candidate_id": None,
        }

    if record.state in {"SUPPRESSED", "EXPIRED"}:
        self.last_observed_step = source_step
        return {
            "written": False,
            "source_step": source_step,
            "action_family": action_family,
            "action_key_sha256": action_key,
            "changed_pixel_fraction": changed_fraction,
            "no_material_progress": True,
            "support_created": False,
            "candidate_matured": False,
            "candidate_id": None,
            "reason": f"inert_record_{record.state.casefold()}",
        }

    if record.state == "READY":
        raise A12IntegrityError(
            "READY record survived its immediate read window"
        )

    if source_step - record.first_support_step > 12:
        record.state = "EXPIRED"
        self.counters["first_support_expiry_count"] += 1

        replacement = make_first_support_record(
            context=self.active_context,
            source_step=source_step,
            action_family=action_family,
            action_key=action_key,
            action_label=action_label,
            before_desc=before_desc,
            after_desc=after_desc,
            changed_fraction=changed_fraction,
            summary_sha=summary_sha,
        )
        self.failure_records[action_key] = replacement

        self.last_observed_step = source_step

        return {
            "written": True,
            "source_step": source_step,
            "support_created": True,
            "support_count": 1,
            "candidate_matured": False,
            "candidate_id": None,
            "reason": "old_first_support_replaced",
        }

    # Second independent support.
    record.state = "READY"
    record.support_count = 2
    record.second_support_step = source_step
    record.last_support_step = source_step
    record.second_before_exact_sha256 = before_desc.exact_sha256
    record.second_after_exact_sha256 = after_desc.exact_sha256
    record.second_changed_fraction = changed_fraction
    record.second_summary_sha256 = summary_sha
    record.maturity_step = source_step
    record.eligible_read_step = source_step + 1
    record.expiry_read_step = source_step + 1
    record.evidence_signature = make_evidence_signature(
        context=self.active_context,
        action_family=action_family,
        first_step=record.first_support_step,
        second_step=source_step,
    )

    self.counters["candidate_matured_count"] += 1
    self.last_observed_step = source_step

    return {
        "written": True,
        "source_step": source_step,
        "action_family": action_family,
        "action_key_sha256": action_key,
        "changed_pixel_fraction": changed_fraction,
        "no_material_progress": True,
        "context_invalidated": False,
        "support_created": True,
        "support_count": 2,
        "candidate_matured": True,
        "candidate_id": record.record_id,
        "maturity_step": source_step,
        "eligible_read_step": source_step + 1,
        "expiry_read_step": source_step + 1,
        "evidence_signature": record.evidence_signature,
    }
```

---

# 23. Post-read causal audit

Post-read watch 只更新 audit，不影响 memory read、trigger 或 action。

## 23.1 Next-action divergence

Read 后的第一个 executed action：

```text
next_action_diverged =
next canonical action family != failed canonical action family
```

对于 tap/long-press：

- 不同 grid cell 计为不同 target；
- 同 grid cell 但 summary 不同仍视为同 family；
- 不使用模型声称“点击了不同对象”来伪造 divergence。

## 23.2 Visible progress horizon

在 read 后的前 2 个 executed actions 中，若任一 action 满足：

```text
P > 0.001
OR screen context lost
```

则：

```text
material_progress_within_2 = true
```

这不是 semantic success。

## 23.3 Immediate relapse

在 read 后 4 个 executed actions内，再次出现：

```text
screen equivalent to failed context
AND canonical family == failed family
AND no material visible progress
```

则：

```text
same_failed_action_within_4 = true
```

## 23.4 Productive divergence hypothesis

只有 prospective live episode 中一条 read 同时满足：

```text
actual_nonempty == true
next_action_diverged == true
material_progress_within_2 == true
same_failed_action_within_4 == false
episode success == true
```

才可记录为：

```text
trace_grounded_productive_divergence_hypothesis
```

Evaluator reward 只在 episode 完成后由结果聚合器 join，不参与 watch 更新或 action decision。

---

# 24. `audit_record()` 与序列化

## 24.1 必须字段

```text
schema
mechanism_id
experiment_id

causal_boundary
  allowed_inputs
  query_used_for_decision = false
  action_summary_used_for_decision = false
  model_calls_added = 0
  evaluator_used_for_decision = false
  hidden_ui_used_for_decision = false
  future_information_used = false
  task_name_used = false
  episode_id_used = false
  guard_enabled = false
  action_override_count = 0
  forced_termination_count = 0

parameters
  screen thresholds
  changed-pixel threshold
  action-family buckets
  support count
  first-support gap
  read window
  cooldown
  all capacities
  all text/token limits

goal
  goal_sha256

active_context
  context_id
  descriptor audit
  created_read_step
  last_matched_read_step
  last_matched_source_step
  context_epoch

failure_records
delivered_failures
read_events
post_read_watches
counters

capacity
  active_failure_record_count
  max_observed_failure_record_count
  delivered_failure_count
  read_event_count
  post_read_watch_count
  max_rendered_chars
  max_rendered_utf8_bytes
  max_rendered_tokens
  serialized_audit_bytes
  resident_state_delta_bytes
```

## 24.2 禁止持久化

不得在 memory state 中保存：

```text
raw RGB arrays
完整 query
完整 action summary
UI tree
activity
package
reward
```

只保存：

```text
hashes
bounded descriptors
bounded action families
bounded exact injected text
```

## 24.3 Deterministic serialization

```python
payload = json.dumps(
    audit_record,
    ensure_ascii=True,
    sort_keys=True,
    separators=(",", ":"),
).encode("utf-8")
```

要求：

```text
len(payload) <= 131072
```

浮点数统一 round 至 6 位小数后序列化。

---

# 25. A-class 等价性证明

A12 与 A0 的唯一区别是：

```text
在满足冻结 trigger 时，
当前 model call 的 user prompt 末尾附加一段 bounded text。
```

A12 不改变：

```text
system prompt
model weights
model revision
sampling
seed
task state
native max steps
action parser
canonical action
action mapper
emulator
evaluator
model call count
transport attempts
```

对任意相同允许输入：

\[
X=(q,I_t,a_t,u_t,I_{t+1},t)
\]

和任意两个隐藏 metadata：

\[
H_1,H_2
\]

必须有：

\[
U(M,X,H_1)=U(M,X,H_2)
\]

\[
R(M,X,H_1)=R(M,X,H_2)
\]

只有模型在 prospective live run 中读取到 A12 text 后自行选择不同动作，轨迹才会改变。A12 不直接改变动作。

---

# 26. 实现文件映射

必须创建独立文件，不覆盖 A10-v2/A11。

```text
GPT_PRO_A12_MINIMAL_ACTION_DIVERGENCE_MEMORY_DESIGN_2026-08-13.md

protocols/
  A12_MADM_IMPLEMENTATION_BINDING_2026-08-13.md

implementation/src/raven_m/official_qwen_mobile/
  a12_minimal_action_divergence.py
  a12_contract.py

implementation/configs/
  a12_minimal_action_divergence_hard_seed20260806.json

implementation/scripts/
  build_a12_reference_segments.py
  replay_a12_offline_traces.py
  preflight_a12.py
  qualify_a12_live_server.py
  start_a12_server.sh

implementation/tests/official_qwen_mobile/
  test_a12_visual.py
  test_a12_action_family.py
  test_a12_state_machine.py
  test_a12_replay_binding.py
  test_a12_controller_integration.py
  test_a12_contract.py
  test_a12_capacity.py
  test_a12_leakage.py

evidence/a12/
  A12_REFERENCE_SEGMENTS.json
  A12_OFFLINE_TRACE_SOURCE_SPEC.json
  A12_STATIC_SOURCE_FREEZE.json
  A12_TEST_MANIFEST.json
  A12_OFFLINE_REPLAY_REPORT.json
  A12_OFFLINE_ABLATION_REPORT.json
  A12_ZERO_GENERATION_PREFLIGHT.json
  A12_LIVE_SERVER_RECEIPT.json
  A12_FINAL_RESULT.json
```

Runner 增加：

```text
--arm a12
```

不得将 A12 写入 A10-v2 或 A11 class。

---

# 27. 静态复杂度预算

Production memory 必须满足：

```text
trigger classes = 1
query parsers = 0
query regexes used for decisions = 0
route record classes = 0
frontier graph classes = 0
phase classes = 0
obligation/anchor classes = 0
score functions = 0
retrieval ranking formulas = 0
```

允许的数据记录类型最多 6 个：

```text
VisualDescriptor
ActiveScreenContext
ActionFailureRecord
DeliveredFailureSignature
ReadEvent
PostReadWatch
```

允许的主要行为阈值：

```text
1. RGB per-channel pixel threshold = 5
2. changed fraction threshold = 0.001
3. DL threshold = 0.06
4. DE threshold = 0.12
5. DV threshold = 0.055
6. repeat count = 2
7. first-support gap = 12
8. cooldown = 4
```

容量阈值不计入行为阈值，但必须全部固定。

---

# 28. 测试清单

## 28.1 Visual tests

| ID | 测试 |
|---|---|
| V01 | 同一 RGB exact hash 相同 |
| V02 | 只改变顶部/底部 4%，descriptor exact 不变 |
| V03 | 合法 near descriptor match |
| V04 | `DL=0.06` 边界匹配 |
| V05 | `DL>0.06` 不匹配 |
| V06 | `DE=0.12` 边界匹配 |
| V07 | `DV=0.055` 边界匹配 |
| V08 | 同均值不同布局由 edge bits 拒绝 |
| V09 | full-RGB changed fraction 正确 |
| V10 | `P=0.001` 为 no-progress |
| V11 | `P>0.001` 为 material progress |
| V12 | shape change 为 material progress |
| V13 | RGBA 只取前三通道 |
| V14 | non-contiguous integer RGB 合法 |
| V15 | float RGB 拒绝 |
| V16 | NaN 拒绝 |
| V17 | negative integer 拒绝 |
| V18 | value>255 拒绝 |
| V19 | H<25 拒绝 |
| V20 | W<8 拒绝 |
| V21 | C<3 拒绝 |

---

## 28.2 Action-family tests

| ID | 测试 |
|---|---|
| A01 | tap grid 边界 |
| A02 | tap 微小 jitter 同 bin |
| A03 | 跨 bin tap 不同 family |
| A04 | long-press 三个 duration buckets |
| A05 | swipe dominant direction |
| A06 | swipe 三个 length buckets |
| A07 | swipe 3×4 start grid |
| A08 | type NFKC deterministic |
| A09 | type text 改变则 family 改变 |
| A10 | `clear_text` 改变则 family 改变 |
| A11 | wait duration buckets |
| A12 | system action families |
| A13 | answer text hash |
| A14 | 非法 action type 抛 integrity error |
| A15 | 非有限坐标拒绝 |
| A16 | 越界坐标拒绝 |
| A17 | action label 不超过 48 chars |

---

## 28.3 State-machine tests

| ID | 测试 |
|---|---|
| S01 | 第一次 no-progress 只产生 SEEN_ONCE |
| S02 | 第二次 matching no-progress 产生 READY |
| S03 | READY 只在下一次 read eligible |
| S04 | Candidate creation 但未实际 read 不计成功 |
| S05 | Material progress 清空所有 active records |
| S06 | Screen context loss 清空 records |
| S07 | Near-equivalent screen 保持 context |
| S08 | Context 只与 representative 比较，防止 drift |
| S09 | 不同 action family 分别计数 |
| S10 | 中间不同 no-progress action 不清除第一 support |
| S11 | First support 超过 12 actions 被替换 |
| S12 | Cooldown=3 时 suppressed |
| S13 | Cooldown=4 时可读取 |
| S14 | Episode 第 6 次 read 被拒绝 |
| S15 | 同 screen/action one-shot |
| S16 | 离开并返回 near-equivalent screen 仍 one-shot |
| S17 | 被 cooldown suppress 的 candidate 不延迟读取 |
| S18 | SUPPRESSED record 在 context 内不重新成熟 |
| S19 | 新 context 可重新收集未曾 delivered 的 identity |
| S20 | 超过 1 个 READY 抛 integrity error |
| S21 | 每 episode reset 清空全部状态 |
| S22 | query 中途改变抛 integrity error |
| S23 | Action summary 改变不改变 decision |
| S24 | Query 文本改变但 goal hash一致性外不参与 trigger |

---

## 28.4 Rendering tests

| ID | 测试 |
|---|---|
| T01 | 模板逐字符完全匹配 |
| T02 | 最长 action label 下 chars<=240 |
| T03 | UTF-8 bytes<=480 |
| T04 | frozen tokenizer<=100 tokens |
| T05 | CJK/adversarial tokenizer fixture |
| T06 | 不含 completion claim |
| T07 | 不含具体 next action |
| T08 | Renderer 不使用 action summary |
| T09 | 空 renderer 被视为 integrity failure |

---

## 28.5 Replay-binding tests

| ID | 测试 |
|---|---|
| B01 | Candidate created、无 read，qualified=0 |
| B02 | READY 但 cooldown blocked，qualified=0 |
| B03 | Wrong screen read，qualified=0 |
| B04 | Wrong action family read，qualified=0 |
| B05 | Read after upper bound，qualified=0 |
| B06 | Empty read text，qualified=0 |
| B07 | Nonempty actual read with all fields，qualified=1 |
| B08 | 一个 read 不得匹配两个 segments |
| B09 | Segment 必须绑定 episode ID |
| B10 | Segment 必须绑定 exact source steps |
| B11 | Maturity step 必须等于 second support |
| B12 | Actual read step 必须等于 second+1 |
| B13 | Evidence signature 必须一致 |
| B14 | Expired candidate 不能匹配 |
| B15 | Candidate-only checker fixture 必须 fail |
| B16 | A6 cap/cooldown theoretical upper bound>=20 |
| B17 | A8 segment 独立匹配 |
| B18 | A9 segment 独立匹配 |

---

## 28.6 Leakage tests

对相同允许输入，分别改变：

```text
evaluator_reward
task_success
task_name
episode_id
ui_tree
accessibility
foreground
activity
package
database_state
transition
future_screenshot
```

必须得到完全相同：

```text
state transition
candidate maturity
read eligibility
rendered text
evidence signature
serialized decision state
```

---

## 28.7 Controller integration

必须断言：

```text
controller.cost_guard is None
controller.source_document_coverage_gate is None
stop_after_markor_source_exit is false

policy canonical action == executed canonical action
memory_added_model_calls == 0
transport_attempts == 1
memory text appended only to current prompt
memory text not inserted into action history
evaluator called only after episode loop
```

---

## 28.8 Maximum simultaneous-state test

必须在同一合法 state 中同时填满：

```text
1 active context
8 active failure records
  - 1 READY
  - 7 SEEN_ONCE
5 delivered failures from prior contexts
5 read events
5 post-read watches
2 descriptor-cache entries
maximum-length labels
maximum-length rendered texts
all counters at large legal values
```

而不是逐项单独填满。

必须满足：

```text
serialized audit <= 128 KiB
resident-state delta <= 2 MiB
```

Resident-state 测量使用 `tracemalloc`，排除 caller 持有的输入 RGB arrays。

---

# 29. 独立 reference segments

## 29.1 禁止循环证明

不得：

```text
运行 A12
→ 从 A12 candidates 中选择 segments
→ 再用这些 segments 证明 A12
```

Reference segments 必须在 formal A12 replay 前冻结。

## 29.2 Reference builder

脚本：

```text
build_a12_reference_segments.py
```

必须满足：

```text
MUST NOT import a12_minimal_action_divergence
MUST NOT read A12 replay output
MUST NOT read A12 candidate/read events
```

它使用：

1. 已冻结的 A10-v1 `loop_qualification_records` 中 23 个 A6 segment identities；
2. raw materialized episode JSON；
3. raw before/after RGB；
4. raw canonical action；
5. 独立实现的 frozen screen/action/no-progress checker；
6. A8-v2 Expense 和 A9 Retro 的独立 segment evidence。

A10-v1 report 保存了 23 个 A6 qualifying loop segments，并报告其中 22 个在旧宽松机制下被视为 qualified；A12 只复用 segment identity，不复用旧 mechanism 的 qualification 结论。

---

## 29.3 Reference-segment schema

```json
{
  "segment_id": "a12seg_<sha256-prefix>",
  "role": "a6|a8v2_expense|a9_retro",
  "episode_id": "...",
  "task_name_audit_only": "...",

  "first_failure_source_step": 0,
  "second_failure_source_step": 0,
  "segment_lower_source_step": 0,
  "segment_upper_source_step": 0,

  "required_maturity_step": 0,
  "required_actual_read_step": 0,
  "read_lower_bound": 0,
  "read_upper_bound": 0,

  "source_screen": {
    "first_exact_sha256": "...",
    "second_exact_sha256": "...",
    "first_descriptor": {},
    "second_descriptor": {},
    "screen_equivalent": true
  },

  "action": {
    "first_canonical_action_sha256": "...",
    "second_canonical_action_sha256": "...",
    "canonical_family": [],
    "action_key_sha256": "..."
  },

  "transition": {
    "first_changed_fraction": 0.0,
    "second_changed_fraction": 0.0,
    "first_no_progress": true,
    "second_no_progress": true
  },

  "third_same_action_step": null,
  "reference_source_sha256": "..."
}
```

## 29.4 Step bounds

对 segment：

```text
segment_lower_source_step = first_failure_source_step
segment_upper_source_step = second_failure_source_step

required_maturity_step = second_failure_source_step
required_actual_read_step = second_failure_source_step + 1

read_lower_bound = required_actual_read_step
read_upper_bound = required_actual_read_step
```

A12 使用 exact immediate-read qualification，不允许 `deadline+2`。

---

# 30. Strict actual-read qualification

一个 reference segment 只有同时满足以下全部条件才算 qualified：

```text
1. same episode
2. maturity source step == frozen second failure step
3. support steps bind frozen first and second steps
4. same canonical action family
5. source screen equivalent to frozen segment screen
6. candidate state == READY before read
7. hard eligibility == true
8. actual read step == frozen required read step
9. actual injected text is nonempty
10. actual injected text equals recorded exact_injected_text
11. evidence signature matches read event
12. candidate not expired
13. candidate not suppressed
14. read one-to-one assigned to this segment
```

以下任何情况均计为 0：

```text
candidate exists
candidate matured but no read
candidate on another screen
candidate for another action
candidate blocked by cooldown
candidate blocked by cap
candidate delivered after deadline
candidate only appears in audit
empty renderer
read text not actually returned to controller
```

---

# 31. Zero-generation replay corpus

正式 A12 replay 必须重新验证现有 materialized corpus：

```text
27 episodes
1,668 files
442,138,413 bytes
generation_calls = 0
```

不得只读取旧报告摘要。必须重新读取真实 episode JSON 与 RGB screenshot bytes，并重新核对 manifest hashes。A10-v2/A11 均对同一 corpus 完成了这些完整性验证。

角色：

```text
4 A0 competent histories
1 additional A0 Recipe failure history
1 A1 Recipe success history
19 A6 failure histories
1 A8-v2 Expense history
1 A9 Retro history
```

Offline replay 不执行模型，也不会把 A12 text 反馈进冻结 action sequence。

---

# 32. Offline replay 可以证明什么

Offline replay 只允许支持以下结论：

```text
trigger recall
false-positive exposure on competent histories
read timing
screen/action binding
actual read eligibility
one-shot correctness
cooldown correctness
capacity
token/character bounds
renderer actionability form
```

Offline replay 不允许支持：

```text
A12 changed the next action
A12 caused loop escape
A12 improved reward
A12 increased success
```

冻结历史中的下一 action 是原 arm 已经生成的 action，不是看到 A12 text 后重新生成的 action。任务书明确要求将这两个证据层级分开。

---

# 33. A6 strict gate

## 33.1 Availability

必须完整冻结并验证：

```text
A6 qualifying segments = 23
```

若不是 23：

```text
reference freeze failure
live forbidden
```

## 33.2 Actual read recall

要求：

\[
Qualified_{A6}\ge20/23
\]

即：

\[
Recall_{A6}\ge0.869565
\]

这比任务书最低的 80% 更具体：由于要求至少 20 个 segment，实际阈值就是 20/23。

## 33.3 Cap-feasibility witness

OsmAndTrack 含 8 个冻结 segment，其 second no-progress steps 包括 5、9、14、19、55、61、75、89；episode read cap 为 5，因此该 episode 理论上最多贡献 5 个。其余 A6 episodes 合计 15 个 segment，所以 whole-corpus 理论上限恰好可以达到：

\[
15+5=20
\]

Reference-freeze 阶段必须按 cooldown、one-shot 和 episode cap 做一次 interval-feasibility calculation。

要求：

```text
theoretical_max_qualifiable_segments >= 20
```

若理论上限小于 20，本文 protocol 在实现前即属于：

```text
PROTOCOL_INVALID
```

不得继续写代码或烧 GPU。冻结 OsmAndTrack 的八个 segment steps 可由当前 A10 report 直接核对。

## 33.4 Precision

在 failure roles：

```text
A6 + A8-v2 Expense + A9 Retro
```

定义：

\[
ReadPrecision
=
\frac{
one\text{-}to\text{-}one\ matched\ actual\ reads
}{
all\ actual\ nonempty\ reads
}
\]

要求：

\[
ReadPrecision\ge0.80
\]

并且：

```text
unbound actual reads <= 5
```

---

# 34. A0 competent-history gate

使用：

```text
ExpenseDeleteMultiple2
RetroSavePlaylist
SimpleCalendarAddOneEvent
SportsTrackerTotalDurationForCategoryThisWeek
```

要求：

```text
total actual nonempty reads across four <= 2
per-episode actual reads <= 1
total read density <= 0.03
total rendered characters <= 480
broad navigation read count = 0
single action support read count = 0
candidate-only qualification count = 0
anti-leakage violations = 0
```

“Broad navigation read”定义为：

```text
read 不绑定同 screen/action family 的两个 no-progress supports
```

由于 A12 只有一个 trigger，任何 broad-navigation read 都属于实现错误。

A11 在四条 competent histories上只读 1 次，说明 `<=2` 是可实现的精度目标，而不需要恢复绝对静默这一可能鼓励过拟合的约束。

历史 A0 sparse gate 只证明 frozen competent sequence 上注入稀疏。真正能力保持仍由 prospective live 4/4 gate 决定。

---

# 35. A8-v2 Expense gate

冻结一个或多个独立 reference segments。

至少要求：

```text
qualifying segment count >= 1
earliest segment actual read = 1
actual read step == earliest second-failure step + 1
all matched fields exact
episode actual reads <= 5
unbound reads before earliest deadline = 0
```

当前证据中 A8-v2 Expense 的 repeated bad branch 资格点位于第二次坏 action 附近，而 A11 直到更晚才产生可用读取；A12 必须在第二次 no-progress 之后的即时 read 上完成 actual injection，而不能以 episode 后部任意 candidate 代替。

---

# 36. A9 Retro gate

冻结 A9 Retro 的三个 independent branch-pair segments。

要求：

```text
qualified actual reads >= 2/3
earliest segment must be qualified
earliest actual read step =
  earliest second-failure step + 1

episode actual reads <= 5
no unbound read before earliest segment
```

A9 的旧 canary 是否存在不参与 A12 decision；它只在 replay report 中作为历史 timing comparator。

---

# 37. A1 Recipe 辅助精度门

A12 不解析 query，不再建立 Recipe constraint parser gate。

A1 Recipe 成功历史只用于辅助 prompt-pollution 检查：

```text
actual nonempty reads <= 1
every read must bind two no-progress supports
unbound reads = 0
```

不得因为它是 A1 的新增成功任务而设置任务白名单。

---

# 38. Formal replay pass 条件

`A12_OFFLINE_REPLAY_REPORT.status` 只有在以下全部满足时才可为 `pass`：

```text
1. exact mechanism ID
2. exact experiment ID
3. 27 episodes complete
4. 1,668 file hashes pass
5. 442,138,413 bytes pass
6. generation_calls = 0

7. reference segment count exact
8. A6 qualified >=20/23
9. A6 actual-read recall gate pass
10. failure-role read precision >=0.80
11. unbound failure reads <=5

12. A0 competent total reads <=2
13. each competent episode reads <=1
14. competent read density <=0.03
15. no broad navigation read

16. A8 earliest segment qualified
17. A9 earliest segment qualified
18. A9 total >=2/3

19. A1 Recipe auxiliary sparse gate pass

20. every qualified segment has actual nonempty read
21. candidate-only qualification count = 0
22. every read chars<=240
23. every read bytes<=480
24. every read tokens<=100
25. every episode reads<=5
26. every episode memory tokens<=500
27. all cooldown gaps>=4
28. one-shot violations=0
29. audit bytes<=128 KiB
30. resident state<=2 MiB
31. hidden/evaluator/future violations=0
32. source hashes exact
33. errors=[]
```

任一失败：

```text
status = fail
live_generation_authorized = false
```

不得把失败降级为 warning。

---

# 39. 防止 checker 假通过

Formal report 必须分别报告：

```text
support_record_count
candidate_matured_count
eligible_candidate_count
actual_nonempty_read_count
qualified_segment_count
```

并断言：

\[
qualified\_segment\_count
\le
actual\_nonempty\_read\_count
\le
eligible\_candidate\_count
\le
candidate\_matured\_count
\]

Replay checker 中不得出现：

```python
qualified += candidate_exists
```

只能出现等价于：

```python
qualified += actual_read_event_matches_all_segment_fields
```

测试必须包含一个专门 fixture：

```text
candidate matured at correct step
but read blocked by cooldown
```

预期：

```text
candidate_matured = 1
actual_nonempty_read = 0
qualified_segment = 0
```

---

# 40. Source freeze，无自引用

## 40.1 两层冻结

### Layer 1 — implementation freeze

先创建：

```text
A12_IMPLEMENTATION_COMMIT
```

该 commit 包含：

```text
design
binding
production implementation
contract
config
scripts
exact tests
reference segments
source specification
test manifest
```

但不包含：

```text
formal replay report
preflight report
live receipt
live result
```

### Layer 2 — evidence commit

在 clean `A12_IMPLEMENTATION_COMMIT` 上执行 formal replay。

之后的 evidence commit 只添加：

```text
A12_STATIC_SOURCE_FREEZE.json
A12_OFFLINE_REPLAY_REPORT.json
A12_OFFLINE_ABLATION_REPORT.json
A12_ZERO_GENERATION_PREFLIGHT.json
```

Production behavior files的 hashes 必须与 `A12_IMPLEMENTATION_COMMIT` 完全一致。

## 40.2 Source-freeze 内容

`A12_STATIC_SOURCE_FREEZE.json` 列出每个具体文件和 SHA256，不允许：

```text
all A12 tests
all relevant scripts
etc.
```

它不得包含自己的 whole-file SHA。

定义：

```python
payload_sha256 = SHA256(
  canonical_json({
    "implementation_commit": "...",
    "files": {
      "exact/path": "sha256",
      ...
    }
  })
)
```

Replay report 绑定 `payload_sha256`。

Preflight 绑定：

```text
source_freeze payload_sha256
replay report whole-file sha256
```

Live receipt 再绑定 preflight SHA。

不存在：

```text
source freeze
→ replay report hash
→ source freeze
```

的循环引用。

---

# 41. Exact source closure

必须逐项列出：

```text
GPT_PRO_A12_MINIMAL_ACTION_DIVERGENCE_MEMORY_DESIGN_2026-08-13.md
protocols/A12_MADM_IMPLEMENTATION_BINDING_2026-08-13.md

implementation/src/raven_m/official_qwen_mobile/a12_minimal_action_divergence.py
implementation/src/raven_m/official_qwen_mobile/a12_contract.py
implementation/src/raven_m/official_qwen_mobile/controller.py
implementation/src/raven_m/official_qwen_mobile/protocol.py
implementation/src/raven_m/official_qwen_mobile/__init__.py

implementation/configs/androidworld_hard_v2_instances.json
implementation/configs/a12_minimal_action_divergence_hard_seed20260806.json

implementation/scripts/run_official_qwen_mobile.py
implementation/scripts/run_a678_arm.py
implementation/scripts/build_a12_reference_segments.py
implementation/scripts/replay_a12_offline_traces.py
implementation/scripts/preflight_a12.py
implementation/scripts/qualify_a12_live_server.py
implementation/scripts/start_a12_server.sh

implementation/src/raven_m/models/vllm_client.py
implementation/src/raven_m/env/androidworld_adapter.py
implementation/src/raven_m/multi_framework_benchmark/task_instances.py

implementation/tests/official_qwen_mobile/test_a12_visual.py
implementation/tests/official_qwen_mobile/test_a12_action_family.py
implementation/tests/official_qwen_mobile/test_a12_state_machine.py
implementation/tests/official_qwen_mobile/test_a12_replay_binding.py
implementation/tests/official_qwen_mobile/test_a12_controller_integration.py
implementation/tests/official_qwen_mobile/test_a12_contract.py
implementation/tests/official_qwen_mobile/test_a12_capacity.py
implementation/tests/official_qwen_mobile/test_a12_leakage.py

evidence/a12/A12_REFERENCE_SEGMENTS.json
evidence/a12/A12_OFFLINE_TRACE_SOURCE_SPEC.json
evidence/a12/A12_TEST_MANIFEST.json

immutable evidence inputs:
evidence/a10/A10_OFFLINE_TRACE_MANIFEST.json
evidence/a10/A10_OFFLINE_REPLAY_REPORT.json
evidence/a10_v2/A10_V2_OFFLINE_REPLAY_REPORT.json
evidence/a11/A11_OFFLINE_REPLAY_REPORT.json
evidence/a2/A0_A1_PAIRED_REFERENCE_20260810.json
evidence/a678/A8_V2_OFFLINE_TRACE_AUDIT_2026-08-11.json
evidence/a678/A89_INITIAL_GATE_RESULTS_2026-08-12.json
```

---

# 42. Zero-generation preflight

输出：

```text
evidence/a12/A12_ZERO_GENERATION_PREFLIGHT.json
```

## 42.1 必查 identity

```text
current source closure matches A12_IMPLEMENTATION_COMMIT
implementation commit is descendant of ee30db369...
worktree tracked files clean
worktree untracked files empty
mechanism ID exact
experiment ID exact
config schema exact
```

## 42.2 Benchmark identity

```text
model ID exact
revision exact
system prompt hash exact
task seed 20260806
generation seed 3407
sampling exact
19 unique tasks
native max steps exact
task order exact
```

## 42.3 Software

```text
all shared official_qwen_mobile tests pass
all eight exact A12 test files pass
failed = 0
errors = 0
deselected = 0
collected test node IDs match A12_TEST_MANIFEST
```

## 42.4 Replay

```text
A12_OFFLINE_REPLAY_REPORT.status == pass
generation_calls == 0
reference hashes exact
actual-read gates exact
```

## 42.5 Tokenizer

使用冻结 Qwen tokenizer，对：

```text
all action labels
max-length template
all action-family variants
Unicode adversarial fixtures
```

计数。

要求：

```text
max tokens/read <=100
max tokens/episode <=500
```

Tokenizer 不得进入 runtime memory module。

## 42.6 Static boundary scan

Production module 禁止 import：

```text
requests
urllib
httpx
socket
openai
transformers
vllm
torch
```

允许：

```text
numpy
hashlib
json
math
unicodedata
dataclasses
typing
```

Production module 中禁止出现：

```text
19 task names
27 episode IDs
frozen screenshot hashes
A0/A1/A6/A8/A9 role strings
Broccoli
RetroSavePlaylist
SimpleCalendarAddOneEvent
```

测试 fixture、contract task order和 evidence builder 不受最后一项字面扫描限制，但不得把这些字符串传给 memory decision。

## 42.7 Runtime canaries

必须包括：

```text
first no-progress → empty read
second no-progress → immediate nonempty read
candidate blocked → no qualified read
material progress → cancel
context loss → cancel
same signature → one-shot
hidden metadata mutation → identical behavior
```

## 42.8 Cost benchmark

在 live host CPU 上对全部冻结 RGB replay 测量：

```text
read_cpu_ms_p50
read_cpu_ms_p95
observe_cpu_ms_p50
observe_cpu_ms_p95
projected_cpu_seconds_for_120_steps
```

准入上限：

```text
read p95 <= 30 ms
observe p95 <= 60 ms
projected 120-step A12 CPU overhead <= 12 seconds
```

这不含：

```text
screenshot acquisition
ADB
model inference
evaluator
disk artifact writing
```

## 42.9 Preflight verdict

```text
PASS
SCIENTIFIC_PREFLIGHT_FAILURE
INFRASTRUCTURE_PREFLIGHT_FAILURE
PROTOCOL_INVALID
```

只有：

```text
status = PASS
errors = []
generation_calls = 0
```

才允许生成 live receipt。

---

# 43. 何时标记 protocol invalid

以下任一成立，必须直接标：

```text
A12_PROTOCOL_INVALID
```

并停止：

1. 相同输入在规范中同时要求 read 和 no-read；
2. 23 个 reference segments 无法在独立 raw trace 中重新验证；
3. episode cap、cooldown、one-shot 下理论最大 A6 qualification 小于 20；
4. 实现必须读取 task name、reward、UI tree 或 future frame 才能达到 gate；
5. source-freeze 只能通过自引用实现；
6. preflight 和 receipt 字段无法一一对应；
7. READY candidate 不可能在 controller 的下一 read 上被观察；
8. renderer 的理论最小文本仍超过 token/character上限；
9. 最大合法 simultaneous state 必然超过 128 KiB 或 2 MiB；
10. 只有增加第二 trigger family 才能达到 formal replay，但没有新版本设计和独立证据。

Protocol invalid 时：

```text
do not continue to GPU
do not weaken gates
do not add task/page exceptions
```

---

# 44. Live receipt

必须创建全新的：

```text
evidence/a12/A12_LIVE_SERVER_RECEIPT.json
```

不得复用 A10-v2、A11、A8 或 A9 receipt。

## 44.1 精确字段

```text
schema
status
mechanism_id
experiment_id

implementation_commit
source_freeze_payload_sha256
offline_replay_sha256
preflight_sha256
launch_intent_sha256

served_model_id
model_realpath
model_manifest_sha256

process_pid
process_cmdline
host
port

vllm_version
torch_version
transformers_version

observed_served_model_ids
qualification_timestamp
generation_calls = 0
```

Preflight、launch intent、receipt 和 contract 必须使用完全相同字段名。

不得出现：

```text
preflight_sha in one file
a12_preflight_hash in another
```

这类隐式映射。

## 44.2 Qualification

必须核对：

```text
preflight.status == PASS
preflight.generation_calls == 0
process alive
/proc PID command exact
served model list exact
model path exact
model manifest exact
package versions exact
receipt age <=12 hours
```

---

# 45. Fresh four-task gate

前四个 valid episodes 顺序固定：

1. `ExpenseDeleteMultiple2`
2. `RetroSavePlaylist`
3. `SimpleCalendarAddOneEvent`
4. `SportsTrackerTotalDurationForCategoryThisWeek`

每个必须：

```text
reward == 1.0
transport_attempt_max == 1
memory_added_model_calls == 0
guard == false
action_override_count == 0
forced_termination_count == 0
```

任一 valid scientific failure：

```text
suite_status = stopped_capability_gate_failure
remaining_15_released = false
```

不得重跑。

若 4/4 通过但 A12 全程静默，只能得出：

```text
A0 capability preservation evidence
```

不能得出：

```text
memory improvement evidence
```

---

# 46. Gate 后的 15 题顺序

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

4/4 通过后必须完成全部 15 题。

不得因：

```text
中间成功数高
中间成功数低
memory没有激活
某任务特别困难
```

提前选择性停止。

---

# 47. Infrastructure invalid

仅以下情况允许：

```text
vLLM process crash
HTTP transport incomplete
transport attempts != 1
ADB disconnect
emulator crash
UIAutomator state acquisition failure
task initialization/reset exception
corrupt screenshot
invalid RGB caused by infrastructure
evaluator exception
evaluator missing/nonfinite result
model/source/config receipt mismatch
artifact corruption before evaluator result commits
```

以下属于 scientific failure：

```text
reward 0
partial reward below success
max_steps
model loop
wrong action
invalid model response
model terminate
model answer
memory silent
memory unhelpful
memory misleading
```

---

# 48. Infrastructure-invalid replacement 与 resume

## 48.1 双向链接

Invalid attempt：

```text
resolved_by_episode_id
```

Replacement valid episode：

```text
resolves_invalid_episode_ids
```

两边必须相互包含。

## 48.2 Identity

Resume 只允许在完全相同：

```text
mechanism_id
experiment_id
config_sha256
source_freeze_sha256
implementation_commit
preflight_sha256
model_manifest_sha256
task seed
generation seed
```

下进行。

不得跨 receipt 进程 resume，除非新 receipt 明确绑定同一 source/preflight/model identity，并被加入 receipt chain。

## 48.3 上限

每个 task 最多允许：

```text
2 infrastructure-invalid attempts
```

第三次仍 infrastructure invalid：

```text
suite_status = infrastructure_incomplete
```

## 48.4 Scientific failure

Scientific failure 是 terminal，不允许 replacement。

---

# 49. Exact 19/19 closure

正式结果必须有：

```text
exactly 19 valid episodes
one valid episode per frozen task
exact frozen order
no duplicated gate task
no omitted task
unique episode IDs
all rewards finite
all transport_attempt_max == 1
all invalid attempts resolved bidirectionally
```

不得拼接：

```text
A10-v2 episodes
A11 episodes
old A0/A1 episodes
diagnostic replications
different A12 implementation versions
```

---

# 50. Full-suite superiority criterion

A12 的 preregistered overall performance target：

```text
success_count >= 6
reward_sum > 5.5
```

这同时意味着：

```text
strictly better success count than A0
strictly better success count than A1
strictly better reward than A1
```

## 50.1 Cost superiority

还必须满足：

```text
memory_added_model_calls == 0
model_calls < 603
executed_actions < 596
total_tokens < 3,464,267
nonempty memory reads <= 95
rendered memory tokens <= 9,500
```

A12 的 hard read cap 使完整 19 题最多有：

\[
19\times5=95
\]

次 memory exposure，仅为 A1 580 次读取的约 16.4%。A12 的 memory text hard upper bound 为 9,500 tokens；A1 相对 A0 的 observed total-token 增量为 2,190,906，但二者不是完全相同的 token accounting，最终仍必须报告真实 prompt、completion 和 total tokens。

Elapsed time 受服务器和 emulator 状态影响，必须报告，但不作为唯一 cost pass/fail 指标。

---

# 51. Result schema

```json
{
  "schema": "a12_madm_result_v1",
  "status": "...",

  "identity": {
    "mechanism_id": "a12_minimal_action_divergence_memory_v1",
    "experiment_id": "A12_MADM_QWEN3VL32B_AW_HARD_T20260806_G3407_V1",
    "review_commit": "ee30db3692bd7797722b3ea29a70266eb6256c7e",
    "implementation_commit": "...",
    "source_freeze_payload_sha256": "...",
    "reference_segments_sha256": "...",
    "offline_replay_sha256": "...",
    "preflight_sha256": "...",
    "live_receipt_chain": ["..."]
  },

  "benchmark": {
    "task_seed": 20260806,
    "generation_seed": 3407,
    "valid_episode_count": 19,
    "invalid_attempt_count": 0,
    "exact_order": true
  },

  "gate": {
    "status": "pass",
    "success_count": 4,
    "required": 4,
    "memory_active_success_count": 0
  },

  "performance": {
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
    "first_support_count": 0,
    "candidate_matured_count": 0,
    "eligible_candidate_count": 0,
    "actual_nonempty_read_count": 0,
    "context_reset_count": 0,
    "cooldown_suppressed_count": 0,
    "cap_suppressed_count": 0,
    "one_shot_suppressed_count": 0,
    "rendered_chars_total": 0,
    "rendered_tokens_total": 0,
    "successful_active_memory_episodes": [],
    "productive_divergence_count": 0,
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
  "read_causal_records": [],
  "errors": []
}
```

---

# 52. Per-episode schema

```text
task_index
task_name
task_seed
native_max_steps

episode_id
episode_json_sha256
resolves_invalid_episode_ids

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

first_support_count
candidate_matured_count
eligible_candidate_count
actual_nonempty_read_count

first_nonempty_read_step
rendered_chars
rendered_tokens

context_reset_count
cooldown_suppressed_count
cap_suppressed_count
one_shot_suppressed_count

next_action_divergence_count
material_progress_after_read_count
same_failed_action_relapse_count

model_calls_added
guard_enabled
action_override_count
forced_termination_count
hidden_ui_used
evaluator_used
future_used
```

---

# 53. 每条 read 的 prospective 因果记录

```text
task
episode_id
read_step

failed_screen_descriptor
failed_action_family
failed_action_label

first_support_step
second_support_step
support_count

maturity_step
eligible_read_step
actual_nonempty

exact_injected_text
rendered_sha256
rendered_chars
rendered_tokens

next_action_step
next_action_family
next_action_diverged

material_progress_within_2
context_loss_within_2
same_failed_action_within_4

episode_reward
episode_success
productive_divergence_hypothesis
```

---

# 54. Offline 与 live 结论边界

## 54.1 Offline pass 允许说

```text
A12 can expose a bounded reminder
at the intended second-failure point
on at least 20/23 frozen A6 segments,
while remaining sparse on competent histories.
```

## 54.2 Offline pass 不允许说

```text
A12 changes actions.
A12 escapes loops.
A12 improves reward.
A12 beats A1.
```

## 54.3 Live pass 可以支持

如果 full suite 达到性能目标且存在 productive divergence，可以说：

> 在固定 seed 和 19 个冻结实例上，A12 相对 A0/A1 获得更高 success/reward，并且至少一条成功轨迹在 memory read 后出现了与失败 family 不同的下一动作和短期可见进展。

仍不能从一个 19-task、单-seed run 推断：

```text
跨 seed 一般显著性
跨模型普适性
跨 benchmark 普适性
严格的单 read 因果证明
```

---

# 55. Ablation plan

Ablation 只用于解释 A12 的设计选择，不得替代主 arm，也不得在 formal primary replay 后据结果继续调参。

## 55.1 A12-R3：第三次失败才读

```text
repeat_count = 3
```

其他规则不变。

报告：

```text
A6 actual-read recall
A0 competent reads
A8/A9 timing
```

目的：验证两次阈值是否确实是高召回所必需。

## 55.2 A12-EXACT：只用 exact screen

```text
near matching disabled
```

目的：量化 near equivalence 对 recall 和 competent exposure 的贡献。

## 55.3 A12-NOCANCEL：不因 material progress 清空

仅 zero-generation diagnostic，永不进入 live。

目的：证明 immediate progress invalidation 是否抑制 stale prompts。

## 55.4 A12-NOONESHOT：取消 one-shot/cooldown

仅 zero-generation diagnostic，永不进入 live。

目的：量化 prompt exposure 的上界爆炸。

## 55.5 Ablation 结论边界

Ablation 只能说明：

```text
trigger recall
exposure
timing
capacity
```

不能说明哪种文本提高 live success。

任何未来 live ablation 必须作为独立 experiment 重新预注册。

---

# 56. 最强失败风险

A12 最强的科学失败风险不是 trigger recall，而是：

> **“知道某动作在此屏没有可见进展”并不等于知道存在一个可行替代动作。**

A12 只提供：

```text
negative local evidence
+
divergence instruction
```

它不提供：

```text
目标对象语义
正确控件位置
新路线
页面结构
任务阶段
成功验证
```

因此即使 A12 达到 20/23 offline actual-read recall，模型仍可能：

1. 忽略 memory；
2. 重复相同 family；
3. 换成另一个同样错误的 family；
4. 离开当前页面后进入更长的错误路线；
5. 因 prompt perturbation 丢失原本会完成的行为。

第二个重要风险是：

```text
没有明显 RGB 变化
```

并不总等于 action 失败。某些动作可能改变不可见状态、等待异步更新，或需要重复输入。A12 通过 two-support、one-shot、immediate cancellation 和 4/4 live gate 缓解这一风险，但不能从根本上消除。

---

# 57. Falsification criteria

## 57.1 Pre-GPU falsification

任一成立即 `A12_ZERO_GENERATION_NO_GO`：

```text
A6 actual reads <20/23
A0 competent reads >2
A8 earliest segment not actually read
A9 earliest segment not actually read
A9 qualified <2/3
failure-role read precision <0.80
candidate-only qualification >0
single-support read >0
broad-navigation read >0
cooldown violation
one-shot violation
token/character/capacity violation
hidden/evaluator/future input
extra model call
source-freeze mismatch
```

## 57.2 Live preservation falsification

四题 gate 任一失败：

```text
A12_CAPABILITY_GATE_FAILURE
```

不释放剩余 15 题。

## 57.3 Full performance falsification

19 题完成但：

```text
success <6
OR reward <=5.5
OR not strictly better than A1
```

则：

```text
A12_SCIENTIFIC_FAILURE
```

## 57.4 Mechanism-evidence falsification

即使达到 6/19，若：

```text
no successful episode contains actual nonempty read
OR no productive divergence hypothesis
```

则：

```text
A12_PERFORMANCE_PASS_MECHANISM_EVIDENCE_FAIL
```

## 57.5 Divergence thesis falsification

若超过 50% 的 actual reads 满足：

```text
next action uses same failed family
AND no material progress within 2
```

则 A12 的 action-divergence thesis 被证伪。

---

# 58. Final verdict taxonomy

```text
A12_PROTOCOL_INVALID
A12_INFRASTRUCTURE_PREFLIGHT_FAILURE
A12_SCIENTIFIC_PREFLIGHT_FAILURE
A12_LIVE_NOT_AUTHORIZED
A12_CAPABILITY_GATE_FAILURE
A12_SUITE_INFRASTRUCTURE_INCOMPLETE
A12_SCIENTIFIC_FAILURE
A12_PERFORMANCE_PASS_MECHANISM_EVIDENCE_FAIL
A12_OVERALL_PASS
```

## `A12_OVERALL_PASS`

只有全部满足：

```text
formal replay pass
zero-generation preflight pass
fresh live receipt pass

4/4 capability gate
exact 19/19 closure

success >=6
reward >5.5

model calls <603
executed actions <596
total tokens <3,464,267

zero extra calls
zero guard
zero override
zero forced termination

at least one successful active-memory episode
at least one productive divergence hypothesis
```

---

# 59. 最小可实现 A12 定义

A12 的完整运行时逻辑可以压缩为以下定义：

```text
1. Bind the currently visible RGB screen.
2. For each canonical action family on that screen:
   - first no-progress result: remember once;
   - second no-progress result within 12 actions:
     create READY.
3. On the immediately following read:
   - require the same screen;
   - require cooldown and episode cap;
   - require that this screen/action failure has never been delivered;
   - inject one fixed <=240-character reminder.
4. Any material visible progress or screen loss clears all active evidence.
5. Never read the same matched screen/action failure twice.
```

它只有：

```text
1 trigger
1 active screen
8 bounded action records
5 delivered signatures
5 maximum reads
0 query parser
0 route graph
0 phase state
0 score
0 planner
0 model calls
```

---

# 60. Pre-GPU checklist

- [ ] Mechanism ID 与 Experiment ID 完全匹配本文。
- [ ] 实现提交是 `ee30db369...` 的后代。
- [ ] Reference segments 在 A12 replay 前独立冻结。
- [ ] 23 个 A6 segments 均从真实 RGB/action 重新验证。
- [ ] A8-v2 Expense 与 A9 Retro segments 独立冻结。
- [ ] Candidate creation 不能计为 actual read。
- [ ] A6 actual timely reads 至少 20/23。
- [ ] A0 四条 competent histories 合计不超过 2 reads。
- [ ] A8 earliest segment 获得即时实际读取。
- [ ] A9 earliest segment 获得即时实际读取，且至少 2/3。
- [ ] Failure-role actual-read precision 至少 0.80。
- [ ] 每次 read 不超过 240 chars、480 bytes、100 tokens。
- [ ] 每 episode 不超过 5 reads、500 memory tokens。
- [ ] Cooldown 至少 4 executed actions。
- [ ] One-shot violations 为 0。
- [ ] Audit JSON 不超过 128 KiB。
- [ ] Resident-state delta 不超过 2 MiB。
- [ ] Read/observe CPU overhead 通过 frozen benchmark。
- [ ] Hidden/evaluator/future invariance tests 全部通过。
- [ ] Extra model calls、guard、override、termination 均为 0。
- [ ] 全部 shared 和 A12 tests 通过。
- [ ] Source closure 精确列出每个文件与测试。
- [ ] Source freeze 无自引用。
- [ ] Preflight/receipt 字段逐字一致。
- [ ] Formal replay `status=pass`。
- [ ] Preflight `status=PASS` 且 `generation_calls=0`。
- [ ] Fresh A12 live receipt 绑定同一 source/preflight/model process。
- [ ] 以上任一项失败时不启动 GPU generation。

---

# 61. 精确 four-task 与 19-task stop rules

## Rule 1 — Pre-GPU stop

Formal replay、source freeze、tests、tokenizer、capacity、preflight 或 receipt 任一失败：

```text
STOP
DO NOT START LIVE GENERATION
```

## Rule 2 — Four-task fail-fast

依次运行四条 A0-success tasks。

任一 valid scientific failure：

```text
STOP IMMEDIATELY
DO NOT RELEASE REMAINING 15
```

## Rule 3 — Infrastructure replacement

只有 infrastructure-invalid attempt 可替换。

必须：

```text
same task
same identities
same seeds
bidirectional linkage
maximum two invalid attempts per task
```

第三次 infrastructure invalid：

```text
STOP AS INFRASTRUCTURE INCOMPLETE
```

## Rule 4 — Gate pass

只有 4/4 后：

```text
RELEASE THE REMAINING 15
```

## Rule 5 — Full-suite closure

Gate 通过后必须按冻结顺序运行全部 15 题。

不得基于 interim success、memory activity 或预期结果提前选择性停止。

## Rule 6 — Final scientific verdict

19/19 后：

```text
success >=6
AND reward >5.5
AND cost criteria pass
AND active-memory success exists
AND productive divergence exists
```

才允许 `A12_OVERALL_PASS`。

---

# 62. 预期 token 与时间开销

## 62.1 Prompt hard upper bound

单次：

```text
<=100 memory tokens
<=240 visible chars
```

单 episode：

```text
<=5 reads
<=500 memory tokens
<=1,200 visible chars
```

完整 19 题：

```text
<=95 reads
<=9,500 memory tokens
<=22,800 visible chars
```

A1 实际发生 580 次非空读取；A12 完整 suite 的理论最高 exposure 是其约 16.4%。

## 62.2 Model-call overhead

```text
exactly 0 extra model calls
```

A12 不增加 transport request 数量。

## 62.3 CPU overhead

算法复杂度：

\[
O(HW)
\]

用于：

```text
RGB validation
exact hash
pixel diff
9x16 descriptor
```

其余 record lookup 最多 8 项，是固定上界。

Formal preflight 必须实测：

```text
read p95 <=30 ms
observe p95 <=60 ms
120-step projected A12 CPU overhead <=12 seconds
```

未测量前不能把更低的 CPU 数字宣称为已实现结果。

---

# 63. 最终裁决

## 63.1 A12 是否值得继续

```text
YES — CONDITIONAL GO
```

理由不是 A12 已经被证明有效，而是：

1. 冻结失败轨迹中存在足够多的直接 repeated state-action no-progress 信号；
2. A10-v2/A11 的主要失败是这些信号到实际 read 之间的链路过长；
3. A12 可以将链路缩短为：

```text
first support
→ second support
→ immediate next read
```

4. 它不需要 route、anchor、phase、score 或 query parser；
5. 它的 offline recall、competent exposure 和 read eligibility 都可以在不调用模型的情况下被严格证伪。

## 63.2 当前是否允许 GPU live

```text
NO
```

必须先完成：

```text
implementation
independent segment freeze
strict actual-read replay
preflight
fresh live receipt
```

## 63.3 最强失败原因

A12 最可能失败的原因是：

> **它可以可靠地告诉模型“不要继续做这个没有可见进展的动作”，但无法告诉模型“哪个替代动作才真正推进任务”。**

因此，A12 即使通过全部 zero-generation gates，也只能获得一次有纪律的 prospective live test 资格，不能提前获得“会超过 A0/A1”的结论。
