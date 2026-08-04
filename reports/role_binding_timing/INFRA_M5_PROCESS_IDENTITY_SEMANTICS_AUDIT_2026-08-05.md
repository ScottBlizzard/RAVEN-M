# INFRA-M5 process-identity semantics audit

## Verdict

The M4 `EXCLUDED_PID_DRIFT` rule can confuse expected, short-lived project helper processes with forbidden unrelated-process drift. It is not a sufficient process-identity policy because it compares a static PID set rather than structural identities and roles.

This does **not** reinterpret M4. M4 remains immutable `RUNTIME_UNSTABLE` with first broken edge `FRAMEWORK_RUNTIME:EXCLUDED_PID_DRIFT`. The exact process that triggered that edge is unresolved because the inherited framework early-return path did not persist its triggering snapshot.

## Direct evidence

The inherited pipeline has two coupled rules:

1. `runtime_snapshot` places every `adb.exe`, `emulator.exe`, or qemu PID other than the listener-derived ADB server, launcher, and qemu core PIDs into `excluded_runtime_pids`.
2. `expected_runtime_issues` requires that list to be exactly the two abnormal PIDs seen before launch, 11316 and 17716.

This means an official child helper with a fresh PID is rejected solely because it did not exist before launch. Executable path, hash, command, parentage, creation time, ports, and role are not considered.

M4 boot observations 1–8 consistently saw only 11316/17716 in that list and the eighth boot observation passed. The framework gate then failed before setup and before its repeated service checks. The first edge was durably saved, but the snapshot that produced it was not.

The immediately subsequent cleanup snapshot contained 13 additional clients using the locked project `adb.exe`. Their commands were emulator bootstrap operations:

- `cmd overlay enable-exclusive`, for internal and SystemUI emulation categories;
- the emulator multidisplay START broadcast.

The locked qemu binary contains the matching overlay command fragments and the exact multidisplay action/component, alongside source-path strings for `QemuMiscPipe.cpp` and `MultiDisplay.cpp`. It also declares `crashpad_handler` and `netsimd` helper roles. There was no 5037 listener in the adjacent snapshot.

These facts demonstrate that the static rule is capable of false rejection. They do not reconstruct the missing framework snapshot, so they cannot prove which PID caused M4.

## Structural identity contract required for M5

Every observed process must carry:

- PID plus creation time, so PID reuse is detectable;
- absolute executable path and SHA-256;
- complete command line;
- parent PID and a recorded parent identity or ancestry chain;
- start time relative to the frozen launch epoch;
- owned listening ports;
- assigned role and first/last observed gates.

Roles and authority are distinct:

| Role | Required evidence | Authority |
|---|---|---|
| Preexisting unrelated | Exact prelaunch identity | May coexist or disappear; never adopted or killed |
| ADB server | Locked ADB path/hash, exact 5038 server grammar, owns 5038, immutable PID+start time | Core owned process |
| Emulator launcher | Locked launcher path/hash, frozen AVD/port/gRPC args, exact Popen PID | Core owned process |
| qemu | Locked qemu path/hash/args, launcher parent, owns 5554/5555/8554 | Core owned process |
| Official helper | Locked binary role, exact command grammar, bounded start interval, recorded ancestry to launcher/qemu | May exist transiently; no independent kill authority |
| Unknown new process | Anything missing, contradictory, unrecognized, or without qualified ancestry | Immediate fail-closed |

The 5037 listener remains forbidden under every role. The 5038 server identity may never change after qualification. A process with the same PID but a different creation time is a new identity. A helper whose parent record is missing is not accepted merely because its executable path looks familiar.

## Required observations and tests

M5 must persist a full process snapshot before and after every launch, boot, framework, burn-in, Settings, grid, cleanup, and seal transition. A failed classification must atomically save the complete triggering snapshot before returning the edge.

Offline tests must cover:

- accepted official short-lived child helpers;
- unrelated or new binaries;
- PID reuse;
- parent mismatch or absent parent evidence;
- listener owner change;
- 5038 server restart;
- triggering-snapshot persistence;
- preexisting unrelated-process non-adoption and non-kill authority.

## Claim–evidence boundary

| Claim | Verdict |
|---|---|
| Static prelaunch PID equality is sufficient | Rejected |
| M4 may have rejected a legitimate helper | Supported as a possibility |
| The exact M4 trigger was a legitimate helper | Unresolved |
| M4 should be relabeled PASS | Rejected |
| A structural policy is ready for live use | Not yet; implementation, tests, protocol freeze, and zero-call gates are required |
| Any a11y, held-out, model, memory, or role-binding claim | Untested |

No model call, device mutation, held-out capture, old-artifact edit, or LaTeX change occurred in this audit.
