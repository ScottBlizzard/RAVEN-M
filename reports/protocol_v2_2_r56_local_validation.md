# Protocol-v2.2 r56 local validation

Status: **local candidate PASS; one exact-source M0 Files development smoke
may be prepared**

Source:
`protocol-v2-2-r56-local-candidate` /
`24ddb7a34c0e873218cbac6b081d7d24ecd7d61e`

## What changed

r55 safely stopped when the exact filename was present in accessibility but
the Files search grid visually clipped several same-prefix labels. Its generic
repair still allowed Search, changing view, or scrolling; the model chose an
already-used Search toggle and hit the loop guard.

r56 narrows that one state. If and only if the exact filename is visible
among at least two candidates and Android DocumentsUI exposes exactly one
enabled list/grid view-mode control, the sole repair must tap that control.
The returned action is independently bound to accessibility. The controller
does not calculate or disclose a coordinate.

The repair cannot Search, type, swipe, long-press, select, navigate, commit,
or finish. It must also leave `state_delta`, `memory_citations`, and
`completion_evidence` empty, so the layout change can become evidence only
after the next observation.

## Validation

The complete local suite passed 405/405. The 155-test focused set covering the
protocol-v2 guard, semantic-progress controller, and full RAVEN policy also
passed. Compilation and `git diff --check` passed.

New deterministic coverage proves:

- the exact r55 ambiguity shape accepts only a view-mode tap;
- an attempted Search repair is rejected before execution;
- a correct view tap with an unobserved progress claim is rejected;
- the generic conservative path remains when no view control exists;
- controls outside Android DocumentsUI do not qualify; and
- multiple distinct view controls remain ambiguous and do not qualify.

The frozen protocol-v1 breadth seal independently reproduced 197/197 files
with zero failures and unchanged SHA-256
`8b707052bbf3d22ff9643dc1fd4bc55d8f09461a00be9c13728e6eacdfa37ac9`.

## Zero-model-call AVD verification

After a bounded cold recovery, the standard AndroidWorld smoke passed. A
separate read-only accessibility probe opened Files without initializing a
scored task or modifying any file. The real AVD exposed:

- package `com.google.android.documentsui`;
- activity `com.android.documentsui.files.FilesActivity`;
- exactly one qualified control;
- accessibility label `List view`;
- resource
  `com.google.android.documentsui:id/sub_menu_list`; and
- pixel bounds `(890,525)-(1017,651)` on a 1080-by-2400 screen.

The r56 helper returned `control_count=1` and `unambiguous=true`. Search was a
separate control. No model call was sent in either probe.

## Preserved safety

The r55 false selection statement remains only an unverified memory
hypothesis; r56 does not promote it. Exact-target selection, loop detection,
text provenance, destination binding, consequential-action adjudication, and
post-destination verification remain active. There is still exactly one
model repair.

## Decision boundary

r56 passes local validation but is not Gate-D qualified. This report permits
preparation of one fresh isolated non-scored M0 `FilesMoveFile` development
smoke after a zero-model-call preflight verifies the exact source/tag, frozen
files, fixed instance, emulator, model identity, and a fresh namespace.

It does not authorize a rerun of r55, formal Gate E, or Gate F. A failed r56
smoke must be sealed and analyzed before any further live action.
