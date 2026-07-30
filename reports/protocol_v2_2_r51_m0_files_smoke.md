# Protocol-v2.2 r51 M0 Files smoke

Status: **valid task failure; r51 branch not reached; Gate D withheld**

Candidate:
`protocol-v2-2-r51-local-candidate` /
`ee6f04a4624e964266836354e1e35a289f52aef9`

Suite:
`nonhard_capability_v2_2_seed20260729_r51_candidate_development_smoke_sequence_4`

## Result

The fresh, isolated, non-scored M0 `FilesMoveFile` smoke completed its full
20-step budget with valid output, a passing semantic audit, clean startup,
and no recorded infrastructure attempt. It did not execute the destination
picker or MOVE commit. AndroidWorld therefore returned native reward 0.0 and
`TASK_UNSUCCESSFUL_AT_BUDGET`.

The r51 destination content-label branch was not reached. This is not
evidence against its deterministic qualification: r51 changes only
post-commit assessment, while this trajectory failed before any commit.

## Causal trace

- At step 5, the exact-target guard rejected a wrong truncated filename and
  repaired to the visible Search icon.
- At step 6, the policy proposed coordinate-bearing
  `type_text(clear_text=true)` while the search input was not visibly active.
  The unfocused-clear guard correctly repaired this to an activation tap.
- The resulting screenshot showed the soft keyboard, but accessibility still
  exposed no focused editable node.
- At step 7, the policy again proposed coordinate-bearing
  `type_text(clear_text=true)`. The post-activation guard removed the
  coordinate but explicitly preserved `clear_text=true`.
- AndroidWorld's clear operation sent Ctrl+A without a confirmed focused
  editable. The before/after screenshots prove the effect: the search view
  changed immediately to the storage-root grid with `14 selected`. The task
  query was not entered into Search.
- Step 8 dismissed the keyboard, but the 14-item selection remained. Steps
  9-13 navigated/scrolled in this corrupted selection state.
- Step 14 finally pressed Back and cleared the multi-selection. The policy
  then reopened Search, typed safely with `clear_text=false`, selected the
  exact file, and opened the overflow menu.
- The budget ended at step 19 before `Move to...`, destination selection, or
  MOVE could execute.

This is an evidence-backed clear-text focus race, not a model outage, emulator
loss, or r51 destination-label regression.

## Bounded r52 scope

A justified r52 may add only a post-activation clear-text safety rule. When
an activation-repair proof is pending, `type_text(clear_text=true)` must not
execute unless current accessibility contains an actually focused editable
node. A visible soft keyboard alone is insufficient evidence because Ctrl+A
can reach the surrounding Files grid.

If an exact activation tap executed, the keyboard is present, but no focused
editable is exposed, the bounded repair must retain task-bound text and
provenance, omit x/y, and set `clear_text=false`. If an actually focused
editable is present, ordinary clear behavior remains available. All text
provenance, field-role, coordinate-target, source-exit, one-commit,
destination content-label, and second-mutation guards remain unchanged.

r52 requires complete local and Protocol-v1-seal validation, a new source
tag, a zero-call preflight, and at most one fresh isolated M0 Files smoke.
r51 is immutable and may not be resumed. Formal Gate E and Gate F remain
unauthorized.

