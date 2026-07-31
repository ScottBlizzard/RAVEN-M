# Protocol v2.2 r59 H01 Candidate Smoke — Binding and Semantics Fail

## Decision

r59 is frozen as a failed, non-scored development smoke. The environment and
five-click execution were healthy, but the verified ledger bound to the wrong
Chrome control and encoded the task's number sequence incorrectly. No formal
Gate-F run is authorized.

## What happened

At step 3, the ledger treated Chrome's setup button `Accept & continue` as the
task's repeated button. The task says “the button” and mentions Chrome, so the
r58 generic role-plus-package rule was too broad for initializing persistent
progress. The ledger was fixed to tap `(0.5, 0.915)` with count `1/5`.

When the actual task page appeared, its load-time value was `6`. Because the
incorrect ledger still had one unfilled operand slot, it captured that `6`.
The real `Click Me` control at `(0.5, 0.208)` then executed five times at steps
9–13, including both bounded fourth/fifth overrides, but none advanced the
ledger because its action key differed. At step 14 the model proposed a sixth
click twice; the ordinary loop guard blocked both, no sixth click executed,
and the smoke stopped with `MODEL_OUTPUT_INVALID_AFTER_REPAIR`.

## Ground-truth task semantics

The AndroidWorld implementation resolves an important off-by-one ambiguity:

1. `generateNumber()` runs once on page load.
2. Clicks 1–4 each generate the next value.
3. Click 5 generates no number; it hides the number/button and reveals the
   answer form.

The screenshots and source therefore agree on:

- load: `6`
- click 1: `2`
- click 2: `3`
- click 3: `9`
- click 4: `10`
- click 5: answer form

The correct operands are `6, 2, 3, 9, 10`, and their product is **3240**.

This also corrects the causal interpretation in the immutable r58 audit, which
described `2, 3, 9, 10, 10` and product `5400`. The r58 raw files, failed
status, and formal-run boundary remain unchanged; r59 records the correction
without rewriting history.

## Bounded next direction

The next candidate must use a two-axis state machine:

- bind a numeric repeat ledger only when the proposed control and exactly one
  numeric value coexist on the task UI;
- create the ledger only after that target action actually executes;
- retain the pre-action value as operand 1;
- collect at most one new value for each of clicks 1–4;
- track five executed clicks separately from five collected operands;
- accept click 5 as completion even though the numeric label disappears;
- expose the deterministic product only for post-repeat input when both axes
  are complete.

Chrome setup buttons without a task numeric value must be explicit negative
tests. Missing or duplicated numbers must never be backfilled.

## Evidence

Principal hashes:

- checkpoint/progress/summary:
  `7f6c9a3fe8386490d9667cf215bb8625e6ea56b96fa67962fc62cc5927d1acb0`
- episode:
  `4ecf3a695bff7d857384b55ad70edd595c574f1a8bb333323f7d78cabaa73a92`
- events:
  `932c3059968523e44370fbfc89e79809f2ff16e188006e85de7186ab20613603`
- AndroidWorld browser task source:
  `01a50bdc144f6b13556553b4159039f8f6e1bccb233d0637ca3770924434f85d`

The complete audit is in
`reports/protocol_v2_2_r59_h01_candidate_smoke_stopped.json`.

