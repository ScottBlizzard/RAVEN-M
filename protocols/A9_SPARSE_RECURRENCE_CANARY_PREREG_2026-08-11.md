# A9 Sparse Recurrence Canary — frozen preregistration

Date: 2026-08-11
Status: integrated and zero-generation qualified; never empirically run
Arm: `A9_SPARSE_RECURRENCE_CANARY_QWEN3VL32B_AW_HARD_S20260806_V1`

## 1. Motivation and contrast

A1 showed that persistent pending-work memory can add a success, but it also prolonged several wrong loops. A2's strict repeated-action guard rarely fired because long navigation loops can change pages. A3 and A5 depended on extra model-authored formats and usually failed to activate. A6 injected recent transitions on almost every step and duplicated ordinary history, producing 0/19. A7 was cheaper but its goal parser often remained inactive.

A9 therefore does not summarize every step and does not ask the model to author memory. It targets only three directly observed recurrence patterns: repeated text/query entry, repeated clear-and-reentry, and an exact visible-screen navigation cycle. It is a sparse diagnostic intervention, not a planner, critic, semantic verifier, or action guard.

## 2. Frozen causal hypothesis

When Qwen returns to the same visible route or re-enters the same text, a short one-shot recurrence fact may cause it to reconsider the route before history grows into a long loop. Because ordinary steps receive no memory text, A9 should preserve A0 behavior better than always-on A1/A6 memories. A positive mechanism result requires both canary delivery and a downstream behavioral divergence; activation alone is not task effectiveness.

## 3. Mechanism invariants

1. Episode-local state only; no cross-task donor or prior result.
2. Inputs are limited to executed canonical action, the policy's own action prose, response receipt hash, and exact RGB pixels visible to the policy before and after the action.
3. Evaluator reward, database state, accessibility tree, foreground package/activity, hidden UI metadata, and future frames are never read for writing or retrieval.
4. No extra model call, model-authored memory prefix, history rewrite, action repair, action rejection, or action override.
5. A canary states recurrence only. It never claims failure, correctness, semantic progress, or completion.
6. Normal reads are empty. Each recurrence signature is injected once per episode.
7. Pixel matching is exact after cropping the top and bottom 4%; near-match and learned similarity are disabled.

## 4. Frozen write rules

After every executed action, deterministically append the exact visible destination fingerprint to a bounded screen trace.

- `QUERY_REENTRY`: normalize whitespace and case in a non-empty `type_text` value. Fire when the same value appears exactly twice within 12 steps.
- `QUERY_CLEAR_REENTRY`: the query condition above plus canonical `clear_text=true`, or the policy action prose explicitly describing clearing a text/search/query/input field within the preceding two steps.
- `STATIONARY_SCREEN`: fire when three consecutive screen observations have the same exact fingerprint, corresponding to two executed transitions.
- `NAVIGATION_CYCLE_P2/P3`: fire when an exact fingerprint sequence of period two or three occurs twice as the current suffix.

The first event for a signature is retained; later occurrences of that signature do not create another prompt message.

## 5. Frozen read rules and capacity

The next read pops at most one pending event and renders at most 280 characters. Pending capacity is 2; event audit capacity is 16. The trace holds 13 screens. At most 8 distinct normalized text keys and 4 recent occurrences per key are retained. Query occurrences older than 12 steps cannot activate a canary.

The rendered text asks the policy to reassess the currently visible route, but specifies no replacement action. An empty queue produces exactly an empty memory string.

## 6. Activation and effect evidence

For every read/write, log the event kind, source/evidence steps, exact evidence hash, rendered hash, bounded state sizes, and cumulative counters. The activation canary is satisfied only by a non-empty read whose `activation_canary=true`. Mechanism activity is not equivalent to evaluator success.

Behavioral influence should later be audited at the first post-canary action: compare whether the next canonical action continues the identified recurrence signature. Evaluator reward remains end-of-episode evidence only.

## 7. Capability gate and stopping

Run the four paired A0 successes first: `ExpenseDeleteMultiple2`, `RetroSavePlaylist`, `SimpleCalendarAddOneEvent`, and `SportsTrackerTotalDurationForCategoryThisWeek`. A9 must score 4/4 before any remaining task is released. A scientific failure is terminal and is not rerun. Only a documented infrastructure-invalid episode may resume the same task.

## 8. Required pre-run tests

- dormant read before any canary;
- same-query activation and one-shot retrieval;
- clear/re-entry classification;
- exact stationary and period-two navigation-cycle activation;
- no activation for distinct queries or non-repeating routes;
- bounded capacities and rendered length;
- hidden metadata/evaluator perturbations leave decisions unchanged;
- audit states zero added calls, no guard, no override, and recurrence-only claims.

## 9. Integration point

The standalone class is `SparseRecurrenceCanaryMemory` in `implementation/src/raven_m/official_qwen_mobile/a9_recurrence_memory.py`. It is integrated in the runner's per-episode memory factory as arm `a9`, included in the CLI/contract allow-list and source freeze, and reuses the existing controller `read(context=...)` / `observe_step(...)` interface. A fresh live receipt remains mandatory before any generation.
