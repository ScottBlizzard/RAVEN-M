# INFRA-M6 Result

- Date: 2026-08-05
- Frozen input commit/tag: `7f7ee217b08e16032fce18a211ff8075ef548b46` / `role-binding-timing-infra-m6-freeze-20260805`
- Mode: zero-model, DEV-only, one frozen live chain

## Final verdict

**FAIL — `PROCESS_IDENTITY_FAILED_BEFORE_DISPLAY_QUORUM`.**

The first broken edge is:

`PROCESS_IDENTITY:PROCESS:496@1785880048.227501:ADB_COMMAND_ROLE`

It was first persisted at `boot_16_after`. The run stopped before framework/display qualification, burn-in, Settings a11y, or the 12-cell DEV grid. Consequently, INFRA-M6 does not answer the display-observability question and does not authorize preparation of v0.3.

## Direct failure evidence

The continuous process history contains the complete rejected identity:

- executable: locked project `adb.exe`;
- executable SHA-256: `957e46b8615f7af5b7292a2ddabe98d2e61940c3fb2b0545756507f080613e71`;
- command: `adb.exe -P 5038 devices -l`;
- parent: the frozen M6 runner PID;
- first persisted policy failure: `boot_16_after`;
- classification: `ADB_COMMAND_ROLE`.

This command is not an unrelated process. It is the task-agnostic, read-only `devices -l` command invoked by the frozen boot-readiness loop itself. The inherited M5 client policy accepts direct-runner serial commands and start/kill-server operations but does not accept this non-serial discovery command. M6 therefore produced a policy false rejection. The short-lived client was caught by continuous sampling on this attempt; its first capture does not imply that boot attempt 16 was its first invocation.

The result does not show that boot or display would otherwise have passed. Boot readiness had not yet qualified, and no M6 display quorum sample was executed.

## Gate accounting

| Gate | Result |
|---|---|
| Lock/tag/hash preflight | PASS, 59/59 inputs |
| Exclusive 5038/core registration | PASS |
| Launch | PASS |
| Boot | FAIL at attempt 16 due process-policy rejection |
| Display/framework quorum | NOT RUN |
| Burn-in | 0/24, NOT RUN |
| Settings a11y | 0/3, NOT AUTHORIZED |
| Four-app DEV grid | 0/12, NOT AUTHORIZED |
| Generation calls / model tokens | 0 / 0 |
| Held-out captures | 0 |
| Terminal completion | PASS, rich mode, schema-valid, exactly once |

## Cleanup and evidence sealing

The canonical completion correctly retains `cleanup.passed=false` and `log_seal.passed=false`. The same historical PID 496 record was re-evaluated during cleanup, so cleanup policy remained false and the runner skipped normal sealing. These canonical values were not rewritten.

Direct secondary evidence shows:

- the emulator stop and 5038 ADB stop commands returned successfully;
- the exact qemu → locked `cmd.exe` → official emulator `-kill <qemu-pid> -sleep 20` helper was accepted as `emulator_shutdown_helper`;
- registered emulator/ADB core identities are gone;
- no listener remains on 5037, 5038, 5554, 5555, or 8554;
- two external logs passed closed-handle rename probes, were copied once into `postmortem_sealed_logs`, hashed, and their project-owned temporary root was removed.

This postmortem copy is recovery of evidence after termination, not a relabeling of the frozen runner's log-seal gate.

## Claim–evidence verdict

| Claim | Verdict |
|---|---|
| M5's `display_on=false` was caused by a marker/command mismatch. | Supported by the separate M6 audit; M5 remains immutable. |
| M6 process policy falsely rejected its own locked `devices -l` client. | Supported by executable hash, exact command, parent identity, runner source, and continuous history. |
| M6 cleanup-only shutdown ancestry works for the observed exact chain. | Narrow implementation signal only; the helper was classified correctly. |
| M6 display quorum is valid or stable. | Untested; framework gate never ran. |
| Burn-in or AndroidEnv a11y is stable. | Untested. |
| v0.3 collection may be prepared. | No. |
| Role-binding timing, memory efficacy, or controller efficacy was tested. | No. |

## Integrity

- Original terminal validation: schema-valid, one `qualification_completion.json`.
- Original finalizer manifest: all recorded files present and hash-valid.
- Postmortem manifest: 277 artifacts before adding the manifest itself, each with bytes and SHA-256.
- Frozen lock: 59/59 paths present and unchanged.
- Protected legacy WIP: all three before/after/current hashes match the preregistered values.
- Formal LaTeX report: untouched.
- No Git push performed.

## Stop decision and next boundary

M6 stops here and remains FAIL. No retry, display-threshold adjustment, a11y run, DEV grid, held-out capture, or model call is permitted under this version.

A future separately reviewed infrastructure version would first need to broaden the runner-client grammar in a task-agnostic way to include exact explicit-port, read-only discovery commands while retaining direct-runner parent, locked binary/hash, 5037 veto, port-owner continuity, PID reuse checks, and fail-closed behavior. That repair must be tested and frozen before any new live chain; this M6 run cannot be relabelled or reused as qualification evidence.
