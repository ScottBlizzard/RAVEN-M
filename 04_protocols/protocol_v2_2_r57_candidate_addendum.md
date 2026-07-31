# Protocol-v2.2 r57 development-candidate addendum

Date: 2026-07-31  
Parent formal result: r56 Gate F stopped at H01 B3  
Parent checkpoint SHA-256:
`c095b69e550c66c01fa5e75c5cc1aa29cce1d26868001716590868611297cda6`

## Motivation

The valid second H01 B3 attempt reached the local Chrome task and executed
three exact-coordinate taps on the visible `Click Me` button. The screen and
semantic UI changed after every tap, exposing values 2, 3, and 9. The task
explicitly requires five clicks on that same button.

At the fourth proposed tap, the generic coordinate-streak guard rejected both
the initial output and its one bounded repair solely because three identical
tap coordinates had already executed. Its diagnostic no-effect count was
zero, no A-B cycle had occurred, no visible failure appeared, and the
proposed coordinate remained on the task-required control.

The r56 task failure remains immutable. r57 addresses only the newly observed
task-interface incompatibility in a fresh development lineage.

## Trigger

r57 permits an exact repeated tap beyond the generic three-action ceiling only
when every condition below holds:

1. protocol-v2.2 is active;
2. TASK explicitly contains a finite request to click, tap, or press a
   control between two and twenty times;
3. the proposed action is `tap`;
4. its coordinate hits exactly one visible, enabled, clickable, labelled,
   noneditable control;
5. that control is outside System UI and the soft keyboard and is not
   commit-like;
6. every preceding action in the exact-coordinate streak produced semantic
   progress;
7. the proposed one-based ordinal does not exceed the task-requested count;
8. the caller-provided streak and no-effect counts exactly match the guard's
   internal counters; and
9. the current semantic-state/action fingerprint is not blocked.

The accepted assessment records the task-requested count, proposed ordinal,
control label and package, prior streak count, and no-effect count. An
override is recorded only for an action that would otherwise cross the
generic ceiling.

## Preserved boundaries

r57 does not:

- authorize a sixth tap when TASK requests five;
- infer a repeat count from model rationale, memory, or visual text;
- authorize a repeated tap when TASK has no finite count;
- authorize long-presses or swipes through this contract;
- authorize an ambiguous, unlabelled, editable, disabled, hidden, System UI,
  keyboard, or commit-like target;
- authorize a streak containing any no-effect transition;
- bypass a blocked fingerprint, A-B cycle, visible failure, exact-target,
  destination, provenance, field-role, or consequential-action guard;
- change r56's scored result, resume its stopped suite, or start Batch 2; or
- make a method-performance claim from the H01 counterfactual.

The generic three-action ceiling remains unchanged for every nonqualifying
tap and long-press.

## Validation requirement

Before any live model call, r57 must pass:

- exact fourth- and fifth-tap positives followed by a sixth-tap denial;
- no-count, no-effect, commit-control, ambiguous-control, and count-exceeded
  denials;
- an A-B cycle denial even when the task-count assessment otherwise passes;
- an integrated controller replay of the r56 H01 decision shape;
- confirmation that pre-v2.2 controller behavior remains unchanged;
- all protocol-v2 controller and runner tests;
- the complete local suite;
- `compileall` and `git diff --check`; and
- the unchanged 197-file protocol-v1 breadth seal.

A fresh exact-source zero-model-call preflight must then verify the model,
emulator, candidate hashes, parent Gate-E evidence, and an absent development
namespace. Only one isolated, explicitly non-scored H01 B3 development smoke
may follow. A smoke result cannot resume r56 Gate F or authorize a new formal
Gate F without fresh Gate-E requalification.
