# Protocol-v2.2 r41 M0 Expense development smoke

Status: **REJECTED; Gate D not authorized**

Candidate source:
`84a587917dfd090d3d3c8dc92eef8c0e4dddd580`

## Outcome

The fresh, non-scored M0 cell returned native reward 0.0 after 12 actions and
22 model calls. It entered the requested name, amount, and note, but never
navigated the horizontal category row to Donation and never saved.

The semantic audit passed mechanically: no blocked action executed, no memory
audit error occurred, and all outputs were valid after at most one repair.
The task itself nevertheless failed at the frozen budget.

## What r41 proved

The unverified-progress repeat guard fired twice. In particular, the second
category tap was rejected before execution at step 8, so the r40 exact-repeat
defect was removed.

However, the generic repair prompt did not force the model to reconsider the
visible layout axis. It replaced the blocked tap with a downward swipe, then
reversed upward, and continued alternating on the same vertical axis. None of
steps 8–11 changed the category row.

The focused-empty tap guard did not fire. After step 2, the screenshot visibly
showed the Name caret, but accessibility still reported zero focused inputs.
The next coordinate-bearing text proposal therefore triggered the existing
unfocused-clear race guard a second time and executed another activation tap
at step 3.

## r42 scope

r42 must not lower a global threshold or infer focus from pixels. It uses two
bounded controller contracts:

1. when an `UNFOCUSED_CLEAR_TEXT_GUARD` repair has executed the exact
   accessibility-bound activation tap, retain one-step controller proof that
   input activation was attempted; on the next step, require the model to
   return the same task-bound text without coordinates and with
   `clear_text=false`;
2. when repairing an exact repeat after unverified progress, re-read the
   current layout: side-by-side options require a horizontal navigation axis,
   while vertically stacked options require a vertical axis. Reversing an
   unsupported axis merely to differ is invalid recovery.

The controller still injects neither text nor a coordinate. The model must
bind the task value and gesture direction from the frozen task and current
screen.

## Evidence boundary

The r41 directory and hashes are retained. This is a valid agent/controller
failure, not infrastructure. It does not authorize Gate D and is not pooled
with r39 or r40.
