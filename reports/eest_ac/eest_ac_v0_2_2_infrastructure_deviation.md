# EEST-AC v0.2.2 Infrastructure Deviation: Explicit ADB Server Port

Observed: 2026-08-04, before the v0.2.2 live lock and before any v0.2.2 generation call.

## Deviation

The normal local ADB server port 5037 could not be reused because a pre-existing orphan `adb.exe` process remained in the Windows process table with no executable path or command line and could not be terminated under the current account. It did not expose a usable listener. Repeated official-client attempts to start a new server on 5037 failed before AndroidWorld environment creation.

An official ADB server was therefore started on port 5038. This is acceptable only as an explicit, frozen, task-agnostic runtime parameter. The v0.2.2 config, zero-call preflight, AndroidWorld loader, qualification runner, task actions, and reset actions all use 5038. Port mismatch fails before environment creation. There is no automatic or in-run fallback to 5037.

## Frozen identity

- ADB server port: `5038`.
- ADB client binary: `D:/ZJU/Summer_Camp/RAVEN-M-Research/06_local_runtime/android/sdk/platform-tools/adb.exe`.
- ADB client SHA-256: `957e46b8615f7af5b7292a2ddabe98d2e61940c3fb2b0545756507f080613e71`.
- ADB server executable: the same official binary.
- ADB server SHA-256: `957e46b8615f7af5b7292a2ddabe98d2e61940c3fb2b0545756507f080613e71`.
- Device serial: `emulator-5554`.
- Initial readiness check: official server discovered the serial, transport reached `device`, and `sys.boot_completed=1`.

The preflight rechecks port, both binary hashes, serial, device observation, adapter coverage, and model revision. Failure of any check forbids live probes.

Before measurement-contract v2 is allowed to pass, the same official client must also complete a frozen stress audit: 25 rounds of four commands (`get-serialno`, `get-state`, `sys.boot_completed`, and a shell echo), for 100 sequential commands total. Every subprocess includes `-P 5038` and `-s emulator-5554`, has a bounded timeout, and must return the exact expected value. The listener PID and server-binary hash must be unchanged before and after; an attempted runtime assertion using 5037 must be rejected as `fallback=forbidden`. Any failure ends v0.2.2 at the infrastructure floor.

## Why this does not change the controller claim

ADB server port selection is a local transport parameter below the decision envelope, parser, action adapter semantics, and model endpoint. It neither changes screenshots nor rewrites model output, canonical actions, evidence/citations, intent metadata, state-change criteria, or reset criteria. The model service remains independently pinned by ID, revision, and backend on its existing endpoint. Using one frozen port for the complete preflight/execute/reset chain avoids cross-port trajectory differences.

The qualification can support a controller-contract claim only if all three live cells use the frozen 5038 path and the final process audit confirms no fallback. If 5038 cannot stably expose the device, the study stops as an infrastructure failure and produces no live controller verdict.
