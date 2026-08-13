# Component Evidence Ledger for Post-Memory Composite Research

Date: 2026-08-13 (Asia/Hong_Kong)

Status: design input only; no composite arm has been implemented or scored.

This ledger supports seven independent GPT Pro design studies. It does not
authorize combining all seven components into one arm, and it does not change
the status of any A-series experiment.

## Fixed empirical boundary

All full-suite results below use the same 19 AndroidWorld Hard instances and
task seed `20260806`.

| Evidence | Result | Calls | Tokens | Interpretation |
|---|---:|---:|---:|---|
| A0 official baseline | 4/19 | 329 | 1,273,361 | frozen paired baseline |
| A1 Action Working Memory | 5/19 | 603 | 3,464,267 | one gain, no loss, but much higher cost |
| A2 compound verified-progress arm | 0/19 | 705 | 3,170,413 | complete negative compound control |
| A6 short episodic memory | 0/19 | 628 | 2,674,422 | complete negative always-on memory control |
| A7 goal-item ledger | 4/19 | not used as a pristine cost comparison | not used as a pristine cost comparison | transparent stitched 19-task control |

A1's only paired gain was
`RecipeDeleteMultipleRecipesWithConstraint`. Its defensible primitive is
bookkeeping for an operation that remains unconfirmed. Its observed liabilities
are stale pending records, loop reinforcement, and duplicated `MEMORY[...]`
content in ordinary history plus the injected block.

The remaining evidence levels must not be flattened into equivalent results:

- A3, A4, and A5 stopped after the first capability-gate failure. A4 replayed
  one weak donor on every step; A5 never produced a compliant graph write.
- A6 completed 19 tasks at 0/19. It wrote on nearly every step and often replayed
  low-information transitions.
- A7 is 19/19 infrastructure-valid and 4/19 successful, but is stitched across
  an original run and a later amendment. Some successes occurred while its
  ledger was inactive.
- A8-v2 failed its first Expense gate with 14 reads. A9 passed Expense while
  silent, then failed Retro with three reads.
- A10-v1, A10-v2, and A11 failed formal offline qualification. They are not
  successful prospective arms.
- A12 is formally `A12_PROTOCOL_INVALID`; independent replay found only 11/23
  actually qualifying reference segments, below its required 20/23.
- The A10-v2/A11/A12 enriched six-task runs are post-hoc diagnostics, not
  held-out evaluation and not repairs of their formal status. A10-v2 scored
  2/6 with six reads, A11 2/6 with four reads, and A12 1/6 with three reads.
  All had zero productive-divergence signals; all their successes were
  memory-silent.

## Reusable primitives and their evidence strength

| Primitive | Source | Permitted role in a new study | Evidence strength |
|---|---|---|---|
| pending/unconfirmed operation receipt | A1 | minimal state supplied to a decision policy | one paired gain, but not isolated causally |
| action-to-visible-transition outcome | A2/A6 | update signal or audit feature; normally silent | directly observable, no accuracy gain |
| goal item and constraint ledger | A7 | unresolved-item representation; never a completion oracle | representation worked mechanically; benefit unproven |
| sparse recurrence detection | A8/A9 | trigger for another component | activation demonstrated; benefit unproven |
| post-intervention divergence/progress/relapse audit | A12 diagnostic tooling | causal measurement only | useful audit concept; A12 policy itself invalid |
| exact repeated-no-progress guard | A2 | separately identified safety/cost intervention | not memory intelligence; A2 compound result negative |
| obligation parsing / multi-support confirmation | A10/A11 | offline feature candidate only | formal replay failed; no live benefit evidence |
| donor workflow bank | A4 | frozen retrieval source only after leakage and relevance controls | first implementation failed; direct weak-donor injection prohibited |

## Patterns that must not be inherited as if they were successes

- Always-on prose injection or storing the same memory in ordinary history and
  a second memory block.
- Treating pixel change as task progress or task completion.
- Requiring the policy model to emit a fragile auxiliary syntax.
- Injecting a donor merely because it is available.
- Complex frontier, route, score, and maturity state machines without a direct
  observed failure that requires each field.
- Counting writes, non-empty reads, action changes, shorter failures, or
  successful memory-silent episodes as evidence of component benefit.
- Using task names, application whitelists, hidden UI state, evaluator reward,
  future frames, or post-hoc task-specific thresholds in runtime decisions.

## Seven independent design tracks

These are `SYS-*` design tracks, not registered A13-A19 arms. An arm identity is
assigned only after a proposal passes adjudication and zero-generation
qualification.

| Track | Single research question | New component under test |
|---|---|---|
| SYS-HMP | Can a visible-evidence-constrained milestone plan reduce long-horizon drift? | bounded hierarchical planner/replanner |
| SYS-VOV | Can an independent visible-outcome verifier prevent unconfirmed continuation and false completion? | post-action visual verifier |
| SYS-TRC | Can sparse stagnation evidence justify a useful recovery critique? | triggered critic |
| SYS-CAA | Can a judge select better actions at frozen high-uncertainty decision points? | candidate generation and arbitration |
| SYS-BTM | Can a zero-call trajectory monitor improve native action-budget allocation? | deterministic budget/progress monitor |
| SYS-EPHC | Can evidence-preserving compression lower context cost without losing commitments? | bounded history summarizer |
| SYS-FWRE | Can independently sourced successful workflows be retrieved and adapted without leakage? | frozen workflow retrieval executor |

These are seven separate prospective hypotheses. A Pro assigned one track must
not silently absorb another track's intervention. Cross-track combination is a
later factorial or staged study only after at least one component has positive
evidence.

## Common scientific contract for all seven design studies

1. Pin the repository commit supplied in the conversation and distinguish
   formal evidence, post-hoc diagnostics, inference, and unknowns.
2. Keep the official Qwen3-VL-32B model revision, AndroidWorld instances, task
   seed `20260806`, generation seed `3407`, sampling, action schema, native step
   limits, and evaluator unchanged unless the track explicitly studies an
   additional model call. Every extra call and token must be counted.
3. Never expose evaluator state, reward, hidden UI tree, activity/package,
   future screenshots, or task-name whitelists to a runtime component.
4. Freeze one design, not a menu. Every state field, threshold, call, and prompt
   token must answer a cited failure.
5. Separate implementation activation, behavioral effect, final reward, and
   resource cost. Success while the tested component is inactive is
   unattributed.
6. Include A0, Full, role-shadow, and one mechanism-specific ablation. A
   role-shadow uses the same trigger and auxiliary call but prevents its output
   from influencing the executor. For history compression, also include a
   token-matched mechanical compression control.
7. Use the ordered A0 preservation gate first: `ExpenseDeleteMultiple2`,
   `RetroSavePlaylist`, `SimpleCalendarAddOneEvent`, and
   `SportsTrackerTotalDurationForCategoryThisWeek`. Then run A1's unique gain,
   `RecipeDeleteMultipleRecipesWithConstraint`, before releasing the other 14.
8. A scientific failure is not rerun. Only a recorded infrastructure-invalid
   episode may be replaced on the same task.
9. Report accuracy, cost, and causal mechanism as independent conclusions.
   More than A1's 5/19 with no loss on A1's five successes is the primary
   accuracy target. Equal accuracy at materially lower cost is Pareto evidence,
   not an accuracy improvement.
10. All 19 seed-matched tasks have already been observed. The study is a matched
    prospective paired diagnostic, never a pristine held-out generalization.

Before any live call across the seven tracks, jointly freeze all component
boundaries, triggers, auxiliary-call caps, five-task gates, shadow controls, and
the 19-task order. Publish all seven outcomes, including gate failures. A
cross-track comparison with unequal resource budgets is an accuracy-cost Pareto
analysis, not an unconditional ranking. Combining two winning tracks requires a
new preregistered factorial arm; it cannot be presented as one of these seven.

## Required source reading

Start with `HANDOFF_2026-08-13.md`, the A0 and A1 result documents, A1 protocol
and implementation, `protocols/A345_FAILURE_FORENSICS_AND_SUCCESSOR_CONSTRAINTS_2026-08-11.md`,
the A7/A8/A9 evidence, the A10-v2/A11/A12 formal replay evidence, the enriched
six-task protocol and results, and the track-specific request. Raw runs are not
in Git; any claim requiring them must be marked as an information gap unless a
hash-bound derived audit is committed.
