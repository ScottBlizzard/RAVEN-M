# A1-R1 BPR v2 Zero-Generation Qualification Summary

Date: 2026-08-14 (Asia/Hong_Kong)

Status: **PASS; live generation authorized only after a fresh arm-specific
server receipt is produced.**

- frozen implementation commit: `cbbca60d656e1ac16a892e4977696ec85442413b`
- design SHA-256: `e6ff3a975484502e2b7368dd3f9775956957a613e3cf4a355e4e7e1c8d1ffc07`
- formal offline replay: `PASS`, `generation_calls=0`
- R3 reconstruction: 511/514 legacy non-none pending records satisfy both
  `<=100` code points and `<=128` UTF-8 bytes; frozen minimum is 489
- R5: `PROSPECTIVE_UNKNOWN_PRELIVE` (no prospective claim was manufactured)
- BPR-specific tests embedded in preflight: 19 passed
- complete `implementation/tests/official_qwen_mobile` regression before final
  evidence generation: 273 passed
- runtime canary: 1000 iterations, p99 below 2 ms and maximum below 10 ms
- automatic transport retry: disabled for both BPR arms
- primary schedule: A0-preservation four tasks, then RecipeDelete sentinel,
  then the remaining fourteen
- empty-read schedule: the fixed five tasks, non-fail-fast, and only after a
  complete immutable primary result

Authoritative machine-readable artifacts:

- `A1R1_BPR_V2_SOURCE_FREEZE.json`
- `A1R1_BPR_V2_OFFLINE_REPLAY_REPORT.json`
- `A1R1_BPR_V2_ZERO_GENERATION_PREFLIGHT.json`

This document does not claim scientific effectiveness. It records only that
the no-GPU implementation, evidence, replay, and launch gates are closed and
that a fresh live process may now be qualified.
