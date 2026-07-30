# Protocol-v2.2 r50 development-candidate addendum

Status: live source-exit qualified; destination-navigation boundary
over-constrained; candidate frozen

This addendum follows the immutable r49 development smoke. It preserves
r49's exact post-transfer destination-navigation binding, its native task
success, and all prior protocol artifacts.

## Exact source-directory exit

After the single MOVE commit in r49, the first bounded repair correctly
pressed Back out of Search. The newly observed screen still showed `Music` as
the current Android Files title and breadcrumb. The policy nevertheless
scrolled the source files and reopened Search until the 20-step budget ended.
Those actions could not verify `Ringtones` and could only create a path toward
reselection of a file already moved.

r50 adds one source-context assessment. It is true only when current
accessibility contains the exact `FilesMoveFile.params.source_folder` label:

- in package `com.google.android.documentsui`;
- explicitly visible and enabled;
- with a valid accessibility bounding box; and
- centered in the top 20% of the screen, where Android Files renders its
  current title or breadcrumb.

The vertical constraint distinguishes a current `Music` directory from a
same-named ordinary folder tile at storage-root level.

When one destination commit is already active, the destination picker is
inactive, and this exact source context is present, a non-terminal GUI action
must be `press_back`. A swipe, tap, long press, wait, type, Enter, or app
navigation is rejected before execution. The sole bounded repair must return
exactly `{"type":"press_back"}`. The guard records the source assessment,
blocked action, semantic-state hash, and one source-exit block.

## Preserved boundary

The rule does not apply:

- before the first destination commit;
- while the destination picker is active;
- outside the Android Files package;
- when the exact task source label is absent;
- when a same-named source folder appears below the top navigation region;
- after the parent/root directory has been reached; or
- to a terminal response with no GUI action.

The r49 exact `Ringtones` verification tap remains allowed only after the
commit and only under its own task-label, clickable-container, package, and
non-commit binding. Copy/Move, repeated transfer, exact-file selection,
text-provenance, loop, readiness, action-budget, model-budget, schema,
memory, evaluator, and Protocol-v1 behavior are unchanged.

## Qualification boundary

The deterministic full-chain regression executes one bottom MOVE, observes
the exact top-region `Music` source, rejects a source-folder swipe, repairs it
to Back, and reaches the parent. A negative repair test rejects any
non-Back response. Unit tests prove that the same source label at root-tile
height, a wrong label, a non-Files package, absent accessibility, pre-commit
state, and an active destination picker do not trigger the rule.

The exact candidate passed 385/385 project tests, 135/135 focused tests,
`compileall`, `git diff --check`, and the unchanged 197/197 Protocol-v1
breadth seal.

The authorized fresh, isolated, non-scored M0 `FilesMoveFile` smoke completed
with native reward 1.0, one MOVE, no second mutation, valid bounded repairs,
clean recorded infrastructure accounting, and one live source-exit block.
The repair pressed Back and reached the storage root.

The real root-level `Ringtones` tap overlapped the exact Android Files label
and entered the correct directory, but the label had no separately exposed
clickable accessibility container. The r49 navigation assessment therefore
remained false. r50 is frozen and may not be resumed. A future r51 is bounded
to accepting an exact, visible, enabled, noneditable Android Files
destination-label hit in the content region below the top 20%, while
preserving all prior denial cases and safety guards. This does not authorize
formal Gate E or Gate F.
