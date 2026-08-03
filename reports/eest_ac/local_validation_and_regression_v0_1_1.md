# EEST-AC v0.1.1 Local Validation and Regression

## Outcome

- Focused EEST-AC suite: **21/21 passed**.
- Full repository suite under the isolated AndroidWorld Python: **1023 passed, 1 failed** in 272.86 seconds.
- The sole failure was `test_r78_candidate_static_manifest_validation_passes`. It is the already archived incompatibility between the unfinished legacy r79 source bytes and the frozen r78 manifest hashes. It is not an EEST-AC failure and was not hidden, bypassed, or “fixed” by editing the old manifest.
- Static zero-generation-call preflight: passed.
- Runtime zero-generation-call preflight: passed with the real emulator, ADB/gRPC, exact Qwen3-VL revision/backend, deterministic task hashes, isolated empty run root, source-isolation audit, and preserved r79 WIP hashes.
- Model generation calls before the real batch: **0**.

## Focused gates covered

- immutable task literals and append-only hash-chained EventLog;
- exact current-screen evidence grounding and source-hash corruption rejection;
- wrong-entity corruption rejection;
- closed GoalLedger and invented-requirement rejection;
- Recovery Registry activation only from an executed same-hash transition record;
- cross-page evidence replay and old-current-page suppression;
- low-risk navigation negative controls;
- action-conditioned Save/Send/Delete/Answer/Done trigger tests;
- independent decision schema and rejection of Planner state;
- B3-MATCH useful summary calls without neutral padding;
- M-SLOTS context routing without auxiliary calls.

## Audit anchors

- Protocol freeze: `eest-ac-smoke-v0.1-protocol-freeze-20260803`
- Amendment/implementation freeze: `eest-ac-smoke-v0.1.1-protocol-freeze-20260803`
- Final executable freeze: `eest-ac-smoke-v0.1.1-implementation-freeze-20260803`
- Runtime preflight: `runs/eest_ac_preflight_v0_1_1_20260803/preflight_runtime.json`
- Legacy archive: `reports/legacy_h17_route_archive_2026-08-03.md`
