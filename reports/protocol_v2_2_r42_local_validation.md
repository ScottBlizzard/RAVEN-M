# Protocol-v2.2 r42 local validation

Status: **PASS locally; M0 Expense smoke pending**

Parent commit:
`f5ed64b082551975df5014e13507f96c7682f398`

## What changed after r41

r42 adds a one-executed-action proof after the existing unfocused-input repair
has actually tapped a visible editable field. On the next policy action, the
model may enter the same task-bound value without coordinates; an empty target
must use `clear_text=false`. The proof then expires.

The unverified-progress repeat repair also receives explicit visible-layout
guidance: a horizontal option row must be navigated horizontally, while a
stacked list uses the vertical axis. The controller does not synthesize the
gesture.

## Local evidence

- 349 tests collected and 349 passed.
- Unit tests cover proof creation, exact-tap rejection, coordinate removal,
  empty-target clearing, and proof expiry.
- Controller integration covers the initial invalid response, the bounded
  repair prompt, the repaired task-bound action, and final validation.
- `compileall` and `git diff --check` passed.
- The Protocol-v1 breadth seal verified 197 files with 0 failures.

## Historical compatibility audit

The audit parsed 6,468 executed steps in 402 trajectory files with zero parse
failures. It found 40 prior executions in which
`UNFOCUSED_CLEAR_TEXT_GUARD` was repaired by an activation tap and had a next
executed action.

All 40 next model drafts proposed coordinate-bearing `type_text`. Under r42,
those drafts receive the existing single repair and must preserve the
task-bound text while omitting coordinates. Historically, 34 final next
actions were text entry and 6 were another exact activation tap; all 40 next
actions changed semantic state. r42 therefore changes a known compatibility
path, but bounds the change to one action and specifically removes the six
observed redundant taps. It does not reinterpret historical scores.

## Evidence boundary

No live server/GPU result has been produced with r42 source. r39 remains the
immutable Gate-E engineering requalification, while r40 and r41 remain
development evidence. The next admissible action is one fresh, non-scored M0
Expense smoke; Gate D and formal execution remain unauthorized.
