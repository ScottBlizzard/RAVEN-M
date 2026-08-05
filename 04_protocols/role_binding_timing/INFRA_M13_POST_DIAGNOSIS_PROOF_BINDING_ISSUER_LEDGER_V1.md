# INFRA-M13 post-diagnosis proof-binding and issuer-ledger contract v1

## Honest status and scope

- Contract type: `POST_DIAGNOSIS_DEV_ENGINEERING_CONTRACT`.
- Phase: freeze only. The M13 implementation must not exist in this phase.
- This contract is neither independent preregistration nor held-out evidence. It follows the locked M12 code-review diagnosis.
- M12 remains immutable and is `NOT_AUTHORIZED_FOR_OFFLINE_GATES`; it is not repaired, imported, or executed here.
- M10 and M11 remain excluded boundary records and are not read, imported, copied, or reused.
- All M13 tests and the contamination gate are frozen but not executed. Their exact state is `NOT_RUN_EXPECTED_FAIL_MISSING_IMPLEMENTATION`.
- Generation calls/tokens, held-out captures, Stage 1, Destination-First Gate, offline behavior executions, and live chains are zero.

Freeze tag: `role-binding-timing-infra-m13-freeze-20260805`.

## New namespace

- Future implementation: `05_project/src/raven_m/role_binding_timing/infra_m13_proof_bound_attestation.py`
- Canonical-view tests: `05_project/tests/role_binding_timing/test_infra_m13_canonical_view_binding_contract.py`
- Issuer-ledger tests: `05_project/tests/role_binding_timing/test_infra_m13_issuer_ledger_contract.py`
- Config: `05_project/configs/role_binding_timing/infra_m13_post_diagnosis_proof_binding_issuer_ledger.json`
- Input lock: `05_project/configs/role_binding_timing/infra_m13_post_diagnosis_proof_binding_issuer_ledger.lock.json`
- Completion schema: `05_project/schemas/role_binding_timing_infra_m13_completion.v1.schema.json`
- Static gate: `05_project/scripts/check_role_binding_timing_infra_m13_contamination.py`
- Future offline root: `05_project/artifacts/role_binding_timing/infra_m13_proof_binding_issuer_ledger_offline_gates`
- Future result root: `05_project/artifacts/role_binding_timing/infra_m13_proof_binding_issuer_ledger`

## Authorization root 1: raw-and-locked recomputation

The classifier version is `infra-m13-proof-bound-role-views-v1`. Raw rows never carry authority. Any `role`, `observed_class`, derived partition, candidate reason, proof flag, adoption flag, or lifecycle authority in either `all_processes` or `structural_processes` fails closed.

One complete atomic raw snapshot is fused by exact `PID + create_time` identity. The two raw sources must agree canonically on every shared field. Duplicate PID, one PID with multiple creation times, missing universe rows, capture errors, incomplete listener evidence, or field conflicts fail closed. The exact locked runner must match identity, path, executable SHA-256, and command line uniquely. Candidate reasons are derived only from exact locked path-plus-hash membership or complete controlled-port ownership. Support nodes are same-sample, bounded ancestors ending at the exact runner and never receive role, adopt, kill, cleanup, port, or independent authorization.

Verification must first recompute the four complete partitions and `candidate_ancestry` from raw data and locked inputs. It then performs exact canonical equality against every supplied partition row and ancestry object. Equality includes every allowed field and rejects extra fields, missing fields, changed values, changed order where order is normative, duplicate rows, and changed proof fields. Stored labels, reasons, hashes, partitions, or seals are never an authorization input.

The four partitions remain:

1. `trusted_runner_root`;
2. `project_authorization_candidates`;
3. `support_only_ancestry_nodes`;
4. `unrelated_observed_processes`.

They are disjoint and cover the complete nonrunner universe. The M12 role-source and temporal fault matrices remain as DEV regression requirements, but M12 code is not imported.

## Hash boundary

Canonical SHA-256 values are content-addressing and corruption-index fields only. A caller can recompute them, so no public hash is an authorization root. Sealed-view authorization comes from fresh raw-plus-locked recomputation followed by exact canonical equality. Hash verification is performed only after that equality and cannot substitute for it.

The sealed object binds raw snapshot, runner, known paths, ports and port evidence, classifier version/contract, future implementation SHA-256 and committed blob OID, every canonical partition, complete `candidate_ancestry`, and content-addressing hashes. Verification recomputes all of them on every call.

## Birth evidence is deterministically reconstructed

`birth_candidate_record` is not an independent truth. Verification first verifies the sealed view, then extracts the exact candidate row by `PID + create_time`. The expected birth chain is rebuilt deterministically from verified `candidate_ancestry` and the exact sealed records.

Any mismatch in candidate identity, executable path/hash, command line, parent, accessibility state, proof fields, sample sequence/time, source-record hash, chain length, chain order, chain membership, or extra/missing field fails closed. A copied candidate or chain may be retained only as observability data and must equal this deterministic reconstruction exactly.

## Authorization root 2: run-local issuer ledger

The future issuer creates an unpredictable per-run nonce and unpredictable attestation ID using an operating-system cryptographic random source. A process-local ledger stores, for every issued object, the exact canonical attestation digest, run ID, nonce, epoch, attestation ID, and active state.

Verification requires all of the following:

- the exact current ledger instance and active run session;
- exact run ID, unpredictable nonce, epoch, and attestation ID;
- an active ledger entry created by the issuer;
- exact canonical digest equality with the ledger entry;
- successful sealed-view and birth-evidence recomputation;
- no conflict with current evidence.

A caller-recomputed attestation SHA-256 is insufficient. Hand-built objects, copied-and-modified objects, unissued objects, missing ledger entries, wrong nonce/epoch, and objects presented to a fresh/empty verifier process are rejected. The design intentionally does not establish cross-process persistent trust: process restart invalidates every old serialized attestation because the new process lacks its issuer-ledger entry.

Terminal completion atomically marks the run tombstoned and revokes every entry. The tombstone is irreversible for that ledger instance. Neither the original object nor any replay can verify after terminal. Support nodes never enter the ledger as candidates or lifecycle targets.

## Temporal boundary and current evidence

- Evidence is restricted to one M13 run and one atomic birth sample; cross-sample stitching, cross-run replay, PID-only/path-only inference, and post-disappearance reconstruction are forbidden.
- An exited candidate can establish historical classification only, never current authority.
- A still-live candidate with exited parents requires exact current candidate identity/path/hash/command, a complete verified birth chain, and no current/history conflict.
- Current observable evidence always wins. PID reuse, runner mismatch, missing critical fields, AccessDenied critical fields, capture errors, controlled-port conflict, or current/history contradiction fails closed.

## Frozen offline matrix

Canonical-view gates run before issuer-ledger/temporal gates. They retain the M12 role-source matrix and add:

- non-identity tampering in runner, candidate, support, and unrelated rows followed by recomputation of every public hash;
- added and removed fields in any supplied row;
- candidate-ancestry field, node, order, and membership tampering;
- source-record proof tampering followed by complete public rehash;
- sealed partition and complete-view tampering after caller rehash.

Issuer-ledger/temporal gates retain the M12 temporal matrix and add:

- birth candidate executable/path hash/command tampering followed by attestation rehash;
- birth-chain node mutation, reorder, insertion, and deletion;
- candidate-ancestry mutation;
- hand-forged and unissued attestation rejection;
- copied attestation mutation plus rehash rejection;
- missing ledger entry, wrong nonce, wrong epoch, and wrong attestation ID;
- empty/fresh verifier ledger rejection, representing process restart;
- terminal revocation of the original and every replay.

The tests are diagnostic DEV engineering gates exposed to prior diagnosis. They are not held-out. In this freeze phase they are not run and are expected to fail import because the implementation is absent.

## First-broken-edge and future execution boundary

No implementation or execution is authorized by this freeze. A separately reviewed implementation commit and implementation lock would be required before any offline gate. Canonical-view gates must pass before issuer-ledger/temporal gates. Any failure in a future version is the immutable first broken edge; no same-version patch-and-rerun is allowed.

Even after all future offline gates pass, live remains separately unauthorized until parent review. The single possible DEV chain remains:

`exclusive 5038 -> launch -> boot -> display/framework -> 24 cycles and >180 seconds burn-in -> Settings a11y 3/3 -> 4 apps x 3 DEV rounds`

It is recorded only as a future boundary, not launched or made eligible here.

## Claim–evidence boundary

This freeze supports only that a post-diagnosis DEV contract and fault matrix precede M13 code. It does not prove implementation correctness, exploitability, security, infrastructure qualification, role binding, memory efficacy, task success, novelty, held-out behavior, or generalization.
