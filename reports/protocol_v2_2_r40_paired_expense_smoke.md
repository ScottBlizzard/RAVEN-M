# Protocol-v2.2 r40 paired Expense development smoke

Status: **REJECTED; Gate D not authorized**

Candidate source:
`16f8ff8084774e12205d28e7ece5f272b697b0b1`

This was a fresh, non-scored paired smoke on `ExpenseAddSingle`, seed
`20260729`. It is development evidence only.

## Results

| Variant | Native reward | Steps | Model calls | Elapsed |
|---|---:|---:|---:|---:|
| B3 | 1.0 | 12 | 17 | 602.016 s |
| M0 | 0.0 | 12 | 19 | 639.813 s |

B3 entered all fields, used three valid horizontal swipes, selected Donation,
and saved. M0 entered the same three text fields, spent two actions tapping
the category row under an incorrect popup-menu model, then used three valid
horizontal swipes. At the budget boundary, Donation and Save were visible but
Donation was not selected and the row was not saved.

The swipe language/geometry repair behaved correctly: every declared-left
gesture was horizontal and no mismatch was executed.

## Memory boundary exposed by the live run

The repeated no-effect action generated deterministic failure `f_0009`.
The r40 repair correctly superseded `m_0007`, the unverified progress record
from the first category tap. However, the second tap wrote another unverified
progress record, `m_0008`, earlier in the same transition. Because r40 only
selected records created at `step - 1`, `m_0008` remained active alongside
the failure.

The repair therefore implemented only half of the causal invalidation
contract. The next version must cover action-linked zero-confirmation records
created both in the current failure transition and the immediately preceding
identical transition.

## Why the global loop threshold is not lowered

An offline audit scanned 377 existing trajectory files and found 78 immediate
identical actions following a semantic no-effect observation. The second
action later changed semantics in 46 cases and remained unchanged in 32.
This demonstrates real UI/readiness delay and makes a blanket
“block every first repeat” rule unsafe.

The r41 candidate instead uses narrower evidence:

- reject an exact repeat only when the preceding unchanged action itself
  asserted an unverified `progress` or `page_hypothesis`;
- reject tapping the same already-focused empty editable, where another tap
  cannot add cursor-position value;
- preserve the existing global two-no-effect and three-coordinate bounds for
  all other actions.

## Evidence boundary

The r40 raw directories and hashes are retained. This failure is not
infrastructure, must not be overwritten by a later rerun, and does not revise
the immutable r39 Gate-E result. r40 does not authorize Gate D or any formal
suite.
