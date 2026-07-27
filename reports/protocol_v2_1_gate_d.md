# Protocol-v2.1 Gate D

Date: 2026-07-27

Implementation commit:
`5c1cb952aaa93f1c526ae38fb68a1339a073d5df`

Trigger: protocol-v2 Gate-F batch 1 exposed semantic false progress: status-bar
and toast pixel changes hid repeated no-progress actions, while a visible
calendar validation failure did not stop repeated Save taps.

Decision: **PASS**

## Repair frozen for requalification

- Visible accessibility elements now define task progress. Hidden nodes,
  system UI, coordinates, and validation overlays do not alter the progress
  digest.
- Newly visible validation text remains explicit evidence and immediately
  blocks the responsible state/action fingerprint.
- Repeated semantic no-progress and A-B-A-B cycles are enforced
  deterministically for B3 and M0.
- RAVEN variants additionally store an observed, episode-scoped FAILURE and
  route it as ALERT.
- Environment construction now persists the initial typed infrastructure
  failure, permits one audited cold recovery, and stops after a second
  failure.
- The legacy protocol-v2 Gate-F runner refuses continuation from its
  diagnostic checkpoint, preventing mixed v2/v2.1 evidence.

## Gate D verification

- protocol-v1 seal: 197/197 hashes, zero failures;
- selected task/action coverage: 19/19;
- full local regression: 153/153 tests;
- explicit v1 isolation: no semantic prompt, semantic state, page prefix, or
  loop-extractor change when v2 is disabled;
- live answer/reset smoke: correct score 1.0 in three cycles, empty-cache
  score 0.0 in all three, wrong-answer score 0.0;
- live semantic smoke: 19 raw accessibility elements, five system-UI elements
  excluded, 14 task-visible elements in the digest, no screenshot fallback;
- post-freeze AndroidWorld startup invocation: clean, zero recorded failures;
- both live smokes used zero model calls and ran zero GPU experiment cells;
- no protocol-v2.1 Gate-E or Hard run directory exists;
- old Gate-F batch 1 remains four diagnostic cells and batch 2 remains
  unauthorized and absent.

Gate D authorizes preparation of a fresh eight-cell Gate E under a new v2.1
suite ID. It does not authorize an automatic Gate E launch, and no Gate-E or
Hard cell was started in this round.
