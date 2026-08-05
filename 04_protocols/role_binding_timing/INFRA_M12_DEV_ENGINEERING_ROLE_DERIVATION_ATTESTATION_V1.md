# INFRA-M12 DEV engineering role-derivation and attestation contract v1

## Honest status

- Contract type: `DEV_ENGINEERING_CONTRACT`.
- This is not a clean, independent, or held-out preregistration. Its design follows prior DEV diagnosis.
- Phase: freeze only; implementation, tests, and live execution are prohibited in this phase.
- Freeze tag: `role-binding-timing-infra-m12-freeze-20260805`.
- Generation calls, generation tokens, held-out captures, Stage 1 runs, Destination-First runs, and live chains are all zero.

M9 remains an immutable failed result. M10 remains invalid. M11 V1 remains frozen at its original object but is `NOT_AUTHORIZED_FOR_IMPLEMENTATION`. M10 and M11 V1 are contamination/boundary records only; no code, tests, or contract text from them may be imported, copied, or reused.

## New namespace

- Future implementation: `05_project/src/raven_m/role_binding_timing/infra_m12_sealed_role_derivation.py`
- Role-source tests: `05_project/tests/role_binding_timing/test_infra_m12_role_derivation_contract.py`
- Temporal tests: `05_project/tests/role_binding_timing/test_infra_m12_temporal_attestation_contract.py`
- Config: `05_project/configs/role_binding_timing/infra_m12_dev_engineering_role_derivation_attestation.json`
- Input lock: `05_project/configs/role_binding_timing/infra_m12_dev_engineering_role_derivation_attestation.lock.json`
- Classifier contract: `05_project/configs/role_binding_timing/infra_m12_authorization_view_classifier.contract.json`
- Future result root: `05_project/artifacts/role_binding_timing/infra_m12_role_derivation_attestation`
- Future offline root: `05_project/artifacts/role_binding_timing/infra_m12_role_derivation_attestation_offline_gates`

## Primary correction: roles are derived, never declared

Raw process records must not contain a trusted role, `observed_class`, candidate reason, authority flag, adoption flag, or lifecycle-target flag. Presence of any such authority-bearing field fails closed with `RAW_AUTHORITY_LABEL_PRESENT`; it is never treated as a hint.

The only authority-view entry point is frozen as:

`derive_authorization_views(raw_snapshot, locked_runner_record, locked_known_paths, controlled_ports, classifier_version, classifier_contract_sha256, classifier_implementation_sha256)`

All four views are recomputed from one complete atomic raw process universe:

1. `trusted_runner_root`: the unique row exactly matching the locked runner PID, creation time, executable path/hash, and command line;
2. `project_authorization_candidates`: nonrunner rows whose exact normalized path and executable hash match a locked project binary, or whose PID owns a controlled port under complete listener evidence;
3. `support_only_ancestry_nodes`: noncandidate same-frame ancestors required to connect a derived candidate to the exact runner within the fixed depth bound;
4. `unrelated_observed_processes`: every remaining nonrunner row.

The views must be mutually disjoint and cover all nonrunner rows. Candidate reasons are derived output and never input. A support node that owns a controlled port invalidates the view.

## Machine bindings

The classifier policy version is `infra-m12-derive-authorization-views-v1`. The exact classifier-contract SHA-256 is `973192F1D6153F099D9BCC38E784B4C9E2F5203F9CAC77910B349BCCE31D70A0`.

Every sealed view must bind and allow recomputation of:

- raw snapshot SHA-256;
- locked runner-record SHA-256;
- locked known-paths/config SHA-256;
- controlled-port evidence and canonical port-set SHA-256;
- classifier version and classifier-contract SHA-256;
- future implementation SHA-256 and committed blob OID;
- per-view partition SHA-256 values and complete-view SHA-256;
- exact identity keys based on PID plus creation time;
- candidate reasons and same-sample parent chains.

The future implementation hash/blob must be added to a separately reviewed implementation lock; it cannot be invented in this freeze-only phase. A sealed view lacking that binding is invalid.

Current verification must rerun classification from the current raw snapshot and locked inputs. It may not merely validate an old role label or stored partition hash. Attached or supplied derived views are untrusted until exact recomputation matches.

## Temporal attestation boundary

The attestation API may either derive internally from raw input or accept only a recomputation-verified sealed derived view plus one exact candidate identity key. It may never accept a caller-declared role.

1. Evidence is valid only inside one future M12 run and one atomic sample. Cross-sample stitching, cross-run replay, PID-only inference, path-only inference, and reconstruction after disappearance are forbidden.
2. An exited candidate can receive only historical classification, never current authority.
3. A still-live candidate with an exited parent can use its birth sample only if current PID, creation time, executable path/hash, and command line exactly match, and the complete same-frame birth chain remains hash-bound.
4. Support is permanently `role_authority=false`, `adoptable=false`, `kill_target=false`, and `cleanup_target=false`; it cannot own a controlled port or independently authorize a candidate.
5. Current evidence has priority. Any current/history conflict, PID reuse, runner mismatch, missing field, AccessDenied critical field, hash mismatch, classifier mismatch, locked-input mismatch, or broken chain fails closed.
6. Attestations expire at terminal completion and cannot become reusable whitelists.

## Frozen DEV engineering gates

The role/view-source test file must execute and pass before any temporal-attestation test is allowed to execute. The role-source matrix includes:

- raw self-label rejected;
- support-to-candidate and unrelated-to-candidate escalation rejected;
- fake trusted runner rejected;
- candidate-reason tampering rejected;
- known-path configuration tampering rejected;
- controlled-port evidence tampering rejected;
- derived partition class tampering rejected;
- classifier version/hash mismatch rejected;
- sealed view/raw snapshot mismatch rejected;
- same PID with different creation time rejected;
- compatibility replay against the exact committed M9 derivation on locked M9 raw snapshots.

Only after that file passes may the temporal matrix run. It includes lossless support projection, the `12 exited + 1 current` shape, same-frame acceptance, cross-frame rejection, parent/child PID reuse, missing fields, AccessDenied, source/snapshot/partition tampering, cross-run replay, current/history conflict, support authority/port/lifecycle violations, candidate/support masquerade, missing chain, runner reuse, and terminal expiry.

These are fixed DEV engineering gates exposed to prior diagnosis. They are not held-out and are not independent preregistration. In this freeze phase they are written but not executed; the exact state is `NOT_RUN_EXPECTED_FAIL_MISSING_IMPLEMENTATION`.

## First-broken-edge and unique future live chain

Any future offline failure stops before live. Role-source gates run before temporal gates. The first failure is atomically journaled and immutable. No test, classifier rule, threshold, config, or protocol may be patched and rerun under this version.

Only after all frozen offline gates pass unchanged and a separate parent review locks the implementation hash/blob may exactly one DEV chain run:

`exclusive 5038 -> launch -> boot -> display/framework -> 24 sequential burn-in cycles lasting more than 180 seconds -> Settings a11y 3/3 -> 4 apps x 3 DEV rounds`

The first live failure stops the chain. No same-version retry is allowed. Only 12/12 DEV permits preparation, not execution, of v0.3. Model generation, held-out collection, Stage 1, and Destination-First Binding Gate remain prohibited.

## Claim–evidence boundary

This freeze proves only that the M12 DEV contract, role-provenance rules, failure matrix, and stop rules preceded M12 code. It does not establish independent preregistration, implementation correctness, infrastructure qualification, task success, memory efficacy, role-binding effects, novelty, or generalization.
