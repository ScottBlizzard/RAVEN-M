# Protocol v2.2 r58 Candidate Addendum

## Status and scope

r58 is a local candidate derived from the immutable failed r57 H01 development
smoke. It changes only the task-bounded repeated-tap evidence path. It does not
alter the frozen Hard task set, seeds, variants, prompts, budgets, pairing,
native evaluator, batch isolation, or formal acceptance criteria.

r57 remains a failed, non-scored development result and may not be resumed,
relabelled, or included in formal statistics.

## Observed incompatibility

In r57 H01, the first `Click Me` activation changed the rendered page from
value `6` to a temporary blank. The immediate accessibility snapshot retained
the old semantic hash, while the next fresh pre-action snapshot exposed value
`2` and a new semantic hash. r57 retained one no-effect count despite this
delayed semantic convergence and therefore denied the fourth requested tap.

## r58 delayed-progress reconciliation

One previously recorded no-effect may be reconciled only if every condition
below is true:

1. the proposed action is a tap at the exact coordinate of the immediately
   preceding coordinate action;
2. the immediately preceding transition recorded identical before/after
   semantic hashes;
3. the current fresh pre-action semantic hash differs from that recorded
   after-action hash;
4. the prior action fingerprint has not already been blocked;
5. the current UI exposes no visible failure;
6. the tap hits exactly one labelled, visible, enabled, clickable,
   non-editable, non-commit control;
7. the goal explicitly requests a finite count from 2 through 20;
8. the control is task-bound either by an explicit target-label match or by a
   button-role plus application-name match between the control package and the
   task text;
9. the proposed ordinal does not exceed the requested count.

The reconciliation removes one stale identical-coordinate no-effect count and
one corresponding unblocked fingerprint count. It records the raw state,
effective state, current semantic hash, previous semantic hashes, control
binding, and action in the episode audit.

## Preserved denials

r58 does not reconcile or override:

- pixel-only change without a new semantic state;
- a current visible failure or infrastructure-failure state;
- a blocked prior fingerprint;
- a different coordinate or a non-tap action;
- an ambiguous, unnamed, disabled, invisible, editable, system-UI, keyboard,
  or commit-like control;
- an unrelated app-level button such as Android's `Just once`;
- a generic repeated-button instruction lacking both label and application
  grounding;
- an ordinal beyond the task's finite count;
- a fingerprint block, visible-failure block, or A-B-cycle block that remains
  active after reconciliation.

## Validation and launch boundary

Required local evidence before another live smoke:

- focused guard/controller tests for the exact delayed-DOM trace;
- negative tests for every preserved denial above;
- complete project test suite;
- protocol-v1 breadth seal verification;
- clean diff and compilation;
- zero-call model/emulator health check;
- a fresh candidate commit, tag, freeze manifest, and preflight report.

Passing local validation alone does not authorize a formal Gate-F rerun. At
most one new H01/B3 development smoke may be proposed after its own zero-call
preflight; it must remain under `runs/protocol_v2_2_development/` and be marked
`development_smoke=true`, `formal_scoring=false`.

