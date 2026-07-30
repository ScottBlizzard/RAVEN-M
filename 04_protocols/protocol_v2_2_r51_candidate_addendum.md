# Protocol-v2.2 r51 development-candidate addendum

Status: valid pre-commit smoke failure; destination branch unexercised;
candidate frozen

This addendum follows the immutable r50 development smoke. It preserves
r50's native task success, live-qualified source-exit behavior, one-commit
boundary, and all prior protocol artifacts.

## Exact destination content-label binding

In the r50 smoke, the post-commit step-18 tap overlapped the exact visible
`Ringtones` label in the Android Files storage root. The semantic UI changed
and Android Files entered `Ringtones`, but the r49/r50 assessment returned
`permitted=false`: the exact label hit count was one while the separately
clickable hit count was zero. The real Files root row did not expose a
clickable accessibility ancestor at that coordinate.

r51 removes only that unsupported clickable-ancestor requirement. A
post-commit tap is exact destination-verification navigation only when the
task's exact `destination_folder` label:

- belongs to `com.google.android.documentsui`;
- is explicitly visible and enabled;
- has a valid accessibility bounding box containing the tap;
- is not editable;
- is centered below the top 20% of the screen; and
- is not itself, or paired at that coordinate with, a commit-like control.

The content-region constraint distinguishes a root folder row/card from a
same-named current-directory title or breadcrumb. A separately clickable
ancestor remains recorded as optional audit evidence but is no longer
required. Exact hit geometry, center position, editability, labels, package,
and commit classification are persisted in the v2 assessment.

## Preserved boundary

The allowance still activates only after one destination-picker commit and
while the picker is inactive. It does not apply to:

- a wrong or absent destination label;
- a non-Files package;
- a top-region title or breadcrumb;
- an editable target;
- a commit-like target;
- a non-tap action;
- pre-commit navigation; or
- any repeated transfer, file selection, text entry, or other mutation.

r50's exact source-directory exit, completion critic, task-literal
provenance, loop, readiness, action-budget, model-budget, schema, memory,
evaluator, and Protocol-v1 behavior are unchanged.

## Qualification boundary

The deterministic real-shape regression contains the exact nonclickable
`Ringtones` text node without any clickable parent. It is classified as
observe-navigation, bypasses only the generic false-positive consequential
critic, executes after one MOVE, and increments the post-destination
verification-navigation counter. Negative tests retain the top-region,
editable, compound commit-label, wrong-label, non-Files, empty-state, and
pre-commit denials.

The exact candidate passed 389/389 project tests, 139/139 focused guard,
controller, and full-memory-policy tests, `compileall`, `git diff --check`,
and the unchanged 197/197 Protocol-v1 breadth seal.

The authorized fresh, isolated, non-scored M0 `FilesMoveFile` smoke completed
with clean infrastructure and valid safety accounting but exhausted 20 steps
before opening the destination picker. A post-activation
`type_text(clear_text=true)` executed while only the soft keyboard, not an
actually focused editable node, was visible to accessibility. AndroidWorld's
Ctrl+A clear operation selected all 14 root folders. Recovery consumed the
budget before MOVE, so native reward was 0.0 and the r51 branch was not
reached.

r51 is frozen and may not be resumed. A future r52 is bounded to preventing
post-activation `clear_text=true` unless current accessibility proves an
actually focused editable. When only the soft keyboard and activation proof
exist, a bounded repair may retain task-bound text and provenance, omit x/y,
and set `clear_text=false`. This does not authorize formal Gate E or Gate F.

