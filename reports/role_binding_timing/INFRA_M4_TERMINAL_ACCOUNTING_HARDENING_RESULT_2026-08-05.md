# INFRA-M4 Terminal-Accounting Hardening — Result

Date: 2026-08-05 (Asia/Hong_Kong)

Scope: zero-model, DEV-only infrastructure maintenance

Frozen commit: `e0f70d11a5b9614a215c52e9f1af86f3f8fec5f7`

Frozen tag: `role-binding-timing-infra-m4-freeze-20260805`

Verdict: **`RUNTIME_UNSTABLE` / STOP**

## Plain-language verdict

The one preregistered M4 chain stopped at the first framework gate, before burn-in or accessibility qualification. The exact durable first broken edge is `FRAMEWORK_RUNTIME:EXCLUDED_PID_DRIFT`. M4 therefore does **not** authorize preparation of v0.3 and provides no evidence about accessibility delivery, role binding, memory, or model performance.

The terminal-accounting hardening itself worked on this real early-failure path: the first edge survived cleanup, both live logs were sealed after their owners exited, exactly one schema-valid rich completion was written by the independent finalizer, and no previous artifact or protected WIP changed.

## Frozen execution result

| Gate | Result | Direct evidence |
|---|---:|---|
| Clean baseline | PASS | No listener on 5037/5038/5554/5555/8554 and no project-owned runtime process before launch |
| Launch | PASS | Explicit 5038 ADB PID 6100; launcher PID 26328; qemu/5554/5555/8554 PID 33236; no 5037 listener |
| Boot | PASS | 8 bounded attempts; final `get-state=device` and `sys.boot_completed=1` under the frozen checks |
| Framework | FAIL | `FRAMEWORK_RUNTIME:EXCLUDED_PID_DRIFT`; failure occurred before any framework setup command or stability sample |
| Burn-in | NOT RUN | 0/24 cycles, 0 seconds credited |
| Settings a11y | NOT RUN | 0/3 observations; AndroidEnv was not instantiated |
| DEV grid | NOT RUN | 0/12 cells |
| Cleanup | PASS | Emulator and locked 5038 server exited; final clean-baseline wait passed |
| Seal | PASS | Two external logs copied once after handle closure; temporary live root removed |
| Terminal writer | PASS | One rich completion, schema errors `[]`, 12 ordered journal entries |

Run wall time was 129.548 seconds. Generation calls, model tokens, held-out captures, and task actions were all zero.

## First-broken-edge interpretation

Direct evidence:

- The write-once checkpoint fixes the first edge at journal sequence 6, phase `framework`.
- The frozen framework routine returned before setup and before its repeated stability loop because the observed excluded-process PID set differed from the two preregistered abnormal PIDs (11316 and 17716).
- The immediately subsequent cleanup snapshot contained multiple short-lived project ADB helper command processes in addition to 11316/17716. Examples include emulator overlay and multidisplay setup commands. There was still no 5037 listener.
- Cleanup later converged to the exact original excluded set, with all project listeners and owned runtime processes absent.

Inference, not a direct reconstruction of the failed sample:

- The most plausible explanation is that the generic ownership check treated legitimate, short-lived emulator startup ADB clients as forbidden excluded-PID drift. This is an invariant/observability mismatch, rather than evidence that framework services themselves failed.
- The exact pre-framework snapshot was not persisted by the inherited early-return path. Therefore this run cannot identify the precise transient PID(s) that triggered sequence 6, and it must remain `RUNTIME_UNSTABLE` rather than being relabeled as a false rejection.
- Per the frozen stop rule, no rule was changed and no second M4 chain was run.

## Terminal and artifact audit

- Artifact manifest: 83 listed files; 83 actual non-manifest files; 0 missing, extra, size-mismatched, or hash-mismatched records.
- Journal: 12 immutable entry files and 12 NDJSON records; sequences 1–12 contiguous and semantically identical.
- Terminal accounting: exactly one `qualification_completion.json`; `terminal_mode=rich`; validation passed with zero schema errors.
- First edge preservation: later cleanup, sealing, and terminal success did not replace `FRAMEWORK_RUNTIME:EXCLUDED_PID_DRIFT`.
- Log lifecycle: `emulator.stdout.bin` = 13,900 bytes, SHA-256 `1800b0a6c332139aefccbde85e31359d1683c2fb54b514e515d36c0dda1375a7`; `emulator.stderr.bin` = 0 bytes, SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

- Post-run residue: no listener on 5037/5038/5554/5555/8554; no project ADB/emulator/qemu process; no `infra_m4_live_*` temporary directory.
- Legacy M1 log remains 9,590 bytes with SHA-256 `ffddf9d0862f8f3e58b424e1e8f774e546875634a0ba81f5e720333284b48b1c`.
- Protected WIP before/after/current hashes are unchanged:
  - `episode_controller.py`: `fc0e82e0fde90119365d4f685f080eb4519bf2f602e4bda58de5d4809a40fe33`
  - `protocol_v2_guard.py`: `ff89d6b70be4b4738646d262beb67d7b7e932e9eb95956d940b1c5000a999d10`
  - `test_protocol_v2_2_r79_r78_trace_replay.py`: `5bb1f1e3de673a1072cfee62938b761a62fd69c187d5eadf54bc46b115a3fd0a`

## Offline qualification accounting

- Focused M4 fault tests: 17/17 passed, covering every phase plus missing helper/`AttributeError`, rich JSON serialization failure, process timeout, cleanup exception, duplicate completion, and independent-finalizer execution.
- Full `role_binding_timing` namespace: passed (160 tests represented by the frozen quiet-output stream).
- Full regression: 1,150 passed and the same one accepted legacy failure remained: `tests/scripts/test_protocol_v2_2_r78_h17_candidate.py::test_r78_candidate_static_manifest_validation_passes`.
- Compile, schema corruption, source-isolation, binary-hash, protected-WIP, legacy-log, and zero-call runtime preflight gates passed.

## Claim–evidence verdict

| Claim | Verdict | Boundary |
|---|---|---|
| M4 preserves the first broken edge through a real early failure | SUPPORTED | One real framework-gate failure plus fault-injection coverage |
| Independent terminal writer leaves exactly one valid completion | SUPPORTED | One rich completion; schema validation passed; duplicate guard tested |
| External live-log ownership and post-close sealing work | SUPPORTED | Both logs sealed once; handles closed; source temp root removed |
| Explicit 5038 registration and boot readiness work | SUPPORTED, NARROW | This one run only; 5037 remained absent |
| Runtime is stable for at least 24 cycles / 180 seconds | UNTESTED | Burn-in was not reached |
| Settings same-observation screenshot+a11y succeeds 3/3 | UNTESTED | AndroidEnv/a11y route was not started |
| Four-app DEV grid succeeds 12/12 | UNTESTED | Grid was not started |
| v0.3 preparation is authorized | REJECTED | Requires 12/12 DEV after qualified burn-in |
| Any held-out, model, memory, controller-efficacy, or role-binding claim | UNTESTED | 0 generation calls, 0 held-out captures, 0 efficacy cells |

## Stop decision

`STOP_INFRA_M4_RUNTIME_UNSTABLE`. No retry, held-out collection, Phase C, model call, or v0.3 protocol preparation is authorized by this result. A future phase, if separately approved and preregistered, would first need to distinguish persistent forbidden owners from bounded project-owned transient ADB clients while preserving exact command-line and parentage evidence at the failing checkpoint.

## Authoritative artifacts

- `05_project/artifacts/role_binding_timing/infra_m4_terminal_accounting_hardening/qualification_completion.json`
- `05_project/artifacts/role_binding_timing/infra_m4_terminal_accounting_hardening/terminal_validation.json`
- `05_project/artifacts/role_binding_timing/infra_m4_terminal_accounting_hardening/terminal_writer_receipt.json`
- `05_project/artifacts/role_binding_timing/infra_m4_terminal_accounting_hardening/phase_journal/`
- `05_project/artifacts/role_binding_timing/infra_m4_terminal_accounting_hardening/artifact_manifest.json`
- `05_project/artifacts/role_binding_timing/infra_m4_offline_gates/offline_gate_result.json`
