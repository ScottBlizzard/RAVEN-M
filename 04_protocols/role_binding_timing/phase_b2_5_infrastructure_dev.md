# Role-Binding Timing B2.5 DEV infrastructure stability protocol

Status: model-free DEV qualification; not held-out and not hypothesis evidence.

## Question

Can a new task-agnostic collector execute repeated reset → launch → foreground → UI-dump → screenshot → cleanup sequences across multiple apps while one explicitly identified official ADB server remains continuously present on port 5038?

## Fixed boundary

- Zero model-generation calls; `generation_eligible=false`.
- Four DEV apps in fixed order: Settings, Clock, Tasks, Broccoli; three rounds each, giving 12 sequences.
- All states, screenshots, UI trees, labels, packages, and traces are permanently DEV-contaminated and never eligible for v0.3 or Phase C.
- The old v0.2 collector, pool, protocol, lock, and verdict remain immutable.
- No AndroidWorld controller calls are used because its pinned ADB controller may automatically kill/start the server on a device-specific failure. Every device command instead uses the locked official binary with `-P 5038 -s emulator-5554`.

## Managed ADB invariant

The runner adopts the single pre-existing 5038 listener only if its executable hash equals the frozen official ADB hash. It records PID, executable path, creation time, port, and serial. Before and after every command, netstat must show the same listener PID. If the listener is absent or changes, the runner stops without issuing a replacement/start command and records `NOT_ELIGIBLE`. No 5037 call is permitted.

Framework services `package`, `window`, and `activity` are checked before launch, after capture, and after cleanup in every sequence. Any missing service is a hard failure.

## Generic sequence

For each app and round:

1. press Home, force-stop the declared package, and verify the reset command;
2. launch the declared AndroidWorld-resolved component using raw `am start -W -n` and retain stdout/stderr/return code;
3. collect bounded activity and window foreground witnesses, accepting `topResumedActivity`, `mResumedActivity`, or `ResumedActivity` plus `mCurrentFocus`, `mFocusedApp`, or `FocusedWindow`;
4. collect a raw `uiautomator` XML and require a nonempty tree containing the expected package;
5. collect and validate a 1080×2400 PNG;
6. exercise the task-agnostic locator hierarchy on one deterministic DEV-only unique clickable witness: package-scoped exact resource ID, then normalized content description, then normalized text, each resolved to the nearest enabled clickable ancestor;
7. force-stop the package, return Home, and repeat the framework/server checks.

The app/component list is scene configuration, not a production-code branch. No coordinates, task names, entity names, or app-specific click rules exist in the implementation.

## Filesystem correction

Remote `sh -c` and pipelines are forbidden. File counts use direct `find <root> -maxdepth 1 -type f -print`, validate every returned path remains below the requested root, and count lines locally. This primitive is covered by corruption tests but is not used to change any v0.2 artifact.

## Stop rule and PASS

Any sequence failure stops the batch immediately. No code/config adjustment and retry is allowed in this DEV version. PASS requires 12/12 sequences, all four apps, one unchanged 5038 PID/hash, zero implicit restart, continuous framework services, valid launch/foreground/UI/screenshot/reset evidence, locator provenance for every sequence, schema-valid exactly-once terminal certificate, and zero generation calls.

PASS authorizes only a separate v0.3 protocol freeze with entirely new entity values, setup seeds, and candidate instances. FAIL returns `NOT_ELIGIBLE` and forbids v0.3 freeze/capture and Phase C.
