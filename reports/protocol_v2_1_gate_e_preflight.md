# Protocol-v2.1 Gate E preflight

Date: 2026-07-27

Decision: **READY TO LAUNCH, NOT AUTOMATICALLY STARTED**

Source implementation:
`9c39b75f7eea3952da738a092deb7eb02c506468`
(`protocol-v2-1-gate-e-dev`)

## Frozen design

Gate E remains the same controlled comparison used by protocol v2:

- four non-Hard tasks;
- one B3 and one M0 cell for each task;
- the same instance seed `20260729`;
- the same blocked order seed `2026072901`;
- eight total cells and no Hard-task overlap;
- a fresh suite ID:
  `nonhard_capability_v2_1_seed20260729_r1`;
- a separate output root: `runs/protocol_v2_1`.

No task was replaced or reordered based on earlier success or failure.

## Reliability additions

- Every environment-construction attempt is persisted before scoring.
- One cold startup recovery is allowed; a second failure stops the suite and
  still produces a summary.
- Every executed action must contain before/after semantic UI evidence and a
  guard transition.
- Executing a fingerprint that was already blocked, or exhausting the one
  bounded repair after a guard block, stops the suite.
- The runner audits visible failures, semantic no-progress counts, screenshot
  fallback observations, memory isolation, evaluator leakage, pairing and
  model identity.
- Gate F remains a manual decision; there is no automatic transition.

## Verification

- full local regression: 159/159 tests;
- frozen critical files: 14/14 hashes match;
- task/action capability audit: pass;
- all four deterministic instance hashes generated successfully;
- emulator `emulator-5554`: connected;
- Qwen3-VL-32B service: loaded with the frozen revision and backend;
- intended suite directory: absent;
- preflight model calls: 0;
- preflight GPU experiment cells: 0;
- Gate E cells started: 0.

The health field `concurrent_generations: 1` is the service's configured
single-generation concurrency limit, not evidence of an active experimental
cell.
