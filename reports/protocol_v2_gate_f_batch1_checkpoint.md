# Protocol-v2 Gate F batch-1 checkpoint

Date: 2026-07-27  
Freeze: `protocol-v2-gate-f-freeze` at
`5bc6292480eb56ddb0213294ccc5629f1ffd3bf8`  
Decision: **diagnostic pause; batch 2 is not authorized**

## Outcome

Batch 1 completed all four frozen cells in 3,359.844 active seconds
(55 minutes 59.844 seconds). All four are valid scored episodes, but none
passed the native AndroidWorld evaluator.

| Seq. | Variant | Task | Result | Termination | Calls | Wall time | Max prompt |
|---:|---|---|---|---|---:|---:|---:|
| 1 | B3 | `BrowserMultiply` | fail | max steps | 26 | 559.7 s | 4,284 |
| 2 | M0 | `SportsTrackerActivitiesOnDate` | fail | incorrect answer | 13 | 248.3 s | 4,540 |
| 3 | B3 | `ExpenseAddMultipleFromMarkor` | fail | max steps | 74 | 1,529.8 s | 5,248 |
| 4 | M0 | `SimpleCalendarAddOneEvent` | fail | max steps | 46 | 901.0 s | 6,033 |

The projected twelve-cell active time is 8,363.17 seconds (139.4 minutes),
below the frozen 210-minute cap. The current M0/B3 mean model-call ratio is
0.59 and the wall-time ratio is 0.55, both within their frozen limits.

## Automatic protocol audits

The four episodes have:

- exact frozen instance hashes and no pairing error;
- zero invalid outputs after bounded repair;
- zero provenance, memory-isolation, or evaluator-leakage findings;
- zero reset or teardown findings;
- zero context-cap findings;
- no exact pixel-identical third no-effect action;
- one normal M0 answer termination with a 1/1 interaction-cache match.

The H17 answer channel was therefore correct even though its content was
wrong: the expected activity type was `swimming`, while the model answered
`Bicycle`.

## Manual semantic-progress audit

The automatic pixel-hash loop criterion is insufficient on these Hard
episodes:

- H01 steps 9–21 oscillated among Chrome recovery and sync prompts and never
  reached the task page.
- H03 steps 45–51 repeatedly scrolled, then steps 52–59 repeatedly reopened
  the same Markor file instead of entering the two reimbursable expenses.
- H16 steps 19–33 repeated the identical save tap fifteen times. The form
  visibly showed an invalid end time (`00:30` after an `08:00` start) and the
  toast “The event cannot end earlier than it starts.”

Clock changes, toast animation, and other transient pixels changed screenshot
hashes, so the exact-image guard counted these as progress. This is a generic
reliability defect, not a reason to tune a task-specific prompt.

## Infrastructure note

The first launch produced no episode and no scored result. Initial AndroidEnv
construction failed while reinstalling the accessibility APK. A project-only
emulator cold restart followed by a load-reset-close smoke test recovered the
environment, after which the full scored batch ran without an infrastructure
retry.

That invalid launch is preserved in the local runtime log, but the current
runner reports zero infrastructure attempts because initial environment
construction occurs before its attempt recorder. This accounting gap should
also be repaired generically.

## Decision and next gate

Batch 2 must not be launched unchanged. The next implementation round should:

1. detect semantic no-progress using a normalized UI/accessibility digest
   that excludes clocks and transient toast animation;
2. require a different recovery action after repeated commit/navigation
   attempts on the same semantic state;
3. turn visible validation errors into typed failure records that prevent the
   same action from being repeated without changing the invalid field;
4. record and recover initial environment-construction failures;
5. add generic regression fixtures from these trajectories;
6. rerun Gates D and E, then restart Gate F from batch 1 under a new frozen
   protocol version rather than mixing revised and unrevised cells.

This checkpoint is not a final Gate-F failure because only 4/12 cells ran.
It is a deliberate human checkpoint showing that continuing unchanged would
spend compute on a known reliability blind spot.
