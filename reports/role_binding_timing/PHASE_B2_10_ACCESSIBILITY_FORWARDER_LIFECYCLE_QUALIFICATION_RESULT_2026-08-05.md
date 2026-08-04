# B2.10 DEV accessibility-forwarder lifecycle qualification result

## Final verdict

**`FAIL_LIFECYCLE_REBIND` at `REBIND_COMMAND:wake`.** The one frozen batch stopped on its first hard failure. AndroidEnv was never created, the accessibility service was not disabled/rebound, Settings qualification remained 0/3, and the 12-cell DEV grid remained unauthorized and 0/12.

This is a command-lifecycle/infrastructure failure. It is not evidence about accessibility transport repair, snapshot quality, role-binding timing, memory, controller efficacy, or an outcome oracle. v0.3 preparation is not authorized.

## Separate evidence phases

- Read-only root-cause audit commit: `532d202ae5594d31f7fc96a2447fb8638623de23`.
- Protocol/implementation freeze commit: `58b004d596c39338c4133920c566856e7214f9af`.
- Freeze tag: `role-binding-timing-b2.10-lifecycle-qualification-freeze-20260805`, resolving exactly to the freeze commit.
- B2.9 and all earlier frozen verdicts/artifacts remained unchanged.

The audit established 313 forwarder send attempts to the exact B2.9 host endpoint, 313 timeout warnings, and zero successes. It justified the bounded generic intervention but did not causally prove the credentials mismatch.

## Offline gates before mutation

The authoritative v2 gates ran on the exact frozen source:

| Gate | Result |
|---|---:|
| New lifecycle focused tests | 17/17 passed |
| Role-binding-timing namespace | 103/103 passed |
| Full regression | 1236 passed, 1 known legacy failure |
| Known failure | protected r79/r78 Gate-F frozen-manifest hash mismatch only |
| Source isolation | passed; no app/task/coordinate/H17/r79 production branch |
| Zero-call runtime preflight | passed |

The pre-freeze runtime identity was ADB 5038 PID 29964 and emulator gRPC 8554 PID 7172, with no 5037 listener. Generation calls, AndroidEnv sessions, held-out captures, and device mutations were all zero. The first gate result was retained as superseded because the runner's freeze check was then corrected to avoid a self-referential future-commit field; all gates were rerun in v2 after that generic correction.

## Frozen live execution

The preregistered first mutation was `adb -P 5038 -s emulator-5554 shell input keyevent 224`.

- It reached the 25-second frozen timeout (`25.219 s`).
- Return code is `null`, `timed_out=true`.
- Stdout and stderr are both empty, each with SHA-256 `e3b0c442...b855`.
- The 5038 listener remained the same PID before and after.
- Because this first command failed, the runner did not execute dismiss-keyguard, accessibility disable/clear, forwarder force-stop, component restore, service enable, readiness sampling, AndroidEnv creation, or any `get_state`.

Therefore the evidence does not establish whether the wake keyevent took effect. The exact failing layer is bounded ADB shell command completion/observability, not a proven Android action rejection.

## Cleanup and residue

Cleanup is secondary evidence and did not replace the primary failure:

- `DISABLE_GRPC` and `DISABLE_ACCESSIBILITY_TREE_LOGS` each printed a broadcast-completed payload but did not terminate before the 25-second timeout.
- `press_home` also timed out with empty output.
- AndroidEnv was never created, so there was no sidecar host listener to close and no implicit refresh/reconnect.
- Final listeners remained 5038/PID 29964 and 8554/PID 7172; 5037 and the random sidecar listener were absent.

A bounded read-only post-run check later returned `get-state=device`, `sys.boot_completed=1`, and `Service activity: found` in roughly 0.16–2.11 seconds. This suggests a transient command-completion stall, but it does not retroactively turn the frozen timeout into a pass and was not used to retry the batch.

## Accounting

| Item | Result |
|---|---:|
| Frozen batch wall time | 120.762 s |
| Model generation calls / tokens | 0 / 0 |
| AndroidEnv sessions | 0 |
| `get_state` calls | 0 |
| Rebind commands completed | 0/7 |
| Settings observations | 0/3 |
| DEV grid cells | 0/12 |
| Held-out captures | 0 |
| Terminal completion records | exactly 1 |
| Completion schema errors | 0 |

The authoritative completion record is `05_project/artifacts/role_binding_timing/phase_b2_10_accessibility_forwarder_lifecycle_qualification/qualification_completion.json`, SHA-256 `10b82d65697c6a19f9d61b8a5efff50f15920a96eb5c0966a2dbbbac6e669457`. The manifest SHA-256 is `31626ef61a96fedbab90ee0af51de2129f935b67cc9473a6c0df24f7bd556b49`; all 14 listed artifacts revalidated with zero mismatches.

## Claim–evidence verdict

| Claim | Verdict |
|---|---|
| B2.9 first broken edge was device-to-host a11y delivery | Supported by the separate audit |
| The B2.10 transport/lifecycle correction delivers a11y | Not tested; AndroidEnv was never created |
| Explicit service rebind succeeds | Not tested; execution stopped before the rebind settings commands |
| Same-observation screenshot+a11y is qualified | Not tested |
| Settings repeated observations pass | Rejected as a completed qualification; 0/3 run |
| 12-cell multi-app stability passes | Not tested; grid unauthorized |
| v0.3 preparation is authorized | Rejected |
| Role-binding timing or memory efficacy received evidence | Not tested |

## End boundary

B2.10 ends here under its first-failure stop rule. A future revision would need a new preregistration and must treat this exact run as contaminated infrastructure failure evidence; it may not repair and relabel this run. No held-out collection, Phase C, model generation, oracle evaluation, Destination-First Gate, or v0.3 preparation follows from this result.

The three protected r79 WIP SHA-256 values were identical before and after the batch, and they remain unstaged. No push was performed.
