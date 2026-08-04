# INFRA-M2 emulator-to-ADB port registration and burn-in v1

## Scope and claim boundary

INFRA-M2 is zero-model, DEV-only infrastructure qualification. Its only question is whether the pinned emulator can register exclusively with the locked official ADB server on port 5038 when the verified `ANDROID_ADB_SERVER_PORT=5038` environment is inherited at launch, and then remain stable for 24 cycles over at least 180 seconds.

PASS does not qualify AndroidEnv/a11y, the 4-app grid, held-out capture, role binding, memory, controller, or task efficacy. It only authorizes a separate a11y qualification stage. Any failure stops INFRA-M2 without an a11y test.

## Evidence basis and single correction

Read-only audit commit `f392ddccbba51c79782ff3e0bc6781643f7eef01` verified the following locally:

- the pinned qemu binary reads and range-checks `ANDROID_ADB_SERVER_PORT` in its ADB host-server path;
- the pinned ADB binary recognizes the same variable;
- prior project launcher source sets this variable immediately before emulator `Popen`;
- INFRA-M1 omitted it and logged a default-port connection to 5037.

The only registration correction is:

```text
child_env["ANDROID_ADB_SERVER_PORT"] = "5038"
```

`-ports`, `-adb-path`, `-no-direct-adb`, `ADB_SERVER_SOCKET`, and `ANDROID_ADB_SERVER_ADDRESS` are not added. Existing AVD, console/device ports, gRPC port, binary paths, and emulator arguments remain unchanged.

## Bounded legacy cleanup before M2 launch

The inherited M1 failure scene contains project-created resources: official ADB 5038 PID 35452, official implicit ADB 5037 PID 24580, emulator launcher PID 7616, and qemu PID 37004. PIDs 11316 and 17716 are excluded unknown/stale ADB processes and must not be targeted.

Before mutation, exact binary paths/hashes, command lines, parent relation, listener ownership, protected WIP hashes, and the audit manifest must match. Then:

1. use the verified current 5037 server exactly once to send `emu kill` to its already-connected `emulator-5554`;
2. require launcher/qemu and ports 5554/5555/8554 to disappear without force-kill;
3. send `kill-server` specifically to verified 5037, then verified 5038;
4. require ports 5037/5038/5554/5555/8554 all absent and excluded PIDs unchanged.

This is a contaminated cleanup boundary, not M2 launch evidence. After the clean baseline, no command may address 5037.

The currently running M1 emulator still owns its M1 stdout handle. M2 never opens for writing, truncates, reuses, restores, or stages that frozen path. Its committed/current byte hash is checked before cleanup and immediately after emulator exit; any shutdown-time suffix is a hard `LEGACY_FROZEN_LOG_DRIFT` stop before the M2 launch. The new emulator can write only to the new ignored M2 runtime-log root.

## Frozen M2 launch

1. Start the locked official ADB binary using explicit `-P 5038 start-server` and require one fresh, correctly identified 5038 owner.
2. Require 5037 listener/process absence.
3. Launch the exact `AndroidWorldAvd` with frozen arguments, a new runtime-log root, project AVD/SDK paths, no conflicting ADB socket/address variables, and the single inherited `ANDROID_ADB_SERVER_PORT=5038` value.
4. At every launch/readiness observation, fail immediately if any 5037 listener or process command line appears.
5. Require a fresh launcher/qemu pair, qemu ownership of 5554/5555/8554, the same 5038 PID, `adb -P 5038 devices` visibility of `emulator-5554`, device state, and boot completion.
6. Require three consecutive framework-ready observations with package/window/activity services, awake/interactive display, unlocked keyguard, and nonempty activity state.

The runner records only an immutable terminal snapshot of the live emulator log under the artifact root; the live writer uses a new ignored runtime directory, so no prior frozen log handle can be touched.

## Burn-in

Run exactly 24 sequential cycles over at least 180 seconds, separated by 8 seconds. Each cycle requires:

- 5037 absent before and after every cycle, including both listeners and identifiable process command lines;
- unchanged ADB 5038, launcher, and qemu PIDs and exact listener ownership;
- device state and boot-complete through 5038;
- package/window/activity service checks;
- wake, dismiss-keyguard, and Home commands;
- power, display, policy, and activity dumps;
- a valid 1080×2400 PNG screenshot;
- zero command timeout/nonzero return code/unexpected stderr;
- excluded-process PID continuity and protected-WIP continuity.

## Stop rules

- Any pre-clean ownership mismatch stops before mutation.
- Any cleanup failure stops without launch.
- Any 5037 listener/process after the clean baseline is an immediate `FORBIDDEN_5037` failure.
- Any launch, registration, boot, framework, command, PID/port, screenshot, duration, manifest, or protected-file failure produces `RUNTIME_UNSTABLE` and stops.
- No same-version patch or retry is allowed.
- Only `RUNTIME_STABLE_24_OF_24` authorizes a separately frozen generic gRPC/a11y Settings 3/3 and 4-app × 3-round DEV qualification.
- Even on PASS, no held-out collection or model generation is authorized.
