# Protocol-v2.2 r49 M0 Files smoke

Status: **native task PASS; r49 branch not live-triggered; Gate D withheld**

Candidate:
`protocol-v2-2-r49-local-candidate` /
`6ee10feb10786cdb710e5ea6a1710001b0cd24f5`

Suite:
`nonhard_capability_v2_2_seed20260729_r49_candidate_development_smoke_sequence_4`

## Result

The fresh, isolated, non-scored M0 `FilesMoveFile` smoke moved
`nature_sounds.mp3` from `Music` to `Ringtones`. AndroidWorld returned native
reward 1.0. Exactly one bottom MOVE commit executed, no later transfer or
selection mutation executed, all 20 actions had semantic audit records, all
responses were valid after at most one repair, and there were no
infrastructure attempts.

The run nevertheless ended at `max_steps`, not an evidence-backed terminal
decision. The new r49 post-destination verification-navigation record remained
at zero because the policy never returned to the storage root and never
proposed the `Ringtones` verification tap. r49 therefore passes end-to-end
task safety and native execution, but its new branch is still only
deterministically qualified. Gate D is withheld.

## Trajectory audit

- Steps 0-15 located the exact file, opened `Move to...`, selected
  `Ringtones`, and executed the bottom MOVE once.
- The exact-target guard rejected a same-prefix wrong-file long press and
  repaired it to Search before execution.
- Text-target and focused-input guards repaired unsafe coordinate-bearing
  typing without introducing any ungrounded text.
- The empty destination-picker guard repaired an unbound tap to the visible
  roots drawer.
- At step 16, the post-commit guard rejected a wait on the stale search view
  and repaired it to `press_back`.
- The resulting step-17 screen visibly and semantically remained the `Music`
  source folder. Instead of pressing Back once more, the policy swiped through
  source files, then reopened Search and focused its field at steps 18-19.
- The action budget ended before the storage root, the destination tap, or a
  terminal response.

The startup environment was clean on attempt 1. Initial throughput was slow
because the shared 4090 host had near-total CPU saturation while the model
service performed image/prompt preprocessing; the tunnel, model identity,
emulator, and GPU service remained healthy. This delay affected wall time, not
the semantic result.

## Bounded r50 scope

A justified r50 may add only a post-commit source-exit rule. When:

- one destination commit has already executed;
- current Android Files accessibility contains the exact
  `source_folder` task parameter;
- the destination picker is inactive; and
- the proposed action is not `press_back` or a supported terminal response,

the action must be rejected before execution and the sole repair must be
exactly `{"type":"press_back"}`. This prevents scrolling, searching, typing,
selecting, or waiting inside a task source after its file has already moved.

The rule must not apply before the commit, outside Android Files, when the
exact source folder is absent, or after the source folder has been exited. It
must preserve r49's exact `Ringtones` verification-navigation allowance and
all existing second-mutation blocks.

Any r50 live action requires a new source tag, local full-suite and
Protocol-v1-seal validation, a fresh zero-call preflight, and a new
development namespace. r49 is immutable and may not be resumed. Formal Gate E
and Gate F remain unauthorized.
