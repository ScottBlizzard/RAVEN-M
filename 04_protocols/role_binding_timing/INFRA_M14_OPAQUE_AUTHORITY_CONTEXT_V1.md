# INFRA-M14 opaque authority-context contract v1

## Honest status

- Contract kind: `POST_DIAGNOSIS_DEV_ENGINEERING_CONTRACT`.
- Phase: freeze only. M14 implementation must not exist in this phase.
- This contract follows the locked M13 code-review diagnosis. It is not an independent preregistration or held-out evidence.
- M13 remains immutable and `NOT_AUTHORIZED_FOR_OFFLINE_GATES`. Its runtime is an audit input only and may not be imported or copied.
- M10 and M11 remain excluded boundary records and are not read, imported, copied, or reused.
- M14 tests and static gate are frozen but not executed: `NOT_RUN_EXPECTED_FAIL_MISSING_IMPLEMENTATION`.
- Generation, held-out capture, Stage 1, Destination-First Gate, offline behavior, and live counters are zero.

Freeze tag: `role-binding-timing-infra-m14-freeze-20260805`.

## New namespace

- Future implementation: `05_project/src/raven_m/role_binding_timing/infra_m14_authority_context_attestation.py`
- Authority/view tests: `05_project/tests/role_binding_timing/test_infra_m14_authority_context_contract.py`
- Ledger/temporal tests: `05_project/tests/role_binding_timing/test_infra_m14_context_bound_issuer_ledger_contract.py`
- Config: `05_project/configs/role_binding_timing/infra_m14_opaque_authority_context.json`
- Input lock: `05_project/configs/role_binding_timing/infra_m14_opaque_authority_context.lock.json`
- Completion schema: `05_project/schemas/role_binding_timing_infra_m14_completion.v1.schema.json`
- Static gate: `05_project/scripts/check_role_binding_timing_infra_m14_contamination.py`
- Future offline root: `05_project/artifacts/role_binding_timing/infra_m14_authority_context_offline_gates`
- Future result root: `05_project/artifacts/role_binding_timing/infra_m14_authority_context`

## Authority root 1: trusted bootstrap and opaque context identity

Before any process snapshot, derivation, seal, verification, ledger session, or issuance, a project-owned trusted runner bootstrap creates exactly one `TrustedRunnerInitializer` capability for the run/session. This initializer is not constructed from method-call dictionaries and is not exported by the M14 method API. A future separately locked harness must provide the DEV initializer fixture before tests may execute.

The initializer captures once:

- the exact runner PID, creation time, executable path/hash, and command line observed at trusted startup;
- the exact canonical known-path entries and executable hashes;
- the exact ordered controlled-port set `[5037, 5038, 5554, 5555, 8554]`;
- the M14 config SHA-256 and input-lock SHA-256;
- run identity, session identity, bootstrap sample identity, and initializer instance identity.

`create_locked_authority_context(trusted_initializer_capability)` accepts only that opaque initializer and no replaceable runner/path/port arguments. It produces a process-local `LockedAuthorityContext` registered by object identity. The initializer and context are single-use, nonserializable, noncopyable, and cannot be represented by a normal dictionary. Their content hashes are observability indexes, not authority. An initializer or context from another process, run, session, or registry is rejected.

After context creation, these APIs accept the context capability rather than caller-supplied lock values:

- `derive_authorization_views(raw_snapshot, authority_context)`
- `seal_authorization_views(raw_snapshot, derived_views, candidate_ancestry, authority_context, implementation_binding)`
- `verify_sealed_authorization_views(raw_snapshot, sealed_view, authority_context, implementation_binding)`
- `begin_issuer_run(ledger, authority_context)`
- `issue_temporal_attestation(verified_seal, candidate_identity, ledger, issuer_session, authority_context)`
- `verify_temporal_attestation(attestation, current_raw, ledger, issuer_session, authority_context)`
- `terminate_issuer_run(ledger, issuer_session, authority_context)`

The context identity is bound into every verified-seal capability, ledger session, ledger entry, attestation, and terminal tombstone. Two contexts containing identical visible fields are still different capabilities. Cross-context seal, session, or attestation replay fails closed.

## Exact immutable controlled-port policy

The initializer and context must contain exactly `[5037, 5038, 5554, 5555, 8554]`, once each. Empty, subset, superset, reordered canonical mismatch, noninteger, or duplicate inputs are rejected before context creation. The method API offers no per-call port override.

Complete listener evidence is required. Every PID appearing in `all_tcp_listener_ports_by_pid` must resolve to exactly one `PID + create_time` identity in the complete fused process universe. Unknown owner PID, duplicate/reused PID, ambiguous identity, malformed port list, or missing owner evidence fails closed, whether or not the port would create a candidate reason.

## Complete-root ancestry before authorization

Candidate-like reasons are provisional until a same-frame bounded ancestry chain is proven complete and ends at the exact context runner identity. A candidate-like row with a missing parent, wrong root, cycle, depth overflow, PID reuse, critical-field failure, or incomplete chain causes `INCOMPLETE_CANDIDATE_ANCESTRY`; it is not downgraded or emitted as an authorized candidate.

Only after all provisional candidates have complete chains may the candidate view be materialized. Support contains only noncandidate ancestors from those complete chains. No node from an incomplete chain may enter support. Support remains permanently non-authoritative, non-adoptable, and ineligible for ledger, kill, cleanup, or controlled-port ownership.

## Retained canonical proof binding

The M13 exact-equality contract remains: verification recomputes the complete four partitions and candidate ancestry from raw evidence plus the opaque context, then compares every canonical field, list order, multiplicity, proof value, and allowed-key set. Extra fields, missing fields, duplicate rows, changed record values, changed ancestry, or reordered normative lists fail closed before content hashes are considered.

Ordinary SHA-256 remains content addressing only. It cannot substitute for context identity, raw recomputation, exact equality, or issuer-ledger membership.

## Retained context-bound issuer ledger

The nonserializable process-local ledger retains CSPRNG run nonce and attestation IDs, exact digest membership, active state, and atomic terminal tombstones. In M14, ledger creation/session begin and every entry are additionally bound to the exact context object identity and its registry identity. A ledger/run cannot switch context. A seal or attestation from another context is rejected even when all visible context fields are equal.

Birth candidate and chain remain deterministic outputs of the verified seal. Observability copies must equal the candidate extracted by exact identity and the chain rebuilt from verified ancestry and sealed records. Current evidence has priority; an exited candidate is historical only and receives no current authority.

## Frozen DEV fault matrix

The authority/view suite retains all M13 canonical-equality cases and adds:

- unrelated process, support process, same-PID/different-creation-time, changed path, changed executable hash, and changed command substituted for the context runner;
- ordinary dictionary context forgery; initializer/context copy and serialization rejection;
- context from a different run/session or independently created but visibly identical context;
- empty, subset, superset, duplicate, malformed, and reordered controlled-port input;
- listener owner absent from the fused universe, PID-reused owner, and ambiguous owner;
- candidate-like row with missing parent, wrong root, cycle, or depth overflow;
- proof that incomplete-chain ancestors never appear in support;
- cross-context sealed-view verification.

The ledger/temporal suite retains all M13 issuer, birth, replay, current-evidence, and terminal cases and adds:

- beginning an existing ledger/run with another context;
- issuing with a verified seal from another context;
- verifying an attestation under another context;
- copied visible context fields in a new capability do not authorize replay;
- terminal and tombstone remain scoped to and inseparable from the original context.

The tests receive a future separately locked `trusted_initializer_factory` DEV fixture. That fixture may construct malformed initializer capabilities solely for negative cases, but it is not an M14 runtime authority API and cannot make a normal dictionary authoritative. No fixture or implementation exists in this freeze phase.

## Stop and execution boundary

No implementation or offline execution is authorized now. A later implementation must be committed and locked separately before any static or behavior gate. Authority-context tests must pass before canonical view tests, which must pass before ledger/temporal tests. First failure is immutable; no same-version patch-and-rerun is allowed.

Live remains separately unauthorized even after future offline success. The maximum possible future DEV chain remains one attempt of exclusive 5038, boot/framework, 24 cycles over 180 seconds, Settings a11y 3/3, and 4 apps by 3 rounds. This freeze neither launches nor authorizes that chain.

## Claim–evidence boundary

The authorization roots are exactly: opaque registered context identity, raw recomputation plus exact canonical equality, and active issuer-ledger membership. This freeze proves only that these rules and fault cases precede M14 implementation. It proves no implementation correctness, security, infrastructure qualification, role-binding effect, memory efficacy, held-out behavior, novelty, or generalization.
