# INFRA-M5 Process-Identity Semantics — Result

## Verdict

**FAIL — `RUNTIME_UNSTABLE`; first broken edge: `FRAMEWORK_NOT_STABLE`.**

The single frozen M5 chain passed exclusive-5038 launch and boot, but all 20 preregistered framework observations reported `display_on=false`. Package, window, and activity services were healthy in all 20 observations; `awake`, `interactive`, `keyguard_not_showing`, and `no_dead_object` were also true in all 20. Process identity had no failure during launch, boot, or the 20 framework checks. The chain therefore stopped before burn-in, Settings accessibility qualification, and the 4-app × 3-round DEV grid.

This is infrastructure-only, DEV-contaminated evidence. It contains zero model calls, zero model tokens, zero held-out captures, and no role-binding, memory, controller, or task-efficacy result. It does not authorize v0.3 preparation.

## Phase accounting

| Phase | Result | Direct evidence |
|---|---:|---|
| Freeze/offline gates | PASS | M5 focused 15/15; M4 terminal accounting 17/17; namespace PASS; full regression had only the frozen r79 manifest conflict |
| Launch | PASS | 3 discovery attempts; locked ADB on 5038, launcher, and qemu identities registered; no 5037 |
| Boot | PASS | 12 bounded attempts; device and boot-complete evidence passed |
| Framework | **FAIL** | 20/20 services and identity checks passed, but `display_on=false` in 20/20; maximum stable consecutive count 0/3 |
| Burn-in | NOT RUN | Stop rule applied; 0/24 |
| Settings a11y | NOT RUN | 0/3 |
| DEV grid | NOT RUN | 0/12 |
| Terminal writer | PASS | one rich completion, 12 journal entries, schema valid, 667-entry repository manifest verified |

Frozen run wall time was 257.697 seconds. There were 83 gate snapshots and 407 continuous process samples covering 73 unique structural history records, with no sampler errors.

## What M5 says about the M4 PID rule

The evidence supports a bounded conclusion: the M4 static equality rule was overbroad. M5 admitted, by path/hash/command/parent/time/role evidence, 15 unique emulator bootstrap ADB helpers, 24 runner ADB clients, one official netsimd process, and one official emulator crashpad process while completing launch, boot, and all 20 framework identity checks without process drift. These are processes that a static “only prelaunch PIDs may exist” comparison cannot distinguish from unrelated drift.

The stronger historical claim remains unavailable: M4 did not persist the exact snapshot that triggered `EXCLUDED_PID_DRIFT`, so the exact M4 offending PID cannot be reconstructed. M4 remains immutable and is not reclassified.

## Secondary cleanup finding

Cleanup physically succeeded: the canonical emulator stop and explicit 5038 server stop returned successfully, the emulator/qemu and 5038 server exited, and the final listeners on 5037, 5038, 5554, 5555, and 8554 were all empty.

The frozen process policy nevertheless returned a **secondary** cleanup failure. It observed the official locked command `emulator.exe -kill 36924 -sleep 20`, started through the locked `cmd.exe` whose parent was the frozen qemu PID, but the generic wrapper predicate only authorized ADB-bearing wrappers. This caused `HELPER_PARENT_CHAIN` at snapshot 83. The result correctly preserved `FRAMEWORK_NOT_STABLE` as the primary edge; no code was patched and no retry was run.

Because the terminal cleanup verdict was false, the runner did not call its normal log-seal phase. After the runner and owned processes had exited, the already-closed external logs were copied once into `postmortem_external_logs/` and `postmortem_runner_console/`, hashed, and their exact temporary sources removed. This preservation step does not change the terminal log-seal verdict or overall FAIL.

## Claim–evidence ledger

| Claim | Verdict | Evidence / boundary |
|---|---|---|
| Static excluded-PID equality is an adequate ownership rule | **Rejected, bounded** | M5 safely admitted many evidenced official transient helpers that M4 would count as PID drift; exact M4 trigger remains unavailable |
| M5 process semantics qualified end-to-end | **FAIL** | Runtime gates were clean, but the shutdown-wrapper ancestry grammar failed during cleanup |
| Runtime qualified for burn-in | **FAIL** | `display_on=false` in every one of 20 framework observations |
| Accessibility sidecar qualified | **Untested** | Settings 0/3 |
| Multi-app grid qualified | **Untested** | Grid 0/12 |
| v0.3 preparation authorized | **No** | Requires 12/12 DEV after all earlier gates |
| Role-binding or memory hypothesis tested | **No** | Zero model calls and zero held-out captures |

## Integrity and stop boundary

- Freeze commit/tag: `38fc46e7e8d036851543678e4ab1be01537e722f` / `role-binding-timing-infra-m5-freeze-20260805`.
- Generation calls / tokens / held-out captures: `0 / 0 / 0`.
- Terminal completion: exactly one, rich mode, schema valid.
- Repository manifest: 667 entries, all verified; SHA-256 `c35d1fd1cd22cabf37652cd7ce28e8296250ecd119596ba038fc0e443c389126`. Its only transport adjustment is the result-root `.gitattributes` newline (`CRLF` runtime metadata to `LF` Git metadata); both byte/hash pairs are recorded in `postmortem_audit.json`, and no raw command, process, terminal, or experiment evidence changed.
- Protected r79 WIP hashes remained exactly unchanged.
- No listener remained on 5037/5038/5554/5555/8554, and no project ADB/emulator/qemu process remained.
- M5 stops here. No retry, new live chain, held-out capture, model generation, Phase C, or v0.3 preparation is authorized.

Machine-readable details are in `postmortem_audit.json`; the frozen terminal verdict remains in `qualification_completion.json`.
