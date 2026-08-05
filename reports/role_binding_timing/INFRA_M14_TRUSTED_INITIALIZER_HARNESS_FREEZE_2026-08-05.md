# INFRA-M14 trusted-initializer harness freeze report

## Verdict

`HARNESS_FROZEN_NOT_EXECUTED`.

The missing pytest authority-root fixture has been defined and frozen independently of the M14 implementation. This is an offline DEV engineering harness only. It does not authorize M14 implementation, pytest execution, offline behavior gates, emulator/live work, or research claims.

## M14 boundary

- immutable M14 freeze commit: `7fb2aee39f0ec327fc1cd9437637ff25d4152c6d`;
- immutable annotated-tag object: `f08a189129218e70d61bed21bea7b1eb6d76a974`;
- M14 implementation path remains absent;
- neither immutable M14 freeze artifacts nor frozen M14 tests were modified.

## Frozen harness artifacts

| Artifact | SHA-256 | Prospective Git blob |
|---|---|---|
| `04_protocols/role_binding_timing/INFRA_M14_TRUSTED_INITIALIZER_HARNESS_FREEZE_V1.md` | `D9716C2434C286276A71CCD7112E8C43F2E5854416CA5BB495794044AEEDB6F0` | `a3e8e858d3fe0d739b0bd18edd97e1f60582f47a` |
| `05_project/tests/role_binding_timing/infra_m14_trusted_initializer_harness.py` | `2ACB3866F172B140FDC1490C3A4D0DDCDA88D5DE21D182101681E367187D08C7` | `614d02d89df3fe512cd8a961f7b5d2373ad73c4d` |
| `05_project/tests/role_binding_timing/test_infra_m14_trusted_initializer_harness_contract.py` | `D9C98F1700960BF9C6020E01D5B8EB767BD02F58BF6B0914C0BBC2FC282F1AB9` | `7c356f7b230cba7a8a9296917365d5b09d579453` |

## Exact `conftest.py` registration

Before:

- SHA-256 `CDF5B6DF6F7605CA14D7C05613A2A5FD33FBA56681797EB20FB080FDEC3CD908`;
- blob `92860d6ac209bd0843646d1554983b4f0ebf7a9e`.

After:

- SHA-256 `D12C1BCE097AE8FA2EA641A493E6E9B8EE42853E7F5116B6834A6968E1AD754E`;
- prospective blob `3f3f08b6f276d4aac413c530524cc7a5dbced3e9`.

Exact diff: two added lines, zero removed lines—one blank separator and:

```python
pytest_plugins = ("role_binding_timing.infra_m14_trusted_initializer_harness",)
```

No other existing test file changed.

## Authority and trust boundary

The plugin exposes exactly one session fixture: `trusted_initializer_factory`. Importing the plugin does not import M14. The first factory call lazily invokes the future M14 private DEV bootstrap using a plugin-issued, process-local, non-copyable/non-serializable capability. Registration is one-time; a normal dictionary, ordinary object, capability from another plugin instance, or second registration must be rejected.

The harness separately fixes:

- config SHA-256 `8421E4985DEF834F84D5B22FFC0B2D22FF2A063473861213A64C4990C694C661`;
- input-lock SHA-256 `11BA21E3DAF4D8ED4BD0D2633E5D2EE9FD9583FB7060169FC3950AE777ADF4A6`;
- ports `(5037, 5038, 5554, 5555, 8554)`.

Malformed values may be supplied only as negative-test inputs. They cannot replace these expected authority bindings. The factory returns only `TrustedRunnerInitializer`; it cannot create or return an authority context, verified seal, ledger entry, or attestation, and it cannot skip the future `create_locked_authority_context` validation.

This boundary assumes no malicious same-process Python before first registration. It does not claim protection against arbitrary reflection, monkey-patching, debugger/native-memory access, or hostile private-member modification. It is not a production security mechanism.

## Execution and evidence boundary

- harness contract tests: `NOT_RUN`;
- frozen M14 tests: `NOT_RUN`;
- contamination/static gates: `NOT_RUN`;
- replay/offline behavior/full regression/live: `NOT_RUN`;
- generation calls/tokens, held-out captures, offline behavior executions, live chains, Stage 1 and Destination-First Gate runs: all `0`.

The only supported claim is that the harness interface, registration diff, failure cases, and limitations were fixed before an M14 implementation exists. No behavior or efficacy conclusion follows.
