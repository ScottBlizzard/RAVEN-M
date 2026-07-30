# Protocol-v2.2 r49 development-candidate addendum

Status: locally qualified; one fresh M0 Files smoke authorized

This addendum follows the immutable r48 formal Gate-E stop. It preserves the
four valid native successes, all r45-r48 guard behavior, and every frozen r48
artifact. It does not reinterpret or resume the stopped r48 suite.

## Post-transfer verification navigation

In r48 sequence 4, the bottom MOVE action had already executed and the native
evaluator awarded 1.0. M0 then returned to the storage root and proposed
tapping the visible task destination, `Ringtones`, to inspect its contents.
Because the action summary used `confirm`, the generic consequential-action
heuristic invoked the critic. The critic circularly required the folder to be
selected and its contents visible before allowing the tap that opens it.

r49 treats this one evidence shape as reversible navigation rather than a
new mutation. The classification is permitted only when:

- the guard has observed exactly one destination-picker Copy/Move commit;
- the destination picker is no longer active;
- the action is a tap;
- `FilesMoveFile.params.destination_folder` supplies a non-empty target;
- current accessibility contains that exact label at the tap coordinate;
- the coordinate also overlaps a visible, enabled, clickable, non-editable
  container;
- the matched nodes belong to
  `com.google.android.documentsui`; and
- neither the target label nor the clickable container is commit-like.

For this classification only, the history policy receives
`consequential_action_candidate=false`. Its action authority is recorded as
`observe_navigation` with both current-screen and task-parameter authority.
The guard records the action, before-state semantic hash, required
destination, matched label, and package.

## Preserved safety boundary

r49 does not bypass adjudication for:

- the original or any later Copy/Move commit;
- pre-transfer destination-folder taps;
- a tap while the destination picker remains active;
- a different folder, partial label, or absent task destination;
- non-Files, system, keyboard, editable, disabled, invisible, unnamed, or
  unbounded controls;
- Save, Delete, Confirm, Move, Copy, or another commit-like target; or
- a long press, swipe, text action, Enter, or terminal response.

The post-destination mutation guard, one-repair limit, loop thresholds,
readiness checks, prompts, schemas, memory policies, evaluator, task and model
budgets, and Protocol-v1 surface remain unchanged.

## Qualification and authorization boundary

Deterministic full-chain regressions execute the original MOVE commit, expose
the storage-root `Ringtones` row, and prove that only its exact Android Files
tap becomes non-consequential. The positive chain emits one structured audit
record. A package-only negative control retains critic authority and prevents
the second execution. Unit cases separately reject wrong-folder,
commit-label, non-Files, no-accessibility, and pre-commit variants.

The exact candidate commit passed 377/377 project tests, 127/127 focused
tests, `compileall`, `git diff --check`, and the unchanged 197/197
Protocol-v1 breadth seal. A zero-model-call preflight verified the candidate
tag, all 27 frozen files, the four deterministic task instances, the exact
Qwen3-VL model identity, the emulator, and absence of the new suite directory.

Only one fresh, isolated, non-scored M0 `FilesMoveFile` development smoke at
sequence 4 is authorized. It must stop for diagnosis on invalid output,
repeated mutation, infrastructure contamination, absent live branch
consumption, or native task failure. Success may support a later, separate
Gate-D freeze; it does not authorize formal Gate E or Gate F.
