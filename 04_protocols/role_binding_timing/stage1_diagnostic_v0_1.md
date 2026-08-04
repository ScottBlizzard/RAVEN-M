# Role-Binding Timing Stage-1 Diagnostic Protocol v0.1

Status: **preregistered for offline qualification only**  
Namespace: `role_binding_timing`  
Novelty status: **UNRESOLVED**  
Generation eligibility at freeze: **false**

## Question and claim boundary

With the same correct source fact, model revision, decoding, matched screenshot/UI-tree state, call count, prompt-token budget, completion-token cap, and action budget, does exposing the fact before destination grounding rather than after it interact with source/destination role ambiguity to raise `WrongTarget@FirstTargetingAction`?

A positive result would establish only a narrow critical-decision effect. It would not establish end-to-end memory efficacy, RAVEN-M superiority, M-SLOTS efficacy, M-RISK efficacy, or mobile-task success. RAVEN-M is instrumentation only. Novelty remains unresolved even though Phase A found no exact overlap in its bounded corpus.

## Experimental unit and 2×2 design

The analysis unit is a **base family**, not an individual model call. A base family contains a matched high-ambiguity and low-ambiguity critical-state variant. Screenshot bytes and UI-tree bytes are identical between early and late timing within a variant. High and low variants may differ, but must be collected by the same harness and matched on app, action class, candidate count, target-widget class, layout family, and instruction length.

Each base family yields four cells:

| Cell | FactTiming | RoleAmbiguity |
|---|---|---|
| EL | early | low |
| LL | late | low |
| EH | early | high |
| LH | late | high |

Every cell has exactly two model calls and one proposed-action budget:

1. **Grounding call:** select a blinded destination target ID and bind source/destination entity roles.
2. **Action call:** emit the first target-bearing canonical action (`tap` or `type_text`) using the frozen grounding commitment.

The early transcript puts the fact block in the grounding turn and a token-matched neutral block in the action turn. The late transcript reverses them. In either logical transcript the fact block occurs exactly once. Because the HTTP service is stateless, the second request reserializes the earlier transcript; this is logged as request-level reprocessing, not a second logical fact occurrence. The early and late request pairs must nevertheless have identical text-token counts under the locked tokenizer after canonical commitment serialization. Image tokens are invariant because image bytes are identical within each timing pair.

Call-1 raw prose is never copied into Call 2. The strict parser converts it to a compact canonical commitment. All permitted target aliases must have equal locked-token length. Invalid Call 1 output makes the cell invalid; there are no selective repairs or reruns.

## Frozen compute and decoding

- model: `Qwen/Qwen3-VL-32B-Instruct`
- revision: `0cfaf48183f594c314753d30a4c4974bc75f3ccb`
- backend: `qwen3_vl_32b_transformers_bf16_4x4090_v1`
- decoding: `temperature=0`, `do_sample=false`
- maximum new tokens: 128 per call
- exactly 2 calls per cell; no repair call
- exactly 1 target-bearing action proposal per cell; no environment execution in Stage 1
- text prompt-token difference within an early/late pair: 0 tokens under the locked tokenizer/chat template
- completion-token caps and all other budgets are identical; realized tokens, latency, and invalid outputs are reported without padding or retry

## Input qualification and contamination

Every variant requires a fresh PNG screenshot and a same-state raw UI-tree JSON, each hash-frozen before condition assignment. The oracle maps blinded target IDs to a unique UI-tree selector, entity ID, widget role, and bounds. A target ID must resolve to exactly one node. The intended destination target and destination widget role must be fixed before model output is viewed.

Old AndroidWorld runs, H17/rXX material, EEST-P1/P2/N2, and the eight Phase-A screenshots are `development_contaminated=true` and may only drive replay/corruption/unit tests. They cannot enter the pilot or Stage 1. Snapshot/oracle qualification is the proportion of frozen variants passing all hash, uniqueness, pairing, and oracle checks; it must be at least 95% and all eight pilot base families must retain both ambiguity variants.

## Outcomes

Primary outcome:

- `WrongTarget@FirstTargetingAction`: the action call's first `target_id` differs from the preregistered destination target ID.

Diagnostics:

- grounding destination-ID accuracy;
- action target-ID accuracy;
- `PostGroundingDrift` (action call changes the grounded destination ID);
- `ExactValueRecall` after Unicode NFC normalization only;
- `SourceAsTargetRate`;
- `OtherWrongEntityRate`;
- `CorrectTargetWrongWidgetRate`;
- source/destination role-binding accuracy;
- confidence;
- parser/schema failure;
- calls, prompt/completion/total tokens, latency, and invalid-cell rate.

## Controls and alternative explanations

The 8-family qualification pilot contains only the 2×2 cells. Low ambiguity is the minimal within-pilot diagnostic for a general position/recency effect: an equally large early–late difference in both ambiguity strata must not be called role binding. The pilot is a qualification study and is not powered for a mechanism claim.

The following controls are frozen for later Stage-1 manifests and may not be improvised after unblinding: task-literal/no-memory, irrelevant same-format fact, position placebo, recency placebo, source/destination label swap, destination-provided, no-commitment, delay-only, and local-visible. Stage-1 interpretation requires position/recency placebos and semantic-role swap. Other controls are diagnostic or staged follow-ups. No control may receive extra calls, tokens, action proposals, or retries.

## Blinding and run discipline

Condition IDs are HMAC-derived from a secret held outside the public run manifest. Public cell IDs do not reveal timing or ambiguity. Oracle labels and the unblinding map are read only after all cells in the frozen batch terminate. The pilot has 8 base families × 4 cells = 32 critical decisions and 64 planned calls. There is no selective rerun, prompt edit, parser edit, or template replacement after unblinding.

## Qualification pilot gates

Interpretation requires all of the following:

- `ExactValueRecall >= 95%`;
- snapshot/oracle qualification `>= 95%`;
- parser/schema failure `< 5%`;
- pre-manipulation infrastructure failure `< 10%`;
- low-ambiguity action target accuracy `> 80%`.

Failure stops generation for the round. The first broken information-chain edge is reported. A generic task-agnostic defect may be fixed only in a newly versioned preregistered pilot; the failed pilot remains contaminated and is never relabeled held-out.

## Stage-1 screening gate

Only a qualified pilot permits a separately frozen 48-family study: 48 × 4 = 192 critical decisions, two fixed calls each. Analysis uses matched conditional logistic regression or the frozen matched alternative, paired McNemar tests, absolute risk differences, and cluster bootstrap confidence intervals clustered by base family.

Method development is permitted only if all hold:

- high-ambiguity early-minus-late wrong-target risk is at least 15 percentage points;
- the clustered 95% CI for Timing × Ambiguity excludes 0;
- `ExactValueRecall > 95%`;
- low-ambiguity absolute early–late difference is below 5 points;
- position/recency placebos do not explain the effect;
- the effect follows semantic roles under label swap;
- at least one premature-commitment diagnostic supports the mechanism.

A null result stops the memory-method line and reports an effect-size upper bound. Equal timing effects in both ambiguity levels are relabeled position/recency. A wrong destination before fact exposure pivots to grounding; a correct proposed target followed by execution failure pivots to controller. Stage 2 requires a new preregistration and is outside this protocol version.

## Immediate stop rule

At this protocol freeze, held-out qualified base families are zero. Therefore this version remains `generation_eligible=false`. Offline implementation and zero-generation preflight may proceed, but no pilot call may occur until a new immutable snapshot manifest passes the 95% gate and every other lock/preflight condition passes.
