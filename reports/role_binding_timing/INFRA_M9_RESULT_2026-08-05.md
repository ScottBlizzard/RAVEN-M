# INFRA-M9 authorization-view separation — final result

## Verdict

**FAIL_TEMPORAL_SUPPORT_ATTESTATION.** The one frozen chain stopped in framework setup with immutable first edge:

`PROCESS_IDENTITY:PROCESS:22504@1785886374.192433:HELPER_PARENT_CHAIN`

M9 therefore does not authorize v0.3 preparation. It made zero model calls and zero held-out captures. Launch and boot passed; framework did not complete; burn-in, Settings a11y and the 12-cell DEV grid were not run.

## What M9 resolved—and what it did not

The M8 prelaunch false rejection did not recur. At the failure trigger, the four views remained disjoint, support/unrelated role authority was false, and launch plus boot had passed. This is narrow evidence that the old AccessDenied ancestry row no longer vetoed baseline merely by appearing in `structural_processes`. It is not a qualification pass because the full frozen chain did not complete.

The new first edge is temporal. Thirteen exact locked `adb.exe` helper identities were recovered from continuous history. All 13 had their parent in the same history sample, in the support-only view, with the view-disjoint assertion true. At the later framework trigger, 12 of the 13 helper identities and their short-lived `cmd.exe` parents had exited; inherited current-only ancestry validation therefore reported missing parents. The one helper still current had a current support parent, but its executable hash—present in the frozen `structural_processes` source—was not carried into M9's derived support row, so the wrapper could not be verified.

Direct evidence thus separates two defects:

- 12/13: co-observed ancestry was not preserved as a bounded historical attestation for later evaluation.
- 1/13: current support evidence lost a hash field during view projection.

The defensible next question is whether support observations can retain proof fields and a sample-bound ancestry attestation without granting the support process any project authority. M9 itself is immutable and was not patched or retried.

## Accounting and cleanup

- Phase journal: launch PASS, boot PASS, framework FAIL, cleanup secondary failure, log-seal secondary failure, terminal PASS.
- Process snapshots: 34; continuous-history samples: 97; terminal journal entries: 12.
- Completion: exactly one, rich mode, schema valid, receipt hash matched.
- Result manifest: 236 artifacts, all hashes valid.
- Generation calls / model tokens / held-out captures: 0 / 0 / 0.
- Burn-in / Settings / grid: 0/24, 0/3, 0/12.

The frozen cleanup and log-seal verdicts remain **false** because stale-history ancestry failures persisted into cleanup and the runner therefore refused normal sealing. A post-terminal read-only host check found no controlled-port listener and no locked project runtime process. The two closed external log files were copied byte-for-byte into the separate result-audit root for postmortem preservation only; that copy does not reclassify cleanup or log sealing as passed.

Before the real chain, one operator command used system Python and failed during import (`android_env` unavailable) before M9 `main()`, run-root creation or any project resource start. This is recorded as a reconstructed orchestration deviation, not raw runner evidence and not a second frozen chain. The actual chain used the locked environment without source/config changes.

## Claim–evidence boundary

- Authorization-view separation qualified: **no**.
- Temporal support attestation qualified: **no**.
- Exclusive 5038 launch and boot: tested in this DEV chain; not enough for an overall pass.
- Display/framework completion, burn-in, a11y and 12-cell grid: not completed/tested.
- v0.3 preparation: not authorized.
- Held-out collection, model behavior, role binding, memory efficacy and novelty: not tested.

The machine-readable audit and postmortem log copies are under `05_project/artifacts/role_binding_timing/infra_m9_result_audit/`.
