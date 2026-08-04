# EEST-AC v0.2.4 Claim-Evidence Verdict

Overall: **`FAIL_COLLECTION`** in `CLQ-RUN-01` before readiness, because AndroidEnv could not initialize while the device's `settings` service was absent. `CLQ-RUN-02` was not run.

| ID | Verdict | Evidence | What remains untested |
|---|---|---|---|
| CL-C1 | **NOT TESTED live** | Environment initialization failed before readiness attempt 1; action count remained 0. | Whether two stable valid Settings pre observations can be acquired live. |
| CL-C2 | **PASS synthetic only** | Five-attempt timeout test produces no action. | A live readiness timeout path; this run failed earlier. |
| CL-C3 | **PASS for tested paths** | Synthetic present/absent/race/error tests pass; live reverse was `already_absent` and verified residue-free. | Removal of a present listener in a completed live run. |
| CL-C4 | **PASS synthetic; vacuous live** | Injected primary+cleanup test preserves both. Live primary was preserved and cleanup had no secondary error. | A live dual-failure instance. |
| CL-C5 | **PASS for failed run path** | One schema-valid atomic terminal record, matching hash, zero temp residue, duplicate tests pass. | Exactly-once behavior after a successful full collection. |
| CL-C6 | **PARTIAL / overall FAIL** | Frozen 5038 bootstrap and binary/serial isolation passed; no 5037 fallback; abnormal PID untouched. Android framework-service readiness failed afterward. | Isolation and reset across two successful complete runs. |
| CL-C7 | **FAIL prerequisite / NOT TESTED** | Only run_01 completed and it failed before action; run_02 correctly not run. | Two-run semantic repeatability. |
| CL-C8 | **PASS** | Generation calls 0, call files 0, held-out traces 0, oracle efficacy evaluations 0. | All oracle, memory, controller, and task efficacy questions. |

Claim boundary: the run demonstrates that the new failure-accounting and idempotent-cleanup path is materially more auditable than v0.2.3, but it does **not** qualify the collector lifecycle because the two-run success condition was not reached.
