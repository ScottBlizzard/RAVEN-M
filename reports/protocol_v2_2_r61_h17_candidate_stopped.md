# Protocol v2.2 r61 H17 Candidate Stop Audit

## Decision

**The targeted r61 mechanism passed live, but the end-to-end H17/M0 candidate
failed.** The single development cell is stopped and immutable. It was
non-scored and does not authorize formal Gate F.

Attempt 1 lost Android accessibility during reset and was archived as
`INFRA_EMULATOR_LOST`. The audited cold recovery succeeded. Attempt 2 was a
valid method result: native reward 0, 13 executed actions, 31 model calls,
611.9 seconds, `MODEL_OUTPUT_INVALID_AFTER_REPAIR`, and a passing post-episode
reset.

## What r61 fixed

The two transition shapes that failed in r60 no longer crossed a policy-step
boundary:

- the repeated Markers tap changed from `06de312ae857...` to
  `94f944ba80e4...` on the second post-action observation;
- the Search tap changed from `06de312ae857...` to `f19d911aa418...` on the
  second post-action observation.

In both cases, the first observation was explicitly marked settle-pending. The
new bounded window captured the finished UI before the next decision, so no
false no-progress outcome or stale critic constraint survived onto the new
screen. The cross-step reconciliation count is zero for this reason, not
because r61 was inactive. No blocked fingerprint executed and the loop guard
was not loosened.

## Why the task still failed

The initial screen was already a reverse-chronological activity list. The
agent never swiped it. Instead it:

1. interpreted the map-pin icon as a date picker and opened empty `Markers`;
2. returned and repeated that same semantic mistake once;
3. opened text Search and entered `September 24 2023` as a query;
4. treated the empty text-search result as evidence that the target date had
   no activity; and
5. proposed `No activities recorded`, which was not visible and was not an
   activity type.

The provenance/visual critic correctly rejected that unsupported answer. Its
bounded repair proposed another wait on the same empty semantic state, and the
loop guard correctly rejected it. The unresolved repair then stopped the
candidate according to protocol.

The upstream cause is therefore no longer delayed readiness. It is a generic
navigation-grounding error: using unlabeled toolbar icons and text search as
speculative date navigation instead of moving through a visible chronological
list.

## Safe next scope

A new candidate may encode a general rule that, when a task asks for an older
date and the visible content is a chronological history/list, the policy should
move through that list toward older dates before speculating about unrelated
toolbar icons. A map pin must not be treated as a calendar/date picker, and an
empty text-search query must not prove absence for a date unless the UI
explicitly establishes date-search semantics.

This rule must not mention H17, OpenTracks, the target date, `swimming`, or any
hidden evaluator field. It requires replay-shaped positive and negative tests,
full regression, a new source tag/namespace, and another zero-call preflight.
The r61 cell may not be retried or overwritten.

Machine-readable evidence:
`reports/protocol_v2_2_r61_h17_candidate_stopped.json`.
