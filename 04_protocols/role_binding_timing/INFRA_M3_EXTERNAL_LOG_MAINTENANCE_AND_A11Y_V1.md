# INFRA-M3 external-log maintenance and DEV a11y qualification v1

## Scope and claim boundary

INFRA-M3 is zero-model, DEV-only infrastructure qualification. It asks whether the pinned AndroidWorld runtime can complete exclusive-5038 launch, 24 stable cycles over at least 180 seconds, and only then the already audited AndroidEnv accessibility Settings 3/3 plus 4-app × 3-round DEV grid, while no live process log is placed inside the repository or any artifact root.

PASS authorizes preparation, not execution, of a fresh v0.3 collection protocol. It does not support held-out, role-binding, memory, controller, oracle-efficacy, or task-efficacy claims.

## Corrected log lifecycle

1. Protocol, source, configuration, schemas, and tests are immutable inputs. Runtime log content is not an immutable input.
2. Before launch, create one fresh root below the frozen OS-temporary parent `C:/Users/lenovo/AppData/Local/Temp/raven_m_role_binding_timing`. The resolved path must be outside the repository and every configured artifact/frozen root.
3. Emulator stdout/stderr are opened only in that live root. No prior frozen log path may be opened for append, truncate, replacement, or restoration.
4. Parent-side file handles close immediately after `Popen`; descendant ownership ends only after the emulator and both verified project ADB servers have cleanly stopped.
5. Before sealing, each live log must pass a same-directory rename round trip. Failure means an incompatible handle remains and sealing is forbidden.
6. Closed logs are copied exactly once into the new M3 result root and hashed as terminal evidence. They are never used as a lock input. The external temporary root is removed only after successful sealing.
7. Any lifecycle, handle, copy, hash, or residue failure is terminal. No same-version patch or retry is allowed.

## Residual cleanup and exclusive registration

The pre-run residual is the verified official ADB 5038 server PID 35452. Port 5037 and emulator ports are absent; unknown/stale ADB PIDs 11316 and 17716 are excluded and never targeted.

1. Reconfirm the exact residual binary hash, command line, PID, listener, protected hashes, and clean emulator absence.
2. Stop only the verified 5038 server with the locked official ADB client. Require ports 5037/5038/5554/5555/8554 absent and excluded PIDs unchanged.
3. Start a fresh official 5038 server.
4. Launch the exact `AndroidWorldAvd` with the frozen arguments and child-only `ANDROID_ADB_SERVER_PORT=5038`. Conflicting socket/address variables are rejected.
5. At every stage, any 5037 listener or identifiable 5037 server is an immediate failure. No command after baseline may address 5037.
6. Require fresh launcher/qemu/ADB PIDs, correct ownership of 5038/5554/5555/8554, device registration through 5038, boot completion, and three consecutive framework-ready observations.

## Burn-in gate

Run exactly 24 sequential cycles separated by 8 seconds and require at least 180 seconds total. Every cycle requires unchanged process/port identities, zero 5037, device/boot readiness, package/window/activity services, wake/dismiss-keyguard/Home, power/display/policy/activity dumps, and one valid 1080×2400 PNG. Any command timeout, nonzero return, unexpected stderr, service/display failure, screenshot failure, PID drift, or protected-WIP drift stops before a11y.

## Post-burn-in accessibility qualification

Only after a 24/24 burn-in may the frozen generic B2.10 route run:

- exact forwarder APK/component identity;
- explicit same-port rebind and Bound-state evidence;
- one fresh fail-closed AndroidEnv session using locked 5038 and emulator gRPC 8554;
- explicit `SET_GRPC`, `ENABLE_GRPC`, and `ENABLE_ACCESSIBILITY_TREE_LOGS`;
- three consecutive same-observation Settings screenshot+a11y successes;
- then one fixed 3-round grid over Settings, Clock, Tasks, and Broccoli, totaling 12 cells;
- nonempty, package-consistent, losslessly serialized accessibility elements, usable screenshots, stable oracle fields, unchanged ADB/emulator/forwarder/sidecar identities, zero 5037, and zero implicit refresh/restart.

The first failed Settings observation or grid cell stops the batch. Apps and states are DEV-contaminated and cannot become held-out evidence.

## Terminal cleanup and stop rules

After success or failure, preserve the primary error, close the AndroidEnv session if created, stop only the exact M3 emulator through 5038, stop the exact M3 5038 server, verify no project listener/process residue, prove log handles closed, seal the logs once, and atomically write one terminal record and manifest.

Strict outcomes:

- `PASS_12_OF_12_DEV`: 24/24 burn-in, Settings 3/3, grid 12/12, clean shutdown, log seal, schema, hashes, protected files, and zero-call accounting all pass. Only v0.3 preparation is authorized.
- `RUNTIME_UNSTABLE`: ownership, launch, boot, framework, or burn-in fails.
- `A11Y_QUALIFICATION_FAILED`: burn-in passes but Settings/grid fails.
- `LOG_SEAL_FAILED`: process/log ownership or finalization fails.

Any failure ends M3. No held-out capture, model generation, v0.3 execution, LaTeX modification, or push is authorized.
