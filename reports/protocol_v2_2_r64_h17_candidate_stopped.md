# Protocol v2.2 r64 H17 candidate stop audit

Decision: `r64_visual_row_tap_validated_but_unvisited_row_routing_and_icon_field_grounding_failed`.

This was one non-formal H17/M0 development attempt. It executed seven actions in
409.858 seconds and used 15 model calls. Startup, teardown, and reset accounting
passed; there was no excluded infrastructure attempt. The evaluator received no
answer action.

## What r64 proved

r64 fixed the precise failure isolated in r63. Once both target-date rows were
visible, the guard blocked another blind swipe. The exact r63 repair tap at
normalized coordinate `(0.5, 0.775)` then passed the generic same-row/content-side
geometry checks without relying on missing accessibility `clickable` metadata, was
executed, and opened the first target-date detail page.

This is a mechanism success, but not a task success.

## Why this candidate is stopped

The detail page contained a title (`Skill work`) and date (`Sep 24`), while the
requested activity category/type was represented by a large icon rather than a
separately labelled text field. The model twice treated the title as the requested
field. The association and enumeration guards correctly rejected those answers.

After returning to the list, the model selected the same first row instead of the
second target-date row. Only one distinct visit key, `target-row-y:0.747`, was
established. The final bounded repair again proposed the first-row coordinate and
the loop guard rejected it before execution. Thus r64 lacks both deterministic
unvisited-row routing and an auditable path from a semantically clear detail icon to
the requested category field.

The suite is immutable and must not be resumed, overwritten, retried, or relabelled.
r65 may address only the generic failures above, must add negative tests, and must
freeze a new source commit and zero-call preflight before another live request.

