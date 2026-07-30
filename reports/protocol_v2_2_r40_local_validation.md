# Protocol-v2.2 r40 local validation

Status: **PASS locally; live development smoke pending**

Parent commit:
`d28ac9a1ec6088a0a16f85d0c92c8c7b6d8b3623`

## Implemented

The r39 Expense-M0 diagnosis produced two generic repairs:

1. a repeated same-action/no-effect failure now supersedes the immediately
   preceding, action-linked, zero-confirmation progress/page hypothesis;
2. protocol v2 rejects an explicitly directed swipe when its canonical
   coordinate displacement points in another direction.

The first repair preserves both records and the supersession edge in the
append-only log, but removes the falsified hypothesis from active retrieval.
It does not revoke independent visible facts. The second repair runs before
execution, consumes the existing single repair allowance, and never rewrites
coordinates. Protocol v1 remains isolated.

## Local evidence

- 338 tests collected and 338 passed.
- `compileall` passed.
- `git diff --check` passed.
- The protocol-v1 breadth seal verified 197 files with 0 failures.
- The controller-level fixture proves that a declared-left/actual-up proposal
  is rejected and repaired into an actual left swipe in exactly two model
  calls.
- The memory fixture proves that the causal hypothesis is superseded, the
  deterministic failure remains ALERT, the supersession event replays, and an
  independent visible fact is not superseded.

## Historical trajectory audit

The guard was applied offline to all 1,042 recorded swipe actions under
`runs/`. It adjudicated only the 204 summaries that explicitly stated a
direction. Exactly two proposals were mismatches, and both were the retained
r39 Expense-M0 actions that said “swiping left” while executing an upward
gesture. No other recorded swipe was rejected.

This is a retrospective compatibility check, not scored evidence.

## Integrity and evidence boundary

The immutable r39 suite files still have their recorded hashes:

- suite summary:
  `fcb3e9880448f0423ce8459a5d8e91e78b453c802e682d82ea1af317f5ff68b9`;
- manifest snapshot:
  `0ae96dd85e0eb9aa059ccb4627f1ee42ec843b99d91bf04dcb47b6ce9a7e86e0`;
- instances snapshot:
  `13d6ab543008b94d38e789105210d7fc56eb2eec7f66ed498f7113c910ae79b5`.

No server/GPU experiment was used for this validation. The next admissible
step is one fresh, non-scored paired Expense smoke under a new candidate
commit. A passing smoke would authorize Gate-D preparation only; it would not
be a formal result or a method-superiority claim.
