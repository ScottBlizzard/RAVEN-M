# Protocol-v2.2 r43 development-candidate addendum

Status: locally qualified; fresh M0 Expense smoke pending

This addendum follows the rejected r42 M0 development smoke. It preserves all
r39-r42 raw evidence and does not amend any frozen formal result.

## Progress-conditioned exact-swipe streak

The three-action streak rule is now action-type and evidence aware.

For an exact repeated `swipe`:

- another repetition is admissible when every transition in the current
  streak changed the semantic UI;
- the existing streak rejection remains when any transition in that streak
  produced no semantic UI change; and
- if the immediately preceding stalled swipe asserted only unverified
  progress or a page hypothesis, that more specific repeat rule is evaluated
  first and requires the current layout to be re-read.

Exact repeated taps and long-presses retain the unconditional three-action
limit. This avoids generalizing carousel evidence to same-coordinate click
loops whose semantic hashes may change for unrelated reasons.

The rule does not assert that semantic change proves task completion. It only
distinguishes a verified state transition from an already observed stall.
The no-effect threshold, visible-failure blocks, A-B-A-B detector, and frozen
step budget remain the terminal safeguards.

## Historical boundary

Across 403 trajectory files, only three model proposals triggered the
coordinate-streak guard. Two were swipe proposals after three
semantic-changing transitions and become admissible; both source episodes
failed. The third was the retained r40 B3 Expense case whose streak contained
a no-effect transition and remains blocked.

A broader audit found ten actually executed fourth coordinate actions after
three semantic-changing transitions: nine were taps and one was a swipe.
All nine taps remain subject to the hard limit; eight of them belonged to one
known failed Files click loop. The single swipe's fourth transition then
stalled, which r43 records and blocks before another exact continuation.

## Frozen invariants

r43 changes no model, seed, task instance, evaluator, action or model-call
budget, schema, memory threshold, readiness bound, text/coordinate authority,
or Protocol-v1 artifact. The one-repair limit remains unchanged.

## Qualification boundary

The only authorized live action after local qualification is one fresh,
non-scored M0 Expense smoke. It cannot be pooled with prior development cells
or authorize a formal result by itself.
