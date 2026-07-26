# Frozen Hard breadth gate review

Date: 2026-07-26  
Suite: `hard_v1_breadth`  
Protocol: `androidworld_hard_protocol_v1`

## Gate decision

**Operational gate: PASS. Scientific continuation gate: HOLD for manual
review.**

The frozen breadth phase is complete and internally auditable.  All 95
scheduled cells have one valid scored result, all 19 task instances contain
the required five variants, and the rebuilt suite has zero episode-audit and
zero pairing errors.

The breadth outcome is nevertheless at the evaluator floor: only 1 of 95
episodes succeeded, while the proposed method M0 succeeded on 0 of 19 tasks.
The remaining 269 frozen cells must therefore not be started mechanically.
This is the manual review point required by the plan adjustment.

## Completion and integrity

| Check | Result |
|---|---:|
| Scheduled / completed cells | 95 / 95 |
| Valid scored episodes | 95 |
| Five-variant task pairs | 19 / 19 |
| Pairing invariant errors | 0 |
| Episode audit errors | 0 |
| Successful episodes | 1 / 95 (1.05%) |
| Model calls | 4,021 |
| Total tokens | 17,971,842 |
| Summed episode wall time | 22.01 h |
| Summed model latency | 13.22 h |
| First episode start | 2026-07-24 19:43 HKT |
| Last episode finish | 2026-07-26 19:44 HKT |

There were 11 invalid infrastructure attempts affecting eight cells: nine
model-unavailable events and two emulator-loss events.  These attempts were
excluded under the frozen retry rules.  The final scored-attempt distribution
was 87 first attempts, six second attempts, one third attempt, and one
authorized fifth attempt.  No infrastructure-invalid attempt was scored.

## Pairing metadata correction

The first completed summary reported one pairing error for
`H15-s20260720` (`SaveCopyOfReceiptTaskEval`).  Its five goals, seeds, file
names, image modes, image sizes, and remaining parameters were identical.
Only a PIL `ImagingCore` object's process-local memory address differed in the
serialized parameter metadata.

Protocol amendment `protocol-v1-hotfix-005` removed the runtime address only
for the derived parameter hash, retained every previous hash in the affected
records, and rebuilt both suite summaries.  It did not rerun an episode or
change any prompt, observation, action, reward, success label, failure code,
or scientific metric.  The correction is fixed at Git tag
`protocol-v1-hotfix-005` (commit `e65c8aa`) and passed the complete 86-test
suite.

## Outcome by variant

| Variant | Success | Mean calls | Mean tokens | Mean wall time |
|---|---:|---:|---:|---:|
| B0 | 0 / 19 | 35.53 | 127,873 | 10.84 min |
| B1 | 0 / 19 | 38.84 | 168,683 | 12.45 min |
| B2 | 1 / 19 | 35.95 | 193,415 | 12.04 min |
| B3 | 0 / 19 | 43.47 | 180,404 | 13.57 min |
| M0 | 0 / 19 | 57.84 | 275,511 | 20.61 min |

The sole success was B2 on `SimpleCalendarAddOneEvent`
(`H16-s20260720`).  Therefore no breadth result supports a positive M0 effect.
Compared with B3, M0 used about 33% more model calls, 53% more tokens, and 52%
more wall time without improving task success.

## Failure profile

Across all variants:

- 53 episodes ended unsuccessful at the native step budget;
- 21 were declared infeasible by the model;
- 19 ended in premature completion;
- one ended after invalid model output could not be repaired;
- one succeeded.

All 19 M0 episodes ended specifically at the task budget.  M0 never declared
the task infeasible or prematurely complete, but it also never satisfied an
evaluator.  A trace comparison on the only solvable task illustrates the
problem: B2 saved the calendar event and passed in 21 actions, whereas M0
repeated the same time-picker tap through its last steps and exhausted the
budget.

## Mechanism health

The result is not explained by a completely inactive memory subsystem:

- M0 produced memory bundles in 758 decisions;
- 457 decisions cited memory;
- the history path made 270 model calls;
- the router emitted 150 FACT, 2,777 HYPOTHESIS, 105 ALERT, and 5,684
  SUPPRESS decisions;
- all 19 M0 memory audits reported zero schema or consistency errors.

However, M0 logged 46 loop events and spent considerably more compute without
success.  The current evidence is therefore consistent with a functioning
memory pipeline whose information does not translate into reliable GUI
control under these Hard tasks.

## Interpretation

This breadth run is a valid high-quality negative/floor result, not evidence
that Selective-Trust Memory Routing improves task success.  Because all four
comparison families are also near zero, the primary M0-versus-B3 contrast is
not identifiable with useful power in this task/model regime.  Running the
remaining frozen schedule unchanged would preserve preregistration but would
likely add roughly 60 or more serial experiment hours while leaving the main
success-rate question at the floor.

Hard observations must not be used to silently tune protocol v1.  The two
scientifically defensible options are:

1. retain protocol v1 as a completed breadth negative result and build a
   separately labelled exploratory protocol v2 after forensic trace review;
2. continue the remaining frozen phases only if strict preregistered
   completion is more important than the current low information yield.

For the summer-camp deliverable, the recommended choice is the first: analyze
representative success, premature-completion, infeasible, budget-exhaustion,
and M0 loop traces; explain the discovered failure mechanism; then run a
smaller, explicitly exploratory validation rather than automatically spending
the remaining 269 cells.

## Reproducibility pointers

- Suite summary:
  `runs/frozen_hard_v1/hard_v1_breadth/suite_summary.json`
- Per-cell scored results and raw traces:
  `runs/frozen_hard_v1/hard_v1_breadth/episodes/`
- Amendment:
  `04_protocols/amendments/protocol_v1_hotfix_005.md`
- Repair implementation:
  `05_project/scripts/apply_pairing_hash_hotfix_005.py`
- Regression test:
  `05_project/tests/scripts/test_protocol_hotfix_005.py`
