# B2.8 AndroidEnv accessibility-sidecar diagnosis verdict

## Verdict

**`FAIL_SETTINGS_DIAGNOSTIC — PRE-LIVE RUNNER PREFLIGHT PARSER FLOOR`.** The one frozen Settings DEV diagnosis stopped before AndroidEnv construction and before any `env.get_state` call. It therefore supplies no evidence that the `androidenv_accessibility_sidecar` route is usable or unusable. The preregistered stop rule applies: no 12-cell DEV grid was frozen or run, no v0.3 protocol was prepared, and no retry or same-version patch was made.

This is contaminated infrastructure evidence only. Model generation, held-out capture, oracle efficacy, role-binding timing, memory efficacy, and controller efficacy all remain untested.

## Frozen boundary

- Diagnosis protocol commit: `6a135047eb25b3ca6aef9812f6a398242e37fc7f`.
- Implementation-freeze commit: `b988b2a39eef29e36df5a661c4dd9b3bde9c684a`.
- Freeze tag: `role-binding-timing-b2.8-sidecar-diagnosis-freeze-20260804`, resolving to the freeze commit.
- Frozen route label: `androidenv_accessibility_sidecar`; no equivalence to UIAutomator XML was claimed.
- Authorized calls: one explicit `get_state`, zero model-generation calls. Actual calls: zero and zero, respectively.

Before freeze, the final offline gate passed 13/13 focused tests and the full role-binding namespace. The full regression retained only the already declared protected r79/r78 frozen-manifest conflict. A superseded pre-freeze gate had additionally failed one EEST replay because the gate runner used the repository root instead of `05_project`; that raw result was retained, the gate CWD was corrected generically before freeze, and the EEST failure disappeared. Neither offline run called AndroidEnv or a model.

## Exact first broken edge

The frozen runner first executed the official ADB package-service check through port 5038. The command returned code 0 and exact stdout `Service package: found`; its stdout is 24 bytes with SHA-256 `6646a4c4c5f32c1b42a810b8ccca7d503c94367ea9293d9d57c9c434d4194bba`, and stderr is empty with SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

Immediately afterward, the runner evaluated `stdout.casefold()` although `stdout` was a Python `bytes` object. Python raised:

```text
AttributeError: 'bytes' object has no attribute 'casefold'
```

This occurred at the framework-preflight parser layer. Direct evidence establishes that the package service was available; it does not establish the status of the later window/activity checks because those checks were not reached. AndroidEnv was not constructed, the sidecar host was not created, foreground readiness was not sampled, and no screenshot, protobuf forest, `UIElement`, field manifest, or oracle candidate was captured.

The generic defect is identifiable, but the frozen rule forbids patch-and-retry within v0.2.8. Any correction would require a new version, an explicit bytes/decoded-text test at this boundary, a new lock, and separate authorization.

## Accounting and residue audit

| Item | Observed |
|---|---:|
| Model-generation calls | 0 |
| Explicit `env.get_state` calls | 0 |
| Held-out captures | 0 |
| Foreground readiness samples | 0 |
| Observation records | 0 |
| Wall time | 18.828 s |
| Cleanup home actions | 1, code 0 |
| Cleanup force-stop actions | 1, code 0 |

Cleanup preserved the primary error. Home and Settings force-stop both completed with continuous 5038 PID 29964. After cleanup, 5038 still listened on PID 29964, emulator gRPC 8554 still listened on PID 7172, and 5037 had no listener. No experiment Python process remained. The two pre-existing non-listening abnormal ADB candidates were recorded before freeze and were not killed or otherwise mutated.

The three protected WIP SHA-256 values were identical before and after:

- `episode_controller.py`: `fc0e82e0fde90119365d4f685f080eb4519bf2f602e4bda58de5d4809a40fe33`;
- `protocol_v2_guard.py`: `ff89d6b70be4b4738646d262beb67d7b7e932e9eb95956d940b1c5000a999d10`;
- `test_protocol_v2_2_r79_r78_trace_replay.py`: `5bb1f1e3de673a1072cfee62938b761a62fd69c187d5eadf54bc46b115a3fd0a`.

## Claim–evidence table

| Claim | Evidence | Verdict |
|---|---|---|
| Frozen package-service command executed through 5038 | Code 0, preserved stdout/stderr, PID continuity | Supported |
| Frozen Settings sidecar route qualified | AndroidEnv never constructed; 0 `get_state` calls | Not tested |
| Sidecar returned screenshot and a11y in one observation | No observation occurred | Not tested |
| Lossless 22-field serialization works on a real state | Synthetic tests passed; no real state | Offline mechanism only; live not tested |
| 12-cell multi-app stability grid passed | Grid not frozen or run | Not tested |
| v0.3 fresh collection may start | Prerequisite Settings and grid gates absent | Rejected |
| Role-binding timing hypothesis received evidence | No model, task, or critical decision | Not tested |
| B2.7 UIAutomator verdict changed | B2.7 artifacts were read-only and untouched | Rejected; B2.7 remains FAIL |

## Artifacts and stop decision

The machine-readable terminal record is `05_project/artifacts/role_binding_timing/phase_b2_8_androidenv_sidecar_diagnosis/diagnosis_completion.json`, SHA-256 `e6d16a94a0f12141482046bc05e73666cc48976df1bac74b78ee1775d926e3f8`. `artifact_manifest.json` enumerates and rehashes that terminal record and all six raw preflight/cleanup streams. The result is terminal for v0.2.8: **stop; do not freeze or run the grid; do not prepare v0.3; do not generate.**
