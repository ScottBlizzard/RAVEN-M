# GPT_PRO_A10_V2_STANDALONE_MEMORY_DESIGN_2026-08-12.md

> **文档状态**：A10-v2 最终机制规范、实现合同与前瞻性实验预注册  
> **设计父版本**：`4548b932bc3b189507e1442e312c73c8f35dbdb8`  
> **设计日期**：2026-08-12  
> **机制名称**：证据成熟的义务—分支前沿记忆  
> **英文名称**：Evidence-Matured Obligation–Branch Frontier Memory  
> **缩写**：EM-OBF  
> **Mechanism ID**：`a10_v2_evidence_matured_obligation_branch_frontier_v2`  
> **Experiment ID**：`A10_V2_EMOBF_QWEN3VL32B_AW_HARD_S20260806_G3407_V1`  
> **CLI arm**：`a10_v2_emobf`  
> **结论边界**：本文只冻结机制、实现规则、测试门和实验协议，不宣称 A10-v2 已经达到 6/19，也不授权在 zero-generation preflight 通过之前启动 live generation。

---

## 1. 文档目的

本文正式废止 A10-v1 作为可启动 live generation 的候选协议，并定义一个新的 A10-v2。

A10-v2 不是对 A10-v1 失败报告的重新解释，也不允许把 A10-v1 的失败结果改写成通过。A10-v1 的以下文件必须原样保留：

```text
GPT_PRO_A10_STANDALONE_MEMORY_DESIGN_2026-08-12.md
protocols/A10_ECOBF_IMPLEMENTATION_BINDING_2026-08-12.md
evidence/a10/A10_OFFLINE_REPLAY_REPORT.json
implementation/src/raven_m/official_qwen_mobile/a10_obligation_branch_frontier.py
implementation/scripts/replay_a10_offline_traces.py
```

A10-v2 必须拥有：

```text
新的 mechanism ID
新的 experiment ID
新的实现文件
新的配置文件
新的 contract
新的测试文件
新的 replay 脚本
新的 replay 报告
新的 zero-generation preflight
新的 source freeze
新的 live receipt
新的完整 19 题 prospective suite
```

A10-v1 与 A10-v2 的 episode、aggregate、checkpoint、preflight、receipt 或结果不得拼接。

---

## 2. 审阅基线与可审计事实

本设计以仓库 commit：

```text
4548b932bc3b189507e1442e312c73c8f35dbdb8
```

为设计父版本。该版本在 A10-v1 正式实现与审计基础上，将证据 provenance 改为平台稳定的 canonical JSON 哈希，同时保留 A10-v1 replay 的失败状态；它并未把失败门改成通过。

A10-v1 implementation binding 明确规定：

- exact 和 threshold-qualified near visual match 均为合法匹配；
- 不得为通过历史轨迹而弱化 T2；
- 如果成功历史轨迹存在符合原公式的无增益 closed route，机制就应创建并可能读取 T2；
- replay 门失败必须阻止 live generation。

正式 replay 脚本确实：

- 物化真实 episode 和 RGB 截图；
- 校验 episode、截图和 suite metadata 哈希；
- 对每个 executed step 调用真实 A10-v1 `read()` 与 `observe_step()`；
- 不进行任何 generation；
- 将 A0、A1 Recipe、A6、A8-v2 Expense、A9 Retro 共 27 个 episode 纳入同一正式报告。

正式报告的可审计结论为：

| 项目 | 结果 |
|---|---:|
| Episode 数量 | 27 |
| 已验证文件 | 1,668 |
| 已验证字节 | 442,138,413 |
| Generation calls | 0 |
| A6 qualifying loops | 23 |
| A6 及时激活 | 22 |
| A6 激活率 | 95.65% |
| Replay status | `fail` |
| 失败门 1 | `a0_success_silence_gate_failed` |
| 失败门 2 | `a1_recipe_sentinel_or_trace_evidence_failed` |

这些结论直接保存在正式 JSON 末尾，文件哈希验证本身通过，但科学协议门失败。

项目交接同时说明：

- A10-v1 已完成两轮独立审查；
- `official_qwen_mobile` 全套 148/148 tests passed；
- 没有启动 live generation。

本文接受这些作为交接事实，但它们不替代 A10-v2 的新实现测试、新 replay、新 source freeze 和新审查。

---

## 3. A10-v1 失败与内部冲突的正式裁定

### 3.1 裁定一：A10-v1 的 T2/T3 与 A0 绝对静默门互相冲突

A10-v1 的 T2 允许一次满足以下条件的 closed route 直接形成可检索 trigger：

\[
\text{RETURNED}
\land
\text{route length}\le4
\land
\Delta C_{\text{anchor}}<0.15
\land
\text{phase/open mask unchanged}
\]

A10-v1 的 T3 又只要求：

- 七步内三次 frontier visit；
- 两个 resolved attempt；
- 没有 trusted durable escape；
- anchor gain 小于 0.15。

它不要求这些 resolved attempt 真正是失败，也允许由局部可见变化和正常页面工作流构成的 frontier visit 形成 collapse。仓库单元测试甚至明确验证了“resolved local changes 无需额外 bad gate 也能触发 T3”。

真实 A0 replay 结果是：

| A0 历史成功任务 | A10-v1 非空读取 |
|---|---:|
| ExpenseDeleteMultiple2 | 0 |
| RetroSavePlaylist | 2 |
| SimpleCalendarAddOneEvent | 1 |
| SportsTrackerTotalDurationForCategoryThisWeek | 0 |

Retro 的 v1 false-positive trigger 全部是 T2/T3，没有 repeated no-progress qualifying segment；三个 T2 分别绑定三个不同 frontier。Calendar 也没有 qualifying loop，其三个 T2 分别绑定三个不同 frontier，而唯一 T3 在非常早的普通设置流程中出现。

Calendar 的一次 T2 最终通过 near retrieval 得到：

\[
D_V=0.003746
\]

\[
Score=0.781799>0.68
\]

因此，只要同时遵循原 T2、near retrieval 与原 score，就必须读取；不能再要求同一轨迹绝对静默。

**正式裁定：**

```text
A10-v1 的 mechanism rules 与 §30.2 replay gate 不可同时满足。
A10-v1 formal preflight 必须失败。
A10-v1 不得启动 live generation。
```

这不是实现 bug，而是协议层面的不可满足条件。

### 3.2 裁定二：A10-v1 parser 与 Recipe gate 互相冲突

冻结 query 为：

```text
Delete the recipes from Broccoli app that use zucchini in the directions.
```

仓库冻结 query set 对该文本及其 SHA256 有明确记录。

A10-v1 只允许：

```text
quoted literal
colon-list literal
marker-list literal
numeric/date/time literal
temporal literal
```

该 query 不包含任何合法结构，因此实际 replay 中：

```text
anchor_count = 0
```

A0 Recipe 与 A1 Recipe 均进入 sentinel fallback；A1 Recipe 尽管最终 reward 为 1.0，仍然没有合法 anchor。

但 v1 replay gate 又要求：

```text
anchor_count >= 2
```

并要求存在相关 trace evidence。正式 replay 脚本也明确注释：不能临时发明 object 或弱化 gate，只能将其报告为失败。

**正式裁定：**

```text
A10-v1 的冻结 parser 与 A1 Recipe replay gate 不可同时满足。
A10-v1 formal preflight 必须失败。
```

---

## 4. A10-v2 的核心设计选择

### 4.1 一句话因果假设

> **单次页面往返只说明模型完成了一次导航，不足以说明策略空间正在收缩；只有当同一义务阶段、同一视觉决策 frontier 上出现至少两个相互独立的停滞证据——例如同一动作分支重复无变化、同一路线再次返回，或多个分支连续产生坏结果且没有任何可见生产性转移——记忆才成熟并进入 prompt。**

### 4.2 A10-v2 的最小检索对象

\[
\boxed{
\text{unresolved obligation group}
\land
\text{matching visual frontier}
\land
\text{matured stagnation evidence}
}
\]

其中 `matured stagnation evidence` 是 A10-v2 相对 v1 的核心变化。

单个 closed route：

\[
\text{one return}
\]

只会形成不可读取的 `ClosedRouteWatch`，永远不会直接形成 memory read。

### 4.3 A10-v2 对两项冲突的解决

#### 冲突一

A10-v2：

- 删除“单次 closed route 直接形成 T2”的规则；
- T2 必须有第二个同 route-key 停滞证据；
- T3 必须包含至少三个坏决策事件、至少两个不同坏分支、至少一个重复坏分支，并且坏事件窗口内不存在任何生产性可见转移；
- 单纯 visit、local visible change、一次 Settings 往返或一次时间编辑往返均不能形成 T3。

#### 冲突二

A10-v2 增加固定、确定性的 relative-clause constraint grammar，将 Recipe query 解析为：

```text
Constraint group:
  head/value: zucchini
  qualifier/field: directions
  polarity: REQUIRE
  predicate: USE
  group kind: FILTER_SET
```

同时明确排除：

```text
Broccoli
app
recipes
Delete
from
in
```

这些词不会成为 obligation anchor。

---

## 5. A10-v2 与 A10-v1 的逐项差异

| 项目 | A10-v1 | A10-v2 |
|---|---|---|
| Mechanism ID | `a10_evidence_calibrated_obligation_branch_frontier_v1` | `a10_v2_evidence_matured_obligation_branch_frontier_v2` |
| Experiment ID | `A10_ECOBF...V1` | `A10_V2_EMOBF...V1` |
| 单次 closed route | 直接产生 T2 | 只产生不可读取的 route watch |
| T2 成熟 | 一次返回 | 第二次相同 route-key 返回，或返回后同一 departure branch 再次失败 |
| T3 依据 | visit + 任意 resolved attempt | 至少 3 个坏事件、2 个坏分支、1 个重复坏分支、0 个生产性事件 |
| 普通 local visible change | 可参与 T3 | 明确视为 productive，阻止 T3 |
| Route return 对 branch bad confidence | 所有 return 都计入 | 只有已成熟为停滞的 return 才计入 |
| Route return 对 anchor confidence | 一次 return 即负证据 | 只有 T2 成熟后才写 `BAD_ROUTE_MATURED` |
| Parser | quote/list/numeric/temporal | 增加固定 constraint bundle grammar |
| Recipe query | 0 anchors | `zucchini` + `directions` |
| Constraint completion | 不存在 | `FILTER_SET` 永远保持 open，不因删除一个对象而虚假完成 |
| Near state match | \(D_V\le0.055\) | route matching 保留；prompt retrieval 收紧为 \(D_V\le0.040\) |
| Retrieval threshold | 0.68 | 0.72 |
| Candidate lifecycle | 创建后立即可检索 | `PROVISIONAL → MATURE → DELIVERED/DISMISSED/EXPIRED` |
| Phase switch 后 cooldown | v1 可重置 | 全局 cooldown 不重置 |
| A0 历史成功门 | 绝对 0 read，但与公式冲突 | 仍为绝对 0 read，新公式使其逻辑可满足 |
| Recipe replay gate | 模糊要求多个目标/约束 | 精确要求一个两成员 constraint bundle |
| Source-specific exceptions | 禁止 | 继续禁止 |
| Task/page whitelist | 禁止但未单独静态扫描 | 新增 AST、字符串和动态不变性扫描 |

---

## 6. 冻结身份与实验常量

```text
DESIGN_PARENT_COMMIT =
4548b932bc3b189507e1442e312c73c8f35dbdb8

MECHANISM_ID =
a10_v2_evidence_matured_obligation_branch_frontier_v2

EXPERIMENT_ID =
A10_V2_EMOBF_QWEN3VL32B_AW_HARD_S20260806_G3407_V1

CONFIG_SCHEMA =
a10_v2_emobf_arm_v1

OFFLINE_REPLAY_SCHEMA =
a10_v2_offline_replay_report_v1

PREFLIGHT_SCHEMA =
a10_v2_zero_generation_preflight_v1

LIVE_RECEIPT_SCHEMA =
a10_v2_live_server_receipt_v1

RESULT_SCHEMA =
a10_v2_emobf_result_v1
```

冻结 benchmark/model 常量：

```text
model_id =
Qwen/Qwen3-VL-32B-Instruct

model_revision =
0cfaf48183f594c314753d30a4c4974bc75f3ccb

official_system_prompt_sha256 =
9d060af15f62acb31b9fb197649ec001d4096491d7fb102de929316944b3e26d

task_seed = 20260806
generation_seed = 3407

temperature = 0.7
top_p = 0.8
top_k = 20
presence_penalty = 1.5
repetition_penalty = 1.0
max_tokens = 32768
backend = vLLM BF16
task_count = 19
```

这些常量与 A10-v1 contract 和配置中冻结的 A 类比较条件一致。

---

## 7. 允许输入与禁止输入

在 executed step \(s\)，A10-v2 只允许使用：

\[
q
\]

task query；

\[
I_s
\]

执行前模型可见 RGB；

\[
a_s
\]

已经由 policy 生成并实际执行的 canonical action；

\[
u_s
\]

policy 自己生成的 action summary；

\[
I_{s+1}
\]

执行后模型可见 RGB；

\[
s
\]

单调递增的 executed-action index。

### 7.1 允许字段白名单

`read(context)`：

```text
context["goal"]
context["before"]["pixels"]
```

`observe_step(...)`：

```text
source_step
action_summary
canonical_action
before["pixels"]
after["pixels"]
source_response_sha256       # audit-only
source_screenshot_sha256     # audit-only
```

哈希字段只保存于 audit，不参与：

```text
状态匹配
trigger
score
confidence
rendering
eviction utility
```

### 7.2 明确禁止

```text
evaluator reward
success flag
task ground truth
future screenshot
UI tree
accessibility nodes
activity
foreground package
package name
app database
hidden task state
task_name
episode_id
历史最终结果
A0/A1 reward
人工页面标签
人工任务白名单
```

A10-v2 不读取 controller 传入的 `transition` 字典，而是从允许的 before/after RGB 自行计算变化。

### 7.3 决策不变性

对任意相同的允许输入 \(X\) 和任意两个隐藏输入 \(H_1,H_2\)：

\[
R(M,X,H_1)=R(M,X,H_2)
\]

\[
U(M,X,H_1)=U(M,X,H_2)
\]

单元测试必须比较：

```text
read text
read audit
observe result
trigger IDs
scores
serialized decision state
```

并要求完全一致。

---

## 8. 状态 schema 与容量

### 8.1 顶层状态

| 字段 | 类型 | 上限 |
|---|---|---:|
| `mechanism_id` | `str` | 常量 |
| `experiment_id` | `str` | 常量 |
| `goal_sha256` | `str[64]` | 1 |
| `operation_class` | enum | 1 |
| `anchors` | `list[GoalAnchor]` | 8 |
| `obligation_groups` | `list[ObligationGroup]` | 8 |
| `phase_id` | `int` | native step bound |
| `frontiers` | ordered map | 16 |
| `attempt_receipts` | deque | 32 |
| `pending_routes` | list | 4 |
| `closed_route_watches` | list | 4 |
| `partial_escape_watches` | list | 2 |
| `trigger_candidates` | list | 8 |
| `delivered_signatures` | deque | 12 |
| `screen_trace` | deque | 17 |
| `read_events` | list | 5 |
| `phase_events` | deque | 8 |
| `counters` | fixed dict | 固定字段 |

### 8.2 冻结容量

```text
MAX_ANCHORS = 8
MAX_OBLIGATION_GROUPS = 8
MAX_EVENTS_PER_HEAD = 6

MAX_FRONTIERS = 16
MAX_VISUAL_EXEMPLARS_PER_FRONTIER = 3
MAX_BRANCHES_PER_FRONTIER = 5

MAX_ATTEMPT_RECEIPTS = 32
MAX_PENDING_ROUTES = 4
MAX_CLOSED_ROUTE_WATCHES = 4
MAX_PARTIAL_ESCAPE_WATCHES = 2

MAX_TRIGGER_CANDIDATES = 8
MAX_DELIVERED_SIGNATURES = 12
MAX_SCREEN_TRACE = 17

MAX_NONEMPTY_READS_PER_EPISODE = 5
MAX_NONEMPTY_READS_PER_PHASE = 2
GLOBAL_READ_COOLDOWN_ACTIONS = 4

MAX_RENDERED_CHARS = 420
MAX_RENDERED_UTF8_BYTES = 720
MAX_FROZEN_TOKENIZER_TOKENS_PER_READ = 192
MAX_FROZEN_TOKENIZER_TOKENS_PER_EPISODE = 960

MAX_SERIALIZED_AUDIT_BYTES = 131072
```

---

## 9. Query 与 constraint parser

## 9.1 规范化

输入 query 执行：

```text
Unicode NFKC
保留原始字符串和原始 offset
casefold 版本只用于匹配
连续空白折叠为一个空格
anchor normalization 将非字母数字序列折叠为空格
```

不得调用：

```text
LLM
embedding model
NER model
parser model
OCR
word vector
外部词典服务
```

## 9.2 旧结构化抽取规则

A10-v2 保留以下 v1 规则：

1. `QUOTED`
2. `COLON_LIST`
3. `MARKER_LIST`
4. `NUMERIC_OR_TIME`
5. `TEMPORAL`

### 9.2.1 Quoted

支持：

```text
"…"
'…'
“...”
‘...’
`...`
```

长度：

```text
2–64 Unicode code points
```

### 9.2.2 Colon list

仅处理 query 最后一个冒号后的内容。

按：

```text
comma
semicolon
newline
```

分割。

只有有效项数量至少为 2 时，整个结构才合法。

### 9.2.3 Marker list

固定 marker：

```text
following
these
named
called
titled
containing
```

从 marker 后开始，到当前句号结束。

只有分割后至少两个有效项时才激活。

### 9.2.4 Numeric/time

固定 regex 支持：

```text
integer
decimal
currency
date
clock time
duration
distance
amount
coordinate
numeric interval
```

### 9.2.5 Temporal

固定词表：

```text
today
tomorrow
yesterday
this week
last week
next week
Monday ... Sunday
January ... December
```

---

## 9.3 Constraint grammar

### 9.3.1 基础 token

Python regex 定义：

```python
WORD = r"[^\W_](?:[\w'’./+\-]*[^\W_])?"
VALUE = rf"{WORD}(?:\s+{WORD}){{0,5}}"
```

匹配 flags：

```python
re.IGNORECASE | re.UNICODE | re.VERBOSE
```

### 9.3.2 固定 predicate lexicon

```python
CONTENT_PREDICATES = (
    "use", "uses", "using",
    "contain", "contains", "containing",
    "include", "includes", "including",
    "mention", "mentions", "mentioning",
    "have", "has", "having",
)
```

```python
COMPARISON_PREDICATES = (
    "take", "takes", "taking",
    "cost", "costs", "costing",
    "last", "lasts", "lasting",
)
```

```python
NAME_PREDICATES = (
    "named", "called", "titled",
)
```

### 9.3.3 固定 field lexicon

按最长字符串优先匹配：

```python
FIELD_ALIASES = {
    "file name": "file name",
    "filename": "file name",

    "directions": "directions",
    "direction": "directions",

    "ingredients": "ingredients",
    "ingredient": "ingredients",

    "description": "description",

    "notes": "notes",
    "note": "notes",

    "content": "content",
    "body": "body",
    "text": "text",

    "title": "title",
    "name": "name",

    "category": "category",

    "date": "date",
    "time": "time",
    "duration": "duration",

    "distance": "distance",
    "amount": "amount",
    "price": "price",

    "tags": "tags",
    "tag": "tags",

    "labels": "labels",
    "label": "labels",

    "prepare": "preparation time",
    "complete": "completion time",
    "finish": "completion time",
}
```

`app` 和 `application` 明确不属于 field lexicon。

### 9.3.4 App locator exclusion

先标记但不抽取以下 span：

```python
APP_LOCATOR_RE = re.compile(
    r"""
    \b(?:from|in|on|using|via|into|to)\s+
    (?:the\s+)?
    (?P<app>
        [A-Za-z0-9][A-Za-z0-9'’._-]*
        (?:\s+[A-Za-z0-9][A-Za-z0-9'’._-]*){0,4}
    )
    \s+
    (?:recipe\s+|maps\s+)?
    (?:app|application)\b
    """,
    re.IGNORECASE | re.UNICODE | re.VERBOSE,
)
```

任何 constraint value 与 app-locator span 重叠时，候选必须被拒绝。

### 9.3.5 Relative field constraint

```python
REL_FIELD_RE = re.compile(
    rf"""
    \b(?P<rel>that|which)\s+
    (?P<neg>
        (?:(?:do|does)\s+not|
           don['’]t|
           doesn['’]t)\s+
    )?
    (?P<predicate>
        use|uses|using|
        contain|contains|containing|
        include|includes|including|
        mention|mentions|mentioning|
        have|has|having
    )
    \s+
    (?P<value>{VALUE})
    \s+
    (?P<prep>in|within|from|on)
    \s+(?:the\s+)?
    (?P<field>
        file\s+name|filename|
        directions?|ingredients?|
        description|notes?|content|body|text|
        title|name|category|
        date|time|duration|distance|amount|price|
        tags?|labels?
    )
    \b
    """,
    re.IGNORECASE | re.UNICODE | re.VERBOSE,
)
```

对目标 Recipe query：

```text
that use zucchini in the directions
```

必须得到：

```text
predicate = use
value = zucchini
field = directions
polarity = REQUIRE
```

### 9.3.6 Relative bare constraint

先运行 `REL_FIELD_RE`，标记其 span。之后只在未重叠区域运行：

```python
REL_BARE_RE = re.compile(
    rf"""
    \b(?P<rel>that|which)\s+
    (?P<neg>
        (?:(?:do|does)\s+not|
           don['’]t|
           doesn['’]t)\s+
    )?
    (?P<predicate>
        use|uses|using|
        contain|contains|containing|
        include|includes|including|
        mention|mentions|mentioning|
        have|has|having
    )
    \s+
    (?P<value>{VALUE})
    (?=
        \s*(?:[,;.!?]|$|\band\b|\bor\b|\bthen\b)
    )
    """,
    re.IGNORECASE | re.UNICODE | re.VERBOSE,
)
```

Bare constraint 只创建 head/value anchor，不创建 qualifier。

### 9.3.7 With/without field constraint

```python
WITH_FIELD_RE = re.compile(
    rf"""
    \b(?P<polarity>with|without)\s+
    (?P<value>{VALUE})\s+
    (?P<prep>in|within)\s+(?:the\s+)?
    (?P<field>
        file\s+name|filename|
        directions?|ingredients?|
        description|notes?|content|body|text|
        title|name|category|
        date|time|duration|distance|amount|price|
        tags?|labels?
    )
    \b
    """,
    re.IGNORECASE | re.UNICODE | re.VERBOSE,
)
```

`with` 映射为：

```text
polarity = REQUIRE
```

`without` 映射为：

```text
polarity = EXCLUDE
```

### 9.3.8 Numeric comparison constraint

```python
REL_NUMERIC_RE = re.compile(
    r"""
    \b(?:that|which)\s+
    (?:must\s+)?
    (?P<predicate>
        take|takes|taking|
        cost|costs|costing|
        last|lasts|lasting
    )
    \s+
    (?P<value>
        \d+(?:\.\d+)?\s*
        (?:
            ms|
            seconds?|secs?|
            minutes?|mins?|
            hours?|hrs?|
            days?|
            dollars?|usd|
            meters?|metres?|
            km|kilometers?|kilometres?
        )
    )
    (?:\s+to\s+
        (?P<field>prepare|complete|finish)
    )?
    """,
    re.IGNORECASE | re.UNICODE | re.VERBOSE,
)
```

例如：

```text
that take 2 hrs to prepare
```

创建：

```text
head = 2 hrs
qualifier = preparation time
group kind = FILTER_SET
```

### 9.3.9 Relative name constraint

```python
REL_NAME_RE = re.compile(
    rf"""
    \b(?:that|which)\s+
    (?:is|are)\s+
    (?P<predicate>named|called|titled)\s+
    (?P<value>{VALUE})
    (?=\s*(?:[,;.!?]|$|\band\b|\bor\b|\bthen\b))
    """,
    re.IGNORECASE | re.UNICODE | re.VERBOSE,
)
```

---

## 9.4 Constraint value 接受条件

候选 value 必须同时满足：

```text
2 <= Unicode 字符数 <= 48
1 <= lexical token 数 <= 6
不与 app locator span 重叠
不以介词或限定词开头
不以介词结尾
至少含一个非 stopword、非 generic noun token
不含句子边界符
```

固定 stopword：

```python
STOPWORDS = {
    "a", "an", "the",
    "of", "to", "from", "in", "on", "at", "for",
    "with", "without",
    "that", "which",
    "and", "or",
    "app", "application",
    "it", "them",
}
```

固定 generic noun：

```python
GENERIC_NOUNS = {
    "item", "items",
    "entry", "entries",
    "record", "records",
    "recipe", "recipes",
    "expense", "expenses",
    "note", "notes",
    "file", "files",
    "song", "songs",
    "activity", "activities",
    "event", "events",
    "task", "tasks",
    "data",
    "thing", "things",
    "value", "values",
}
```

固定 command-verb rejection：

```python
COMMAND_VERBS = {
    "delete", "remove", "erase",
    "add", "create", "save",
    "open", "launch", "navigate",
    "send", "share",
    "find", "calculate",
}
```

若 candidate 全部由以上集合组成，拒绝。

---

## 9.5 Anchor 与 constraint group

### 9.5.1 `GoalAnchor`

| 字段 | 类型 | 含义 |
|---|---|---|
| `anchor_id` | `str<=24` | 稳定 ID |
| `literal` | `str<=64` | query 原始片段 |
| `normalized` | `str<=64` | 匹配形式 |
| `source_kind` | enum | 抽取来源 |
| `role` | `HEAD` / `QUALIFIER` | 是否是义务主体 |
| `group_id` | `str<=24` | 所属 group |
| `specificity_weight` | int | 排序/检索权重 |
| `confidence` | float/None | 仅 HEAD 使用 |
| `status` | enum | 仅 HEAD 动态更新 |
| `persistent_open` | bool | 是否为开放集合约束 |
| `evidence_events` | list | 最多 6 |
| `last_evidence_step` | int/None | 最近证据 |

### 9.5.2 `ObligationGroup`

| 字段 | 类型 |
|---|---|
| `group_id` | str |
| `kind` | enum |
| `head_anchor_id` | str |
| `qualifier_anchor_ids` | list，最多 2 |
| `predicate_class` | enum |
| `predicate_literal` | str |
| `polarity` | `REQUIRE` / `EXCLUDE` |
| `render_label` | str<=64 |
| `persistent_open` | bool |
| `specificity_weight` | int |
| `status` | enum |

Group kind：

```text
ENUM_ITEM
SCALAR_VALUE
FILTER_SET
QUALIFIED_SCALAR
```

Recipe constraint：

```text
kind = FILTER_SET
persistent_open = true
render_label = zucchini in directions
```

`FILTER_SET` 不会因为一次删除、一次 visible change 或一次 durable departure 被标为已完成。其 group 始终保留在 open mask 中。

这是因为：

```text
“已处理一个符合约束的对象”
```

不等于：

```text
“所有符合约束的对象均已处理”
```

允许输入无法可靠证明后者。

---

## 9.6 优先级、去重与容量

抽取单位不是单个 anchor，而是 `ExtractionUnit`。

| Unit | Anchor 成本 | Priority |
|---|---:|---:|
| Quoted anchor | 1 | 6 |
| Colon/marker-list item | 1 | 5 |
| Constraint bundle | 1 或 2 | 4 |
| Numeric/time | 1 | 3 |
| Temporal | 1 | 2 |

Constraint bundle 的：

```text
head
qualifier
```

必须原子插入。

若 head 已与已有 anchor 去重，只计算新增 qualifier 成本。

排序：

```text
priority descending
source_offset ascending
unit_sha256 lexicographic
```

逐 unit 插入，直到 `MAX_ANCHORS=8`。

如果一个完整 constraint bundle 无法在剩余容量中原子放入，则跳过整个 bundle；不得只留下 qualifier。

全局按 normalized literal 去重。

同一 literal 同时被 numeric parser 和 constraint parser 抽取时：

- 保留一个 anchor；
- 将其链接到 constraint group；
- source kinds 以列表形式保留；
- 不重复占用容量。

---

## 9.7 Recipe query 的冻结预期

对：

```text
Delete the recipes from Broccoli app that use zucchini in the directions.
```

必须精确得到：

```json
{
  "anchor_count": 2,
  "group_count": 1,
  "anchors": [
    {
      "literal": "zucchini",
      "normalized": "zucchini",
      "source_kind": "CONSTRAINT_VALUE",
      "role": "HEAD",
      "persistent_open": true
    },
    {
      "literal": "directions",
      "normalized": "directions",
      "source_kind": "CONSTRAINT_FIELD",
      "role": "QUALIFIER",
      "persistent_open": false
    }
  ],
  "group": {
    "kind": "FILTER_SET",
    "predicate_class": "CONTENT",
    "predicate_literal": "use",
    "polarity": "REQUIRE",
    "render_label": "zucchini in directions",
    "persistent_open": true
  }
}
```

必须断言以下 normalized literal 不在 anchors 中：

```text
broccoli
app
recipes
delete
from
in
```

---

## 9.8 Parser 正例

| Query 片段 | 预期 head | 预期 qualifier |
|---|---|---|
| `that use zucchini in the directions` | `zucchini` | `directions` |
| `which contain peanuts in the ingredients` | `peanuts` | `ingredients` |
| `that include alpha beta in the body` | `alpha beta` | `body` |
| `with urgent in the title` | `urgent` | `title` |
| `without nuts in the ingredients` | `nuts` | `ingredients` |
| `that mention 2024-Q4` | `2024-Q4` | none |
| `that take 2 hrs to prepare` | `2 hrs` | `preparation time` |
| `which is titled Quarterly Plan` | `Quarterly Plan` | none |

## 9.9 Parser 负例

| Query 片段 | 结果 |
|---|---|
| `Open Broccoli app.` | 无 constraint |
| `Delete the recipes from Broccoli app.` | 无 constraint |
| `Open the Settings page and return.` | 无 constraint |
| `Create a recipe in the app.` | 无 constraint |
| `that use the app` | value 全为 generic，拒绝 |
| `that use in the directions` | 无合法 value，拒绝 |
| `that use delete in the directions` | command verb value，拒绝 |
| `from Broccoli app` | app locator，只标记排除 |
| `the recipes` | generic noun phrase，拒绝 |

## 9.10 对抗样例

以下必须具有固定结果：

```text
Delete app that uses Broccoli in the app.
```

结果：

```text
0 constraint groups
```

原因：

```text
field “app” 不在 field lexicon
```

```text
Delete items that use red green blue yellow orange purple black in the title.
```

结果：

```text
0 constraint groups
```

原因：

```text
value 超过 6 tokens
```

```text
Delete items that use zucchini in the application.
```

结果：

```text
0 constraint groups
```

原因：

```text
application 不是合法 field
```

```text
Delete items that use zucchini in the directions; then open Cedar app.
```

结果：

```text
一个 zucchini/directions constraint
Cedar 不成为 anchor
```

---

## 10. Target-anchor 与 target-group 匹配

## 10.1 匹配输入

仅匹配：

```text
policy action summary
canonical type_text.text
```

不匹配 screenshot OCR，不匹配 UI tree。

## 10.2 Tokenization

对 summary 和 typed text：

```text
NFKC
casefold
非字母数字折叠为空格
按空格切 token
```

Anchor phrase 只有在完整连续 token subsequence 出现时匹配。

例如：

```text
anchor = public transit
```

匹配：

```text
delete public transit
```

不匹配：

```text
public transportation
```

不得使用 stemming、embedding 或同义词扩展。

## 10.3 Anchor mask

```python
target_anchor_mask: int
```

每个 anchor 对应一 bit。

HEAD 和 QUALIFIER 均可有 anchor bit。

## 10.4 Group mask

```python
target_group_mask: int
```

只有以下情况设置 group bit：

1. HEAD literal 完整匹配；
2. canonical `type_text` 完整包含 HEAD literal。

仅匹配 qualifier 不得设置 group bit。

例如：

```text
summary = inspect the directions
```

得到：

```text
qualifier anchor bit = 1
group bit = 0
```

```text
summary = inspect directions for zucchini
```

得到：

```text
head bit = 1
qualifier bit = 1
group bit = 1
```

## 10.5 Proximity closure

如果同一 group 的 HEAD 与 QUALIFIER：

- 均在 summary 中出现；
- 两者 token 起始位置差不超过 12 tokens；

则设置两个 anchor bit 和 group bit。

不得仅因 predicate verb 出现而推断未出现的 value。

---

## 11. 视觉状态描述符

A10-v2 复用 v1 已严格实现和测试的 controller-only RGB descriptor。v1 测试已经覆盖 exact、near、crop、narrow width、非法 dtype、RGBA 和 non-contiguous 输入。

## 11.1 RGB 校验

合法输入：

```text
ndim == 3
H >= 25
W >= 8
C >= 3
integer dtype
all values in [0,255]
```

使用前 3 个通道并转为 contiguous。

非法输入抛：

```text
A10V2VisibleInputError
```

## 11.2 Crop

裁掉顶部与底部各 4%：

\[
I^{crop}
=
I[
\lfloor0.04H\rfloor:
\lceil0.96H\rceil
]
\]

## 11.3 Exact hash

\[
h^{exact}
=
SHA256(
shape
\Vert
dtype
\Vert
RGB\ bytes
)
\]

## 11.4 9×16 luma descriptor

每个 cell 的 RGB 整数均值：

\[
Y=\frac{77R+150G+29B}{256}
\]

量化：

\[
q_{r,c}
=
\left\lfloor
\frac{Y_{r,c}}{16}
\right\rfloor
\in\{0,\ldots,15\}
\]

## 11.5 Edge bits

水平：

\[
e^H_{r,c}
=
\mathbf 1[q_{r,c+1}>q_{r,c}]
\]

垂直：

\[
e^V_{r,c}
=
\mathbf 1[q_{r+1,c}>q_{r,c}]
\]

共 263 bits。

## 11.6 距离

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
D_V
=
0.7D_L+0.3D_E
\]

## 11.7 三种视觉阈值

### Route/state match

用于 route return 解析：

\[
D_L\le0.06
\]

\[
D_E\le0.12
\]

\[
D_V\le0.055
\]

或 exact hash 相同。

### Frontier merge

\[
D_V\le0.035
\]

同时要求：

```text
phase_id 相同
open_group_mask 相同
```

### Prompt retrieval near match

Exact 始终合法。

Near retrieval 必须同时满足：

\[
D_L\le0.05
\]

\[
D_E\le0.10
\]

\[
D_V\le0.040
\]

A10-v2 没有取消 near retrieval，而是将 prompt exposure 的 near 阈值从 0.055 收紧至 0.040。

---

## 12. Canonical action、intent 与 branch

## 12.1 Geometric action family

### Tap

\[
x_{bin}=\min(11,\lfloor12x\rfloor)
\]

\[
y_{bin}=\min(23,\lfloor24y\rfloor)
\]

```text
("tap", x_bin, y_bin)
```

### Long press

在 tap family 基础上增加：

```text
short  : duration < 700 ms
medium : 700 <= duration <= 1500 ms
long   : duration > 1500 ms
```

### Swipe

方向取 dominant axis。

长度：

\[
l=\sqrt{dx^2+dy^2}
\]

```text
short  : l < 0.25
medium : 0.25 <= l < 0.55
long   : l >= 0.55
```

起点为 \(3\times4\) 网格。

### Type text

```text
(
  "type_text",
  SHA256(normalized_text),
  length_bucket,
  clear_text
)
```

长度：

```text
1–8
9–32
33–96
97+
```

### 其他

```text
press_back
press_home
press_enter
press_recents
wait + duration_bucket
answer + text_sha256
```

## 12.2 Intent class

按以下顺序取第一个匹配类别。

### `COMMIT`

```text
delete remove erase
add create save
send share submit confirm
merge copy mark
```

### `CONFIGURE`

```text
set change edit adjust
toggle enable disable
pick configure
```

### `INPUT_OR_SEARCH`

```text
type enter fill search
```

### `OPEN_OR_SELECT`

```text
open launch navigate
select choose
```

### `INSPECT`

```text
inspect check view read
find calculate
```

### `RECOVER`

```text
back return close cancel
```

然后依 canonical action fallback：

```text
SCROLL
WAIT
ANSWER
OTHER
```

`CONFIGURE` 是通用操作类别，不包含任何 app 名、任务名或页面名。

## 12.3 Branch key

\[
BKey
=
SHA256(
canonical\_family,
intent\_class,
target\_anchor\_mask,
target\_group\_mask
)
\]

同坐标但不同 target group 的动作是不同 branch。

---

## 13. 像素转移与 route

## 13.1 Pixel change

\[
P_s
=
\frac{1}{HW}
\sum_{i,j}
\mathbf 1
\left[
\max_c|I_s(i,j,c)-I_{s+1}(i,j,c)|>5
\right]
\]

## 13.2 Immediate outcome

| 条件 | Outcome |
|---|---|
| RGB 完全一致 | `NO_PROGRESS_EXACT` |
| \(P_s\le0.001\) | `NO_PROGRESS_NEGLIGIBLE` |
| \(P_s>0.001\) 且 route/state match | `LOCAL_VISIBLE_CHANGE` |
| 不 match | `DEPARTURE_PENDING` |

`LOCAL_VISIBLE_CHANGE` 不是任务完成证据，但在 A10-v2 中是阻止弱 T3 的生产性可见事件。

## 13.3 Pending route

每个 `DEPARTURE_PENDING` 创建 pending route：

```text
source_step
source_frontier_id
source_branch_id
source_branch_core
source_descriptor
source_phase
source_open_group_mask
source_target_group_mask
source_head_confidences
route_work_event_count
target_context_changed
```

## 13.4 Route length

若 source action 为 \(s_0\)，在 observe step \(s_r\) 返回：

\[
route\_length=s_r-s_0+1
\]

## 13.5 Route outcome

| 条件 | Outcome |
|---|---|
| 1–4 actions 内返回 source match | `RETURNED` |
| 第 4 action 后仍未返回 | `DURABLE_DEPARTURE` |
| 第 5–8 action 返回 | `LATE_RETURN` |
| 超过 8 actions | route 关闭，不再修订 |

`LATE_RETURN` 必须修订此前同一 receipt 的 durable departure，不得双计数。A10-v1 已对此建立相应实现和测试，A10-v2 可复用该修订逻辑。

## 13.6 Route work event

route 内部某个 action 只有同时满足以下条件才计为 `route_work_event`：

```text
intent ∈ {COMMIT, CONFIGURE, INPUT_OR_SEARCH}
```

且：

```text
outcome ∈ {LOCAL_VISIBLE_CHANGE, DEPARTURE_PENDING}
```

`NO_PROGRESS_*` 永不计为 work event。

非空 `type_text` 只有在：

```text
P > 0.001
```

或 destination 不 match source 时计入。

---

## 14. ClosedRouteWatch：正常导航与失败路线的核心区分

## 14.1 Watch 创建条件

一个 `RETURNED` route 只有同时满足以下条件才创建 watch：

```text
route_length <= 4
source phase == return phase
source open_group_mask == return open_group_mask
target_context_changed == false
route_head_gain < 0.15
```

第一次满足时只创建：

```text
stage = PROVISIONAL_POST_RETURN
return_count = 1
witness_count = 1
```

此时：

```text
不得创建 T2
不得进入 trigger_candidates
不得形成 memory read
```

## 14.2 Route key

\[
RouteKey
=
SHA256(
source\_frontier\_id,
source\_phase,
source\_open\_group\_mask,
departure\_branch\_core
)
\]

其中：

```text
departure_branch_core =
(canonical_family, intent_class,
 target_anchor_mask, target_group_mask)
```

不同 frontier、不同 departure branch 或不同目标上下文的路线不能互相提供 T2 witness。

## 14.3 Watch 时间窗

```text
post_return_deadline = returned_step + 3
recurrence_deadline = returned_step + 12
```

### `PROVISIONAL_POST_RETURN`

持续至三个后续 executed actions 均已观察，或提前被成熟/驳回。

### `DORMANT_SINGLE_RETURN`

如果三个后续 actions 内既没有生产性证据，也没有第二个停滞 witness：

```text
stage = DORMANT_SINGLE_RETURN
```

它仍然不可读取，只等待同 route-key 第二次返回。

超过 `recurrence_deadline`：

```text
stage = EXPIRED
```

## 14.4 正常工作流驳回条件

Watch 在以下任一条件成立时立即设为：

```text
DISMISSED_PRODUCTIVE_WORKFLOW
```

1. phase 或 open group mask 变化；
2. 任一 open HEAD confidence 增益：

\[
\Delta C\ge0.10
\]

3. 返回后从 source frontier 采用一个在该 frontier 的 return step 之前未出现过的 branch，并且该 branch 产生：
   - `LOCAL_VISIBLE_CHANGE`；或
   - `DEPARTURE_PENDING`，随后在 4 actions 内没有返回；
4. route 自身 `route_work_event_count>=1`，且返回后的第一个 source-frontier branch：
   - 与 departure branch 不同；
   - 结果不是 `NO_PROGRESS_*`；
5. target group context 改变。

被驳回的 watch：

```text
不能恢复
不能参与 T2
不能作为 branch bad-return evidence
```

## 14.5 第二个停滞 witness

Watch 只有通过以下两种方式之一才能成熟。

### W2-A：同 route-key 第二次返回

在 recurrence deadline 内：

```text
第二个 RETURNED route
RouteKey 完全相同
route_head_gain < 0.15
phase/open mask unchanged
target_context_changed == false
```

则：

```text
return_count = 2
witness_count = 2
stage = MATURE_STAGNATION
```

### W2-B：返回后同 departure branch 再次失败

在 post-return deadline 内，当前 before screen match 原 source frontier，并且模型再次执行同一 departure branch core。

若结果为：

```text
NO_PROGRESS_EXACT
NO_PROGRESS_NEGLIGIBLE
```

则：

```text
witness_count = 2
stage = MATURE_STAGNATION
```

若它再次离开页面：

- 暂不成熟；
- 等待其 route resolution；
- 若再次 RETURNED，则按 W2-A 成熟；
- 若 durable departure，则 watch 被驳回为 productive escape。

## 14.6 单次 route 不可能触发 T2 的证明

设一个 episode 只有一次符合 watch 创建条件的 closed route，且之后不存在：

```text
同 RouteKey 的第二次 RETURNED
同 departure branch 的 no-progress retry
```

则：

\[
witness\_count=1
\]

而 T2 要求：

\[
witness\_count\ge2
\]

因此：

\[
\text{single closed route}
\not\Rightarrow
T2
\]

这一性质由 hard condition 保证，不依赖 score。

---

## 15. Anchor evidence 与 confidence

## 15.1 Evidence event

只给 HEAD 写动态 evidence。QUALIFIER 不独立获得完成置信度。

正证据：

| Event | 权重 |
|---|---:|
| `ACTION_MENTION` | +0.20 |
| `TYPE_EXACT` | +0.25 |
| `COMMIT_INTENT` | +0.20 |
| `MATERIAL_VISIBLE_CHANGE` | +0.10 |
| `DURABLE_ROUTE_DEPARTURE` | +0.15 |
| `INDEPENDENT_SECOND_SUPPORT` | +0.15 |

负证据：

| Event | 权重 |
|---|---:|
| `NO_PROGRESS_COMMIT` | -0.20 |
| `BAD_ROUTE_MATURED` | -0.25 |
| `REVERSAL_OR_FAILURE_PROSE` | -0.45 |
| `LATER_REOPEN_ATTEMPT` | -0.30 |

A10-v2 删除“一次普通 route return 就写负 anchor evidence”的规则。

只有 ClosedRouteWatch 成熟为 T2 时，才给该 route 明确触及的 HEAD 写：

```text
BAD_ROUTE_MATURED
```

## 15.2 去重

同一：

```text
(anchor_id, source_step, event_kind)
```

只写一次。

`INDEPENDENT_SECOND_SUPPORT` 只在第二个不同 source step 出现正支持时自动写一次，不允许由自身递归生成。

## 15.3 衰减

`DURABLE_ROUTE_DEPARTURE` 和 `INDEPENDENT_SECOND_SUPPORT`：

\[
\lambda=0.995
\]

其他正证据：

\[
\lambda=0.97
\]

负证据：

\[
\lambda=0.99
\]

当前 step \(s\)：

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

## 15.4 Closer status

对非 persistent-open HEAD：

| Confidence | Status |
|---|---|
| \(C<0.35\) | `OPEN` |
| \(0.35\le C<0.60\) | `TOUCHED` |
| \(0.60\le C<0.80\) | `PROVISIONAL` |
| \(C\ge0.80\) 且 hard support 通过 | `LOCALLY_SUPPORTED` |
| 支持后出现强负证据 | `REOPENED` |

Hard support：

1. 至少一个 `ACTION_MENTION` 或 `TYPE_EXACT`；
2. 至少一个 `COMMIT_INTENT`；
3. 以下至少一个：
   - `DURABLE_ROUTE_DEPARTURE`；
   - 两个不同 source step 的 `MATERIAL_VISIBLE_CHANGE`/独立支持。

## 15.5 Persistent filter status

`FILTER_SET` HEAD：

```text
OPEN_FILTER
TOUCHED_FILTER
PROVISIONAL_FILTER
```

其 confidence 可以更新，但永远不能进入：

```text
LOCALLY_SUPPORTED
```

也不会离开 open group mask。

---

## 16. Branch evidence 与置信度

A10-v2 区分：

```text
raw_return_count
bad_return_count
```

单次正常 return 只增加 `raw_return_count`。

只有 ClosedRouteWatch 成熟为停滞后，相关 return 才增加 `bad_return_count`。

时间衰减：

\[
d(e,s)
=
0.85^{
\left\lfloor
\frac{s-e.step}{8}
\right\rfloor
}
\]

\[
N
=
\sum_{\text{NO\_PROGRESS}}d
\]

\[
R
=
\sum_{\text{MATURED\_BAD\_RETURN}}1.25d
+
\sum_{\text{MATURED\_LATE\_RETURN}}0.75d
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

\[
S_e=1-e^{-0.7A}
\]

\[
C_{\text{bad}}
=
\frac{1+N+R}
{2+A}
S_e
\]

\[
C_{\text{escape}}
=
\frac{1+D}
{2+A}
S_e
\]

`trusted_bad_branch`：

\[
C_{\text{bad}}\ge0.55
\]

且：

```text
至少两个不同 source_step 的 bad witness
```

---

## 17. 生产性事件、坏事件与中性事件

对一个 frontier 的 resolved receipt：

### `BAD_EVENT`

满足任一：

1. `NO_PROGRESS_EXACT`
2. `NO_PROGRESS_NEGLIGIBLE`
3. 对应 route watch 已成熟为 `MATURE_STAGNATION`

并且：

```text
head gain < 0.10
phase/open group mask 未变化
```

### `PRODUCTIVE_EVENT`

满足任一：

1. `LOCAL_VISIBLE_CHANGE`
2. `DURABLE_DEPARTURE`
3. HEAD gain \(\ge0.10\)
4. phase switch
5. route watch 被标记为 `DISMISSED_PRODUCTIVE_WORKFLOW`

### `NEUTRAL_EVENT`

包括：

```text
未解析 departure
单次 provisional return
dormant single return
未达到 0.10 的其他非坏转移
```

中性事件不能单独触发 T3。

---

## 18. Phase switch

## 18.1 Open group mask

只有 obligation group 有 group bit。

非 persistent group 在 HEAD 为：

```text
LOCALLY_SUPPORTED
```

时从 open mask 中移除。

Persistent `FILTER_SET` 始终保留。

## 18.2 Phase switch 条件

以下任一成立：

1. open group mask 改变；
2. 没有任何 obligation group，且一次 `COMMIT` action：
   - 产生 `LOCAL_VISIBLE_CHANGE`；
   - 随后 4 actions 内没有返回 source frontier。

## 18.3 Phase switch 后

```text
phase_id += 1
current_phase_read_count = 0
旧 phase candidate 失效
旧 phase provisional watch 失效
旧 frontier 保留审计但不可与新 phase 合并
```

全局：

```text
last_nonempty_read_step
```

不得重置。

因此，即使刚切换 phase，距离上次非空读取仍必须至少 4 个 executed actions。

---

## 19. Candidate 生命周期

```text
PROVISIONAL
MATURE
DELIVERED
DISMISSED
EXPIRED
```

只有 `MATURE` 可以进入 retrieval。

每个 candidate 记录：

```text
created_step
matured_step
expires_step
witness_steps
witness_count
bad_event_count
productive_event_count
frontier_id
phase_id
open_group_mask
branch_ids
expected_descriptor
baseline_head_confidences
evidence_signature
```

## 19.1 Expiry

| Trigger | `expires_step` |
|---|---|
| T0 | `matured_step + 6` |
| T1 | `matured_step + 6` |
| T2 | `matured_step + 6` |
| T3 | `matured_step + 5` |
| T4 | `matured_step + 6` |

## 19.2 Evidence signature

\[
Signature
=
SHA256(
mechanism\_id,
trigger\_kind,
phase,
open\_group\_mask,
frontier\_id,
sorted(branch\_ids),
sorted(witness\_steps),
sorted(group\_ids)
)
\]

同 signature 只读一次。

同 frontier、同 kind 在一次 read 后，至少需要两个新的 witness source steps，才能形成新的 signature。

---

## 20. 全部 trigger 的精确条件

# 20.1 T0：`PARTIAL_OBLIGATION_ESCAPE`

只对非 persistent、可关闭的枚举义务使用。

条件：

1. 至少 2 个可关闭 obligation groups；
2. 一个 `COMMIT` branch 使某 group HEAD confidence 增益：

\[
\Delta C\ge0.20
\]

3. 至少另一个 group 仍 open；
4. 此后连续两个已观察 destination screen 均不 match commit source frontier；
5. 其他 open group 最大 HEAD gain：

\[
<0.10
\]

6. 没有返回原工作 frontier；
7. 没有相同 signature。

成熟 witness：

```text
commit support
first off-frontier observation
second off-frontier observation
```

Recipe 的 `FILTER_SET` 不参与 T0 的“已处理一个、仍有另一个”逻辑。

---

# 20.2 T1：`BAD_BRANCH_REPEAT`

条件：

1. 同 phase；
2. 同 open group mask；
3. 同 frontier；
4. 同 branch key；
5. 至少两个不同 source steps；
6. 两次都为 `NO_PROGRESS_*`；
7. 两次之间不存在 `PRODUCTIVE_EVENT`；
8. 从第一次 bad attempt 起最大 HEAD gain：

\[
<0.10
\]

9. retry exemption 不成立。

等价 decayed 门：

\[
N\ge1.80
\]

## 20.2.1 Retry exemption

一次 branch/phase 最多使用一次 retry exemption。

以下任一成立：

1. action 为 `wait`，且该 branch raw no-progress count \(\le2\)；
2. 当前 `type_text.clear_text=True`；
3. 最近两步内存在明确 clear action；
4. 前一次同 branch 的 source exact hash 不同，只是 near-match；
5. 前一次 outcome 仍为 `DEPARTURE_PENDING`；
6. target group mask 改变；
7. 前一次为 `LOCAL_VISIBLE_CHANGE` 且 HEAD gain \(\ge0.10\)。

Exemption 被使用后：

```text
branch.retry_exemption_used = true
```

后续相同理由不能无限豁免。

---

# 20.3 T2：`MATURED_CLOSED_ROUTE_STAGNATION`

T2 不再叫 `CLOSED_ROUTE_WITHOUT_ADVANCE`，避免把单次往返定义为失败。

条件：

1. 存在 `ClosedRouteWatch`；
2. watch stage 为 `MATURE_STAGNATION`；
3. witness count \(\ge2\)；
4. 成熟来源为：
   - W2-A 同 RouteKey 第二次 return；或
   - W2-B 返回后同 departure branch no-progress；
5. phase/open mask 未变化；
6. 自 watch 创建以来最大 HEAD gain：

\[
<0.10
\]

7. watch 未被 productive workflow 驳回；
8. 当前 screen match watch source frontier。

单次 return 无论 score 多高，都没有 T2 candidate，因此不能依靠 score 意外越过 maturity gate。

---

# 20.4 T3：`MATURED_FRONTIER_EXHAUSTION`

在当前 step \(s\)，取窗口：

\[
W_s=[s-9,s]
\]

只统计：

```text
同 frontier
同 phase
同 open group mask
```

的 receipts。

定义：

```text
V = distinct source-step visits
B = BAD_EVENT count
P = PRODUCTIVE_EVENT count
D = distinct bad branch count
Q = sum(max(0, bad_count(branch)-1))
```

T3 条件：

\[
V\ge4
\]

\[
B\ge3
\]

\[
D\ge2
\]

\[
Q\ge1
\]

\[
P=0
\]

并且：

\[
\max \Delta C_{\text{HEAD}}<0.10
\]

还要求：

```text
当前没有同 frontier 的未交付成熟 T1
当前没有同 frontier 的未交付成熟 T2
当前没有同 frontier 的未交付成熟 T4
```

因此，下列情况不能触发 T3：

```text
三次普通 visit
两次 local visible change
一次 Settings 往返
一次修改开始时间
一次修改结束时间
多个不同 frontier 的返回
```

---

# 20.5 T4：`VALUE_REENTRY_AFTER_BAD_OUTCOME`

条件：

1. canonical action 为 `type_text`；
2. normalized text 非空；
3. 12 actions 内出现相同 normalized text；
4. 相同 phase；
5. 相同 open group mask；
6. 相同 source frontier match；
7. 相同 target group mask；
8. 第一次输入对应：
   - `NO_PROGRESS_*`；或
   - 已成熟的 bad route return；或
   - source frontier reentry 且 HEAD gain <0.10；
9. 中间没有合法 clear，或 clear 后仍回到同一坏 frontier。

两次输入是两个 witness。

---

## 21. Retrieval hard eligibility

Candidate 必须同时满足：

1. `stage == MATURE`
2. 未 delivered；
3. 当前 step 不超过 expires；
4. phase 完全相同；
5. open group mask 完全相同；
6. evidence signature 未交付；
7. 当前 screen：
   - exact match；或
   - 满足严格 near retrieval 阈值；
8. witness 数：
   - T0 \(\ge3\)
   - T1 \(\ge2\)
   - T2 \(\ge2\)
   - T3 \(\ge3\)
   - T4 \(\ge2\)
9. 自 candidate baseline 以来最大 HEAD gain：

\[
<0.15
\]

10. candidate 没有被 productive evidence 驳回；
11. episode nonempty reads < 5；
12. current phase reads < 2；
13. 与上次非空读取相距至少 4 executed actions；
14. score \(\ge0.72\)。

任何 hard eligibility 失败都返回空字符串，不允许 score 补救。

---

## 22. Retrieval score

## 22.1 Visual match \(M\)

Exact：

\[
M=1
\]

Near：

\[
M=
\max
\left(
0,
1-\frac{D_V}{0.040}
\right)
\]

## 22.2 Evidence strength \(E\)

### T0

\[
E=
\min(1,\Delta C_{\text{completed head}}+0.20)
\]

### T1

\[
E=
\max(0.60,C_{\text{bad branch}})
\]

### T2

\[
E=
\min
\left(
1,
0.55
+
0.15\min(3,witness\_count)
+
0.15\mathbf1[return\_count\ge2]
\right)
\]

### T3

\[
E=
\min(1,B/4)
\]

### T4

\[
E=
\max(0.65,C_{\text{prior bad branch}})
\]

## 22.3 Unresolved obligation ratio \(U\)

只统计 obligation group HEAD specificity。

\[
U
=
\frac{
\sum_{g\in open}w_g
}{
\sum_gw_g
}
\]

无 anchor/group 时：

\[
U=1
\]

Persistent filter 始终在 numerator。

## 22.4 Stagnation strength \(S\)

### T0

\[
S=
1-\min
\left(
1,
\frac{\max other\_group\_gain}{0.15}
\right)
\]

### T1

\[
S=\min(1,N/2)
\]

### T2

\[
S=
\min
\left(
1,
\frac{witness\_count}{2}
\right)
\]

### T3

\[
S=
\frac{B}{\max(1,B+P)}
\]

### T4

\[
S=1
\]

## 22.5 Maturity \(W\)

\[
W=
\min
\left(
1,
\frac{witness\_count}{required\_witness\_count}
\right)
\]

## 22.6 No-progress continuation \(G\)

\[
G=
1-
\min
\left(
1,
\frac{\max HEAD\ gain\ since\ baseline}{0.15}
\right)
\]

## 22.7 Freshness \(F\)

\[
F=
e^{-\frac{s-matured\_step}{8}}
\]

## 22.8 最终 score

\[
Score
=
M
\left(
0.30E+
0.20U+
0.20S+
0.15W+
0.10G+
0.05F
\right)
\]

读取阈值：

\[
\boxed{Score\ge0.72}
\]

## 22.9 排序

按以下 tuple 升序排序：

```python
(
    -score,
    -trigger_priority,
    visual_distance,
    -matured_step,
    trigger_id,
)
```

Priority：

```text
T0 = 5
T1 = 4
T2 = 3
T4 = 2
T3 = 1
```

每次 `read()` 最多选择一个 candidate。

---

## 23. Rendering template

固定模板：

```text
A10-v2 frontier; observed history only, current screen controls.
Open: {OPEN}. Evidence: {EVIDENCE}.
This warning requires repeated stagnation, not one navigation return. Reassess a different action family, target, or route only if the screen supports it. Nothing is blocked or selected.
```

### 23.1 字段预算

```text
OPEN <= 56 chars
EVIDENCE <= 86 chars
FULL <= 420 chars
UTF-8 <= 720 bytes
```

### 23.2 OPEN

最多显示两个 open obligation groups：

```text
"Bike Repairs", "Public Transit" (+1 more)
```

Constraint：

```text
"zucchini in directions"
```

无 anchor：

```text
task completion is not established
```

每个 label 最多 24 chars。

### 23.3 EVIDENCE

#### T0

```text
"Tuition Fees" gained support, but other listed items stayed open after leaving
```

#### T1

```text
tap lower-middle for "Bike Repairs" had no visible change on 2 attempts
```

#### T2

```text
tap lower-middle left and returned twice without visible obligation progress
```

或：

```text
after one return, the same departure branch was retried with no visible change
```

#### T3

```text
4 visits contained 3 bad outcomes across 2 branches and no productive transition
```

#### T4

```text
the same text was re-entered after its earlier branch produced no progress
```

### 23.4 截断算法

1. 分别将 OPEN 截至 56 chars、EVIDENCE 截至 86 chars；
2. 组装完整模板；
3. 若 chars > 420，逐字符缩短 EVIDENCE；
4. 若 UTF-8 bytes > 720，继续逐字符缩短 EVIDENCE；
5. 若仍超限，逐字符缩短 OPEN；
6. 固定第三行不得截断；
7. 最终执行硬断言。

模板不得出现：

```text
completed
success
task finished
verified by evaluator
must click
do not click
blocked
forced
```

固定句子 `Nothing is blocked or selected.` 中的 `blocked` 是否定性边界说明，completion-claim 检查不得将其误判为动作阻止。

---

## 24. 合并、衰减与淘汰

## 24.1 Anchor event 淘汰

超过 6 个 event：

1. 计算当前衰减后绝对贡献；
2. 优先保留最新负证据；
3. 其余淘汰绝对贡献最小者；
4. 平局淘汰最旧；
5. 再以 event kind 字典序。

## 24.2 Branch 淘汰

\[
U_b
=
2C_{\text{bad}}
+
C_{\text{escape}}
+
0.5\mathbf1[
target\_group\_mask
\cap
open\_group\_mask
\ne0
]
+
e^{-\frac{s-last\_step}{8}}
\]

淘汰最低 \(U_b\)。

平局：

```text
last_step ascending
branch_id lexicographic
```

## 24.3 Frontier 淘汰

\[
U_f
=
3A_f+
1.5J_f+
1.5E_f+
T_f+
e^{-\frac{s-last\_visit}{12}}
\]

其中：

```text
A_f = 1 if current matched frontier else 0
J_f = weighted Jaccard with current open groups
E_f = min(1, bad/productive evidence mass / 3)
T_f = 1 if it owns mature undelivered trigger else 0
```

淘汰最低。

## 24.4 ClosedRouteWatch 淘汰

\[
U_r
=
2\mathbf1[stage=MATURE\_STAGNATION]
+
1.5\max(0,return\_count-1)
+
0.5\mathbf1[stage=PROVISIONAL\_POST\_RETURN]
+
e^{-\frac{s-last\_update}{6}}
\]

成熟 watch 已生成 trigger 后可以删除 watch，只保留 bounded trigger payload。

## 24.5 Trigger 淘汰

\[
U_t
=
Score_{\text{creation}}
+
0.15(witness\_count)
+
e^{-\frac{s-matured\_step}{6}}
+
b_{\text{kind}}
\]

```text
T0 bonus = 0.20
T1 bonus = 0.18
T2 bonus = 0.15
T4 bonus = 0.10
T3 bonus = 0.05
```

淘汰最低。

---

## 25. `read(context)` 伪代码

```python
def read(self, context: dict | None = None) -> tuple[str, dict]:
    context = context or {}
    read_step = self.read_count
    self.read_count += 1

    goal = str(context.get("goal") or "")
    self._initialize_goal_once(goal)

    before = dict(context.get("before") or {})
    pixels = self._extract_visible_rgb_only(before)
    current = describe_visual_state(pixels)

    self._refresh_head_confidences(read_step)
    current_open_mask = self._open_group_mask()

    self._expire_or_dismiss_stale_candidates(
        step=read_step,
        phase_id=self.phase_id,
        open_group_mask=current_open_mask,
    )

    if self.nonempty_read_count >= 5:
        return "", self._empty_read_audit(
            step=read_step,
            reason="episode_read_cap",
            descriptor=current,
        )

    if self.current_phase_nonempty_reads >= 2:
        return "", self._empty_read_audit(
            step=read_step,
            reason="phase_read_cap",
            descriptor=current,
        )

    if (
        self.last_nonempty_read_step is not None
        and read_step - self.last_nonempty_read_step < 4
    ):
        return "", self._empty_read_audit(
            step=read_step,
            reason="global_cooldown",
            descriptor=current,
        )

    eligible = []

    for candidate in self.trigger_candidates:
        if candidate.stage != "MATURE":
            continue
        if candidate.delivered:
            continue
        if read_step > candidate.expires_step:
            continue
        if candidate.phase_id != self.phase_id:
            continue
        if candidate.open_group_mask != current_open_mask:
            continue
        if candidate.evidence_signature in self.delivered_signatures:
            continue
        if candidate.witness_count < required_witnesses(candidate.kind):
            continue

        distance = strict_retrieval_distance(
            current,
            candidate.expected_descriptor,
        )
        if distance is None:
            continue

        max_gain = self._max_head_gain_since(
            candidate.baseline_head_confidences
        )
        if max_gain >= 0.15:
            candidate.stage = "DISMISSED"
            candidate.dismiss_reason = "observed_progress"
            continue

        score, components = retrieval_score(
            candidate=candidate,
            visual_distance=distance,
            open_groups=self.obligation_groups,
            current_step=read_step,
            max_head_gain=max_gain,
        )

        if score < 0.72:
            continue

        eligible.append(
            (
                -score,
                -trigger_priority(candidate.kind),
                distance.dv,
                -candidate.matured_step,
                candidate.trigger_id,
                candidate,
                components,
            )
        )

    if not eligible:
        return "", self._empty_read_audit(
            step=read_step,
            reason="no_eligible_mature_candidate",
            descriptor=current,
        )

    eligible.sort()
    _, _, _, _, _, selected, components = eligible[0]
    rendered = render_a10_v2(
        candidate=selected,
        groups=self.obligation_groups,
        max_chars=420,
        max_utf8_bytes=720,
    )

    assert len(rendered) <= 420
    assert len(rendered.encode("utf-8")) <= 720

    selected.stage = "DELIVERED"
    selected.delivered = True
    selected.delivered_step = read_step

    self.delivered_signatures.append(selected.evidence_signature)
    self.delivered_signatures = self.delivered_signatures[-12:]

    self.nonempty_read_count += 1
    self.current_phase_nonempty_reads += 1
    self.last_nonempty_read_step = read_step

    event = self._make_read_event(
        step=read_step,
        candidate=selected,
        score=-eligible[0][0],
        components=components,
        rendered=rendered,
        current_descriptor=current,
    )
    self.read_events.append(event)
    self.read_events = self.read_events[-5:]

    return rendered, self._nonempty_read_audit(event)
```

---

## 26. `observe_step(...)` 伪代码

```python
def observe_step(self, **kwargs) -> dict:
    step = int(kwargs["source_step"])

    if step != self.last_observed_step + 1:
        raise A10V2IntegrityError("non-monotonic source_step")

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

    before_desc = describe_visual_state(before_pixels)
    after_desc = describe_visual_state(after_pixels)

    self._refresh_head_confidences(step)
    phase_before = self.phase_id
    open_mask_before = self._open_group_mask()
    confidence_before = self._head_confidence_tuple()

    source, source_created, source_merged = (
        self._match_or_create_frontier(
            descriptor=before_desc,
            phase_id=phase_before,
            open_group_mask=open_mask_before,
            step=step,
        )
    )
    source.register_visit_once(step)

    intent = classify_intent(summary, action)

    anchor_mask, group_mask = target_masks(
        summary=summary,
        action=action,
        anchors=self.anchors,
        groups=self.obligation_groups,
    )

    branch_key = canonicalize_branch(
        action=action,
        intent_class=intent,
        target_anchor_mask=anchor_mask,
        target_group_mask=group_mask,
    )
    branch, branch_created = source.get_or_create_branch(branch_key)

    fraction = changed_pixel_fraction(
        before_pixels,
        after_pixels,
    )
    immediate_outcome = classify_immediate_outcome(
        before_pixels=before_pixels,
        after_pixels=after_pixels,
        before_descriptor=before_desc,
        after_descriptor=after_desc,
        changed_fraction=fraction,
    )

    receipt = create_attempt_receipt(
        source_step=step,
        source_frontier=source,
        branch=branch,
        phase_id=phase_before,
        open_group_mask=open_mask_before,
        target_anchor_mask=anchor_mask,
        target_group_mask=group_mask,
        immediate_outcome=immediate_outcome,
        source_descriptor=before_desc,
        destination_descriptor=after_desc,
        audit_hashes=allowed_audit_hashes(kwargs),
    )

    self._append_receipt_bounded(receipt)
    branch.register_attempt(receipt)

    anchor_events = derive_head_events(
        step=step,
        summary=summary,
        action=action,
        intent=intent,
        target_anchor_mask=anchor_mask,
        target_group_mask=group_mask,
        outcome=immediate_outcome,
        groups=self.obligation_groups,
    )
    self._apply_head_events(anchor_events)

    if immediate_outcome == "DEPARTURE_PENDING":
        self._append_pending_route(
            receipt=receipt,
            source_frontier=source,
            source_descriptor=before_desc,
            source_confidences=confidence_before,
        )

    self._update_pending_route_interiors(
        step=step,
        action=action,
        intent=intent,
        outcome=immediate_outcome,
        target_group_mask=group_mask,
    )

    route_resolutions = self._resolve_pending_routes(
        step=step,
        current_descriptor=after_desc,
    )

    closed_route_watch_events = []

    for resolution in route_resolutions:
        self._write_resolution_to_receipt(resolution)
        self._revise_late_return_if_needed(resolution)

        if resolution.outcome == "DURABLE_DEPARTURE":
            self._write_targeted_durable_head_evidence(resolution)

        if resolution.outcome == "RETURNED":
            watch_event = self._create_or_update_closed_route_watch(
                resolution=resolution,
                current_step=step,
            )
            if watch_event is not None:
                closed_route_watch_events.append(watch_event)

    self._refresh_head_confidences(step)
    self._refresh_branch_confidences(step)

    phase_switch = self._apply_phase_switch_if_needed(
        step=step,
        old_open_mask=open_mask_before,
        intent=intent,
        immediate_outcome=immediate_outcome,
        after_descriptor=after_desc,
    )

    open_mask_after = self._open_group_mask()

    destination, destination_created, destination_merged = (
        self._match_or_create_frontier(
            descriptor=after_desc,
            phase_id=self.phase_id,
            open_group_mask=open_mask_after,
            step=step + 1,
        )
    )
    destination.register_visit_once(step + 1)

    # Update post-return watches using only the now-observed action/frame.
    matured_route_watches, dismissed_route_watches = (
        self._update_closed_route_watches_from_observed_step(
            step=step,
            source_frontier=source,
            branch=branch,
            immediate_outcome=immediate_outcome,
            phase_switch=phase_switch,
            open_mask_after=open_mask_after,
            after_descriptor=after_desc,
        )
    )

    enqueued = []

    # T1
    t1 = self._maybe_make_t1(
        step=step,
        frontier=source,
        branch=branch,
        phase_switch=phase_switch,
    )
    if t1 is not None and self._enqueue_if_novel(t1):
        enqueued.append(t1.trigger_id)

    # T2
    for watch in matured_route_watches:
        t2 = self._make_t2_from_mature_watch(
            step=step,
            watch=watch,
        )
        if self._enqueue_if_novel(t2):
            enqueued.append(t2.trigger_id)
            self._write_bad_route_head_evidence(watch)

    # T4
    t4 = self._maybe_make_t4(
        step=step,
        action=action,
        frontier=source,
        branch=branch,
        phase_switch=phase_switch,
    )
    if t4 is not None and self._enqueue_if_novel(t4):
        enqueued.append(t4.trigger_id)

    # T3 only after higher-priority triggers.
    if not self._has_active_high_priority_trigger(source):
        t3 = self._maybe_make_t3(
            step=step,
            frontier=source,
            phase_switch=phase_switch,
        )
        if t3 is not None and self._enqueue_if_novel(t3):
            enqueued.append(t3.trigger_id)

    # T0
    self._update_partial_escape_watches(
        step=step,
        source_frontier=source,
        destination_frontier=destination,
        intent=intent,
        confidence_before=confidence_before,
    )
    for watch in self._mature_partial_escape_watches(step):
        t0 = self._make_t0(watch)
        if self._enqueue_if_novel(t0):
            enqueued.append(t0.trigger_id)

    self._update_post_read_behavior(
        step=step,
        executed_branch=branch,
        after_descriptor=after_desc,
    )

    evictions = self._enforce_all_capacities(step)

    self.last_observed_step = step

    written = any(
        (
            source_created,
            source_merged,
            destination_created,
            destination_merged,
            branch_created,
            bool(anchor_events),
            bool(route_resolutions),
            bool(closed_route_watch_events),
            bool(matured_route_watches),
            bool(dismissed_route_watches),
            phase_switch,
            bool(enqueued),
            bool(evictions),
        )
    )

    return {
        "written": written,
        "source_step": step,
        "phase_before": phase_before,
        "phase_after": self.phase_id,
        "phase_switch": phase_switch,
        "source_frontier_id": source.frontier_id,
        "destination_frontier_id": destination.frontier_id,
        "branch_id": branch.branch_id,
        "immediate_outcome": immediate_outcome,
        "target_anchor_mask": anchor_mask,
        "target_group_mask": group_mask,
        "anchor_events": audit_events(anchor_events),
        "route_resolutions": audit_resolutions(route_resolutions),
        "closed_route_watch_events": audit_watch_events(
            closed_route_watch_events
        ),
        "matured_route_watch_ids": [
            item.watch_id for item in matured_route_watches
        ],
        "dismissed_route_watch_ids": [
            item.watch_id for item in dismissed_route_watches
        ],
        "trigger_ids_enqueued": enqueued,
        "evictions": evictions,
    }
```

---

## 27. Audit record

`audit_record()` 至少包含：

```text
schema
mechanism_id
experiment_id

decision_boundary
  allowed_inputs
  ignored_input_keys
  model_calls_added = 0
  guard_enabled = false
  action_override_count = 0
  forced_termination_count = 0
  evaluator_used = false
  hidden_ui_used = false
  future_information_used = false
  task_name_used = false
  episode_id_used = false

parameters
  all frozen constants and thresholds

goal
  goal_sha256
  operation_class
  anchor_count
  group_count
  anchors
  groups
  parser_diagnostics
  rejected_candidates
  app_locator_spans

phase
  phase_id
  phase_switch_count
  phase_events

frontiers
  current_count
  max_observed_count
  merge_count
  eviction_count
  records

branches
  current_count
  raw_outcome_counts
  bad_return_counts
  confidence values

attempts
  retained_count
  receipts

routes
  pending_count
  returned_count
  durable_count
  late_return_count
  normal_workflow_dismissal_count

closed_route_watches
  current_count
  created_count
  matured_count
  dismissed_count
  expired_count
  records

triggers
  provisional_count
  mature_count
  delivered_counts_by_kind
  created_counts_by_kind
  expired_count
  duplicate_suppressed_count
  candidates

reads
  read_count
  nonempty_read_count
  phase_read_count
  last_nonempty_read_step
  max_rendered_chars
  max_rendered_utf8_bytes
  delivered_signatures
  read_events

post_read_behavior
  next_branch_novel_count
  same_branch_after_read_count
  escaped_frontier_within_3_count
  returned_within_4_count
  head_gain_after_read_count

capacity
  serialized_audit_bytes
  estimated_resident_state_bytes
  max_observed_frontiers
  max_observed_branches
  max_observed_route_watches
  max_observed_triggers
```

每个 `read_event`：

```text
read_id
read_step
trigger_id
trigger_kind
candidate_created_step
candidate_matured_step
phase_id
open_group_mask
frontier_id
branch_ids
witness_steps
witness_count
score
score_components
visual_distance
exact_injected_text
rendered_sha256
rendered_chars
rendered_utf8_bytes

next_action_step
next_branch_id
next_action_was_novel
escaped_frontier_within_3
returned_within_4
head_confidence_delta_within_4
phase_switch_within_4
```

最后几项只在未来步骤真实发生后更新，不能反向修改当时 read 使用的 evidence。

---

## 28. Controller 与 runner 集成

## 28.1 新文件

```text
implementation/src/raven_m/official_qwen_mobile/
  a10_v2_obligation_branch_frontier.py
  a10_v2_contract.py

implementation/configs/
  a10_v2_evidence_matured_obligation_branch_frontier_hard_seed20260806.json

implementation/scripts/
  replay_a10_v2_offline_traces.py
  preflight_a10_v2.py
  qualify_a10_v2_live_server.py
  start_a10_v2_server.sh

implementation/tests/official_qwen_mobile/
  test_a10_v2_parser.py
  test_a10_v2_obligation_branch_frontier.py
  test_a10_v2_route_maturity.py
  test_a10_v2_controller_integration.py
  test_a10_v2_contract.py
  test_a10_v2_offline_replay.py
  test_a10_v2_adversarial.py
```

## 28.2 禁止覆盖 v1

不得：

```text
修改 A10_OFFLINE_REPLAY_REPORT.json 的 status
将 v2 class 写回 a10_obligation_branch_frontier.py
复用 v1 MECHANISM_ID
复用 v1 EXPERIMENT_ID
复用 v1 preflight schema
复用 v1 live receipt
```

## 28.3 Controller

```python
memory = EvidenceMaturedObligationBranchFrontierMemory(...)
```

Controller 必须保持：

```text
system_prompt = exact OFFICIAL_SYSTEM_PROMPT
history_policy = official_text_action_summaries_only
cost_guard = None
source_document_coverage_gate = None
stop_after_markor_source_exit = False
```

A10-v2 不实现：

```text
history_summary()
record_protocol()
filter_action()
override_action()
should_terminate()
```

Memory 文本只附加到当前 user prompt，不进入后续 official action history。

## 28.4 Proposed/executed action

每步必须：

```text
decision.canonical_action
==
executed canonical action
```

A10-v2 没有任何可以更改等式右侧的 API。

---

## 29. 复杂度、有界性与成本

## 29.1 每步时间复杂度

RGB descriptor：

\[
O(HW)
\]

Frontier comparison：

\[
O(
16\cdot3\cdot407
)
\]

其中 407 为 144 luma + 263 edge bits 的固定维度。

其他：

\[
O(
32\ receipts
+
80\ branches
+
8\ anchors
+
8\ triggers
+
4\ route\ watches
)
\]

总体：

\[
\boxed{
O(HW)+O(1)
}
\]

所有非图像项均有固定上界。

## 29.2 状态内存

不计 controller 持有的 before/after RGB 输入数组，A10-v2 常驻状态必须满足：

```text
serialized audit <= 128 KiB
tracemalloc steady-state delta <= 2 MiB
```

`2 MiB` 是包含 Python object overhead、tuple、dict、hash string 和 descriptor cache 的实现上界，不是 prompt 成本。

Descriptor cache 最多保留：

```text
20 entries
```

与 v1 replay 的 bounded image cache 思路一致。

## 29.3 Prompt 成本

每 episode：

\[
5\ reads
\times
420\ chars
=
2100\ chars
\]

整套 19 题：

\[
19\times2100
=
39900\ chars
\]

Frozen tokenizer：

\[
192\ tokens/read
\]

\[
960\ tokens/episode
\]

\[
18240\ tokens/19-task\ suite
\]

均为绝对最坏上界，正常静默 episode 为 0。

额外模型调用：

\[
\boxed{0}
\]

---

## 30. 具体测试清单

# 30.1 Identity 与 causal boundary

| ID | 测试 |
|---|---|
| ID01 | Mechanism ID 精确匹配 v2 |
| ID02 | Experiment ID 精确匹配 v2 |
| ID03 | v2 不继承或 alias v1 class |
| ID04 | `model_calls_added == 0` |
| ID05 | 无 model/network client import |
| ID06 | 无 guard API |
| ID07 | 无 override API |
| ID08 | 无 forced terminate API |
| ID09 | 无 evaluator input |
| ID10 | 无 UI/accessibility/activity/package input |
| ID11 | 无 future frame |
| ID12 | 无 task_name/episode_id 决策分支 |

# 30.2 Parser

| ID | 测试 |
|---|---|
| P01 | NFKC/casefold/whitespace |
| P02 | Quote extraction |
| P03 | 最后一个 colon list |
| P04 | Marker list 至少两项 |
| P05 | Numeric/time |
| P06 | Temporal |
| P07 | Recipe exact constraint parse |
| P08 | `zucchini` HEAD |
| P09 | `directions` QUALIFIER |
| P10 | Broccoli/app 不抽取 |
| P11 | Positive relative field |
| P12 | Negative relative field |
| P13 | Bare constraint |
| P14 | With/without |
| P15 | Numeric comparison |
| P16 | Relative name |
| P17 | Generic value rejection |
| P18 | Command verb rejection |
| P19 | App span overlap rejection |
| P20 | 6-token boundary |
| P21 | 7-token rejection |
| P22 | Bundle atomic capacity |
| P23 | Constraint/numeric dedup |
| P24 | Metamorphic Cedar/quince query |
| P25 | Parser 不依赖任务名 |

Metamorphic query：

```text
Delete the records from Cedar app that use quince in the notes.
```

必须抽取：

```text
quince
notes
```

不得抽取：

```text
Cedar
app
records
```

# 30.3 Target mask

| ID | 测试 |
|---|---|
| M01 | HEAD exact summary match |
| M02 | HEAD typed-text match |
| M03 | Qualifier-only 不设置 group mask |
| M04 | HEAD+qualifier proximity |
| M05 | Substring 不误匹配 |
| M06 | 同坐标不同 group 得到不同 branch |
| M07 | Same field/different value 分离 |
| M08 | No embedding/synonym expansion |

# 30.4 RGB

| ID | 测试 |
|---|---|
| V01 | exact hash |
| V02 | status bar crop |
| V03 | legal near |
| V04 | layout alias rejection |
| V05 | route threshold |
| V06 | merge threshold |
| V07 | stricter retrieval threshold |
| V08 | H=25/W=8 |
| V09 | H=24 rejection |
| V10 | W=7 rejection |
| V11 | C=2 rejection |
| V12 | float rejection |
| V13 | negative rejection |
| V14 | >255 rejection |
| V15 | RGBA legal |
| V16 | non-contiguous legal |
| V17 | all-black/all-white |
| V18 | keyboard appearance |
| V19 | small spinner |
| V20 | whole-screen brightness shift |

# 30.5 Branch 与 route

| ID | 测试 |
|---|---|
| B01 | Tap binning |
| B02 | Long-press duration |
| B03 | Swipe direction/length |
| B04 | Type-text family |
| B05 | Intent priority |
| B06 | CONFIGURE classification |
| B07 | Exact no-progress |
| B08 | Negligible no-progress |
| B09 | Local visible change |
| B10 | Departure pending |
| B11 | Return 1–4 |
| B12 | Durable at 4 |
| B13 | Late return 5–8 |
| B14 | Late return revises durable |
| B15 | Destination/next-source counted once |
| B16 | Route target-context change |
| B17 | Route work event |
| B18 | Single return creates watch only |
| B19 | Single return never creates T2 |
| B20 | Different frontier returns do not merge |
| B21 | Different branch returns do not merge |
| B22 | Same route second return matures |
| B23 | Same departure branch no-progress matures |
| B24 | Productive novel continuation dismisses |
| B25 | Phase switch dismisses watch |
| B26 | Head gain dismisses watch |
| B27 | Dormant expiry at 12 |
| B28 | Watch capacity/eviction |

# 30.6 Trigger

| ID | 测试 |
|---|---|
| T01 | T0 exact maturity |
| T02 | T0 does not use FILTER_SET as completed item |
| T03 | T1 two no-progress |
| T04 | T1 productive-between-attempts blocks |
| T05 | T1 wait exemption once |
| T06 | T1 changed exact source exemption once |
| T07 | T2 second same route |
| T08 | T2 same branch retry failure |
| T09 | T2 single route impossible |
| T10 | T2 different route key impossible |
| T11 | T3 4 visits/3 bad/2 branches/repeat |
| T12 | T3 local visible change blocks |
| T13 | T3 productive route blocks |
| T14 | T3 one branch only blocked by T1 priority |
| T15 | T4 bad reentry |
| T16 | T4 valid clear blocks |
| T17 | T4 different group blocks |
| T18 | Phase invalidates old trigger |
| T19 | New signature requires two new witnesses |
| T20 | Trigger expiry |

# 30.7 Retrieval

| ID | 测试 |
|---|---|
| R01 | Provisional candidate not eligible |
| R02 | Mature candidate eligible |
| R03 | Exact match |
| R04 | Strict near match |
| R05 | \(0.040<D_V\le0.055\) route-match but no prompt retrieval |
| R06 | Score exact numeric fixture |
| R07 | Threshold 0.72 |
| R08 | Priority tie-break |
| R09 | One-shot |
| R10 | Global cooldown |
| R11 | Phase switch does not reset cooldown |
| R12 | Per-phase cap |
| R13 | Episode cap |
| R14 | Progress dismisses candidate |
| R15 | Rendering chars |
| R16 | Rendering bytes |
| R17 | Frozen tokenizer |
| R18 | No completion claim |

# 30.8 正常行为与假阳性

| ID | 测试 |
|---|---|
| N01 | 一次 Settings-like A-B-A 无读取 |
| N02 | 一次 field editor A-B-A 无读取 |
| N03 | 两个不同 field editor frontier 无合并 |
| N04 | 正常多对象删除 |
| N05 | 同坐标不同对象 |
| N06 | 合法连续滚动 |
| N07 | 第一次 bottom swipe 无变化允许 retry |
| N08 | 第二/第三次 stationary swipe 触发 |
| N09 | Loading wait |
| N10 | Clear and re-entry |
| N11 | 完成对象后返回列表 |
| N12 | 多阶段 workflow 中 visible change 阻止 T3 |
| N13 | exact A-B-A |
| N14 | near A-B-A |
| N15 | A-B-C-A |
| N16 | period-2 但持续有 progress |
| N17 | 同文本不同 phase |
| N18 | 模型 summary 幻觉 completed、RGB 无变化 |
| N19 | 平均亮度相同、布局不同 |
| N20 | 120-step stress |

# 30.9 Leakage

对相同允许输入，改变：

```text
evaluator_reward
task_success
ui_tree
ui_sha256
activity
foreground
package
database_state
task_name
episode_id
```

必须有：

```text
read_A == read_B
observe_A == observe_B
audit_decision_state_A == audit_decision_state_B
```

# 30.10 Capacity

必须构造真实最大边界：

```text
8 anchors
8 groups
48 anchor events
16 frontiers
48 exemplars
80 branches
32 receipts
4 pending routes
4 closed-route watches
2 partial watches
8 triggers
12 delivered signatures
5 read events
```

断言：

```text
serialized audit <= 131072 bytes
steady state <= 2 MiB excluding input RGB
```

---

## 31. 防止任务或页面白名单

## 31.1 Static source scan

对：

```text
a10_v2_obligation_branch_frontier.py
a10_v2_contract.py
```

执行 AST 和原始字符串扫描。

决策实现中禁止出现：

```text
19 个 task class 名称
27 个 episode ID
任何 screenshot SHA256
任何 package ID
Retro Music
Simple Calendar Pro
Broccoli
OpenTracks
pro expense
Markor
OsmAnd
Backup & Restore
```

通用词：

```text
directions
ingredients
title
date
time
duration
settings
```

只有在固定 grammar/field lexicon 中允许；不得与某个 task、step 或 screen hash 联合分支。

## 31.2 Dynamic metadata mutation

相同 query/RGB/action/summary，仅修改：

```text
task_name
episode_id
package
reward
```

结果必须相同。

## 31.3 Query metamorphism

将：

```text
Broccoli → Cedar
zucchini → quince
directions → notes
```

parser 结构必须保持同构。

## 31.4 Formal replay 后不允许同 ID 调参

一旦生成正式：

```text
A10_V2_OFFLINE_REPLAY_REPORT.json
```

以下任一变化必须创建 A10-v3，而不是重跑 v2：

```text
regex
lexicon
threshold
capacity
trigger condition
score coefficient
rendering template
expiry
cooldown
read cap
```

仅修复与本文规范不一致的实现 bug 时，才允许在 v2 implementation freeze 前重跑；修复必须由新增 failing unit test 证明，并在 implementation binding 中记录。

---

## 32. Zero-generation real-trace replay

## 32.1 Trace source

A10-v2 复用已经物化并哈希冻结的 27 个真实 episode 和 1,668 个文件，不修改其字节。

必须重新验证：

```text
episode_count = 27
verified_file_count = 1668
verified_total_bytes = 442138413
manifest_sha256 =
07a326ff4379d51c0d5261e5bf1f28e89ed4176b2130b8fda580079e48e6ff51
generation_calls = 0
```

原 manifest 已经通过这些验证。

A10-v2 生成新的：

```text
evidence/a10_v2/A10_V2_OFFLINE_REPLAY_REPORT.json
```

不得覆盖 v1 报告。

---

## 33. A0 四条历史成功轨迹是否仍要求绝对 0 read

### 33.1 正式决定

\[
\boxed{\text{是，A10-v2 仍要求四条历史 A0 成功轨迹绝对 0 read。}}
\]

要求：

```text
nonempty_read_count == 0
delivered_trigger_count == 0
mature_trigger_count == 0
max_rendered_chars == 0
max_rendered_utf8_bytes == 0
```

允许：

```text
provisional closed-route watch
dismissed normal-workflow watch
expired single-return watch
内部 bounded write
```

但这些对象不得成熟或进入 prompt。

### 33.2 科学理由

四条历史轨迹本身不是 live capability 证明，但它们是当前唯一被冻结的同模型、同 seed、同 benchmark 的已知 competent traces。

保留 0-read 门能够检验：

- v2 是否真的修复 v1 的 false-positive trigger；
- 机制是否在已知顺利轨迹上保持最强稀疏性；
- 修改是否只是把 false-positive 从 T2 改名为其他 trigger。

真正的能力保持仍由 fresh live 4/4 gate 决定。

### 33.3 新公式为何与 0-read 门不再冲突

A10-v1 Retro 与 Calendar 的 false-positive read 只有 T2/T3：

- 两个任务均没有 qualifying repeated no-progress segment；
- `earliest_second_bad_branch_step` 均为空；
- false-positive T2 分别来自不同 source frontier；
- Calendar 的 T3 建立在 v1 允许 local-change resolved attempt 的弱条件上；
- Retro 的 v1 T3 也没有 repeated no-progress qualifying segment。

A10-v2：

- 不允许 single-return T2；
- 不允许不同 frontier/branch 的 route 合并；
- T3 要求真实 BAD_EVENT；
- 任一 `LOCAL_VISIBLE_CHANGE` 都是 PRODUCTIVE_EVENT，令 T3 的 \(P=0\) 条件失败；
- T3 还要求 repeated bad branch；
- v2 constraint parser 不会改变这四个 query 的 obligation 结构。

因此，v1 中导致三次历史读取的充分条件已被删除，而不是通过任务名豁免。

最终仍须由真实 replay 机器验证。如果 v2 正式 replay 在四条成功轨迹中产生任何一次非空读取：

```text
A10-v2 protocol qualification = fail
live generation = forbidden
```

不得再次添加任务特定例外。

---

## 34. A6 失败循环 gate

从 A10-v1 正式报告中确定性提取所有：

```text
role == a6
loop_qualification_records
```

作为 frozen reference segments。

必须：

```text
reference segment count == 23
```

每个 segment 记录：

```text
episode_id
second_no_progress_step
reference frontier/branch identity
```

A10-v2 对一个 segment 的及时资格为：

1. 在第二个 no-progress 的 `observe_step` 完成时或之前；
2. 已有与当前 RGB frontier match 的成熟 T1/T2/T3；
3. 下一次正常 `read()` 已具备 hard eligibility；
4. 发生在第三次相同坏尝试之前。

通过门：

\[
qualified\_segments\ge20/23
\]

即：

\[
qualification\_rate\ge0.869565
\]

另外：

```text
至少 18 个 qualified segments 由 T1 或 T2 资格化
不得主要依赖弱 T3
所有 A6 episode nonempty_reads <= 5
所有 read 满足 cooldown 和 per-phase cap
```

A10-v1 已达到 22/23，这证明实时 RGB 中存在足够早的重复证据，但 v2 仍需独立重新达到上述门。

---

## 35. A8-v2 Expense gate

冻结事实：

```text
earliest second bad branch source_step = 13
```

v1 replay gate 的严格 read deadline 为：

```text
read_step <= 14
```

A8-v2 episode 的 v1 replay 确实存在 qualifying repeated bad branch。

A10-v2 必须：

```text
至少一个 relevant mature candidate
candidate kind ∈ {T1, T2, T3}
candidate matured_step <= 13
first relevant eligible read_step <= 14
nonempty_reads <= 5
rendered text 包含 Open 与具体 branch/route evidence
不得由单次 route watch 资格化
```

---

## 36. A9 Retro gate

冻结 A9 原机制首个非空 canary：

```text
step = 22
```

A10-v1 对相关循环的首个有效 candidate 位于 step 22，首个 read 位于 step 23。

A10-v2 必须：

```text
至少一个 relevant mature candidate
matured_step <= 22
eligible read_step <= 23
kind ∈ {T1, T2, T4}
不得只有 T3
nonempty_reads <= 5
```

A10-v2 不要求在 A9 Retro 上成功；这是 zero-generation 的及时激活资格门，不是性能冒充。

---

## 37. Recipe parser 与 trace gate

对以下三类真实 Recipe trace：

```text
A0 Recipe failure
A1 Recipe success
A6 Recipe failure
```

parser 均必须得到完全相同的 query structure：

```text
anchor_count = 2
group_count = 1
head = zucchini
qualifier = directions
kind = FILTER_SET
persistent_open = true
sentinel = false
```

A1 Recipe 成功 trace：

```text
nonempty_reads <= 1
```

不得为了证明 parser 激活而强迫成功轨迹读取。

在 A0 Recipe failure 与 A6 Recipe failure 中：

```text
至少一个 episode 必须存在 mature candidate
至少一个 eligible memory block 的 Open 字段必须包含
"zucchini in directions"
```

跨三条 Recipe trace：

```text
target_group_match_count >= 1
```

若 policy 的全部 action summary 和 type_text 从未明确提到 `zucchini`，该计数可以失败；此时说明 parser 虽能保存 query constraint，但 branch 无法将其绑定到任何实际动作。正式 preflight 必须失败，不得用模糊语义匹配补救。

---

## 38. Replay 总资格门

A10-v2 offline replay 只有同时满足以下条件才可 `status=pass`：

```text
1. 27 episodes 完整
2. 1668 文件哈希全部通过
3. 442138413 bytes
4. generation_calls = 0

5. A0 四条历史成功轨迹 0 reads
6. A6 >= 20/23 timely qualified
7. A6 strong T1/T2 qualification >= 18
8. A8 relevant mature <= step 13, read <= 14
9. A9 relevant mature <= step 22, read <= 23

10. Recipe exact parser structure
11. Recipe sentinel = false
12. Recipe target-group trace match >= 1
13. 至少一个失败 Recipe read 渲染 constraint

14. 所有 episode reads <= 5
15. 所有 phase reads <= 2
16. 所有 read cooldown >= 4
17. max chars <= 420
18. max bytes <= 720
19. no completion claim
20. no evaluator/hidden UI/future use
21. serialized audit <= 128 KiB
22. no task/page whitelist
```

任一失败：

```text
A10_V2_OFFLINE_REPLAY_REPORT.status = fail
zero-generation preflight = fail
live generation = forbidden
```

---

## 39. Source freeze

A10-v2 implementation commit 必须是设计父 commit 的后代：

```text
4548b932bc3b189507e1442e312c73c8f35dbdb8
```

冻结文件至少包括：

```text
GPT_PRO_A10_V2_STANDALONE_MEMORY_DESIGN_2026-08-12.md

protocols/
  A10_V2_EMOBF_IMPLEMENTATION_BINDING_2026-08-12.md

implementation/configs/
  androidworld_hard_v2_instances.json
  a10_v2_evidence_matured_obligation_branch_frontier_hard_seed20260806.json

implementation/src/raven_m/official_qwen_mobile/
  a10_v2_obligation_branch_frontier.py
  a10_v2_contract.py
  controller.py
  protocol.py
  working_memory.py
  __init__.py

implementation/scripts/
  run_official_qwen_mobile.py
  replay_a10_v2_offline_traces.py
  preflight_a10_v2.py
  qualify_a10_v2_live_server.py
  start_a10_v2_server.sh

implementation/src/raven_m/models/
  vllm_client.py

implementation/src/raven_m/env/
  androidworld_adapter.py

implementation/src/raven_m/multi_framework_benchmark/
  task_instances.py

implementation/tests/official_qwen_mobile/
  test_a10_v2_parser.py
  test_a10_v2_obligation_branch_frontier.py
  test_a10_v2_route_maturity.py
  test_a10_v2_controller_integration.py
  test_a10_v2_contract.py
  test_a10_v2_offline_replay.py
  test_a10_v2_adversarial.py

evidence/a10/
  A10_FROZEN_QUERY_SET.json
  A10_OFFLINE_TRACE_SOURCE_SPEC.json
  A10_OFFLINE_TRACE_MANIFEST.json
  A10_OFFLINE_REPLAY_REPORT.json

evidence/a10_v2/
  A10_V2_OFFLINE_REPLAY_REPORT.json

evidence/a2/
  A0_A1_PAIRED_REFERENCE_20260810.json

evidence/a678/
  A8_V2_OFFLINE_TRACE_AUDIT_2026-08-11.json
  A89_INITIAL_GATE_RESULTS_2026-08-12.json
```

`A10_V2_ZERO_GENERATION_PREFLIGHT.json` 是 source freeze 的输出消费者，不得作为
source freeze 的输入，否则会形成自引用哈希。fresh live receipt 必须单独绑定该
preflight 文件的 raw SHA256 与 canonical JSON SHA256。

每个文件记录 raw SHA256。

对 JSON provenance 另记录 canonical JSON SHA256：

```python
SHA256(
  json.dumps(
    value,
    ensure_ascii=False,
    sort_keys=True,
    separators=(",", ":")
  ).encode("utf-8")
)
```

这延续 commit `4548b932...` 引入的平台稳定 provenance 方式。

---

## 40. 新独立审查门

由于 v2 修改了 parser、T2、T3、route evidence 与 replay gates，v1 两轮审查不能直接覆盖 v2。

Live generation 前必须有两个新的审查文件：

```text
reviews/a10_v2/A10_V2_REVIEW_A.json
reviews/a10_v2/A10_V2_REVIEW_B.json
```

Schema：

```json
{
  "schema": "a10_v2_independent_review_v1",
  "reviewer_id": "...",
  "design_sha256": "...",
  "implementation_sha256": "...",
  "test_collection_sha256": "...",
  "offline_replay_sha256": "...",
  "verdict": "pass",
  "unresolved_blocking_findings": [],
  "unresolved_high_findings": [],
  "reviewed_boundaries": {
    "no_extra_calls": true,
    "no_guard_or_override": true,
    "no_hidden_input": true,
    "single_route_not_triggerable": true,
    "constraint_parser_exact": true,
    "capacity_bounded": true,
    "replay_gates_literal": true
  }
}
```

Preflight 要求：

```text
两个 reviewer_id 不同
两个 verdict 均为 pass
blocking/high 均为空
所有绑定 hash 相同
```

---

## 41. Zero-generation preflight

正式脚本：

```text
implementation/scripts/preflight_a10_v2.py
```

输出：

```text
evidence/a10_v2/A10_V2_ZERO_GENERATION_PREFLIGHT.json
```

### 41.1 必须检查

1. 当前 HEAD 等于声明的 implementation commit；
2. 设计父 commit 是祖先；
3. tracked、untracked、staged、unstaged 工作区全部干净；
4. source freeze 完整；
5. source freeze hashes 匹配；
6. mechanism/experiment/config schema 匹配；
7. model/revision/sampling 匹配；
8. official system prompt hash 匹配；
9. task seed/generation seed 匹配；
10. 19 个唯一 task；
11. native max steps 完整且未修改；
12. A0 gate 顺序和剩余 15 题顺序正确；
13. causal boundary 全部为 false/0；
14. static anti-whitelist 通过；
15. hidden-input dynamic invariance 通过；
16. 全部 `official_qwen_mobile` tests 通过；
17. 全部 v2 tests 通过；
18. pytest collection node-ID hash 冻结；
19. 真实 27-episode replay status 为 pass；
20. replay generation calls 为 0；
21. frozen tokenizer 存在；
22. 所有最大模板 <=192 tokens；
23. 每 episode 最大 memory tokens <=960；
24. 最大状态 audit <=131072 bytes；
25. resident-state stress <=2 MiB；
26. 两份独立审查 pass；
27. runtime causal canary pass；
28. preflight 自身 generation calls 为 0。

### 41.2 Runtime causal canary

构造同一 screen 上两次相同 no-progress branch：

```text
第一次：无 read
第二次：成熟 T1
下一次 read：非空
```

同时断言：

```text
model_calls_added = 0
guard = false
override = 0
forced termination = 0
chars <=420
bytes <=720
audit <=128 KiB
```

### 41.3 Preflight pass

只有：

```text
errors == []
generation_calls == 0
status == "pass"
```

才算通过。

缺失 tokenizer、缺失真实 trace、缺失 reviewer 文件均是 fail，不允许用：

```text
local review only
warning
partial pass
```

替代正式通过。

---

## 42. Live receipt

A10-v2 必须创建新 receipt：

```text
evidence/a10_v2/A10_V2_LIVE_SERVER_RECEIPT.json
```

不得复用：

```text
A10_LIVE_SERVER_RECEIPT.json
A678_LIVE_SERVER_RECEIPT.json
A89 receipt
```

必须绑定：

```text
schema = a10_v2_live_server_receipt_v1
status = pass
generation_calls = 0

a10_v2_preflight_sha256
a10_v2_source_freeze_sha256
launch_intent_sha256
launch_intent_path

served_model_id
model_realpath
model_manifest_sha256

pid
process_cmdline
host
port = 18000

vllm_version
torch_version
transformers_version
served_model_ids_observed
qualification_timestamp
```

资格脚本必须：

1. 验证 preflight status/pass/0 calls；
2. 验证 launch intent 绑定 preflight；
3. 从 `/proc/<pid>/cmdline` 读取真实命令；
4. 命令必须与 intent 数组逐项一致；
5. 查询 `/v1/models`；
6. 只能观察到一个冻结 model ID；
7. 包版本与 intent 一致；
8. receipt 生成期间不调用 generation endpoint。

现有 A10-v1 live qualification 已采用 process cmdline、model endpoint、package version 与 preflight hash 绑定，v2 可复用该控制流但必须更换 schema、路径和 identity。

---

## 43. 何时允许开始 live generation

只有以下全部成立时：

```text
1. A10-v2 implementation commit 已冻结
2. 工作区干净
3. source freeze pass
4. 所有测试 pass
5. 两份独立审查 pass
6. 真实 27-episode replay pass
7. A0 historical silence 4/4 pass
8. A6/A8/A9 timely gates pass
9. Recipe parser/trace gate pass
10. tokenizer/capacity pass
11. zero-generation preflight status=pass
12. fresh live receipt status=pass
13. receipt 与当前 preflight/source freeze 完全绑定
```

缺少任一项：

```text
live generation = forbidden
```

---

## 44. Fresh live 4/4 capability gate

顺序固定：

1. `ExpenseDeleteMultiple2`
2. `RetroSavePlaylist`
3. `SimpleCalendarAddOneEvent`
4. `SportsTrackerTotalDurationForCategoryThisWeek`

每题必须：

```text
finite evaluator reward == 1.0
success == true
transport_attempts == 1 for every model call
model_calls_added_by_memory == 0
guard == false
action_override_count == 0
```

任一科学失败：

```text
suite_status = stopped_capability_gate_failure
remaining_15_released = false
```

不得重跑科学失败。

四个 gate episode 是正式 19 题的前四个有效结果，不再重复运行。

---

## 45. Gate 通过后的 15 题顺序

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

任务 query、顺序和 native max steps 由冻结 AndroidWorld Hard manifest 决定。冻结 query set 中记录了全部 19 个 task seed `20260806` 的实际 query。

---

## 46. Infrastructure invalid

以下才属于 infrastructure invalid：

```text
vLLM process exit
HTTP transport 未返回完整响应
transport_attempts != 1
ADB disconnected
emulator crash
UIAutomator/adapter 无法取得合法 state
app reset/setup 抛基础设施异常
截图文件损坏
RGB shape/dtype/value 非法
evaluator 抛异常或没有有限输出
task params/hash 漂移
model/receipt/source freeze 漂移
artifact 在有限 evaluator reward 形成前不可恢复损坏
```

以下不是 infrastructure invalid，而是 scientific failure：

```text
模型输出格式错误
模型选择非法或错误动作
模型进入循环
模型错误 terminate
模型错误 answer
max_steps
模型未完成任务
memory 没有激活
memory 激活但无效
memory 误导模型
app 正常但模型操作失败
```

如果已经得到有限 evaluator reward：

```text
该 episode 已形成科学结果
```

后续 aggregate 写入问题只能修复 artifact，不得重跑 episode。

---

## 47. Infrastructure-invalid resume

### 47.1 记录

每个 invalid attempt 必须完整保存：

```text
episode_id
task
invalid reason
failure timestamp
steps generated before invalidation
model responses
executed actions
receipt hash
source freeze hash
```

### 47.2 替代 episode

Replacement 必须：

```text
同一 task
同一 task seed
同一 generation seed
同一 params
同一 max steps
同一实现
同一 source freeze
同一 model manifest
```

新 episode 写：

```text
resolves_invalid_episode_id
```

### 47.3 次数上限

每个 task 最多允许：

```text
2 个 infrastructure-invalid attempts
```

第三次 infrastructure invalid：

```text
suite_status = infrastructure_invalid
suite stops
```

不得继续其他任务后再回来补。

### 47.4 Server restart

如果必须重启 vLLM：

- 创建新的 A10-v2 live receipt；
- 新 receipt 必须绑定同一 preflight/source freeze/model manifest/package versions/launch command；
- 将 receipt 加入 `live_receipt_chain`；
- 从当前 invalid task 重新开始；
- 不重跑此前有效 episode。

### 47.5 不允许的 resume

```text
科学失败后 resume
换 seed
改 prompt
改 threshold
改 parser
改 memory capacity
跳过失败 task
从中间 UI state 继续
```

---

## 48. 19/19 closure

完整 suite 必须含：

```text
exactly 19 valid task summaries
exactly one valid summary per frozen task
exact frozen order
task seed = 20260806
no duplicated gate task
no omitted task
```

Invalid attempts 单独记录，不计入 19 个 valid slots。

19 个 valid episode 全部形成后才能计算正式：

```text
success count
reward sum
cost
memory activity
pairwise comparison
final verdict
```

---

## 49. 正式性能目标

必须同时满足：

```text
A0 live capability gate = 4/4

valid tasks = 19/19

success_count >= 6
reward_sum > 5.5

success_count > A1 success_count
reward_sum > A1 reward_sum

extra model calls = 0
guard = 0
override = 0
forced termination = 0

至少一个 successful active-memory episode
至少一个 productive divergence hypothesis
```

这是验收标准，不是设计保证。

---

## 50. Result schema

```json
{
  "schema": "a10_v2_emobf_result_v1",
  "status": "...",

  "identity": {
    "design_parent_commit": "4548b932bc3b189507e1442e312c73c8f35dbdb8",
    "implementation_commit": "...",
    "mechanism_id": "a10_v2_evidence_matured_obligation_branch_frontier_v2",
    "experiment_id": "A10_V2_EMOBF_QWEN3VL32B_AW_HARD_S20260806_G3407_V1",
    "source_freeze_sha256": "...",
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
    "required_success": 4,
    "observed_success": 4,
    "tasks": []
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
    "write_attempt_count": 0,
    "write_success_count": 0,
    "provisional_route_watch_count": 0,
    "mature_route_watch_count": 0,
    "normal_workflow_dismissal_count": 0,
    "mature_trigger_count": 0,
    "nonempty_read_count": 0,
    "active_success_count": 0,
    "max_reads_per_episode": 0,
    "max_reads_per_phase": 0,
    "minimum_read_cooldown": null,
    "rendered_chars_total": 0,
    "rendered_tokens_total": 0,
    "model_calls_added": 0,
    "guard_enabled": false,
    "action_override_count": 0,
    "forced_termination_count": 0
  },

  "mechanism_evidence": {
    "successful_active_memory_episodes": [],
    "productive_divergence_hypotheses": []
  },

  "comparison": {
    "versus_A0": {},
    "versus_A1": {}
  },

  "invalid_attempts": [],
  "tasks": [],
  "errors": []
}
```

---

## 51. Per-task schema

```text
task_index
task_id
task_name
task_seed
native_max_steps

episode_id
episode_json_sha256
resolves_invalid_episode_id

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
provisional_route_watch_count
mature_route_watch_count
normal_workflow_dismissal_count
trigger_count
nonempty_read_count
first_nonempty_read_step
memory_rendered_chars
memory_rendered_tokens
phase_switch_count
frontier_eviction_count
branch_eviction_count
route_watch_eviction_count

model_calls_added
guard_enabled
action_override_count
forced_termination_count
hidden_input_used
evaluator_input_used
future_input_used
```

---

## 52. 逐 read 因果分析

每个 nonempty read 必须记录：

```text
task
episode_id
read_step

trigger_kind
trigger_score
score_components

open_obligation_groups
constraint_groups

matching_frontier
visual_distance

witness_steps
witness_count
prior_branches
prior_bad_outcomes
prior_productive_outcomes
closed_route_watch_history

exact_injected_text
rendered_sha256

next_executed_action
next_branch_id
next_branch_was_novel

escaped_frontier_within_3
returned_within_4
head_gain_within_4
phase_switch_within_4

episode_reward
episode_success
```

## 52.1 Successful active-memory episode

定义：

```text
episode success == true
nonempty_read_count >= 1
```

## 52.2 Productive divergence hypothesis

一条 read 只有同时满足以下条件才能被列为：

```text
trace_grounded_productive_divergence_hypothesis
```

1. episode 最终成功；
2. read 使用成熟 candidate；
3. 下一 executed action 或紧接着的一个 action 使用此前未在该 frontier 出现的 branch；
4. 三个 actions 内离开 read frontier；
5. 四个 actions 内没有返回同一 frontier；
6. 以下至少一个成立：
   - open HEAD confidence 增加至少 0.15；
   - phase switch；
   - 轨迹从此不再返回该 frontier直到 evaluator；
7. 无 guard、override、额外 call。

允许表述：

> 在 step \(t\)，A10-v2 基于两个以上独立停滞 witness 发出 frontier memory。模型随后采用此前未尝试的 branch，并在三步内离开该 frontier，四步内未返回，且 episode 最终成功。因此，这条 memory 可能促成了生产性的策略分化。

禁止表述：

```text
A10-v2 proved causality.
The memory caused success.
The alternative action was verified correct.
The failed branch was impossible.
```

---

## 53. Pairwise comparison

分别对 A0、A1 报告：

```text
wins
losses
ties
success_delta
reward_delta
executed_action_delta
model_call_delta
prompt_token_delta
total_token_delta
elapsed_delta
```

不得只报告成功数而隐藏：

```text
actions
calls
tokens
time
memory exposure
```

由于是固定单 seed 的 19-task comparison，统计检验只能作为描述性补充，不得宣称跨任务分布的一般显著性。

---

## 54. Final verdict

按以下优先级判定。

### 54.1 `A10_V2_PROTOCOL_INVALID`

任一：

```text
mechanism/experiment identity 漂移
source freeze 漂移
使用禁止输入
额外模型调用
guard/override/forced termination
任务/page/hash 白名单
版本拼接
scientific failure 重跑
换 seed
改成功标准
19-task order 不完整
正式 v2 replay 后在同 ID 下改规则
```

### 54.2 `A10_V2_ZERO_GENERATION_PREFLIGHT_FAIL`

在 live 启动前：

```text
测试
replay
tokenizer
capacity
review
source freeze
```

任一未通过。

### 54.3 `A10_V2_INFRASTRUCTURE_INVALID`

通过 preflight 后，suite 因基础设施无法形成完整 19 个有效结果。

### 54.4 `A10_V2_CAPABILITY_GATE_FAILURE`

四题任一科学失败。

### 54.5 `A10_V2_SCIENTIFIC_FAILURE`

19 题闭合，但任一：

```text
success < 6
reward <= 5.5
未严格超过 A1
```

### 54.6 `A10_V2_PERFORMANCE_PASS_MECHANISM_EVIDENCE_FAIL`

性能达到，但：

```text
没有 successful active-memory episode
或
没有 productive divergence hypothesis
或
所有新增成功均发生在 memory inactive episode
```

### 54.7 `A10_V2_OVERALL_PASS`

只有全部满足：

```text
preflight pass
live receipt pass
4/4 gate
19/19 closure
success >= 6
reward > 5.5
strictly better than A1
0 extra calls
0 guard
0 override
0 forced termination
>=1 successful active-memory episode
>=1 productive divergence hypothesis
```

---

## 55. Falsification criteria

以下任一直接证伪 A10-v2 的相应主张。

### 55.1 稀疏性证伪

1. A0 四条历史成功 replay 任一非空读取；
2. 单次 closed route 可直接形成 T2；
3. local visible changes 可独立形成 T3；
4. 不同 frontier 的 route 被合并；
5. 正常工作流 watch 没有被 productive evidence 驳回。

### 55.2 及时性证伪

6. A6 资格低于 20/23；
7. A8 relevant candidate 晚于 step 13；
8. A8 relevant read 晚于 step 14；
9. A9 relevant candidate 晚于 step 22；
10. A9 relevant read 晚于 step 23。

### 55.3 Parser 证伪

11. Recipe query 仍进入 sentinel；
12. 未抽取 `zucchini`；
13. 未抽取 `directions`；
14. 抽取 `Broccoli`、`app`、`recipes` 或 generic verb；
15. 使用自由语义模型；
16. 三条 Recipe real traces 中没有任何 target-group match。

### 55.4 Causal boundary 证伪

17. 任一额外 model call；
18. 任一 guard；
19. 任一 override；
20. 任一 forced termination；
21. evaluator/reward/UI/accessibility/package/future 进入决策。

### 55.5 性能证伪

22. live 4/4 gate 失败；
23. 完整结果小于 6/19；
24. reward 不大于 5.5；
25. 未严格超过 A1；
26. 没有 successful active-memory episode；
27. 没有 productive divergence hypothesis。

---

## 56. 从 A10-v1 迁移到 v2

## 56.1 可以复用

以下纯工具逻辑可以复制或重构到 hash-bound common utility：

```text
RGB 输入校验
4% crop
exact hash
9×16 luma descriptor
edge descriptor
visual distance
changed pixel fraction

tap/long-press/swipe/type-text canonical family
bounded descriptor cache
late-return revision
frontier exemplar storage
bounded audit serialization
controller prompt-only integration pattern
source materialization与哈希验证
canonical JSON provenance
preflight身份校验
live process qualification
```

如抽取 common module，必须：

```text
加入 v2 source freeze
v1 行为测试继续通过
v2 不通过 subclass 继承 v1 trigger 实现
```

## 56.2 必须重新实现

```text
MECHANISM_ID / EXPERIMENT_ID
config / contract / schemas

constraint parser
app locator exclusion
constraint bundles
HEAD/QUALIFIER roles
persistent FILTER_SET

target_group_mask
group-based open mask
group-based phase switch

bad_return_count
route work events
ClosedRouteWatch lifecycle
normal workflow dismissal
T2 maturity
T3 bad/productive event window

retrieval strict near threshold
score threshold 0.72
new score components
candidate lifecycle
new expiry
new signature refresh

global cooldown跨 phase
new rendering template
new audit fields

v2 offline replay gates
v2 preflight
v2 live receipt
v2 result schema
```

## 56.3 禁止的迁移方式

```python
class A10V2(A10V1):
    pass
```

禁止。

也禁止只修改：

```text
T2 threshold
T3 count
parser capacity
```

而保留 v1 candidate lifecycle。A10-v2 必须显式实现 provisional route watch 与 maturity gate。

---

## 57. A10-v2 的新失败模式

| 风险 | 原因 | 协议防护 |
|---|---|---|
| T2 过于保守 | 要求第二个 witness | T1 保留两次 no-progress；A6/A8/A9 timing gate |
| 同 route-key 的合法重复仍误报 | 多次进入同设置页面 | productive continuation、target change、route work dismissal |
| Constraint parser 误抽自然语言 | 固定 grammar 仍可能覆盖错误 span | app overlap、generic/verb rejection、长度/token gate |
| FILTER_SET 永远 open 导致频繁提示 | 无法确定开放集合完成 | 仍需成熟坏 evidence；open 本身不触发 |
| Qualifier-only 动作错误绑定 | “directions”出现但未提 zucchini | qualifier 不设置 group mask |
| Near retrieval 仍错误匹配 | 粗视觉 alias | 收紧至 0.040 + edge threshold + maturity gate |
| Near retrieval 漏检 | 页面轻微动画超过 0.040 | route matching 仍用 0.055；只有 prompt retrieval 更严格 |
| T3 几乎不激活 | productive event 定义较宽 | T1/T2 为主要触发器；T3 只是多分支耗尽后备 |
| Memory read 后模型仍重复 | 提示非强制 | post-read audit；科学上记为 activation without divergence |
| Persistent constraint 无完成 phase | 开放集合无法证明 exhaust | 不虚构完成；live 性能检验其实际代价 |
| Parser 依赖英文句式 | benchmark query 为冻结英文 | 不宣称跨语言通用性 |
| 五次 read 仍增加上下文 | 长 episode 多次停滞 | 420 chars、phase 2、cooldown 4、episode 5 硬上限 |

---

## 58. 最终逻辑裁决

### 58.1 A10-v2 是否逻辑自洽

\[
\boxed{\text{是。}}
\]

A10-v2 的 trigger、maturity、retrieval 与 replay gate 不再存在 A10-v1 那种直接逻辑矛盾：

- 单次 closed route 不能产生 T2；
- T3 不能由普通 visit 或 local visible change 形成；
- A0 历史绝对静默门与新公式可以同时满足；
- Recipe query 可以在冻结 grammar 下合法抽取 constraint bundle；
- Recipe gate 不再要求 parser 完成其明文禁止的抽取。

“逻辑自洽”只指规范内部没有已知不可满足条件，不代表真实 replay 或 live performance 必然通过。

### 58.2 是否解决第一项冲突

\[
\boxed{\text{解决。}}
\]

关键不是给 Retro、Calendar 或特定页面增加豁免，而是普遍规定：

```text
一次 closed route = provisional navigation evidence
两个同局部决策上下文的停滞 witness = mature failure evidence
```

该规则对所有任务、页面和 app 一致。

### 58.3 是否解决第二项冲突

\[
\boxed{\text{解决。}}
\]

Recipe query 按固定 relative-field grammar 产生：

```text
zucchini
directions
```

并通过 app-locator 与 generic-value rejection 排除：

```text
Broccoli
app
recipes
```

不需要自由语义模型或额外调用。

### 58.4 何时允许 zero-generation preflight pass

只有：

```text
新实现严格符合本文
全部测试通过
两个独立审查通过
真实 27-episode replay status=pass
A0 四条历史成功 0 reads
A6 >=20/23
A8/A9 timing pass
Recipe parser/trace gate pass
source freeze pass
tokenizer/capacity pass
generation_calls=0
errors=[]
```

才允许：

```text
A10_V2_ZERO_GENERATION_PREFLIGHT.status = pass
```

### 58.5 何时允许开始 live generation

只有：

```text
zero-generation preflight = pass
fresh A10-v2 live receipt = pass
receipt/source/model/process 全部绑定
```

之后，才允许启动第一道：

```text
ExpenseDeleteMultiple2
```

### 58.6 若仍有不可满足条件

如果正式实现后出现任一情况：

```text
A0 历史成功仍有 read
A6/A8/A9 timing 门不能同时满足
Recipe target-group 无法绑定真实 action history
tokenizer/capacity 越界
任何禁止输入进入决策
```

则必须输出统一的准入失败状态：

```text
A10_V2_ZERO_GENERATION_PREFLIGHT_FAIL
```

并停止。

不得：

```text
继续烧 GPU
把 replay fail 改成 warning
临时降低 gate
添加 task/page whitelist
覆盖 A10-v1 失败报告
在同一 A10-v2 ID 下继续调参
```

任何影响机制结果的新修改必须进入：

```text
新的 mechanism ID
新的 experiment ID
新的设计文档
新的 zero-generation replay
```

在 A10-v2 的正式 preflight 明确通过之前，**不授权任何 live generation**。

---

## 59. 非调参式实现勘误与确定性绑定

本节只消除原规范中会造成两个合规实现产生不同结果的歧义，不改变 T0–T4、
retrieval score、阈值或 replay gate。完整枚举、公式、对象 schema 与淘汰键冻结在
`protocols/A10_V2_EMOBF_IMPLEMENTATION_BINDING_2026-08-12.md`；该 binding 与本文共同
构成机制规范，冲突时以本节及 binding 中标为 `ERRATUM` 的条款为准。

1. source freeze 不包含自身生成的 replay/preflight/live/result 输出；这些输出必须
   绑定 source-freeze manifest、source commit 与生成器 SHA256。
2. 无 group 的 constraint-only phase switch 使用 capacity=1 的
   `NoGroupPhaseWatch`，只在原 COMMIT receipt 发生 local visible change、随后 4 个
   executed actions 未返回原 frontier 时切换。
3. `ClosedRouteWatch` 在 returned step 创建；post-return witness 只能从
   `returned_step + 1` 开始消费，return action本身不得计作第一个 post-return action。
4. `specificity_weight`、`operation_class`、HEAD evidence、`route_head_gain`、
   `target_context_changed`、T4 clear/re-entry、frontier merge/eviction 与 negative
   constraint renderer 均按 binding 的固定表和纯函数执行，禁止运行后再调参。
5. `EXCLUDE` constraint 必须以 `without <value>` 或 `exclude <value>` 渲染，不能
   反向渲染成正向 Open obligation。
6. 真实 replay 任一 gate 失败统一为
   `A10_V2_ZERO_GENERATION_PREFLIGHT_FAIL`；只有机制内部出现逻辑不可实现、禁止输入、
   whitelist 或版本拼接才使用 `A10_V2_PROTOCOL_INVALID`。
