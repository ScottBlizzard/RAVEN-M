# Protocol-v2.2 r56 Gate-F Batch-1 stop report

Date: 2026-07-31  
Decision: **Gate F stopped/failed at 1/12; Batch 1 stopped at 1/4**

## What happened

The formal r56 Gate-F runner started Batch 1 and produced one valid scored
cell, H01 `BrowserMultiply` with B3. Its first attempt was correctly excluded
as `INFRA_EMULATOR_LOST` after an ADB activity-start timeout. The runner
archived that attempt, cold-restarted the emulator, passed the AndroidWorld
smoke test, and regenerated the exact frozen H01 instance.

The second attempt was a valid task trajectory. It ended with native reward
zero and `MODEL_OUTPUT_INVALID_AFTER_REPAIR`. The frozen stop policy therefore
stopped Batch 1 immediately. H17, H03, H16, Batch 2, and Batch 3 were not
started.

The stopped r56 suite is immutable and may not be resumed or relabelled.

## Causal finding

H01 explicitly requires the agent to click the same visible button five
times, remember the five displayed values, calculate their product, and enter
the answer.

After Chrome loaded the local task, the valid trajectory showed:

| State | Action | Visible value | Semantic evidence |
|---|---|---:|---|
| Step 7 | pre-click state | 6 | baseline |
| Step 8 | tap `(0.5, 0.208)` | 2 | changed |
| Step 9 | same tap | 3 | changed |
| Step 10 | same tap | 9 | changed |
| Step 11 | proposed same tap | not executed | blocked |

All three executed taps changed both the screenshot and semantic UI hash.
The third action also left `identical_coordinate_no_effect_count=0`.

At step 11, the model proposed a fourth tap on the same `Click Me` button.
The generic guard blocks any fourth identical tap/long-press after three
consecutive coordinate-identical actions, regardless of verified semantic
progress. The initial response and the one bounded repair were byte-identical
and were both rejected:

> `LOOP_GUARD: the same coordinate tap or long-press has already been
> executed three consecutive times.`

This produced two validation blocks and one unresolved guard repair. No
blocked action was executed.

The failure is therefore not evidence that the model could not navigate to
the task or recognize the required button. It exposes a protocol
compatibility defect: the generic anti-loop ceiling is too strict for a
task-grounded finite repetition. The native zero reward remains authoritative;
the unexecuted counterfactual cannot be scored.

## Infrastructure accounting

- Attempt 1: `INFRA_EMULATOR_LOST`, archived and excluded.
- Recovery: emulator stop and start both returned zero.
- Recovery AndroidWorld smoke: passed.
- Attempt 2: valid scored task failure.
- Startup environment audit: clean.
- Post-episode teardown/reset audit: passed.
- Infrastructure attempts counted in the checkpoint: one.

This separation worked as intended: infrastructure contamination was not
misreported as a model failure, while the later guard incompatibility was not
mislabelled as infrastructure.

## Frozen outcome

- Result count: 1/12.
- Success count: 0.
- Batch 1 completed: false.
- Stopped early: true.
- Active execution: 1,173.047 seconds.
- Projected total before stopping: 6,604.930 seconds, below the 12,600-second
  hard cap.
- Automatic next batch: false.
- Automatic Gate-G transition: false.
- Remaining Gate-F processes after stop: zero.

The formal checkpoint, progress file, and summary are byte-identical, with
SHA-256
`c095b69e550c66c01fa5e75c5cc1aa29cce1d26868001716590868611297cda6`.
The scored episode SHA-256 is
`f27dce2ab98c4d74242fa2fe2aa0890ff7d59ee86451d2c6416b3bda37d5dd20`.

## Bounded next scope

A future candidate may address only this task-interface mismatch. A safe
contract should permit an exact repeated `tap` beyond the generic ceiling
only when:

1. the task text explicitly requests a finite repeated click/tap/press count;
2. the proposed ordinal does not exceed that count;
3. the coordinate hits one visible, enabled, noneditable, non-commit control;
4. every earlier tap in the exact-coordinate streak produced semantic
   progress;
5. no A-B cycle, visible failure, or blocked fingerprint exists; and
6. all no-effect, consequential-action, exact-target, and provenance guards
   remain active.

This must be a new candidate and a fresh namespace. Before another formal
Gate F, it requires local positive and denial tests, the full regression,
the 197-file protocol-v1 seal, a zero-call live probe, one isolated non-scored
H01 smoke, and a fresh Gate-E requalification.

The machine-readable audit is
`reports/protocol_v2_2_r56_gate_f_batch1_stopped.json`.
