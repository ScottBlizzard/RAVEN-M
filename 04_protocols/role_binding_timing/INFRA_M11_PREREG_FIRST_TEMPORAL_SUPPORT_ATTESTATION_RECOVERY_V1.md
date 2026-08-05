# INFRA-M11 prereg-first temporal support attestation recovery v1

## Frozen status and scope

- Phase: protocol freeze only.
- Frozen tag name: `role-binding-timing-infra-m11-freeze-20260805`.
- Implementation status: absent by design.
- Test execution status: not run; the preregistered behavioral tests are expected to fail until the separately reviewed M11 implementation exists.
- Live status: prohibited in this phase.
- Generation calls, generation tokens, held-out captures, and live chains: all fixed at zero.
- M9 remains an immutable failed result. M10 is permanently invalid because implementation preceded freeze.

The only future engineering question is whether a run-local, same-atomic-sample attestation can preserve the historical parent-chain evidence and lossless support projection that M9 failed to retain, without granting any new authority.

## New namespace and contamination boundary

M11 owns new paths that are disjoint from M10:

- Future implementation: `05_project/src/raven_m/role_binding_timing/infra_m11_prereg_first_recovery.py`
- Preregistered tests: `05_project/tests/role_binding_timing/test_infra_m11_prereg_first_recovery_contract.py`
- Operational config: `05_project/configs/role_binding_timing/infra_m11_prereg_first_temporal_support_attestation_recovery.json`
- Frozen input lock: `05_project/configs/role_binding_timing/infra_m11_prereg_first_temporal_support_attestation_recovery.lock.json`
- Future result root: `05_project/artifacts/role_binding_timing/infra_m11_prereg_first_recovery`
- Future offline-gate root: `05_project/artifacts/role_binding_timing/infra_m11_prereg_first_recovery_offline_gates`

The untracked file `05_project/src/raven_m/role_binding_timing/infra_m10_temporal_attestation.py`, previously observed as 47,681 bytes, 882 lines, SHA-256 `D5C0439A39ECD271625502E64F6EBD0BC018F262B9256F6095F44358F90C4BBA`, is DEV-contaminated leaked implementation. It is not an M11 input and must never be opened, read, imported, copied, moved, deleted, formatted, staged, committed, or reused. The static contamination gate may use only these frozen identifiers and candidate-file hashes; it must not read the leaked file.

## Immutable inputs

The historical replay inputs are restricted to the exact M9 result commit and objects named in the input lock. The design rationale is restricted to the exact `db5f4d3` closest-root-cause audit objects. The M10-invalid record is a boundary record, not implementation input.

For offline replay, the committed M9 full process snapshots are the sole raw historical source. For a future M11 live run, each new atomic full-process snapshot captured inside that same M11 run is the sole raw source for its sample. Historical M9 evidence may never grant live M11 authority.

## Machine-checkable process record

Every source and support row used for attestation must losslessly retain:

1. `identity_key`, defined by exact PID plus process creation time;
2. PID, creation time, PPID, and exact parent identity key;
3. executable path and executable SHA-256;
4. full command line;
5. atomic sample sequence and UTC timestamp;
6. source-record SHA-256;
7. full-snapshot SHA-256 and derived-partition SHA-256;
8. field accessibility state and exact access error;
9. observed listening ports and their owning identities.

Hashing uses a frozen canonical JSON representation: UTF-8, sorted keys, compact separators, no NaN, and a trailing newline only where the schema explicitly requires an artifact file. A derived record is invalid unless its stored hashes recompute from its locked raw source and partition.

## Authority semantics

1. An attestation is valid only inside one M11 run and one atomic sample. Cross-sample stitching, cross-run reuse, PID-only inference, path-only inference, and reconstruction after disappearance are forbidden.
2. An exited candidate may use attestation only to classify whether its historical record was legal at the observed sample. It receives no current authority and cannot enter a current authorized-process set.
3. A live candidate whose parent has exited may prove birth provenance only when the candidate's current PID, creation time, executable hash, and command line exactly match its birth record, and the birth sample contains the complete same-frame parent chain with every required proof field.
4. A support-only node always has `role_authority=false`, `adoptable=false`, `kill_target=false`, and `cleanup_target=false`. It cannot own a controlled port and cannot independently authorize a candidate.
5. Current observable evidence has priority. Any conflict between current evidence and historical attestation fails closed.
6. Missing creation time, executable hash, command line, source/snapshot/partition hash, or critical field hidden by AccessDenied fails closed. PID or creation-time reuse, broken chains, tampering, runner-root mismatch, ambiguous ancestry, or controlled-port conflict also fails closed.
7. Attestation is run-local capability evidence, expires at terminal completion, and cannot be serialized as a reusable whitelist. Expired or foreign-run evidence is rejected.
8. Attestation does not change the existing action, model, app, ADB-port, cleanup, or process-ownership permissions.

## Preregistered offline gates

No live chain is eligible until a later implementation commit passes all preregistered tests without changing this protocol or the tests. The frozen fault matrix covers:

- lossless support projection, including executable and record/snapshot/partition hashes;
- the M9-shaped `12 exited + 1 current` replay with no current authority for exited candidates;
- same-frame acceptance and cross-frame stitching rejection;
- parent PID reuse and child PID reuse;
- missing creation time, executable hash, or command line;
- AccessDenied on any critical proof field;
- tampered source-record, snapshot, or partition hash;
- cross-run replay and terminal expiry;
- conflict between current evidence and historical attestation;
- support ownership of port 5038;
- support role authority, adoption, kill-target, or cleanup-target escalation;
- a candidate masquerading as support;
- missing parent-chain segment;
- trusted-runner PID reuse or identity mismatch;
- M11 static contamination and import-graph isolation.

The test suite is frozen now but is not executed in this phase. Its expected pre-implementation state is `NOT_RUN_EXPECTED_FAIL_MISSING_IMPLEMENTATION`.

## First-broken-edge and no-retry rule

The future runner must append an atomic phase journal at `prelaunch`, `exclusive_5038`, `launch`, `boot`, `display_framework`, every burn-in cycle, `settings_a11y`, every DEV-grid cell, `cleanup`, and `seal`. The first failing gate is immutable. Terminal completion must preserve it even if cleanup or rich serialization also fails.

Any offline-gate failure blocks live. During the unique frozen live chain, the first failure stops all later phases. No source, config, protocol, threshold, proof rule, or test may be patched and rerun under this protocol version. A revision would require a new protocol version and parent review.

## Unique future live-chain rule

Only after every offline gate passes and a separate implementation/result lock is reviewed may exactly one chain run:

`exclusive 5038 -> launch -> boot -> display/framework -> 24 sequential burn-in cycles lasting more than 180 seconds -> Settings a11y 3/3 -> 4 apps x 3 DEV rounds`

The chain must retain all M3-M9 controls: external logs, terminal journal, full process snapshots, exclusive locked ADB 5038, 5037 forbidden, stable 5038 server identity, structural process identity, display quorum, same-observation screenshot+a11y, and fail-closed cleanup. Any first failure terminates the chain. Only a complete 12/12 DEV grid may authorize preparation, but not execution, of v0.3. No model generation, held-out capture, Stage 1, or Destination-First Binding Gate is allowed.

## Result and claim boundary

Every terminal result must validate against `role_binding_timing_infra_m11_completion.v1.schema.json`, record zero generation/tokens/held-out, name the exact first broken edge, preserve support non-authority, and bind all artifacts to the frozen commit/tag.

A future PASS would show only that the narrow process-evidence lifecycle qualified on the frozen DEV chain. It would not show AndroidWorld task success, controller efficacy, memory efficacy, role-binding timing effects, novelty, or held-out generalization. This freeze itself provides no implementation or empirical evidence.
