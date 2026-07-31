# Protocol v2.2 r59 Candidate Addendum

## Status and motivation

r59 is a local candidate derived from the immutable r58 H01 development smoke.
r58's delayed-progress reconciliation, task-control binding, fourth/fifth-tap
overrides, and sixth-tap ceiling all passed live validation. The episode failed
because B3's periodic summary remained stale while its two-frame recent window
lost earlier numeric operands.

r59 addresses that memory-authority failure. It does not change the frozen
tasks, seeds, variants, prompts, action budgets, evaluator, pairing, batch
isolation, or formal acceptance criteria.

## Verified repeat-progress ledger

The ledger may start only after an actually executed tap carries a validated
finite-repeat assessment bound to one task control. Its count advances only
inside `observe_transition`; a proposed, rejected, repaired, or merely planned
tap cannot advance it.

The ledger records:

- exact canonical action and task-bound control labels/packages;
- requested and actually executed counts;
- completion state;
- each accepted operand with ordinal and fresh semantic-state hash;
- whether all operands are present;
- a deterministic calculation only after the operand set is complete.

## Numeric evidence boundary

An operand is accepted only when:

1. the goal explicitly connects displayed numbers/values to a product, sum,
   average, multiply, or total operation;
2. the repeat ledger already proves that an ordinal executed;
3. the fresh semantic UI exposes exactly one pure numeric label;
4. that label belongs to the task-bound application package;
5. its element is visible, non-clickable, and non-editable.

Clickable numbers, editable fields, another application/package, multiple
numeric candidates, non-numeric text, or a missing label yield no operand.
Repeated equal values are retained as different verified ordinals rather than
deduplicated.

For a complete product task, the ledger multiplies the exact decimal operands
deterministically and records the result with
`text_origin=deterministic_calculation`.

## Memory precedence and count completion

Before every v2.2 planner call, the controller exposes the current verified
ledger. It explicitly states that executed-action and fresh semantic evidence
is newer and more authoritative than conflicting periodic summaries or recent
entry wording.

When the executed count equals the task's requested count:

- another exact task-bound repeat is rejected with
  `TASK_REPEAT_COUNT_COMPLETE`;
- the rejection contains the full verified ledger;
- the bounded repair must transition to the pending post-repeat subtask;
- if a complete deterministic calculation and matching visible input exist,
  the exact result may be typed with deterministic-calculation provenance;
- missing operands may not be guessed.

## Preserved boundaries

r59 preserves every r58 denial, including unrelated controls, ambiguous target
hits, commit controls, visible failures, blocked fingerprints, pixel-only
changes, A-B cycles, count overflow, and the ban on executing blocked actions.
The ledger never authorizes an additional repeat and never converts an
unverified visual guess into a fact.

## Validation and launch boundary

Before another live H01 smoke, r59 requires:

- focused ledger, stale-summary precedence, complete-count repair, and numeric
  ambiguity tests;
- complete project tests;
- protocol-v1 breadth-seal verification;
- exact source commit/tag and freeze hashes;
- a separate r59 wrapper and zero-call preflight.

Local success alone does not authorize formal Gate F. At most one H01/B3
development smoke may be considered after its exact preflight, and it must
remain non-scored and isolated under `runs/protocol_v2_2_development/`.

