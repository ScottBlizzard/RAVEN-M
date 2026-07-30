# Protocol-v2.2 r49 local validation

Status: **local PASS; native smoke PASS; live branch not triggered**

Candidate commit/tag:
`6ee10feb10786cdb710e5ea6a1710001b0cd24f5` /
`protocol-v2-2-r49-local-candidate`

## Trigger

Formal r48 stopped at sequence 4 after four native task successes. The file
`nature_sounds.mp3` had already been moved to `Ringtones` and the native
evaluator returned reward 1.0. On the storage-root screen, however, the
executor's tap on the visible `Ringtones` folder was classified as
consequential only because its summary used the word `confirm`. The critic
then required the folder to be selected and its contents to be visible before
allowing the tap that would select it. The one permitted repair repeated the
same correct tap and was rejected by the critic-constraint guard.

## r49 change

r49 adds a narrow, accessibility-bound classification for post-transfer
verification navigation. It applies only when:

- exactly one bottom Copy/Move commit has already executed;
- the destination picker is no longer active;
- the candidate is a tap;
- the task has an explicit `destination_folder` parameter;
- the tap overlaps the exact destination label, case-insensitively;
- the same coordinate overlaps a visible, enabled, clickable, non-editable
  container;
- both elements belong to
  `com.google.android.documentsui`; and
- neither the task destination nor the clickable control is commit-like.

Only this action is classified as reversible `observe_navigation` and passed
to the history policy with `consequential_action_candidate=false`. Copy/Move
commits, a second transfer attempt, wrong or unnamed folders, non-Files
packages, editable controls, and commit-like labels retain the previous
adjudication and guard behavior.

Every consumed allowance is recorded with the action, exact matched label,
package, task destination, and before-state semantic hash.

## Local evidence

- 377/377 project tests passed on the exact candidate commit.
- 127/127 focused guard, controller, and full-memory-policy tests passed.
- The full-chain positive regression executes the bottom MOVE commit and then
  the exact `Ringtones` navigation tap. The critic override sequence is
  `[true, false]`, the second action is `observe_navigation`, and one
  structured verification-navigation record is emitted.
- The full-chain negative regression changes only the destination package.
  The override is withheld, the simulated false-positive critic remains
  authoritative, and no second action executes.
- Unit regressions separately reject a wrong folder, a non-Files package, a
  commit-like label, and absent accessibility evidence.
- A guard regression proves that an otherwise valid assessment is not counted
  before the first destination commit.
- `compileall`, `git diff --check`, and the Protocol-v1 197/197 breadth seal
  passed.

## Live smoke evidence and boundary

The one authorized fresh, isolated, non-scored M0 `FilesMoveFile` smoke
completed with native reward 1.0, exactly one MOVE commit, no second mutation,
20 audited actions, valid output after at most one repair, and zero
infrastructure attempts. It ended at `max_steps`, however, rather than an
evidence-backed terminal decision.

After the commit, the guard repaired one stale-view wait to `press_back`.
The next screen was still the exact `Music` source folder, but the policy
spent the remaining three actions scrolling and reopening Search instead of
pressing Back again. It never returned to the storage root, so the exact
`Ringtones` tap and r49 branch were never proposed. The branch remains
deterministically, not live, qualified.

r48 and r49 are immutable and may not be resumed. Gate D, formal Gate E, and
Gate F remain unauthorized. Any r50 change is limited to requiring
`press_back` while the post-commit Android Files screen still exposes the
exact task `source_folder`; it must preserve r49's destination-navigation
binding and all second-mutation blocks.
