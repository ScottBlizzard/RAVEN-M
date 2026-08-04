# Role-Binding Timing B2.6 DEV launch-observability diagnosis

## Verdict

**Outcome B — `B_RENDER_OR_UI_OBSERVABILITY_FLOOR`.** The frozen Settings launch eventually reached the foreground and rendered a usable screen, but the post-launch UI-tree channel failed in every bounded sample. The evidence therefore rejects “the app never became active” for this run, but it does **not** satisfy the preregistered Outcome-A rule for treating `am start -W` `Status: timeout` as a nonfatal signal.

`task_agnostic_timeout_correction_authorized=false`. The conditional v0.2.6 stability-certificate implementation was not created, the 12-cell DEV grid was not run, and no v0.3 protocol or candidate pool was prepared. This is DEV-contaminated infrastructure evidence only. Generation calls remained exactly 0.

## Frozen question and boundary

The diagnosis asked only whether the B2.5 `am start -W` timeout represented:

- **A:** the app foregrounded and both screenshot and UI tree worked, making the timeout a false-negative launch signal under a strict concordance rule;
- **B:** the app started/rendered but a rendering or UI-observability channel failed; or
- **C:** the app never became active, indicating an emulator/framework lifecycle floor.

The protocol required Outcome A to have at least two independent foreground sources **and** a usable screenshot **and** a usable, agreeing UI tree. Exit code 0 alone was never sufficient. The diagnostic protocol, config, classifier, runner, and tests were frozen at commit `ab61387ee9eb154721736bc4026c99a905b2a0c4` and tag `role-binding-timing-b2.6-diagnosis-freeze-20260804` before the single run.

## Direct evidence

### Launch and eventual display

The exact `am start -W` command returned process code 0 in 13.016 s and did not hit the host subprocess timeout, but Android's own result was:

```text
Starting: Intent { cmp=com.android.settings/.Settings }
Status: timeout
LaunchState: UNKNOWN (-1)
Activity: com.android.settings/.homepage.SettingsHomepageActivity
WaitTime: 12447
Complete
```

The bounded ActivityTaskManager log then recorded:

```text
14:11:00.372 START ... com.android.settings/.Settings
14:11:10.950 Launch timeout has expired, giving up wake lock!
14:11:32.480 Displayed com.android.settings/.Settings: +31s584ms
14:11:32.494 Fully drawn com.android.settings/.Settings: +31s584ms
```

Thus the timeout was a real ActivityManager readiness timeout, yet it was not evidence that the activity never appeared: Android reported the activity displayed and fully drawn 31.584 s after start.

Across all three post-`-W` samples:

- `dumpsys activity activities` and `dumpsys window displays` independently identified `com.android.settings` as foreground;
- the Settings process was active;
- each screenshot was a valid 1080×2400 PNG and visibly showed the rendered Settings homepage;
- boot-complete markers remained present, the display was on, wakefulness was awake, and keyguard was not showing.

The three screenshot SHA-256 values were `602d84816e72c578b6d67e37eca4086f5691fb873768b1d8bfb8f17b4afa7a4f`, `2fe5f4ff0e4dfbc4425c26415406acaef4bbf1133cd6d9ef637d43c4aa5660ad`, and `090bd1fc10a9ba82b105730f070529e7c91c34c9b0c96c01836baa05e2359db7`.

The subsequent non-`-W` start also returned code 0 and explicitly said the intent was delivered to the already running top-most instance. Both post-non-`-W` samples again had the same two foreground sources, an active process, and a valid screenshot.

### UI-tree failure

The pre-launch launcher observation had a usable raw UI tree containing the launcher package, so the channel was not globally absent before the action. In contrast, all five post-launch samples failed UI-tree qualification:

- `uiautomator dump` returned code 0, but no requested file was created;
- the subsequent device-side `cat` returned text such as `cat: /sdcard/rbt_b26_post_wait_01.xml: No such file or directory`;
- parsing therefore ended with `ParseError: syntax error: line 1, column 0` and no package evidence.

The runner retained the dump stderr SHA-256 (`406bd8df88b9c43b78dc2a75c35ee3f96f79a5b3ea922e8ead222b4c5b5752f9`) but not its literal stderr text. Consequently, the missing file and parse failure are direct evidence; the precise internal cause of `uiautomator dump` is **not** established by this run.

### ADB and cleanup isolation

- Official locked ADB binary SHA-256: `957e46b8615f7af5b7292a2ddabe98d2e61940c3fb2b0545756507f080613e71`.
- Explicit server/client port: 5038; device: `emulator-5554`; fallback to 5037: false.
- Listener PID was 29964 before and after every recorded command and remained the sole terminal listener PID.
- No implicit daemon restart was observed.
- Home and Settings force-stop cleanup both returned code 0; cleanup issues were empty.

These observations reject 5038 daemon loss as the cause of this particular diagnosis outcome.

## Claim–evidence matrix

| Claim | Evidence status | Verdict |
|---|---|---|
| `am start -W` reported a timeout | Raw stdout says `Status: timeout`, `LaunchState: UNKNOWN (-1)` | Directly supported |
| The command's exit code alone proves launch success | Exit code was 0, but Android reported timeout | Rejected |
| The app never became active | Two foreground sources, active process, three usable screenshots, and `Displayed/Fully drawn` log entries | Rejected for this run |
| The app eventually foregrounded and rendered | Concordant activity/window/process/screenshot/logcat evidence | Directly supported |
| Full Outcome-A observability was achieved | All five post-launch UI-tree observations were unusable | Rejected |
| The `-W` timeout may now be treated as generically nonfatal | Preregistered rule also required usable screenshot and UI tree; UI tree failed | Not authorized |
| The first current floor is launch-observability/UI-tree collection | Launch/render witnesses passed while the required semantic tree channel failed | Supported for this DEV run |
| The precise internal UI-dump failure mechanism is known | Literal dump stderr was not retained | Unresolved |
| 5038 daemon loss caused the failure | PID 29964 remained continuous, with no restart/fallback | Rejected for this run |
| The 12-cell stability grid qualifies | It was not authorized or run | Untested |
| A v0.3 held-out pool may be frozen | Conditional prerequisite was not met | Not eligible |
| Timing × role ambiguity or memory efficacy is supported | Zero model calls and zero held-out instances | Untested; no hypothesis evidence |

## Accounting and integrity

- Single frozen diagnostic wall time: 177.343 s.
- Raw result root: 92 files, 4,295,087 bytes (7 JSON, 73 text, 6 PNG, 6 XML).
- Terminal result: `launch_diagnosis.v0_2_6.json`, SHA-256 `5cd15915568460cd28631b18dba97c1b8578d8f2e71021162c6df95bdbdc925c`.
- ActivityTaskManager log artifact: 634 bytes, SHA-256 `c58a7311273ffd3a9866bd1025fcb6a318983a40f846923a2f7574f317bc1757`.
- Source hashes recorded in the terminal result: classifier `e4b6281c000d79e2b582174260ccf596108fafb0d90492417f1b480309d6806f`, config `aabbf4a8d099774f08b28c38134c61488126c5c87a097bfa6b820a6ca7c31b2d`, runner `e049ff3e0dd74dfde7a83a79db882c7e6fd9ee3ac2ab4120ccb079568546bffc`.
- Frozen offline gates: 21/21 focused diagnosis/infrastructure tests and 48/48 full `role_binding_timing` tests passed; Python compilation, CLI help, and frozen-diff checks passed.
- No model generation, held-out capture, Phase C pilot, method patch, LaTeX modification, or push occurred.

## Stop decision

B2.6 stops at Outcome B. Because the evidence does not authorize the task-agnostic timeout correction, the conditional implementation-freeze and 12-cell result phases do not exist for this version. Any future work must preregister a separate, general UI-tree/semantic-observability diagnosis; this contaminated Settings trace cannot be retried or relabelled as held-out evidence.
