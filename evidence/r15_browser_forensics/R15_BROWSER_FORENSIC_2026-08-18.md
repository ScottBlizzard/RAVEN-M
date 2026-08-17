# A1-R15 BrowserMultiply 法证与第七题候选裁决（2026-08-18）

## 结论

**NO-GO：不建立 R15-derived live 候选。** R15 的 BrowserMultiply 是一条真实、形式可审计的成功轨迹，但 EVR `render_count=0`、`rendered_reads=0`。成功只能标为 `TARGET_SUCCESS_WITHOUT_MATURE_EVR_READ_UNATTRIBUTED`。

R15 在普通模型 Thought/Action 历史中逐步保留了 `1, 8, 10, 7, 2`，计算并输入 `1120`；R2、R13D、R14 到达同一数字序列后分别输入 `120`、`720`、`2310`。现有证据支持“本次模型自身历史推理/算术走对了”，不支持“EVR 造成成功”。

## 证据边界

- 冻结源提交：`152f3b92f6ad1d87f20fa0e6a54101a0d2c07711`。
- 本报告只读取既有 artifact，`generation_calls=0`。
- A0 本地只有汇总/案例笔记，没有 raw Browser episode；因此明确标记 summary-only，不伪造逐步对照。
- A1、A2、A6、A7、R2、SYS-NAG V4、R13D、R14、R15 均绑定 raw episode、events、截图和 UI artifact SHA-256。
- 所有对照的初始截图字节均与 R15 不同，不能声称 exact-prefix causal counterfactual。

## R15 数值链

| 值 | 首次 UI 可见 step | Thought 提及 steps | EVR read steps |
|---:|---:|---|---|
| 1 | 12 | [14, 15, 16, 17, 18, 19] | [] |
| 8 | 13 | [13, 15, 16, 17, 18, 19] | [] |
| 10 | 14 | [16, 17, 18, 19] | [] |
| 7 | 15 | [15, 17, 18, 19] | [] |
| 2 | 16 | [16, 17, 18, 19] | [] |

- step 17：模型在 Thought 中完整列出 `1, 8, 10, 7, 2` 并计算 `1120`。
- step 18：实际 `type_text(1120)`。
- step 19：点击 Submit。
- step 20：当前截图/UI 出现 `Success!`，随后模型终止 success。

## 逐臂结果与首个差异

| Arm | reward | calls | typed text | 首图差异 | 首响应差异 | 首动作差异 |
|---|---:|---:|---|---:|---:|---:|
| A1 | 0.0 | 22 | `[]` | 0 | 0 | 0 |
| A2 | 0.0 | 22 | `[]` | 0 | 0 | 0 |
| A6 | 0.0 | 22 | `[]` | 0 | 0 | 0 |
| A7 | 0.0 | 18 | `[]` | 0 | 0 | 0 |
| A1-R2 | 0.0 | 22 | `['120']` | 0 | 0 | 0 |
| SYS-NAG-V4 | 0.0 | 22 | `['120', '120']` | 0 | 0 | 0 |
| A1-R13D | 0.0 | 22 | `['720']` | 0 | 1 | 3 |
| A1-R14 | 0.0 | 22 | `['2310']` | 0 | 0 | 2 |
| A1-R15 | 1.0 | 21 | `[1120]` | — | — | — |

关键语义对照：R2、R13D、R14 和 R15 都看到相同的五值 UI 序列；其决定性差异发生在计算/输入答案，而不是 EVR 注入。R15 与 R14 从 step 0 起因截图字节差异产生不同响应，且在 EVR 留存任何值之前轨迹已经分叉。

## R2 六个成功题回归风险

R15 冻结的 19 题零生成 replay 中，R2 六个成功题 EVR activation/render/read 均为 0。这个结果只说明历史轨迹静默，不证明一个扩大后的 Browser parser 在 prospective live 中安全。把单条 live 表达继续扩成 R16/R17 会把已观察答案形态编码进机制，并破坏因果边界。

## 因果候选裁决

| 候选解释 | 分类 | 依据 |
|---|---|---|
| EVR rendered values caused the correct product | **CONTRADICTED** | R15 EVR render_count=0 and rendered_reads=0; no EVR text entered any model request. |
| Ordinary model-authored action history retained enough values for the model to reason correctly | **DIRECTLY_EVIDENCED** | R15 thought/action prose enumerates the growing value sequence and the final five values before computing 1120. |
| A reusable memory intervention unique to R15 explains the win | **CONTRADICTED** | The only R15-specific EVR treatment was never rendered/read; R15 diverged from failed runs before any EVR value was retained. |
| The remaining bottleneck is arithmetic/outcome reasoning rather than value availability | **PLAUSIBLE** | R2, R13D, and R14 reached the same five-value UI sequence but typed 120, 720, and 2310; R15 typed 1120. |
| The R15 success is a stable deterministic consequence of its identity | **UNKNOWN** | No exact-prefix counterfactual exists; initial screenshot bytes differ and the identity cannot be rerun. |

## GO/NO-GO

裁决：`NO_GO_R15_DERIVED_LIVE_CANDIDATE`。没有证据支持一个 R15 独有、任务无关、可复用且不会明显危及 R2 六个成功题的机制。强行把 EVR、数字序列或 1120 包装成候选只会形成 Browser 特例。

因此第一阶段不烧 GPU；直接进入独立的 failure-recovery Pro 方向。R15 不重跑，不做 R16/R17 parser 正则补丁，不与 R2 拼成 7/19。

## Machine-readable companion

完整逐 step 的 prompt、memory read/write、model response、Thought/Action、实际动作、visible UI strings、截图/UI/events 文件哈希位于 `R15_BROWSER_FORENSIC_2026-08-18.json`。

JSON canonical content SHA-256：`3fc94b9219d7b9f5711241c57a01b5e14ba8d130343c1f4eb7ca6e82860fef22`。
