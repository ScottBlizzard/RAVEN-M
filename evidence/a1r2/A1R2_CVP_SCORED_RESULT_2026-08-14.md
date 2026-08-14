# A1-R2 CVP scored result

Date: 2026-08-14 (Asia/Hong_Kong)

Mechanism: `a1r2_compact_verified_pending_v1`

Experiment: `A1R2_CVP_QWEN3VL32B_AW_HARD_T20260806_G3407_V1`

## Result

The fixed 19-task matched suite completed with 19 valid episodes and one
infrastructure-invalid attempt that was transparently replaced by a valid
attempt of the same task.

| Metric | A0 | A1 | A1-R2 |
|---|---:|---:|---:|
| Full successes | 4/19 | 5/19 | **6/19** |
| Reward | 4.5 | 5.5 | **6.5** |
| Model calls | 329 | 603 | **603** |
| Executed actions | 316 | 596 | **595** |
| Total tokens | 1,273,361 | 3,464,267 | **2,685,730** |
| Valid elapsed seconds | 6,541.82 | 14,595.49 | **11,230.18** |

Against A1, A1-R2 has one paired win, zero paired losses, and eighteen ties.
The added full success is `OsmAndMarker`. It preserved all five A1 successes:

- `ExpenseDeleteMultiple2`
- `RetroSavePlaylist`
- `SimpleCalendarAddOneEvent`
- `SportsTrackerTotalDurationForCategoryThisWeek`
- `RecipeDeleteMultipleRecipesWithConstraint`

`MarkorCreateNoteAndSms` received partial reward `0.5` but is not counted as a
full success.

## Independent preregistered verdicts

- Accuracy: **PASS**. A1-R2 exceeded 5/19, exceeded reward 5.5, and lost none
  of A1's five successful tasks.
- Cost: **FAIL** under the strict conjunctive rule. Total tokens and elapsed
  time were below A1, but model calls were exactly 603 rather than fewer than
  603.
- Mechanism causality: **NOT ESTABLISHED**. All six successful episodes had
  committed non-empty reads, but no matched read-disabled ablation was run.
  The added `OsmAndMarker` success is therefore a system-level paired gain, not
  a proven causal gain of the memory text.

Memory totals were 436 non-empty reads, 205 successful writes, 108,423
rendered characters, and 21,710 rendered tokens. The mechanism added zero
model calls, used no hidden UI or evaluator signal for decisions, and never
blocked, overrode, repaired, or force-terminated an action.

## Result-layer repair boundary

All 19 episodes finished before aggregation. The frozen shared runner then
failed in result construction because A1-R2 fell into an A12-only branch that
requires `reference_segments_path`. Before that, the first aggregation attempt
also exposed a local tokenizer dependency that was absent from the Windows
analysis environment. Neither failure affected an episode, action, reward, or
model call.

The repository therefore includes
`implementation/scripts/finalize_a1r2_cvp.py`, a zero-generation read-only
finalizer. It verifies exact task order, checkpoint summary hashes, episode
file hashes, run-signature identity, finite rewards, one transport attempt per
call, and same-task resolution of the invalid attempt before aggregating. It
does not rewrite the frozen runner or any episode artifact.

Authoritative machine-readable result:
`evidence/a1r2/A1R2_CVP_SCORED_RESULT_2026-08-14.json`

SHA-256 of the LF-normalized JSON bytes committed to Git:
`69704d3f71ef309c52cd7b00be12800945e90205cdba4d56a239003e70882ae2`

The original local run tree remains outside Git because it contains large
step-level screenshots and traces. The committed result contains every valid
episode ID and episode JSON SHA-256 so the local raw tree can be re-audited.
