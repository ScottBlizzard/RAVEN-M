# Protocol v2.2 r57 H01 Candidate Smoke — Stopped

## Decision

**r57 failed its one-cell development smoke and is frozen as failed.** The run
was diagnostic (`development_smoke=true`, `formal_scoring=false`); it is not a
Gate-F result. No formal r57 suite was created, no later cell was launched, and
no formal rerun is authorized.

## Result

- H01/B3 `BrowserMultiply`, seed `20260730`
- Frozen goal and parameters matched r56
- One attempt, 12 executed steps, 16 model calls
- Reward: 0
- Stop: `MODEL_OUTPUT_INVALID_AFTER_REPAIR`
- Active wall time: 628.589 seconds
- Reset audit: passed
- Infrastructure attempts: 0
- Residual experiment process: none

The Chrome first-run path produced a crash dialog and accessibility retries,
but the agent recovered inside the episode, reopened the frozen HTML task, and
reached the intended repeated-click state. It is therefore contextual evidence,
not the direct cause of the final guard stop.

## What actually happened

The visible number sequence was:

`6 → temporary blank → 2 → 3 → 9`

At step 9, the first `Click Me` tap was executed. Its screenshot changed from
`6` to a temporary blank, but the immediate accessibility snapshot retained
the same semantic hash. Before step 10, the fresh semantic snapshot had changed
and the visible value was `2`. This proves delayed DOM convergence between the
immediate post-action observation and the next pre-action observation.

r57 counted the immediate observation as one no-effect transition and never
reconciled it when the delayed semantic change arrived. After the next two
successful taps displayed `3` and `9`, the guard still held
`identical_coordinate_no_effect_count=1`. It therefore denied the fourth tap;
the bounded repair proposed the same correct tap and was denied again.

The intended r57 override was never exercised:

- bounded repeated-tap overrides: 0
- identical-coordinate blocks: 2
- blocked actions executed: 0
- A-B cycle triggers: 0
- visible-failure triggers: 0

This is a useful negative result: r57 did not weaken the no-effect safety
boundary, but its evidence timing model was too strict for an asynchronously
updated web value.

## Bounded r58 direction

A next candidate may reconcile exactly one prior no-effect only when all of the
following hold:

1. the immediately prior exact-coordinate action was recorded as semantic
   no-effect;
2. the next fresh pre-action semantic state differs from that recorded
   post-action state;
3. the proposed action repeats the same coordinate;
4. it hits exactly one labelled, visible, enabled, clickable, non-editable,
   non-commit control;
5. that control is bound to the repeated-action target expressed by the task.

Pixel-only changes, clocks/status bars, visible failures, ambiguous controls,
commit controls, blocked fingerprints, count overflow, and A-B cycles must
remain denied. The r57 directory is immutable and must not be resumed or
relabelled.

## Immutable evidence

The full hash inventory and causal fields are recorded in
`reports/protocol_v2_2_r57_h01_candidate_smoke_stopped.json`. The principal
hashes are:

- checkpoint/progress/summary:
  `37f588cbf1c8ea21dab234f32b446f4fb63383fe6986492c1821a1e928d7c6df`
- episode:
  `5ae89bd603f5b13c06a544424900ee3ed2372f502bab820da57fa28050d56258`
- events:
  `0032a076a7f059e57ce09d01a0362d5ad4f5a78bda6878d2940ff96a54801b26`

