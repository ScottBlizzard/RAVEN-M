# Role-Binding Timing B2.7 DEV UI-tree export diagnosis

## Verdict

**`UIAUTOMATOR_TOOL_FAILURE`; no acquisition path qualified.** The frozen 16-attempt matrix completed without primary error, schema error, command timeout, ADB PID drift, or cleanup failure, but produced 0 valid XML exports. `task_agnostic_acquisition_authorized=false`.

The evidence localizes the current failure before file serialization or host parsing: `UiTestAutomationBridge` returned a null root node under every preregistered combination. The generic wake/dismiss-keyguard precondition did not change the outcome because the device was already demonstrably interactive and non-idle before it was applied.

Per the frozen stop rule, no new collector implementation was created, the four-app × three-round DEV stability grid was not rerun, and no v0.3 protocol was prepared. Generation calls and held-out captures remained 0.

## Frozen design

The protocol/tooling was frozen at commit `d8b1479bc8673f0801943ed0d2baffa44f404449` and tag `role-binding-timing-b2.7-diagnosis-freeze-20260804` after 32/32 focused/adjacent tests and 59/59 complete `role_binding_timing` tests passed.

The one-shot matrix contained:

- two preconditions: observed state and generic `KEYCODE_WAKEUP` + `wm dismiss-keyguard`;
- normal and `--compressed` dump modes;
- unique `/sdcard` file output and direct `/dev/tty` output;
- two planned repetitions of every path.

That is 2 × 2 × 2 × 2 = 16 attempts. Each attempt preserved exact binary stdout and stderr, command duration/result, target `ls/stat` before and after, four raw device-state channels before and after, acquired candidate bytes, XML validation, and 5038 listener PID before and after every command.

## Direct evidence

### Scene and interaction state

The Settings DEV scene passed the non-UI-tree readiness gate after three samples: the final two consecutive samples had concordant activity/window package evidence, an active process, and a valid 1080×2400 screenshot.

Both preregistered preconditions reported:

- `display_interactive=true` from the raw display dump;
- `wakefulness_awake=true`;
- `display_on=true`;
- `keyguard_showing=false`;
- `device_idle=false`;
- `interactive_verified=true`.

This resolves the B2.6 `interactive_true=false` observation as an incomplete parser location: B2.6 checked the power dump, while this emulator exposed `mInteractive=true` in the display dump. The wake/dismiss command did not turn a non-interactive state into an interactive one; both sides were already qualified.

### Dump matrix

All 16 dump processes returned code 0, none hit the 20-second host timeout, and all retained ADB PID 29964. Nevertheless, all 16 candidates lacked any XML envelope and failed with `ValueError:XML_ENVELOPE_MISSING`.

For the eight remote-file attempts:

- dump stdout was empty;
- exact stderr was the 59-byte CRLF-terminated message `ERROR: null root node returned by UiTestAutomationBridge.`;
- stderr SHA-256 was `03df3acbb061e8724961b6980f150d801858d9c4d9a3fa1f832afe3a6ff5c228` in all eight attempts;
- post-command `ls` said the unique XML path did not exist;
- device-side `cat` likewise returned `No such file or directory`.

For the eight direct-stdout attempts:

- `/dev/tty` existed according to `ls`;
- exact stdout was the equivalent 58-byte LF-terminated message `ERROR: null root node returned by UiTestAutomationBridge.`;
- stdout SHA-256 was `406bd8df88b9c43b78dc2a75c35ee3f96f79a5b3ea922e8ead222b4c5b5752f9` in all eight attempts;
- stderr was empty;
- no XML envelope was present.

The `406bd8...` hash is also the normalized dump-error hash retained by B2.6, explaining its previously opaque code-0/no-file behavior without changing the immutable B2.6 verdict.

Normal versus compressed mode made no qualitative difference. Dump durations ranged from 5.828 to 16.125 seconds. The usage output confirmed this platform advertises both file output and `--compressed`; direct `/dev/tty` was tested as the frozen alternate transport and failed with the same bridge-level error.

### System diagnostics

Logcat shows a fresh `com.android.commands.uiautomator.Launcher` entry and `UiAutomation` initialization for each invocation. It also contains repeated AccessibilityManager slow-dispatch/contention warnings. These entries are consistent with work reaching the UI automation/accessibility subsystem, but they do not establish why the bridge returned a null root. The exact deeper framework mechanism therefore remains unresolved even though the preregistered root-cause class is the UIAutomator tool layer.

### Stat telemetry limitation

The frozen `stat -c %n|%s|%f|%Y <target>` arguments were passed through `adb shell` without protecting the pipe characters. The device shell interpreted them as pipelines; all 16 stat records returned 127 and are non-informative. This is preserved as a diagnostic-harness limitation and was not repaired or rerun.

It does not authorize a different classification: remote-file absence is independently observed by both `ls` and `cat`, while the direct-output cells bypass remote XML creation entirely and still return the identical null-root error. No claim relies on the invalid stat values.

## Claim–evidence matrix

| Claim | Evidence | Verdict |
|---|---|---|
| B2.6 failed because the device was asleep, locked, or idle | Both observed and wake phases were interactive, awake, display-on, unlocked, and non-idle | Rejected |
| Generic wake/dismiss repairs UI export | 0/8 observed and 0/8 wake-phase attempts produced XML | Rejected |
| Compression repairs UI export | 0/8 compressed and 0/8 normal attempts produced XML | Rejected |
| Remote path creation is the sole failure | Direct `/dev/tty` attempts bypassed the `/sdcard` file and returned the same null-root error | Rejected |
| Host parser discarded valid XML | No candidate contained an XML envelope | Rejected |
| UIAutomator returned a null root before serialization | Exact byte-identical error across all 16 attempts | Directly supported |
| The deeper accessibility/framework cause is known | Logcat shows initialization and contention but no definitive causal exception | Unresolved |
| A generic acquisition path is qualified | 0 qualified paths, 0/16 valid attempts | Rejected |
| New collector implementation may begin | Frozen authorization flag is false | Rejected |
| The 12-cell DEV grid or v0.3 may proceed | Prerequisite acquisition path did not qualify | Rejected |
| Role-binding timing or memory efficacy is supported | Zero model calls and zero held-out captures | Untested; no hypothesis evidence |

## Accounting and integrity

- Matrix attempts: 16 planned / 16 completed / 0 valid.
- Matrix completion: true; primary error: null; schema errors: 0.
- Total wall time: 531.140 s.
- Result root: 538 files / 6,890,520 bytes (518 `.bin`, 20 `.json`).
- Terminal result SHA-256: `c20bab707cf318e183ebabe9c5bd1117c48c78393685628548fcd56e547bf1ad`.
- Explicit ADB port: 5038; official binary SHA-256 `957e46b8615f7af5b7292a2ddabe98d2e61940c3fb2b0545756507f080613e71`.
- Listener PID: 29964 throughout and at termination; no 5037 fallback or implicit restart.
- Cleanup: Home and force-stop both passed; cleanup issues were empty.
- Generation calls: 0; held-out eligibility: false; all evidence is DEV-contaminated.

## Stop decision

B2.7 stops at the UIAutomator tool layer. The next permissible work, if separately authorized, is a new zero-model framework/accessibility export investigation using a newly preregistered acquisition mechanism. This failed matrix cannot be repaired, retried, relabelled, or used to support the role-binding hypothesis.
