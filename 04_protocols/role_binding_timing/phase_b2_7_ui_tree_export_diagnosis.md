# Role-Binding Timing B2.7 DEV UI-tree export diagnosis

Status: frozen, bounded, DEV-contaminated command-observability diagnosis. Generation calls and held-out captures are forbidden.

## Question

On the already contaminated native Settings scene, why can `uiautomator dump` return code 0 without leaving a usable remote XML file even though activity, window, process, and screenshot evidence show a rendered foreground page?

The allowed root-cause labels are:

1. `DEVICE_NON_INTERACTIVE_OR_IDLE_STATE_FAILURE`;
2. `REMOTE_PATH_OR_FILE_CREATION_FAILURE`;
3. `UIAUTOMATOR_TOOL_FAILURE`;
4. `PARSER_OR_CAPTURE_BUG`;
5. `UNRESOLVED`.

This diagnosis does not test a model, role binding, memory, or task efficacy.

## Fixed setup and evidence

The official locked ADB binary, explicit port 5038, serial `emulator-5554`, and PID-continuity rules are inherited from B2.6. There is no fallback or implicit daemon restart. Settings is started once with a non-waiting generic activity command, then qualified without UI-tree evidence using two consecutive samples in which activity and window identify the expected package, the process is active, and the screenshot is a valid 1080×2400 PNG.

Before the matrix, the runner clears logcat. For each dump attempt it atomically preserves exact stdout and stderr bytes, command duration/result, ADB PID before/after, target `ls` and `stat` stdout/stderr before and after, power/display/keyguard/device-idle markers before and after, the acquired candidate bytes, and XML validation. Return code 0 never establishes success.

Valid XML must contain exactly one complete XML hierarchy envelope, parse to a `hierarchy` root, contain at least one node, at least one package, at least one semantic text/content-desc/resource-id field, and the expected foreground package.

## Preregistered matrix

The order is fixed. Each path has exactly two planned repetitions, which are measurements rather than retries:

1. observed device state;
2. generic `KEYCODE_WAKEUP` + `wm dismiss-keyguard`, followed by verified interactive state.

Within each precondition:

1. normal dump to a unique `/sdcard` file;
2. `--compressed` dump to a unique `/sdcard` file;
3. normal dump to direct stdout through `/dev/tty`;
4. `--compressed` dump to direct stdout through `/dev/tty`.

Thus the frozen matrix contains 2 preconditions × 4 forms × 2 repetitions = 16 attempts. Every cell is recorded once. Unsupported direct output is recorded as failure; no replacement form or extra cell may be appended.

The B2.6 `interactive_true=false` value is treated as a parser observation, not ground truth: B2.7 checks `mInteractive` in both power and display dumps, requires awake wakefulness, display on, and keyguard not showing, and stores the raw sources.

## Acquisition qualification and stop rule

A task-agnostic acquisition path qualifies only if both preregistered repetitions produce valid XML, both begin in verified-interactive state, and the same 5038 server PID surrounds every operation. At least one qualified path authorizes a separately committed DEV collector correction. Otherwise B2.7 stops after the diagnosis result.

If authorized, implementation must use only the qualifying generic form, retain byte-level provenance and content validation, add corruption tests, and freeze before any grid run. Then the previously specified four-app × three-round B2.5 DEV grid may run exactly once under a new output root. Any first failure stops the grid. Only 12/12 with zero daemon restart may authorize preparation—but not execution—of a fresh v0.3 protocol.

## Permanent boundaries

All Settings evidence and any later four-app grid evidence are DEV-contaminated and held-out-ineligible. B2.6 remains immutable. No selector, coordinate, task-specific production branch, model call, held-out freeze, Phase C pilot, LaTeX change, or push is allowed.
