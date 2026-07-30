# Protocol-v2.2 r44 local validation

Status: **PASS locally; fresh M0 Expense smoke pending**

Parent commit:
`42d5e4a60430a7d923f8d83cb2c5185159c9d96c`

## Change

r44 replaces the non-idempotent clear-then-type sequence for non-empty
`clear_text=true` actions with one compound ADB request. Each hidden
AndroidEnv retry now starts with select-all and delete before replaying the
model-authored, AndroidWorld-formatted input tokens. Any model-supplied focus
click remains first, and Enter follows only a successful compound request.

Short values keep a 10-second request timeout. Longer values scale by input
operation count to a hard 120-second ceiling. This covers the historical
181-token case without allowing an unbounded infrastructure stall.

## Local evidence

- 357 tests collected and 357 passed.
- Adapter tests cover coordinate focus ordering, exact compound command
  construction, multiword formatting, no-coordinate execution, newline
  preservation, bounded timeout scaling, and final failure propagation.
- Controller integration fixtures now exercise the compound request instead
  of assuming the retired upstream `input_text` call.
- `compileall` and `git diff --check` passed.
- The Protocol-v1 breadth seal verified 197 files with zero failures.

## Compatibility audit

The audit parsed 6,492 executed steps in 404 trajectory files with zero parse
failures. Of 913 executed text actions, 739 explicitly requested clearing and
are applicable to r44; 174 non-clearing actions retain their old path.

Of the applicable actions, 736 had model coordinates and three relied on the
current focus. Token counts were 423 one-token, 303 with 2-9 tokens, 12 with
10-49 tokens, and one with 181 tokens. One applicable text contained a
newline, which is preserved as a key event inside the compound request.

This is an executor reliability correction shared by all variants, not a
policy capability or a method-specific recovery.

## Evidence boundary

No server/GPU result has been produced with r44 source. The r43 M0 attempt
remains invalid infrastructure evidence, and the r43 swipe rule remains
unadjudicated live. The next admissible action is one fresh, non-scored M0
Expense smoke. Gate D and formal execution remain unauthorized.
