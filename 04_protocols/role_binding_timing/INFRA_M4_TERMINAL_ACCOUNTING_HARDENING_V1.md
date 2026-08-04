# INFRA-M4 terminal-accounting hardening v1

## Scope and claim boundary

INFRA-M4 is a zero-model, DEV-only infrastructure qualification. Its primary question is whether every launch, boot, framework, burn-in, Settings, grid, cleanup, and seal transition remains durably attributable even if a later operation or terminal serializer fails. Only after the accounting mechanism passes offline fault injection may one frozen maintenance chain test exclusive 5038 launch, 24-cycle/180-second burn-in, Settings 3/3, and the existing 4-app × 3-round DEV grid.

PASS authorizes preparation, not execution, of a new v0.3 collection protocol. It provides no held-out, role-binding, memory, controller, oracle-efficacy, or task-efficacy claim.

## Locally owned terminal evidence

1. M4 owns `atomic_write_bytes` and `atomic_write_json`; imported runner scripts cannot supply terminal writers.
2. Each transition creates an immutable, atomically installed `phase_journal/entries/NNNNNN.json` before and after the operation. An fsync'd append-only NDJSON view is secondary; immutable entry files are authoritative.
3. `first_broken_edge.json` is write-once. Cleanup, seal, terminal, and serialization errors are secondary if an earlier edge exists.
4. The phases are frozen as `launch`, `boot`, `framework`, `burn_in`, `settings`, `grid`, `cleanup`, `seal`, followed by terminal finalization.
5. Rich state is optional. Before attempting rich serialization, the independent terminal finalizer atomically installs a schema-valid minimal completion reconstructed from the journal. Rich failure leaves that canonical fallback intact and records `TERMINAL_RICH_SERIALIZATION:*` when no earlier edge exists.
6. The finalizer is a separate executable with only the M4 accounting module and schema as terminal dependencies. It rejects duplicate completion.
7. The artifact manifest is generated only after canonical completion and validation exist. Manifest failure cannot erase completion.

## Fault-injection gate

Before live execution, model-free tests inject failure at every phase plus missing-helper `AttributeError`, rich JSON serialization failure, process timeout, and cleanup exception. Every case must leave one schema-valid completion, exact write-once first edge, a journal terminal event, closed parent handles, sealed external logs (including fallback seal for injected seal failure), removed test live root, and an unchanged old-artifact canary.

## Live logging and runtime boundary

- All emulator live stdout/stderr remain under a fresh child of `C:/Users/lenovo/AppData/Local/Temp/raven_m_role_binding_timing` until every owning process exits and rename-round-trip handle proof succeeds.
- Live logs are not protocol lock inputs. No M1/M2/M3 artifact path is opened for append, truncate, replacement, or restoration.
- After handle closure, logs are copied once into the M4 result root and hashed.
- Current live baseline must contain no listener on 5037, 5038, 5554, 5555, or 8554 and no project emulator process. Unknown ADB PIDs 11316 and 17716 remain excluded.

## Frozen chain

1. `launch`: require clean baseline, start locked official ADB on 5038, launch exact AndroidWorldAvd with child-only `ANDROID_ADB_SERVER_PORT=5038`, and reject any 5037 listener/process.
2. `boot`: require device visibility, `get-state=device`, and `sys.boot_completed=1` through 5038.
3. `framework`: require wake/dismiss/Home, package/window/activity services, nonempty activity state, interactive display, and stable keyguard state.
4. `burn_in`: require exactly 24 stable cycles separated by 8 seconds and at least 180 seconds, with unchanged identities, service/display evidence, and valid 1080×2400 screenshots.
5. `settings`: only after burn-in, use the previously audited generic accessibility-forwarder route and require three consecutive same-observation Settings screenshot+a11y successes.
6. `grid`: only after Settings 3/3, run the frozen 3-round Settings/Clock/Tasks/Broccoli DEV grid and require 12/12.
7. `cleanup`: close AndroidEnv, disable sidecar flags, cleanly stop the exact emulator and 5038 server, wait through transient owned shutdown helpers, and require the original no-listener baseline.
8. `seal`: prove both external log handles closed, seal once, remove the temporary root, and preserve protected hashes.

Any first failure stops subsequent experimental phases but not cleanup, sealing, journaling, or terminal finalization. Only `PASS_12_OF_12_DEV` authorizes v0.3 preparation. No model calls, held-out capture, v0.3 execution, LaTeX change, old-result edit, or push is authorized.
