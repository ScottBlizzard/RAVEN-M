# INFRA-M2 emulator-to-ADB-port registration result

## Verdict

`RUNTIME_UNSTABLE` / **FAIL before M2 launch**.

The single frozen run stopped at `LEGACY_FROZEN_LOG_DRIFT_ON_SHUTDOWN`. The inherited M1 emulator accepted the preregistered clean-stop command and exited, but its still-open stdout handle appended 4,322 bytes to the committed M1 log during shutdown. The runner detected the change before stopping either ADB server or launching the M2 emulator. Under the frozen stop rule, INFRA-M2 was not retried and the accessibility qualification was not started.

This is infrastructure evidence only. It does not test exclusive 5038 emulator registration, burn-in stability, AndroidEnv accessibility delivery, held-out collection, role binding, memory, controller quality, or task efficacy.

## Frozen inputs and gates

- Registration audit commit: `f392ddccbba51c79782ff3e0bc6781643f7eef01`.
- Protocol-freeze commit/tag: `6781948ecb4aea12d9467a5c90c6ec83047a11e8` / `role-binding-timing-infra-m2-port-freeze-20260805`.
- Verified correction: child-only `ANDROID_ADB_SERVER_PORT=5038`; no `ADB_SERVER_SOCKET`, no `ANDROID_ADB_SERVER_ADDRESS`, and no 5037 fallback.
- Offline focused tests: 11 passed.
- New namespace regression: passed.
- Full regression: the sole failure remained `tests/scripts/test_protocol_v2_2_r78_h17_candidate.py::test_r78_candidate_static_manifest_validation_passes`, the pre-existing frozen-r79 manifest conflict.
- Pre-run lock hashes, tag/HEAD identity, protected-WIP hashes, binary/AVD hashes, inherited process identities, port ownership, fresh roots, and the 9,590-byte legacy-log hash all matched.
- Generation calls: 0. Held-out captures: 0.

## Execution evidence

| Layer | Observation | Verdict |
|---|---|---|
| Pre-clean ownership | 5037 PID 24580, 5038 PID 35452, launcher PID 7616, qemu PID 37004 and ports 5554/5555/8554 matched the frozen inventory; excluded PIDs 11316 and 17716 were not targeted. | PASS |
| Frozen-log precheck | 9,590 bytes; SHA-256 `ffddf9d0862f8f3e58b424e1e8f774e546875634a0ba81f5e720333284b48b1c`. | PASS |
| Contaminated cleanup action | Exact official ADB command on the already-connected 5037 server returned code 0; stdout was `OK: killing emulator, bye bye` / `OK`; stderr was empty. | PASS |
| Emulator exit | Launcher/qemu disappeared and ports 5554/5555/8554 were released after 2 bounded observations. | PASS |
| Frozen-log post-exit guard | 13,912 bytes; SHA-256 `343e0e8f5f101700bc6e933819921e9296592b5c751874d094f3f0090770b5d5`; +4,322 bytes. | **FAIL** |
| Clean baseline | Not reached. The 5037 and 5038 servers were deliberately left at PIDs 24580 and 35452 after the hard stop. | NOT RUN |
| M2 emulator launch | `launch.started=false`; no new emulator process, output stream, or registration attempt. | NOT RUN |
| Burn-in | 0/24 cycles; 0 seconds. | NOT RUN |
| Accessibility Settings 3/3 and 4×3 grid | Not authorized. | NOT RUN |

The shutdown-time suffix is left untouched and uncommitted. It is not restored, truncated, staged, or silently incorporated into the earlier frozen M1 result.

## Artifact validation

The machine-readable terminal record is `05_project/artifacts/role_binding_timing/infra_m2_emulator_adb_burnin/maintenance_completion.json`.

- Status: `RUNTIME_UNSTABLE`.
- First broken edge: `LEGACY_FROZEN_LOG_DRIFT_ON_SHUTDOWN`.
- Completion-schema errors: none.
- Primary exception: none; the failure is a preregistered guard decision.
- Protected WIP before/after hashes: identical to the frozen values.
- Raw cleanup stdout: 37 bytes, SHA-256 `2f2464ff20db7f0caaf9d7ea8b3e7d1356fb4e22dc58d0e17a15faf96bf41822`.
- Raw cleanup stderr: 0 bytes, SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- Completion record: 11,078 bytes, SHA-256 `356a595f601eed238abe9b3d84b04b98b9282d43ba96dd6f9ac6d67ef5a1347c`.
- Artifact manifest: SHA-256 `abb22fbbe64c097b6afc599a9288b9ad1fee5b937f8a4e64d702181f891d32ca`; every listed artifact matched its recorded byte count and hash.

## Claim-evidence boundary

| Claim | Verdict | Evidence boundary |
|---|---|---|
| The locally installed emulator supports a task-agnostic explicit registration control. | Supported at static-audit level only | Pinned binary strings/source and prior local launcher establish `ANDROID_ADB_SERVER_PORT`; no live M2 registration occurred. |
| The inherited runtime could be stopped through its existing 5037 registration. | Supported | The exact cleanup call succeeded and the emulator ports/processes disappeared. |
| M2 achieved exclusive 5038 registration. | Untested | Stop occurred before clean baseline and launch. |
| Runtime is stable for 24 cycles / 180 seconds. | Untested | Burn-in was not started. |
| AndroidEnv/a11y is ready for the DEV grid. | Not authorized | INFRA-M2 did not pass. |
| v0.3 held-out collection is eligible. | **No** | Neither INFRA-M2 nor the a11y grid passed. |
| The role-binding timing hypothesis has evidence from this phase. | **No** | Zero model calls, zero critical decisions, zero held-out captures. |

## Stop decision

INFRA-M2 ends at the frozen-log ownership/lifecycle boundary. No same-version patch, retry, a11y session, DEV grid, v0.3 protocol execution, held-out capture, or model call is permitted by this result.
