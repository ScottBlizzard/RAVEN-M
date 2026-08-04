# EEST-AC v0.2.4 Preregistered Claim-Evidence Table

| ID | Claim under test | Required evidence | PASS condition | Explicitly untested |
|---|---|---|---|---|
| CL-C1 | The collector waits for action-class-required pre evidence before acting. | Per-attempt readiness audit plus raw a11y/package/activity/route hashes in both runs. | Both runs obtain two consecutive valid stable observations within five attempts; no action can precede qualification. | Whether the oracle interprets the evidence correctly. |
| CL-C2 | Readiness timeout fails before action. | Synthetic timeout/no-action test and completion schema. | Five invalid attempts yield a readiness primary error and action count zero. | Live timeout frequency outside this DEV scene. |
| CL-C3 | Reverse cleanup is idempotent without hiding errors. | Present, absent, race, other-error tests plus run cleanup records and post-cleanup residue check. | `removed`, `already_absent`, or verified `already_absent_after_race`; all other errors fail closed. | Cleanup of unrelated listeners or processes. |
| CL-C4 | Cleanup errors do not replace the primary collection error. | Injected dual-failure test and any run failure record. | Primary error is byte-for-byte preserved and cleanup errors remain secondary evidence. | Recovery from the underlying collection failure. |
| CL-C5 | Every run produces exactly one atomic terminal record. | Atomic/duplicate tests, schema validation, raw run-root count and completion hash. | Each attempted run has one and only one schema-valid `collection_complete.json`; no temp residue. | Distributed or multi-host writers. |
| CL-C6 | Explicit 5038 isolation remains fail-closed. | Client/server binary hashes, port/listener PID, serial/state checks, no-5037 audit, frozen bootstrap record. | Both runs use one matching official 5038 server and device; no fallback, unowned PID mutation, or residue. | General ADB availability on other hosts. |
| CL-C7 | The frozen lifecycle is repeatable across two consecutive runs. | Two fresh run roots from one unchanged protocol/config/source lock. | Both runs pass all lifecycle invariants; semantic invariants agree without requiring identical pixels. | Held-out generalization or task success. |
| CL-C8 | The round stays outside method efficacy. | Call/accounting files, source isolation test, run/batch records. | Generation calls, held-out traces, and oracle efficacy evaluations all remain zero. | M-SLOTS, M-RISK, memory, controller, and oracle efficacy. |

Strict stopping verdicts:

- `PASS`: this exact collector lifecycle passed two consecutive contaminated Settings runs; stop without held-out or oracle evaluation.
- `FAIL_COLLECTION`: the first failing run determines the layer; remaining run is not run; no patch/retry in v0.2.4.
- `FAIL_PREFLIGHT`: frozen lock, 5038 isolation, or offline gate failed before an action; no live qualification action.
