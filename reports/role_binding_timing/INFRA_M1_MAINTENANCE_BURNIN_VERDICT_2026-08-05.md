# INFRA-M1 maintenance and burn-in verdict

## Verdict

`RUNTIME_UNSTABLE` at `BOOT_NOT_READY`. The frozen maintenance sequence cleanly replaced the three verified project-owned processes, but the fresh emulator registered through an implicitly created ADB server on forbidden port 5037 rather than through the locked server on 5038. The 5038 client therefore never discovered `emulator-5554`. The framework-stability gate, 24-cycle burn-in, accessibility qualification, and 12-cell DEV grid were not authorized or run.

This is DEV-only infrastructure evidence. It is not evidence about AndroidEnv accessibility delivery, role binding, memory, controller efficacy, or the research hypothesis.

## Frozen boundary

- Protocol freeze commit/tag: `a58ad74708fe43f08a0ea133d0faa35f430f63a7` / `role-binding-timing-infra-m1-maintenance-freeze-20260805`.
- Predecessor: `9bf5722b2122cf99ddcde50868048cae7eec6a54`.
- Exact scope: zero model generations, zero AndroidEnv sessions, zero held-out capture, and one project-owned maintenance attempt.
- Offline gates: INFRA focused tests 21/21; role-binding namespace passed; full regression had only the preregistered legacy r79 frozen-manifest failure.
- Authoritative pre-inventory: `infra_m1_pre_maintenance_inventory_v2`; the first inventory is retained as superseded because its derived degradation flags omitted stderr even though the raw bytes were preserved.

## Direct evidence

| Layer | Evidence | Verdict |
|---|---|---|
| Pre-maintenance ownership | ADB 5038 PID 29964; emulator launcher PID 35116; qemu PID 7172 owning 5554/5555/8554; no 5037 listener | Qualified for bounded maintenance |
| Clean stop | `emu kill` returned 0; old emulator pair and its three ports disappeared after 3 bounded checks. `adb -P 5038 kill-server` returned 0; PID 29964 disappeared after 1 check | PASS |
| Fresh process identity | New official ADB 5038 PID 35452; launcher PID 7616; qemu PID 37004; binary/path/command/parent and listener checks passed | PASS |
| Emulator boot | Frozen emulator stdout records `Boot completed in 89977 ms` and gRPC on 8554 | Emulator itself booted; this does not establish 5038 device readiness |
| Locked ADB readiness | All 90 attempts returned `device 'emulator-5554' not found` for both `get-state` and `sys.boot_completed` through 5038 | FAIL |
| Forbidden fallback | Attempts 1–12 had no 5037. From attempt 13 through 90, PID 24580 listened on 5037. Its executable is the same locked official `adb.exe`, with command line `adb -L tcp:5037 fork-server server --reply-fd 748` | Hard isolation failure; implicit daemon creation |
| Framework and burn-in | Framework attempts 0; burn-in 0/24 | Correctly not run |
| Terminal record | `maintenance_completion.json` validates against the frozen schema with zero schema errors; the 460-entry artifact manifest was rechecked with zero missing/hash/size mismatches | PASS as failure accounting |
| Protected WIP | All three protected SHA-256 values equal their pre-maintenance values | PASS |
| Generation accounting | 0 calls, 0 model tokens | PASS |

The fail-closed stop left the fresh project runtime running for forensic inspection: ADB 5038 PID 35452, launcher PID 7616, qemu PID 37004, plus the unauthorized 5037 ADB PID 24580. No cleanup or second mutation was performed after the terminal record.

The exact first broken operational edge is therefore:

`fresh emulator launch -> emulator/ADB discovery uses default 5037 -> locked 5038 has no device serial -> boot readiness cannot be observed -> framework/burn-in forbidden`.

The likely generic defect is that the frozen launcher environment did not propagate the locked ADB server port to the emulator process. That explanation is supported by the emulator's early `Unable to connect to adb daemon on port: 5037` log and the later appearance of the official 5037 daemon. It is a causal inference, not a repaired or re-tested result.

## Frozen-artifact side effect

Stopping the old emulator caused its inherited stdout handle to flush additional bytes into the already tracked file `05_project/artifacts/role_binding_timing/phase_b2_v0_2/infrastructure/emulator_stdout.log`. The file was clean in the authoritative pre-inventory git status, but after maintenance differs from tracked blob `9aa7d04d0d478e446e49845cae1b1ece8c9a43b8` and currently has SHA-256 `84f0e2be65d8716d707e58e6a8d199a16d5de0b85c3cdbf5c1d3490007e00f7a` (13,343 bytes). This unintended legacy difference is preserved unmodified, unstaged, and uncommitted; it is not folded into the INFRA-M1 result.

## Claim–evidence boundary

| Claim | Verdict | Reason |
|---|---|---|
| Verified project resources can be cleanly replaced without killing the two pre-existing excluded ADB PIDs | Supported for this maintenance attempt | Exact old/new PID and listener evidence; excluded PIDs 11316 and 17716 remained present |
| Fresh runtime is stable | Rejected | Forbidden 5037 appeared and 5038 never discovered the serial |
| 24-cycle burn-in passes | Untested | Blocked before cycle 1 |
| Fail-closed AndroidEnv/a11y route works after maintenance | Untested | Not authorized after runtime failure |
| Settings 3/3 or 4-app × 3-round grid passes | Untested | Not run |
| v0.3 held-out preparation is authorized | No | Requires the a11y qualification and 12/12 DEV grid |
| Role-binding timing hypothesis has support | Untested | No model call, snapshot experiment, or hypothesis evaluation occurred |

## Stop decision

Stop INFRA-M1 with `RUNTIME_UNSTABLE`. Do not freeze or run the accessibility phase, do not prepare v0.3, and do not treat the 90 failed readiness checks as experimental repetitions. A future maintenance version, if parent review authorizes it, must preregister a task-agnostic emulator-to-5038 propagation correction and a zero-5037 assertion before launch; this version is immutable and receives no retry.

## Artifact index

- Machine terminal record: `05_project/artifacts/role_binding_timing/infra_m1_maintenance_burnin/maintenance_completion.json`
- Raw artifact manifest: `05_project/artifacts/role_binding_timing/infra_m1_maintenance_burnin/artifact_manifest.json`
- Frozen protocol/lock: `04_protocols/role_binding_timing/INFRA_M1_MAINTENANCE_BURNIN_V1.md` and `05_project/configs/role_binding_timing/infra_m1_maintenance_burnin.lock.json`
- Raw boot attempts: `05_project/artifacts/role_binding_timing/infra_m1_maintenance_burnin/maintenance/qualification/boot/attempt_01` through `attempt_90`
- Fresh emulator log: `05_project/artifacts/role_binding_timing/infra_m1_maintenance_burnin/maintenance/start/emulator.stdout.bin`
