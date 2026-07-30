# Protocol-v2.2 r49 local validation

Status: **local PASS; one isolated live Files smoke required**

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

## Evidence boundary and next action

No live AndroidWorld action has run from r49 yet. r48 remains immutable and
must not be resumed. The next authorized action is one fresh, isolated,
non-scored M0 `FilesMoveFile` smoke in a new r49 development namespace. It
must verify native reward, single mutation, exact destination binding, live
consumption of the new branch, and a valid terminal decision. A smoke failure
stops r49 for diagnosis. A successful smoke permits a separate Gate-D freeze;
it does not itself authorize formal Gate E or Gate F.
