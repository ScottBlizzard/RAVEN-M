# Phase B2.10 DEV accessibility-forwarder lifecycle qualification v0.2.10

## Scope and claim boundary

This is contaminated infrastructure qualification only. Model generation, held-out collection, oracle efficacy, role-binding timing, memory efficacy, and controller efficacy are all out of scope. B2.9 remains immutable failure evidence.

The sole falsifiable question is whether one task-agnostic lifecycle correction can deliver nonempty AndroidEnv accessibility elements and a usable screenshot from the same `get_state` observation while preserving the locked 5038/8554 identities.

## Frozen intervention

1. Use the official locked ADB binary on port 5038 only. Port 5037 is a veto.
2. Wake and dismiss keyguard, then perform one explicit forwarder rebind: disable accessibility, clear the enabled-service entry, force-stop the forwarder package, restore the exact component, and enable accessibility.
3. Require the component to appear in both Enabled and Bound (not merely Binding) with a nonempty process PID within 8 attempts at 2-second intervals.
4. Construct one fresh AndroidEnv session with explicit 5038 and 8554. AndroidWorld implicit refresh remains forbidden.
5. Replace the wrapper's local-credentials host server before endpoint configuration with one gRPC insecure server bound on `[::]` for the emulator guest's documented plaintext `10.0.2.2` route.
6. After the pinned wrapper setup, issue validated, explicit-component broadcasts whose action and extras are separate argv fields: SET_GRPC with the current random port, ENABLE_GRPC, and ENABLE_ACCESSIBILITY_TREE_LOGS.
7. No app/task selector, coordinate, entity, template, or model behavior is added.

## Settings qualification matrix

Use the native Settings DEV scene. Launch it with the generic non-waiting activity command and require two consecutive activity/window/process foreground witnesses. Acquire exactly 3 consecutive `get_state(wait_to_stabilize=False)` observations in the same fresh session.

Every observation must have:

- a usable `uint8` screenshot of shape 2400×1080×3;
- a nonempty deterministic forest serialization;
- a nonempty lossless `UIElement` serialization;
- the expected package in activity, window, and element-package evidence;
- at least one unique strong oracle candidate from package, resource ID/name, class, and valid bounds;
- identical ADB 5038 PID, emulator gRPC 8554 PID, forwarder process PID, sidecar wrapper/port, APK identity, and bound-service state before/after;
- a host sidecar listener owned by the runner, no 5037 listener, no implicit restart/refresh, and zero generation calls.

Any failure stops B2.10 immediately and forbids the grid.

## One 12-cell DEV grid

Only if all 3 Settings observations pass, run one fixed grid in frozen order: 3 rounds × Settings, Clock, Tasks, Broccoli. Each cell uses generic home/force-stop/non-waiting launch, two consecutive foreground witnesses, and one same-observation screenshot+a11y capture with the same requirements. No cell is replaced or retried beyond the bounded foreground sampling and AndroidWorld's already pinned forest fetch.

The grid passes only at 12/12 with unchanged ADB/emulator/service/sidecar identities and zero 5037 or implicit restart. A first failed cell stops the grid.

## Cleanup and stop rules

Close AndroidEnv once, explicitly disable forwarder gRPC/tree logging, return Home, force-stop the last DEV app, and verify that the random sidecar listener is gone while 5038/8554 remain unchanged and 5037 remains absent. Cleanup errors are reported separately and do not replace the primary error.

If Settings or the grid fails, report the exact first broken edge and stop. If 12/12 passes, only preparation (not execution) of a separately reviewed v0.3 protocol is authorized. No held-out capture or generation follows automatically.
