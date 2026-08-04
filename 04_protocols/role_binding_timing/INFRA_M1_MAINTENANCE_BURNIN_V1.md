# INFRA-M1 project-owned runtime maintenance and burn-in v1

## Scope

INFRA-M1 is zero-model, DEV-only infrastructure maintenance. It is not a retry of B2.10, data collection, an AndroidEnv/a11y qualification, or evidence about role binding, memory, controller, or oracle efficacy.

The maintenance runner may stop and restart only resources proven to be project-owned by concordant path/hash, command line, parent/child relation, and listener ownership:

- official project ADB server listening only on 5038;
- `AndroidWorldAvd` launcher and qemu child on console 5554/device 5555 and emulator gRPC 8554;
- no random accessibility sidecar is expected before maintenance.

Unrelated/non-listening ADB or emulator processes are inventoried and excluded. Port 5037 is never used.

## Frozen maintenance sequence

The authoritative inventory is `infra_m1_pre_maintenance_inventory_v2`. The first inventory directory is retained as superseded diagnostic evidence: its derived degradation flags inspected stdout but not stderr, even though raw stderr was preserved. V2 corrected only that read-only derivation and was captured before any runtime mutation.

1. Verify the committed authoritative pre-maintenance inventory, exact protected WIP hashes, binaries, AVD identity, process command lines, listener PIDs, excluded-process PID set, and absence of 5037.
2. Send one clean `adb -P 5038 -s emulator-5554 emu kill`; do not force-kill on failure. Require both verified emulator launcher/qemu processes and ports 5554/5555/8554 to disappear.
3. Send one official `adb -P 5038 kill-server`; require only the verified 5038 owner to disappear. Do not terminate excluded ADB PIDs.
4. Start the locked ADB binary with `-P 5038 start-server`; require one new verified 5038 owner and no 5037. Clean stop/start commands are judged by timeout/return code plus subsequent identity checks; any diagnostic stderr is preserved and does not by itself override concordant PID/port identity.
5. Start the locked emulator launcher with frozen arguments and `ANDROID_AVD_HOME` pointing to the project AVD directory. Require a new verified launcher/qemu pair, exact port ownership, device availability, boot completion, framework services, and no excluded-process mutation.
6. No AndroidEnv or accessibility-forwarder route is created in INFRA-M1.

## Burn-in contract

Run exactly 24 sequential cycles over at least 180 seconds. Each cycle uses the official 5038 client and contains:

- host/device state and boot-complete checks;
- package, window, and activity service checks;
- wake, dismiss-keyguard, and Home commands;
- power, window-display, window-policy, and activity dumps;
- one PNG screenshot validated by signature, decoding, dimensions, and nonempty bytes;
- before/after verification of the same ADB PID, emulator launcher/qemu PIDs, binary hashes, command lines, ports 5038/5554/5555/8554, device serial, and absence of 5037.

Every command must complete within 15 seconds with return code zero. Power must be awake and interactive, display 0 must be ON, keyguard must not be showing, framework services must be found, and the activity/window dumps must not contain `DEAD_OBJECT` or service errors. Raw pixel hashes may differ.

Cycles are separated by 8 seconds. The batch passes only at 24/24, at least 180 seconds elapsed, zero timeout, zero nonzero return code, zero PID/port drift, zero implicit daemon restart, zero 5037 fallback, and exact protected-WIP continuity.

## Stop and continuation

Any ownership mismatch stops before mutation. Any clean-stop/restart/boot/burn-in failure produces `RUNTIME_UNSTABLE` and stops the phase. No same-version patch/retry and no a11y test follows.

Only `RUNTIME_STABLE_24_OF_24` permits a separate commit that preregisters the already audited fail-closed a11y route. Even then, Settings 3/3 and the 12-cell DEV grid are separate qualification evidence, not held-out data.
