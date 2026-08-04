# INFRA-M3 log-ownership audit

## Verdict

The INFRA-M2 pre-launch failure was caused by a structural evidence-lifecycle mistake: an actively written descendant-process log was placed inside a result artifact root and then treated as an immutable frozen input. A natural shutdown append was therefore both legitimate process behavior and a lock violation.

The exact lingering handle owner was identified and released without targeting unrelated processes. The affected M1 file was then restored to its exact committed blob. This remediation does not revise any M1/M2 result or verdict; M2 remains an immutable pre-launch failure.

## Direct evidence

| Question | Evidence | Finding |
|---|---|---|
| Where did M1 write emulator logs? | `run_role_binding_timing_infra_m1_maintenance.py` opens `emulator.stdout.bin` and `emulator.stderr.bin` directly below its result root before `Popen`. | The log was live while already located in a would-be immutable artifact tree. |
| What changed at M2 shutdown? | M2 terminal record: 9,590 bytes / `ffddf9d…` before shutdown and 13,912 bytes / `343e0e8f…` after emulator exit. | Natural shutdown appended exactly 4,322 bytes. |
| Who retained the file handle? | Windows Restart Manager, registered against the exact file, returned only PID 24580, `adb.exe`, application type console. | The handle belonged to the project-created official 5037 server. |
| Was that process identity verified? | PID 24580 executable path matched the locked platform-tools `adb.exe`, SHA-256 `957e46b…`; command line was `adb -L tcp:5037 fork-server server --reply-fd 748`. | Safe narrow shutdown was available. |
| Were unrelated processes touched? | Only `adb.exe -P 5037 kill-server` was issued; excluded unknown PIDs 11316 and 17716 were not targeted. | No unrelated process termination. |
| Was the contamination restored exactly? | Restored blob `f9edacd191d3a5e65a307afe1588528c7faacd9f`; 9,590 bytes; SHA-256 `ffddf9d0862f8f3e58b424e1e8f774e546875634a0ba81f5e720333284b48b1c`. | Exact restoration passed; appended version was never staged. |

## Root-cause classification

`ACTIVE_LOG_INCLUDED_IN_IMMUTABLE_ARTIFACT_ROOT`

The primary defect is not that the emulator emitted shutdown text. The defect is combining two incompatible roles in one path:

1. a live stdout/stderr sink inherited across a process tree; and
2. an immutable, already-hashed result artifact.

M2's drift guard correctly prevented silent mutation, but repeating M2 would reproduce the same design conflict and would not test exclusive-5038 registration.

## M3 corrective contract

M3 must enforce all of the following before a live run:

- every emulator/ADB/a11y live stdout/stderr path is under a fresh OS-temporary run directory outside the repository and outside every artifact/frozen root;
- no prior frozen log path is opened for append, truncate, replacement, or restoration;
- the temporary root is not an immutable lock input and its live contents are not hashed as frozen protocol evidence;
- process owners are cleanly stopped and all parent-side handles are closed before sealing;
- an exclusive-open/rename-style handle-closure proof succeeds before copying;
- finalized logs are copied into a new result root exactly once, then hashed and included in the terminal manifest;
- path containment and lifecycle ordering are covered by corruption tests;
- M3 still uses the independently audited `ANDROID_ADB_SERVER_PORT=5038` child environment, with 5037 forbidden after residual-server cleanup.

## Claim boundary

This audit supports the handle-owner diagnosis and exact restoration only. It provides no live evidence that exclusive 5038 registration, burn-in stability, AndroidEnv accessibility, the 4×3 DEV grid, held-out collection, or the role-binding timing hypothesis works. Generation calls and held-out captures remain zero.
