# EEST-AC v0.2.4 Collector Lifecycle Qualification — Final Verdict

## Outcome

**Overall verdict: `FAIL_COLLECTION` at `environment_initialization.device_settings_service_missing`.**

The frozen batch stopped after `CLQ-RUN-01`. The explicit 5038 bootstrap, client/server hashes, device serial, and ADB `get-state=device` checks passed. AndroidEnv initialization nevertheless failed because the booted device did not expose the Android `settings` service: the raw stderr repeatedly reports `cmd: Can't find service: settings`. After its bounded restart handling, AndroidEnv raised `TooManyRestartsError`.

The failure occurred before pre-action readiness sampling. Consequently:

- readiness attempts: 0;
- intended swipe executions: 0;
- post observations: 0;
- collection record: not created;
- `CLQ-RUN-02`: not run under the frozen stop rule.

This is not a failure of the v0.2.3 action-conditioned oracle, because that oracle was not evaluated. It is not evidence about memory, M-SLOTS, M-RISK, controller efficacy, task success, or held-out generalization.

## What the lifecycle infrastructure did prove

Although the qualification failed overall, the failure path itself was auditable:

- exactly one schema-valid `collection_complete.json` was atomically published;
- its SHA-256 is `5f48faff80779c389efe57a60bc9a598a9c372310891fd1bf19fb78dabeccb33`;
- the terminal record retained `TOOMANYRESTARTSERROR` as the primary collection error;
- there were no cleanup errors that could replace it;
- reverse `tcp:18765` was already absent and independently verified absent;
- no owned helper PID or temporary completion file remained;
- all artifact hashes embedded in the terminal record match the raw files;
- generation calls, held-out traces, and oracle efficacy evaluations remained zero.

These are partial lifecycle-mechanism signals only. They do not satisfy the preregistered two-run PASS condition.

## Frozen bootstrap and abnormal PID boundary

Before the batch, no listener existed on 5037 or 5038. The frozen procedure made its single permitted call to the locked official binary using `-P 5038 start-server`; it returned successfully. The resulting 5038 server, client, and device checks matched the locked hash `957e46b8...13e71` and serial `emulator-5554`.

PID 17716 remained an unowned abnormal process candidate with 20,480-byte working set and no visible path/command line. It was recorded but never killed, restarted, adopted, or otherwise mutated. No command fell back to 5037.

AndroidEnv restart handling changed the observed 5038 daemon PID later in the failure path. The post-batch listener still resolves to the same locked official binary and port. This PID drift is reported transparently and is not used to turn the failed run into a pass.

## Offline gates

- Focused EEST suite: **131 passed, 0 failed**.
- Full repository suite: **1,133 passed, 1 expected protected legacy failure**, 1,134 collected.
- The only failure is `test_r78_candidate_static_manifest_validation_passes`, caused by the preserved r79/r78 frozen-manifest mismatch.
- The earlier task-interrupted regression is excluded; the reported hashes come from the complete independent rerun.
- Focused stdout/stderr: `a5bc2277...0808a` / empty-file hash `e3b0c442...b855`.
- Full stdout/stderr: `11dd407c...de07` / empty-file hash `e3b0c442...b855`.

## Raw batch evidence

- Batch root: `runs/eest_ac_v0_2_4_collector_lifecycle_qualification_20260804`
- Batch completion SHA-256: `78d39642e88981910c3d858af20c18e6150b3a02057c1dba8d3536fc602c3723`
- Batch stdout SHA-256: `99405717381fedcaa8627dec6495259dc090f1c0cedac44389ef12b8bd5098dd`
- Batch stderr SHA-256: `d0320556a629b4741682be9e96649419a41938551ac772133a63729bade4ba42`
- Lock audit: all 20 frozen artifacts matched; protocol tag resolved to commit `21af26d601ca590b9a0231c0d0e94960af47b817`.

## Protected WIP and final boundary

All three protected WIP hashes match their pre-round values and remain unstaged/uncommitted. The v0.2.3 oracle contract, schema, implementation, lock, and FAIL_COLLECTION verdict were not modified.

The final boundary is strict: v0.2.4 stops here. There is no patch/retry, second Settings run, held-out trace collection, oracle efficacy evaluation, or method claim in this round. A future separately preregistered infrastructure round would first need to qualify Android framework-service readiness, not modify this frozen result.
