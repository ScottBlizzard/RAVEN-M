# Role-Binding Timing B2.6 DEV launch-observability diagnosis

Status: one bounded, DEV-contaminated diagnosis of the frozen B2.5 Settings launch failure. Zero generation calls and no held-out collection.

## Question and fixed scene

Does `am start -W` returning `Status: timeout` mean the Settings launch actually failed, or is that status a false-negative observability signal? The scene, component, port, binary, PID-continuity rule, and device are inherited from the failed B2.5 DEV sequence. No other app or replacement probe is allowed.

## Evidence bundle

After Home + force-stop, the runner records a pre-launch sample, clears logcat, executes the exact `am start -W -n` command, records three one-second-spaced post-`-W` samples, executes one non-`-W` start, and records two further samples. Every sample retains:

- `sys.boot_completed`, `dev.bootcomplete`, and boot-animation state;
- power interactive/wakefulness, keyguard/window-policy, display state;
- raw `dumpsys activity activities`, `dumpsys activity top`, `dumpsys window windows`, and `dumpsys window displays`;
- package `pidof` result;
- raw `uiautomator` dump attempt and XML;
- raw PNG screenshot and validation;
- 5038 server PID before and after every ADB command.

The runner also retains exact `-W` and non-`-W` stdout/stderr/elapsed/result, and bounded ActivityTaskManager, WindowManager, and SurfaceFlinger logcat slices. It performs cleanup in a terminal block but cleanup cannot change the classification.

## Classification

Only post-`-W` samples determine A/B/C; the later non-`-W` command is diagnostic context and cannot rescue the `-W` window.

- **A — false-negative launch signal:** at least two consecutive post-`-W` samples contain the expected package in at least two independent foreground sources, plus a valid screenshot and nonempty UI tree containing that package.
- **B — rendering/UI observability floor:** the expected activity or process is present, but the screenshot/UI-tree/concordance bundle does not satisfy A.
- **C — emulator/framework lifecycle floor:** no post-`-W` sample establishes an active expected package or process.

Return code 0 alone never authorizes A. A task-agnostic future rule allowing `Status: timeout` to be nonfatal is permitted only after A. B or C stops B2.6 without a v0.2.6 stability run.

## Boundaries

The output is permanently DEV-contaminated and cannot be held-out. No Settings production branch, coordinate, model call, Phase C work, v0.3 pool, LaTeX edit, or retry is allowed. The existing B2.5 failure remains immutable regardless of the diagnosis.
