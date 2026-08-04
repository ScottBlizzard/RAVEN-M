# EEST-AC v0.2.4 Collector Lifecycle Qualification Protocol

Status: preregistration draft. It must be committed and tagged with a machine-readable lock before the qualification batch starts.

## Scope and immutable prior evidence

EEST-AC v0.2.3 remains immutable `FAIL_COLLECTION`. Its definitive Settings trace had an invalid pre-observation and its cleanup exception prevented `collection_complete.json`. v0.2.4 does not reinterpret, repair, or evaluate the v0.2.3 method oracle.

This round asks only whether the collector lifecycle can reliably acquire a valid pre-observation, execute one action, preserve primary and cleanup errors, clean idempotently, and publish exactly one terminal completion record.

The round permits zero model-generation calls, zero held-out traces, zero oracle efficacy evaluations, and zero memory/controller efficacy claims. The Settings qualification scene and all synthetic tests are development-contaminated infrastructure evidence.

## Frozen lifecycle policy

### Pre-action readiness

For the scroll qualification, the collector samples at most five pre observations, one second apart. An observation is field-valid only when a11y is available and the following are nonempty: semantic a11y hash, page-content hash, package set, activity, and route signature. Readiness requires two consecutive field-valid observations with identical semantic hash, page-content hash, package set, activity, and route signature. Pixel equality is irrelevant.

If readiness is not achieved within five attempts, the primary error is `PRE_READINESS_TIMEOUT`; the intended swipe is not executed; `action_executed=false`; and the run terminates after cleanup and one atomic failure record.

### Cleanup and error precedence

The only reverse listener in scope is `tcp:18765` on the explicit official ADB server at port 5038. Cleanup first lists reverse mappings. Absence is successful `already_absent`. Presence is removed and verified as `removed`. A racing `listener not found` response is successful only if a subsequent list proves absence, recorded as `already_absent_after_race`. Other list/remove/verification errors fail closed.

Cleanup outcomes are secondary evidence. A collection/readiness/isolation error remains the primary error even when cleanup also fails. No owned helper process may remain.

### Exactly-once completion

Every fresh run root receives exactly one schema-valid `collection_complete.json`, whether the run passes or fails. The writer validates the record, fsyncs a unique temporary file, and publishes via a no-overwrite hard link. A pre-existing or second terminal record is rejected. The record includes readiness attempts, action count, post count, primary error, cleanup outcomes, isolation hashes/port, artifact hashes, and zero-call/zero-held-out accounting.

## Frozen ADB diagnosis and bootstrap

The pre-protocol host audit observed no listener on 5037 or 5038 and an abnormal `adb.exe` PID 17716 with approximately 20 K memory and no visible executable path or command line. This is an unowned stale-process candidate, not proof. It must be recorded but not killed, restarted, adopted, or used to infer server identity.

The frozen batch procedure may make exactly one bounded call to the official locked binary with `-P 5038 start-server` if 5038 has no listener. It may not kill or restart any process and may not issue any command to 5037. The client hash, listening server binary hash, device serial, and device state must then match the lock. Failure creates a single failed run_01 completion with an isolation primary error and no action, then stops.

## Offline gates

Before protocol freeze and batch execution:

1. delayed-ready and readiness-timeout/no-action tests pass;
2. reverse present, already-absent, absent-after-race, and non-not-found failure tests pass;
3. primary plus cleanup failure preserves both with primary precedence;
4. atomic exactly-once completion and duplicate rejection pass;
5. generated schema exactly matches the machine contract;
6. focused EEST tests and the relevant full regression introduce no new failure beyond the protected r79/r78 frozen-manifest mismatch;
7. legacy hashes, v0.2.3 frozen artifact hashes, source/config/schema hashes, port, timing, scene, and stop rules are recorded in the lock.

## Single qualification batch

After the protocol-freeze commit/tag, execute the frozen Settings DEV scene in exactly two consecutive fresh roots, `CLQ-RUN-01` then `CLQ-RUN-02`. No source, config, protocol, schema, or lock change is allowed between or after the runs until the batch has stopped.

Each run must acquire qualified pre evidence before the action, execute the canonical upward swipe exactly once, capture four post observations, write a valid collection record, atomically publish exactly one valid completion, report zero calls/held-out/evaluations, reset, preserve explicit 5038 isolation, and leave no reverse/helper residue. Semantic lifecycle invariants must agree across the runs; raw pixel hashes need not agree.

If either run fails, stop immediately; the other run is `not_run` when applicable. No patch/retry is permitted within v0.2.4. If both pass, stop after run_02. Under neither outcome may the round select held-out traces or evaluate oracle efficacy.

## Claims

PASS supports only that this exact collector lifecycle contract passed two consecutive contaminated Settings runs. It does not support oracle accuracy, action-outcome correctness beyond harness execution, memory efficacy, M-SLOTS, M-RISK, or task success. FAIL remains a collector/infrastructure result with its exact failing layer.
