# INFRA-M2 emulator-to-ADB registration audit

## Verdict

A single task-agnostic correction is locally verified and eligible for a separately frozen INFRA-M2 launch protocol: set `ANDROID_ADB_SERVER_PORT=5038` in the exact environment inherited by the emulator process before `Popen`.

This is a read-only DEV infrastructure audit. It made no device mutation or restart, used no model call, collected no held-out data, and provides no role-binding, memory, controller, AndroidEnv, or a11y efficacy evidence.

## Claim–evidence audit

| Claim | Direct local evidence | Verdict |
|---|---|---|
| The pinned emulator runtime reads an explicit host ADB server port | Locked qemu binary SHA-256 `b8e263a00f9151a494b480f38d39188e73dbf338b27015679311246c59c3dbec` contains the contiguous `AdbHostServer.cpp`, `host:emulator:%d`, `ANDROID_ADB_SERVER_PORT`, range-validation, and `Unable to connect to adb daemon on port:` strings | Supported |
| The pinned ADB binary recognizes the same setting | Locked ADB SHA-256 `957e46b8615f7af5b7292a2ddabe98d2e61940c3fb2b0545756507f080613e71` contains `ADB_SERVER_SOCKET`, `ANDROID_ADB_SERVER_ADDRESS`, `ANDROID_ADB_SERVER_PORT`, its positive-port validation, and socket construction strings | Supported |
| The correction value must be 5038 | Project policy and frozen server identity use one official ADB listener on 5038; 5037 is forbidden | Supported for this project runtime |
| A local launcher already applies this exact mechanism | `collect_role_binding_timing_phase_b2_v0_2.py` line 223 sets `environment["ANDROID_ADB_SERVER_PORT"] = str(adb.port)` immediately before the emulator `Popen` | Supported; prior source evidence only, not new runtime PASS |
| INFRA-M1 omitted the setting | M1 lines 473–484 constructed the inherited environment with `ANDROID_AVD_HOME` and `ANDROID_SDK_ROOT` but no `ANDROID_ADB_SERVER_PORT`, then passed that environment to `Popen` | Supported |
| The omission explains the observed default-port behavior | M1 emulator log says `Unable to connect to adb daemon on port: 5037`; later the same official `adb.exe` appeared as `adb -L tcp:5037 ...`, while 5038 never acquired `emulator-5554` | Supported as a bounded causal diagnosis; the correction is not yet live-qualified |

The installed emulator is version 36.6.11.0 (build 15507667); ADB is 1.0.41 / 37.0.0-14910828. Exact help outputs, executable hashes, binary-string neighborhoods, process inventory, netstat state, source neighborhoods, and M1 log neighborhoods are preserved under `infra_m2_registration_audit`.

## Rejected alternatives

- `-port 5554` chooses the emulator console and reserves 5555 for the guest ADB transport. It does not choose the host ADB server socket.
- `-ports <console>,<adb>` also controls the emulator console/local transport pair; pinned help explicitly warns that such an instance may not be seen by adb. It is not a replacement for selecting server 5038.
- `-adb-path` chooses which ADB executable the emulator uses, not which server socket that executable/runtime contacts.
- `-no-direct-adb` changes internal-versus-external bridge behavior and is a broader mechanism change. No evidence requires it.
- `ADB_SERVER_SOCKET` and `ANDROID_ADB_SERVER_ADDRESS` are recognized by ADB, but the emulator qemu evidence and prior local launcher converge specifically on `ANDROID_ADB_SERVER_PORT`; adding multiple simultaneous controls would make the intervention ambiguous.

## Frozen-protocol eligibility

`ELIGIBLE_FOR_INFRA_M2_PROTOCOL_FREEZE`, with exactly one registration correction:

```text
emulator_child_environment["ANDROID_ADB_SERVER_PORT"] = "5038"
```

The next protocol must also:

1. verify and stop the currently known project runtime only, including the M1-created 5037 PID 24580 after exact binary/command/listener ownership checks;
2. start the locked official ADB server on 5038 before launching the AVD;
3. record an auditable environment allowlist/value and prove the emulator/qemu process was launched from that environment;
4. fail immediately if a 5037 listener or a new 5037 ADB process appears at any pre-launch, launch, readiness, burn-in, or terminal observation;
5. use a new stdout/stderr root and never reuse a frozen log handle;
6. require boot readiness and 24 cycles over at least 180 seconds before any separately gated a11y work.

No restart is authorized by this audit commit itself. The implementation, offline gates, lock, commit, and tag must precede the one M2 launch.

## Artifact index

- Machine audit: `05_project/artifacts/role_binding_timing/infra_m2_registration_audit/registration_audit.json`
- Raw manifest: `05_project/artifacts/role_binding_timing/infra_m2_registration_audit/artifact_manifest.json`
- Audit capture script: `05_project/scripts/audit_role_binding_timing_infra_m2_registration.py`
