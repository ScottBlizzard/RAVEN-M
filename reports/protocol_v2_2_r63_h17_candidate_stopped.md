# Protocol v2.2 r63 H17 Candidate Stop Audit

## Decision

**r63 correctly blocked blind scrolling at the target date, but its bounded
repair contract overconstrained a valid row tap.** The non-scored development
cell is stopped and immutable. It does not authorize formal Gate F or a retry
of the same candidate.

Attempt 1 lost ADB/accessibility during app launch and was archived as
`INFRA_EMULATOR_LOST`; cold recovery succeeded. Attempt 2 is the valid method
result: three actions executed, six model calls, no answer submitted, and a
passing post-episode reset. It stopped as
`MODEL_OUTPUT_INVALID_AFTER_REPAIR`.

## What r63 proved

After opening the app and two upward list swipes, the screen exposed two rows
dated `24 Sep`, with normalized centers `0.747292` and `0.834375`. The model
incorrectly proposed another upward swipe. r63 recognized that the explicit
target date was already visible, rejected that swipe before execution, and
requested a pure target-row detail tap. No visual critic was needed, no
blocked action executed, and no premature or incorrect answer reached the
evaluator.

## Why the repair failed

The model returned a pure tap at `(0.5, 0.775)` with empty `state_delta`,
`memory_citations`, and `completion_evidence`. The screenshot shows this point
inside the first target-date content row and left of the date column; its
vertical distance from that row's date anchor is only `0.027708`.

The repair was nevertheless rejected because r63 additionally required the
tap to hit an accessibility node marked both `is_clickable` and `is_enabled`.
OpenTracks presents the whole row as visually actionable but did not expose a
matching clickable node at that coordinate. Thus the model followed the
intended repair, while the deterministic contract relied on incomplete a11y
affordance metadata.

## Safe next scope

r64 may add a generic fallback based on visible row geometry: the target date
must already be established by the chronological list; the row must contain
non-date content aligned with that date; and the tap must stay in the content
region, left of the date column. Explicit clickable metadata remains strong
evidence when present, but its absence must not invalidate an otherwise
well-grounded content-row tap. Non-target rows, date text, toolbar controls,
swipes, waits, answers, and invented evidence remain forbidden.

The exact r63 action `(0.5, 0.775)` and negative boundary cases require local
replay tests, full regression, a new source tag and namespace, and another
zero-call preflight before any later live request.

Machine-readable evidence:
`reports/protocol_v2_2_r63_h17_candidate_stopped.json`.
