# INFRA-M14 trusted-initializer harness freeze v1

Status: `FROZEN_BEFORE_M14_IMPLEMENTATION`; post-diagnosis offline DEV engineering harness; tests and gates `NOT_RUN`.

## Scope and non-claims

This freeze supplies the missing pytest authority-root fixture required by the two immutable INFRA-M14 test files. It serves only offline DEV contract tests. It is not a production bootstrap, live runner, security boundary against hostile same-process Python, role-binding experiment, held-out instrument, or evidence that M14 works.

The existing M14 freeze remains immutable:

- commit `7fb2aee39f0ec327fc1cd9437637ff25d4152c6d`;
- annotated tag `role-binding-timing-infra-m14-freeze-20260805`, tag object `f08a189129218e70d61bed21bea7b1eb6d76a974`;
- future M14 implementation `05_project/src/raven_m/role_binding_timing/infra_m14_authority_context_attestation.py` remains absent.

## Frozen paths

- pytest plugin: `05_project/tests/role_binding_timing/infra_m14_trusted_initializer_harness.py`;
- plugin contract tests: `05_project/tests/role_binding_timing/test_infra_m14_trusted_initializer_harness_contract.py`;
- registration point: `05_project/tests/conftest.py`;
- machine declaration: `05_project/artifacts/role_binding_timing/infra_m14_harness_freeze/freeze_declaration.json`;
- human report: `reports/role_binding_timing/INFRA_M14_TRUSTED_INITIALIZER_HARNESS_FREEZE_2026-08-05.md`.

## Exact immutable expectations

The harness binds these authority expectations independently of individual fixture calls:

- M14 config SHA-256: `8421E4985DEF834F84D5B22FFC0B2D22FF2A063473861213A64C4990C694C661`;
- M14 input-lock SHA-256: `11BA21E3DAF4D8ED4BD0D2633E5D2EE9FD9583FB7060169FC3950AE777ADF4A6`;
- exact ordered controlled-port tuple: `(5037, 5038, 5554, 5555, 8554)`.

The fixture factory may pass malformed *supplied* runner records, port lists, hashes, or identities to exercise frozen negative cases. Such supplied values never replace the expected bindings above. The factory has no skip, validate-false, direct-context, direct-seal, direct-ledger, or direct-attestation path.

## Import and registration lifecycle

Importing the pytest plugin must not import the M14 implementation. The only fixture is session-scoped `trusted_initializer_factory`. When that factory is first called, it lazily imports the M14 module and invokes the future private entry `_dev_register_trusted_initializer_harness` with:

- an exact process-local `_TrustedInitializerHarnessCapability` issued by this plugin;
- the frozen harness contract version;
- the exact config/input-lock hashes and port tuple above.

The future M14 private entry must call back to this exact plugin's `_claim_capability_for_m14_private_bootstrap`, receive the exact process-local `_HarnessRegistrationReceipt`, and bind both objects to its private DEV bootstrap state. A normal dictionary, ordinary object, class lookalike, capability from another plugin/module instance, copied capability, or second registration must fail closed.

Every initializer request then uses `_dev_create_trusted_runner_initializer`. The future M14 private entry must revalidate the exact capability and receipt through `_validate_active_capability_for_m14_private_bootstrap`, verify its own immutable expected bindings, and return exactly an M14 `TrustedRunnerInitializer`. The pytest factory rejects any context, seal, ledger, attestation, dictionary, or other return type. Tests must later call public `create_locked_authority_context`; the harness cannot call it or bypass it.

## Capability limitations and trust assumption

The capability, receipt, and factory reject normal copying, deep copying, and pickling. Registration is exactly once per plugin process. These controls prevent ordinary argument substitution, accidental copying, duplicate registration, and cross-context fixture misuse under the declared DEV test model.

The harness assumes there is no malicious code in the same Python process before its first registration. It does not claim resistance to arbitrary Python reflection, debugger access, monkey-patching of private members, memory introspection, native-code injection, or hostile code already executing in-process. It is therefore not a general security mechanism.

## Exact `conftest.py` change

Original committed state:

- blob `92860d6ac209bd0843646d1554983b4f0ebf7a9e`;
- SHA-256 `CDF5B6DF6F7605CA14D7C05613A2A5FD33FBA56681797EB20FB080FDEC3CD908`.

Frozen post-change state:

- prospective blob `3f3f08b6f276d4aac413c530524cc7a5dbced3e9`;
- SHA-256 `D12C1BCE097AE8FA2EA641A493E6E9B8EE42853E7F5116B6834A6968E1AD754E`.

The exact and only change is one blank separator plus:

```python
pytest_plugins = ("role_binding_timing.infra_m14_trusted_initializer_harness",)
```

No other existing test file may change in this harness freeze.

## Frozen, unexecuted contract matrix

The prewritten harness tests must cover:

1. plugin import leaves the M14 module unloaded;
2. exactly one pytest fixture exists and it is named `trusted_initializer_factory`;
3. ordinary dictionary, ordinary object, and capability from another plugin object are rejected;
4. second registration and second factory creation are rejected;
5. capability, receipt, and factory reject copy/deepcopy/pickle;
6. fixture factory returns only `TrustedRunnerInitializer`, never context/seal/ledger/attestation;
7. fixed config/input-lock/ports are passed independently of malformed supplied negative inputs;
8. no validation-bypass keyword or direct authority-construction API exists;
9. current `conftest.py` equals the exact post-change hash and removing only the frozen registration reconstructs the exact original hash;
10. M14 implementation remains absent at freeze.

These tests are frozen but must not run in this phase. Static contamination gates, M14 tests, replay, offline behavior, and live chains are also not authorized.

## Stop rule and accounting

Stop after one harness freeze commit and annotated tag `role-binding-timing-infra-m14-harness-freeze-20260805`. Do not implement M14 or execute any test/gate. Generation calls, generation tokens, held-out captures, offline behavior executions, live chains, Stage 1, and Destination-First Gate runs remain zero.
