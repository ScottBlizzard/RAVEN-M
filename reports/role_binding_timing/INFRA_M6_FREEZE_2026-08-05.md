# INFRA-M6 Freeze Record

Date: 2026-08-05

## Frozen claim boundary

INFRA-M6 asks only whether a task-agnostic multi-source display quorum and exact cleanup-only helper ancestry can support one complete DEV maintenance chain. It authorizes zero model calls and zero held-out captures. PASS cannot support role-binding, memory, controller-efficacy, or collection-quality claims; it can only authorize preparation, not execution, of a later v0.3 protocol.

M5 remains immutable `RUNTIME_UNSTABLE:FRAMEWORK_NOT_STABLE`. The M6 read-only audit commit is `5503317e8e990825db14c70db277e3d8f04c8f4c`.

## Offline evidence

Two offline roots are retained.

- Attempt 01: `overall_pass=false`. All pytest, schema, source, binary, protected-WIP, full-regression, and runtime gates passed except the psutil hash comparison. The M6 config contained a one-character transcription error (`...b1fe2...`) against both the actual locked module and the accepted M5 config (`...b1fa2...`). This attempt is preserved and was never generation/live eligible.
- Attempt 02: `overall_pass=true`. The only change was correcting that literal to the directly measured binary SHA-256. It reran every gate from scratch in a new root.

Attempt 02 evidence:

| Gate | Result |
|---|---|
| Compile | PASS |
| M6 focused display/cleanup/terminal tests | PASS, 22 tests |
| Frozen M5 process-identity tests | PASS, 15 tests |
| Frozen M4 terminal-accounting tests | PASS, 17 tests |
| Complete role-binding-timing namespace | PASS |
| Full project regression | Accepted with exactly one preregistered r79 frozen-manifest failure |
| Completion schema/corruptions | PASS |
| Source isolation/no model/no 5037 command | PASS |
| Binary, psutil, protected-WIP hashes | PASS |
| Zero-device runtime preflight | PASS: no listeners on 5037/5038/5554/5555/8554, no project runtime process, no M6 temp residue |

All stdout/stderr and result bytes are retained with SHA-256 in the two offline roots and enumerated by the M6 lock.

## Frozen measurement policy

- Required, conjunctive planes: display service, power, window/policy, and validated screencap.
- SurfaceFlinger is optional only when unavailable/empty; returned unrecognized or contradictory output fails closed.
- A missing legacy M5 marker is never interpreted as OFF.
- A screenshot alone never establishes framework health.
- Framework qualification requires 3 consecutive passing samples within 20 attempts.
- Burn-in requires 24/24 passing cycles and at least 180 seconds.
- Cleanup helper authority exists only for the exact qemu → locked `cmd.exe` → locked official emulator `-kill <qemu-pid> -sleep 20` chain.

## Live authorization

After the lock is committed and tagged, exactly one fresh M6 chain is authorized. Source, config, protocol, schema, tests, and thresholds may not change after the tag. The first failing gate stops all later gates; cleanup and sealing remain secondary evidence and cannot replace the first edge.
