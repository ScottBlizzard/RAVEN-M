# A0–A2-v1r1 Audit Artifact Manifest

Independent review basis: `GPT_PRO_A2_AUDIT_REQUEST.md` and the returned `A2_PRO_AUDIT.md` supplied outside this repository.

## Assignment and paired evidence

- `assessment/夏令营考核题目.pdf`
- `evidence/baseline/official_qwen32b_full_hard_combined_corrected_final.md` — A0 evidence; seed 20260806 is the paired control.
- `evidence/a1/A1_ACTION_WORKING_MEMORY_RESULTS_2026-08-10.md` — A1 result/cost analysis.
- `evidence/a2/A0_A1_PAIRED_REFERENCE_20260810.json` — exact per-episode A0/A1 ledger rebuilt from raw traces.
- `evidence/a2/A1_EXACT_GUARD_REPLAY_20260810.json` — zero-generation corrected-guard replay.
- `evidence/a2/A2_DESIGN_RATIONALE_AND_A1_REPLAY_2026-08-10.md` — targeted design rationale.

## Runtime identity and qualification

- `evidence/a2/A2_RUNTIME_REMOTE_MODEL.json` — all manifest-listed Qwen model files recomputed on the no-GPU server.
- `evidence/a2/A2_RUNTIME_LOCAL_ANDROID.json` — AndroidWorld source digest, emulator/ADB identity, resolution, and ordered tasks.
- `evidence/a2/A2_RUNTIME_QUALIFICATION.json` — combined zero-generation receipt.
- `evidence/a2/A2_ZERO_GENERATION_PREFLIGHT.json` — final source-frozen A2 gate (generated only after all edits/tests).

## Frozen protocol and implementation

- `protocols/A2_VERIFIED_PROGRESS_MEMORY_PREREG_2026-08-10.md`
- `protocols/A2_VERIFIED_PROGRESS_MEMORY_RUNBOOK.md`
- `implementation/configs/a2_verified_progress_memory_hard_seed20260806.json`
- `implementation/src/raven_m/official_qwen_mobile/progress_memory.py`
- `implementation/src/raven_m/official_qwen_mobile/controller.py`
- `implementation/src/raven_m/official_qwen_mobile/a2_suite.py`
- `implementation/src/raven_m/models/vllm_client.py`
- `implementation/scripts/run_official_qwen_mobile.py`
- `implementation/scripts/run_a2_verified_progress.ps1`
- `implementation/scripts/start_a2_verified_progress_server.sh`
- `implementation/scripts/qualify_a2_runtime.py`
- `implementation/scripts/qualify_a2_live_server.py`
- `implementation/scripts/build_a2_reference_ledger.py`
- `implementation/scripts/replay_a1_exact_guard.py`
- `implementation/scripts/validate_a2_paired_suite.py`

## Tests

- `implementation/tests/official_qwen_mobile/test_progress_memory.py`
- `implementation/tests/official_qwen_mobile/test_official_qwen_controller.py`
- `implementation/tests/official_qwen_mobile/test_a2_suite.py`
- `implementation/tests/models/test_vllm_client.py`

## Scope and claim limits

A2-v1r1 is a compound arm: one-state outcome-aware memory, history deduplication, and a separately logged exact repeated-no-progress guard. It uses one seed and supports a descriptive paired diagnostic only. `verified` is a model-authored screenshot assertion, not objective verification. The evaluator remains the only success authority. Guard-exposed gains are never reported as pure memory effects.

Superseded RAVEN-M revisions, MobileUse/B2/C0 code, and earlier planning packets are deliberately absent from this audit branch but remain recoverable in Git history. The exact A1 implementation is recoverable at commit `fbc25dc`.
