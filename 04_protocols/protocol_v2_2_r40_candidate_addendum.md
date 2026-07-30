# Protocol-v2.2 r40 development-candidate addendum

Status: local validation passed; live development smoke not yet run

This addendum applies only to source revisions after the immutable r39 Gate-E
run. It does not revise, reinterpret, or pool evidence with r39.

## Outcome-driven hypothesis supersession

Executor state deltas persist their `delta_kind` and canonical
`action_signature`. When the deterministic semantic-loop detector observes
the same action twice on the same page without semantic effect, it:

1. writes the existing observed FAILURE/ALERT;
2. locates a `progress` or `page_hypothesis` record created by the immediately
   preceding identical action on the same page;
3. requires that record to have zero independent confirmations;
4. supersedes the record with the deterministic failure.

Both records and the supersession edge remain in the append-only event log.
The superseded claim is excluded from active retrieval. Independent visible
facts, confirmed records, and records not causally linked to the repeated
action are unaffected.

## Swipe language-geometry consistency

For protocol v2 only, a swipe whose `decision_summary` explicitly declares
left, right, up, or down is checked against the dominant displacement of its
canonical endpoints. The proposal is rejected before execution when the
sentence and geometry disagree, are diagonal, or have negligible
displacement. The existing single repair budget is used; the controller does
not rewrite coordinates.

Sentences without an explicit swipe direction are not adjudicated. Protocol
v1 does not apply this guard.

## Evidence and promotion boundary

- Local tests and the protocol-v1 seal must pass before any live smoke.
- The first live evidence is one fresh, non-scored paired Expense smoke using
  the frozen r39 task instance and seed.
- Source, prompts, schemas, runtime, model identity, and smoke artifacts must
  be frozen under a new candidate commit.
- Any formal Gate E requires a new Gate-D freeze, clean preflight, and fresh
  suite ID. No r39 cell may be reused.
- A development smoke can reject the candidate; it cannot establish a method
  claim or authorize pooling with r39.
