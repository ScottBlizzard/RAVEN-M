# Protocol v2.2 r58 H01 Candidate Smoke — Mechanism Pass, Task Fail

## Decision

r58 is frozen as a failed, non-scored development smoke. Its guard mechanism
worked exactly as intended, but H01 did not finish, so no formal Gate-F run is
authorized.

## What passed

- Android's unrelated `Just once` button was not task-bound.
- One delayed DOM transition was reconciled: raw no-effect `1`, effective
  no-effect `0`.
- The fourth requested tap executed with override count `1`.
- The fifth requested tap executed with override count `2`.
- All five taps changed the eventual semantic state.
- A proposed sixth tap was rejected twice and never executed.
- No A-B cycle, visible-failure bypass, blocked-action execution, or reset
  error occurred.

Thus the narrow r58 mechanism passed live validation.

## Why the task still failed

The five displayed results were:

`2, 3, 9, 10, 10`

Their product is `5400`. After the fifth click, however, B3 proposed a sixth
click. The repair response was byte-identical and was rejected again.

The cause is a verified memory-lifecycle failure:

1. B3 refreshes its summary every five executed actions.
2. It refreshed after the first button click and recorded “clicked once,
   showing 2; click four more times.”
3. It did not refresh during clicks 2–5.
4. Its recent window retains only two screenshots, so values `3` and `9`
   disappeared from the active context.
5. At the next decision, the stale summary still claimed four clicks remained.

The safety guard correctly knew that 5/5 actions had executed, but that verified
fact was not exposed to the planner. This is direct evidence for the project's
reliability thesis: a stale summary must not outrank a verified execution
ledger.

## Bounded next direction

The next candidate should preserve r58 unchanged and add a small verified
repeat-progress ledger for task-grounded numeric collection:

- count only taps that actually reach `observe_transition`;
- collect a numeric operand only when exactly one visible, non-clickable,
  non-editable numeric element exists in the task-bound application;
- expose `executed/requested` plus collected operands before the next planner
  call;
- explicitly mark the ledger as newer and more authoritative than conflicting
  summary memory;
- at 5/5, forbid another repeat and require transition to deterministic
  calculation and form input.

Ambiguous or missing numeric evidence must remain absent rather than guessed.
r58's directory is immutable and may not be resumed or relabelled.

## Evidence

Principal hashes:

- checkpoint/progress/summary:
  `1e94814cc3addba8949d96699395988c9bcd9406de6028525dce0a8d1cb0a473`
- episode:
  `bc92e5cea160455db17f292caa417130a41ce6164d6e6d81536647b520452958`
- events:
  `be9e3d61f0d8e014b31f8273a98e397dd038d44e52fdb64581d703ac62608a75`

The complete audit is in
`reports/protocol_v2_2_r58_h01_candidate_smoke_stopped.json`.

