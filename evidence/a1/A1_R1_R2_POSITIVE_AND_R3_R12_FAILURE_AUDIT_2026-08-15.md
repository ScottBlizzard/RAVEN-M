# A1 Vertical Reset Audit: R1/R2 Evidence and R3–R12 Failure Lineage

Date: 2026-08-15 (Asia/Hong_Kong)

Repository: <https://github.com/ScottBlizzard/RAVEN-M>

Branch: `a2-verified-progress-audit-20260810`

## Executive conclusion

The next vertical design must restart from the frozen A1-R2 implementation and evidence. It must not inherit the A1-R3–R12 implementation chain.

A1-R2 is the only successful vertical successor so far: it completed the same 19-task suite at 6/19 and reward 6.5, preserved all five A1 full successes, added `OsmAndMarker`, reduced tokens and elapsed time relative to A1, and had zero paired losses. Its strict cost verdict failed only because calls equaled A1 rather than falling below it, and its memory causality remains unproven without a matched ablation.

By contrast, every arm from A1-R3 through A1-R12 failed the first frozen capability task, `ExpenseDeleteMultiple2`, with one scientifically valid reward-0 episode. Because the fail-fast gate worked, none ran another task. The correct notation is therefore ten separate **0/1 gate failures**, not ten 0/19 results.

This is not strong evidence that the R2 direction is exhausted. R3–R12 formed a highly dependent serial patch lineage: R3 failed before its new lifecycle activated; R4 repaired writer activation but became a new regressed base; R5–R12 then accumulated changes on that base and increasingly optimized against one Expense trajectory. The sequence diagnoses our design process more strongly than it diagnoses the full space of memory mechanisms.

## Stable positive reference

| Arm | Full successes | Reward | Calls | Executed actions | Total tokens | Elapsed |
|---|---:|---:|---:|---:|---:|---:|
| A0 | 4/19 | 4.5 | 329 | 316 | 1,273,361 | 6,541.82 s |
| A1 | 5/19 | 5.5 | 603 | 596 | 3,464,267 | 14,595.49 s |
| A1-R2 | **6/19** | **6.5** | 603 | 595 | **2,685,730** | **11,230.18 s** |

A1-R2 versus A1: one win, zero losses, eighteen ties; −778,537 total tokens; −3,365.31 valid seconds; calls unchanged. All six successful R2 episodes had committed nonempty reads, but this is activation evidence, not causal proof.

The six R2 successes that a successor must preserve are:

1. `ExpenseDeleteMultiple2`
2. `RetroSavePlaylist`
3. `SimpleCalendarAddOneEvent`
4. `SportsTrackerTotalDurationForCategoryThisWeek`
5. `RecipeDeleteMultipleRecipesWithConstraint`
6. `OsmAndMarker`

### What R2 actually changed

R2 retained one compact latest `verified + pending` ledger, removed redundant `observed`, and stripped the structured `MEMORY[...]` prefix from ordinary action history so the same state was not stored twice. It added no model call, planner, verifier, guard, action override, forced termination, hidden UI, or evaluator access.

### What remains unknown about R2

- The added `OsmAndMarker` success cannot yet be causally attributed to memory because no matched read-disabled run exists.
- R2 still made 603 executor calls and 436 nonempty reads.
- It recorded 130 same-state refreshes, including long failed episodes with repeated pending prose.
- A later live run can regress even when an offline replay predicts exposure; writer compliance and stochastic policy behavior are not guaranteed by replay.

## R1 is a warning, not the positive base

A1-R1 BPR-v2 failed the first task at 0/1: reward 0, 15 calls, 14 actions, 57,689 tokens. It accepted one bounded receipt and produced one read, but outcome causality was not established. Therefore “restart from R1/R2” must mean audit R1's boundedness ideas while using **R2**, not R1, as the executable parent.

Useful R1 ideas may be reconsidered only if cross-trace evidence supports them: explicit bounded state, expiry, one-copy injection, and confirmation semantics. Its exact mechanism must not be treated as a success prior.

## R3–R12 gate table

| Arm | Frozen intervention | Gate result | Calls | Tokens | Mechanism observation |
|---|---|---:|---:|---:|---|
| R3 SRPL | stale-resistant pending + failed-attempt fact | 0/1 | 34 | 132,775 | 0 valid prefixes, 0 writes, 0 reads; new lifecycle never executed |
| R4 WRPL | always-visible writer reminder | 0/1 | 34 | 134,776 | writer activated, but stale semantic state persisted across pages |
| R5 TIPL | invalidate ledger on material transition | 0/1 | 34 | 134,566 | removed stale page carry; immediate delete/confirm sub-obligation was lost |
| R6 GAPL | inject original requirements every read | 0/1 | 34 | 135,601 | goal retained; wrong spatial tap and weak recovery compliance remained |
| R7 GRPL | two-support same-action no-progress recovery | 0/1 | 34 | 135,717 | trigger missed because failure was a material two-route cycle |
| R8 RCRP | strict ABAB route recurrence | 0/1 | 34 | 134,937 | exact detector had zero exposure on run-length-expanded recurrence |
| R9 RLCR | run-length cycle detector | 0/1 | 34 | 136,442 | detector fired and recovery was injected three times; policy did not change productively |
| R10 PACP | static full-screen coordinate calibration | 0/1 | 34 | 139,172 | 32 calibration reads; reward unchanged and early navigation worsened |
| R11 CSCP | explicit percentage-to-grid self-check | 0/1 | 34 | 141,660 | 34 injections, 10 explicit self-check thoughts, one item deleted; full task failed |
| R12 CHP | consecutive ordinary-history deduplication | 0/1 | 34 | 135,473 | removed 174 duplicate entries and cut 4.37% tokens versus R11; reward unchanged |

## What went wrong in the research process

### 1. We did not reset after the first invalid diagnostic base

R3's proposed lifecycle was not tested because the inherited model-authored prefix contract failed on all 34 actions. The proper response was to return to R2 and redesign the writer boundary. Instead, R4 added an always-visible reminder, and every later arm inherited the resulting prompt distribution.

### 2. We accumulated interventions instead of preserving R2

R5 inherited R4; R6 inherited R5; this continued through R12. A later result therefore tested the whole accumulated stack, not a clean single difference from the successful R2 parent. The line became progressively harder to attribute.

### 3. We overfit successive designs to one failure trajectory

R6–R12 were largely motivated by what happened on the immediately preceding `ExpenseDeleteMultiple2` episode: wrong coordinates, stationary repeats, route recurrence, calibration, then history repetition. These are legitimate trace observations, but optimizing repeatedly against one known task is not a cross-suite memory design method.

### 4. We confused trigger repair with memory improvement

Several mechanisms were dormant because their trigger definition was too narrow. Widening a trigger only established exposure. R9 then showed the deeper problem: even correctly detected and injected recovery evidence did not produce a productive policy divergence.

### 5. We made the prompt increasingly directive and expensive

The later arms injected writer reminders, full goals, recovery instructions, and calibration prose. This moved away from R2's successful compactness. R12 reduced duplicate history cost, but it still inherited the accumulated prompt stack.

### 6. We did not use the full R2 corpus to select the next defect

The next design question should have been: which failure mode is repeated across several of the 13 failed R2 tasks without harming the six R2 successes? Instead, most choices were based on one gate episode. This is the central design error.

## What the negative chain nevertheless taught us

- Model-authored memory syntax is a fragile runtime dependency.
- Current visible state must dominate stale semantic memory.
- Repeated nonempty reads do not imply behavior change.
- A detected loop plus recovery prose can be behaviorally inert.
- Coordinate self-checks can improve individual taps without solving workflow completion.
- Exact history compaction can reduce cost without increasing capability.
- Fail-fast gating saved nine unnecessary 18-task continuations.

These findings should constrain the redesign, not become components that are automatically inherited.

## Clean R3-v2 reset requirements

The historical `A1-R3 SRPL` identity, code, protocol, and evidence remain immutable. A new design must use a new identity such as `A1-R3-v2` or another explicitly prospective name.

The redesign must:

1. start from the exact frozen A1-R2 code and config, not R3–R12;
2. audit all 19 R2 episodes before selecting a mechanism;
3. quantify at least three cross-task failure patterns and their prevalence in R2 successes versus failures;
4. choose one minimal intervention supported across tasks, not an Expense-specific patch;
5. preserve R2 behavior by default, with the new path sparse and fail-closed;
6. avoid always-on writer reminders, full-goal repetition, coordinate tutorials, task/app rules, and cumulative recovery stacks;
7. add zero model calls, no planner/critic/verifier, no hidden UI/evaluator, no action override, and no extra screenshot unless a separate non-memory system is explicitly preregistered later;
8. freeze exact state, update, read, expiry, capacity, renderer, token budget, and trigger rules before live generation;
9. provide offline exposure evidence on multiple R2 tasks without using replay reward as a runtime signal;
10. pass the six R2-success tasks in their fixed order before releasing the other thirteen;
11. separate system accuracy, cost, and mechanism-causal verdicts;
12. include a minimal matched read-disabled or content ablation sufficient to test whether the memory text, rather than stochastic rerun, caused a gain.

## Advancement criteria

- Capability preservation: 6/6 on the six R2 successes, no scientific rerun.
- Full-suite accuracy: strictly greater than 6/19 and reward strictly greater than 6.5, with no loss on the six R2 successes.
- Cost: executor calls no greater than 603, total tokens below 2,685,730, and valid elapsed time below 11,230.18 s. Report each separately; cost cannot substitute for accuracy.
- Mechanism evidence: preregistered productive reads with exact write→read→injected text→next action→visible progress linkage, plus a matched ablation. A silent success is not attributed to memory.

If a Pro audit concludes that no pure-memory change is supported by the R2 corpus, it must say so rather than manufacture a complex mechanism. The correct fallback is to preserve R2 as the best A-class result and open a separately preregistered composite-system track.

## Authoritative evidence

- `evidence/a1r1_v2/A1R1_BPR_V2_PRIMARY_GATE_RESULT_2026-08-14.md`
- `evidence/a1r2/A1R2_CVP_SCORED_RESULT_2026-08-14.md`
- `evidence/a1r3/A1R3_SRPL_PRIMARY_GATE_RESULT_2026-08-15.md`
- `evidence/a1r4/` through `evidence/a1r12/` primary gate results
- `evidence/a1/A1_VERTICAL_ITERATION_R4_R12_SYNTHESIS_2026-08-15.md`
- frozen protocols and implementations for each arm under `protocols/` and `implementation/`

No historical result is rewritten by this audit.
