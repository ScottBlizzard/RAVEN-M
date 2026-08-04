# INFRA-M9 authorization-view separation — protocol freeze

## Frozen decision

The M9 audit commit is `1c7aeea`. The zero-mutation offline gate passed in full, so exactly one DEV-only M9 maintenance chain is eligible to start after this protocol-freeze commit and tag. No model generation or held-out capture is authorized.

## Offline evidence

- M9 focused tests: 14/14 passed, covering the four-view derivation, AccessDenied support, unrelated ancestry, controlled-port support corruption, candidate/support relabeling, missing direct chains, runner identity reuse/drift, core-adoption denial, complete failure persistence, runner overlay and terminal schema.
- Frozen M8, M7, M6, M5 and M4 focused regressions: passed.
- Entire `role_binding_timing` namespace: passed.
- Full repository regression: exactly the preregistered legacy failure `tests/scripts/test_protocol_v2_2_r78_h17_candidate.py::test_r78_candidate_static_manifest_validation_passes`; no new failures.
- Runtime preflight: no controlled-port listener, no project authorization candidate, no M9 temp residue and no M9 output root.
- Locked runtime binary, psutil and protected-WIP hashes: matched.
- Generation calls, device mutations and restart attempts: 0 / 0 / 0.

Raw stdout/stderr and their SHA-256 receipts are frozen under `05_project/artifacts/role_binding_timing/infra_m9_offline_gates/`. The audit ledger is frozen under `05_project/artifacts/role_binding_timing/infra_m9_authorization_view_audit/`.

## Live lock

The lock covers code, config, schema, protocol, tests, audit evidence, offline evidence, the M8 input lock and its immutable dependencies. Runtime emulator/ADB/a11y logs are not immutable inputs: they must be written outside the repository while live handles are open, then copied, sealed and hashed once after cleanup.

The chain is fixed: exclusive 5038 with 5037 forbidden; emulator boot; display/framework quorum; 24 burn-in cycles and at least 180 seconds; Settings a11y 3/3; four-app by three-round DEV grid 12/12; cleanup; log seal; independent exactly-once terminal finalization. The first failed gate stops the chain. No patch or retry is permitted within M9.

## Claim boundary

A complete pass would qualify M9 authorization-view separation and authorize only preparation of a future v0.3 protocol. Any failure leaves it unauthorized. Neither outcome tests held-out data, model behavior, role binding, memory efficacy or research novelty.
