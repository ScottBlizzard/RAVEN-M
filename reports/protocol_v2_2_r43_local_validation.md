# Protocol-v2.2 r43 local validation

Status: **PASS locally; M0 Expense smoke pending**

Parent commit:
`8d63baf17a2d2fda031226fc361589af01d5e666`

## Change

r43 conditions the fourth exact swipe on evidence from its current streak.
Three semantic-changing swipe transitions permit another identical swipe; a
streak containing any no-effect transition is still rejected. Taps and
long-presses retain their unconditional three-action limit.

The immediate unverified-progress/no-effect rule now has precedence over the
generic streak check. A newly stalled productive swipe therefore receives the
current-layout repair that says to tap a now-visible target directly instead
of reversing merely to differ.

## Local evidence

- 352 tests collected and 352 passed.
- Unit tests cover a productive fourth swipe, a no-effect swipe streak, a
  semantic-changing tap that remains blocked, and precedence after a newly
  stalled fourth swipe.
- Controller integration validates that the fourth productive swipe passes
  on the first model response without consuming a repair.
- `compileall` and `git diff --check` passed.
- The Protocol-v1 breadth seal verified 197 files with 0 failures.

## Compatibility audit

The 403-file historical audit found three actual streak-guard proposals. r43
changes two all-progress swipe cases and retains one mixed-progress case.

The broader executed-action audit found ten fourth exact coordinate actions
after three semantic-changing transitions: nine taps and one swipe. The tap
exception was explicitly rejected because eight semantic-changing taps came
from one failed Files loop. The one historical fourth swipe then produced no
semantic change, which would arm r43's no-effect evidence for the next repeat.

This is a narrow compatibility change to verified-progress swipe sequences,
not a global lowering of the loop threshold.

## Evidence boundary

No server/GPU result has been produced with r43 source. r42 remains a retained
development failure. The next admissible action is one fresh, non-scored M0
Expense smoke; Gate D and formal execution remain unauthorized.
