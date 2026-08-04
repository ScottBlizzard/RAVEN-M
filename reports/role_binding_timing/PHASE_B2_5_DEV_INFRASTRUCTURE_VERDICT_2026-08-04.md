# Role-Binding Timing B2.5 DEV infrastructure stability verdict

## Verdict

**`NOT_ELIGIBLE`**. The frozen B2.5 DEV batch stopped at sequence 1 of 12, `R01-B25D-SETTINGS`, exactly as preregistered. No source/config/protocol change or retry occurred after the failure. A v0.3 protocol and candidate pool were therefore **not** created or run.

This is DEV-contaminated infrastructure evidence only. Generation calls remained 0; no model, held-out snapshot, timing × ambiguity cell, Phase C pilot, memory method, or Destination-First Binding Gate was run.

## First broken edge

The following preconditions passed:

- the official locked ADB binary owned the only 5038 listener, PID 29964;
- client/server binary SHA-256 was `957e46b8615f7af5b7292a2ddabe98d2e61940c3fb2b0545756507f080613e71`;
- device serial was `emulator-5554`, with no 5037 fallback;
- framework services `package`, `window`, and `activity` were present;
- Home + Settings force-stop reset-before completed;
- ADB PID was 29964 before and after every executed command.

The frozen launch command was:

`adb -P 5038 -s emulator-5554 shell am start -W -n com.android.settings/com.android.settings.Settings`

It returned process exit code 0 but its authoritative ActivityManager result was:

- `Status: timeout`;
- `LaunchState: UNKNOWN (-1)`;
- `Activity: com.android.settings/.homepage.SettingsHomepageActivity`;
- `WaitTime: 13590` ms;
- runner wall time 14.157 s.

The frozen launch contract rejects any non-`ok` `Status`, so the sequence recorded `LAUNCH_STATUS_NOT_OK` and stopped. The fact that Android reported a concrete redirected activity is insufficient to change the verdict: the protocol required a valid launch result before collecting foreground/UI witnesses. Accepting it after seeing the failure would be a post-hoc measurement change.

Because the failure occurred at launch, foreground activity/window evidence, raw UI tree, screenshot, locator provenance, framework-after-capture, reset-after, and framework-after-reset were not executed. Missing post-failure cleanup is therefore an additional unmet certificate condition, not hidden as success.

## What this resolves

| Claim | Evidence | Verdict |
|---|---|---|
| 5038 daemon instability caused this DEV failure | PID remained 29964; implicit restart count 0 | Rejected for this sequence |
| Framework services were unavailable | All three preregistered services passed before launch | Rejected |
| Generic reset-before failed | Home and force-stop records passed | Rejected |
| Launch completion was qualified | ActivityManager reported timeout/unknown launch state | Rejected |
| Settings probably reached a visible page anyway | Redirected activity name is suggestive, but foreground/UI were intentionally not observed after hard failure | Inference only |
| Foreground parser, UI dump, screenshot, or locator now pass | Those edges were not reached | Untested live |
| v0.3 may be frozen | DEV certificate failed 0/1 completed, planned 12 | Rejected |
| Timing × ambiguity hypothesis is supported or rejected | Zero model calls and zero held-out instances | Untested |

The narrow diagnosis is now **launch-completion/infrastructure qualification floor**, not ADB-server-identity failure. It also supplies a plausible mechanism for some v0.2 AndroidWorld five-second launch timeouts, but it does not retroactively identify each v0.2 foreground-`None` episode.

## Accounting and integrity

- Implementation freeze commit/tag: `e277055c8167a0b58655af6dc543448fa049c821` / `role-binding-timing-b2.5-dev-freeze-20260804`.
- Certificate: `infrastructure_certificate.v0_2_5.json`, SHA-256 `82b9210bb4ee905f39402235d4f8e47b019deb97f734b1964e44be2719709816`.
- Certificate schema errors: 0; terminal certificate count: exactly 1.
- Planned/completed/passed sequences: 12 / 1 / 0.
- Batch wall time: 21.672 s; failed sequence wall time: 18.797 s.
- Implicit ADB restarts: 0; framework failures: 0; generation calls: 0.
- Result root contains 4 raw files / 9,696 bytes: certificate, sequence trace, launch stdout, and empty launch stderr.
- Pre-freeze tests: B2.5 focused 14/14 and full `role_binding_timing` namespace 41/41 passed.
- The previous Phase-B full regression remains reported exactly as `1150 passed / 1 failed` with the known frozen-r79-manifest conflict; it was not rewritten.
- All result files are DEV-contaminated and held-out-ineligible.

## Stop decision

B2.5 stops here. No v0.3 freeze, fresh pool, one-shot qualification, Phase C, or generation is authorized. A future attempt would require a separately versioned and preregistered launch-outcome contract before any new DEV run; this failed batch cannot be retried or relabelled.
