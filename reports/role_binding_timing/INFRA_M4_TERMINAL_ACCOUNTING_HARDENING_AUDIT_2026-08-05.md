# INFRA-M4 terminal-accounting hardening audit

## Verdict

M3's terminal-accounting failure was a generic runner-design defect: the only rich completion and manifest writes occurred after every phase and both depended on an unverified function in a foreign imported script. When that function was absent, the runner lost all in-memory phase state, including the exact earlier runtime edge.

The M4 correction must therefore do more than replace one function name. It must make phase evidence durable before a later exception can occur and must preserve a minimal completion even if rich serialization itself fails.

## Direct evidence

| Failure surface | M3 evidence | Required M4 invariant |
|---|---|---|
| Writer ownership | M3 line 552 and line 557 call `M1.write_json_atomic`; the frozen M1 script defines no such symbol. | M4 owns and tests its writer locally; no imported writer dependency. |
| Phase durability | `first_broken_edge`, cleanup, seal, and completion remained local variables until terminal write. | Append-only journal records phase start/pass/fail and a write-once first edge at every transition. |
| Late exception | The writer raised after runtime cleanup. | Terminal writer runs independently from the main chain and consumes only durable journal/checkpoint state. |
| Serialization robustness | No fallback record existed when rich completion writing failed. | A minimal JSON-safe fallback is atomically installed before rich serialization; rich failure updates fallback without deleting it. |
| Runtime-edge recovery | Boot attempt 8 is durable, but no framework artifact exists; the in-memory edge is unknowable. | The framework-start checkpoint must exist before the first framework operation, and any exception must durably name that phase. |
| Log finalization | M3's external routing protected the old log, but runner sealing/accounting did not complete. | Cleanup and seal each get their own before/after journal entries; terminal evidence records runner seal separately from any postmortem salvage. |

## Frozen M4 test obligations

Before a live run, fault injection must cover launch, boot, framework, burn-in, Settings, grid, cleanup, and seal, plus missing helper/`AttributeError`, JSON serialization failure, process timeout, and cleanup exception. Every injected case must leave:

- one parseable terminal completion;
- the exact first broken edge, never overwritten by cleanup or serialization failures;
- an append-only phase journal ending in a terminal event;
- closed parent handles and no simulated process owner;
- sealed external logs or an explicit seal failure with preserved external path;
- no modification to an old artifact canary;
- zero generation calls and zero held-out captures.

## Current start boundary

Ports 5037, 5038, 5554, 5555, and 8554 are all absent. No project emulator process remains. Unknown ADB PIDs 11316 and 17716 remain excluded. The restored M1 log is still 9,590 bytes with SHA-256 `ffddf9d…`.

This audit provides no M4 runtime, burn-in, a11y, v0.3, held-out, or role-binding evidence.
