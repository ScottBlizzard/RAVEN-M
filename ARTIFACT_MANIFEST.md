# A0–A2 Audit Artifact Manifest

Independent review instructions: `GPT_PRO_A2_AUDIT_REQUEST.md`.

## Assignment

- `assessment/夏令营考核题目.pdf`
- `assessment/夏令营考核题目_提取文本.txt`

## Results and design evidence

- `evidence/baseline/official_qwen32b_full_hard_combined_corrected_final.md` — official-style A0 aggregate across three seeds; seed 20260806 is the paired 19-task control.
- `evidence/baseline/official_qwen32b_full_hard_failure_taxonomy_2026-08-08.md` — A0 failure mechanisms.
- `evidence/baseline/official_qwen32b_full_hard_case_notes_2026-08-08.md` — trace-grounded A0 cases.
- `evidence/a1/A1_ACTION_WORKING_MEMORY_RESULTS_2026-08-10.md` — paired A0/A1 result and cost analysis.
- `evidence/a1/A1_ZERO_GENERATION_PREFLIGHT.json` — A1 no-generation qualification.
- `evidence/a2/A2_DESIGN_RATIONALE_AND_A1_REPLAY_2026-08-10.md` — why A2 contains these minimal changes.
- `evidence/a2/A2_ZERO_GENERATION_PREFLIGHT.json` — A2 no-generation qualification and source freeze.

## Frozen protocols

- `protocols/A1_ACTION_WORKING_MEMORY_PREREG_2026-08-10.md`
- `protocols/A1_ACTION_WORKING_MEMORY_RUNBOOK.md`
- `protocols/A2_VERIFIED_PROGRESS_MEMORY_PREREG_2026-08-10.md`
- `protocols/A2_VERIFIED_PROGRESS_MEMORY_RUNBOOK.md`

## Core implementation

- `implementation/src/raven_m/official_qwen_mobile/protocol.py` — official prompt/action protocol plus opt-in A1/A2 suffixes.
- `implementation/src/raven_m/official_qwen_mobile/controller.py` — screenshot-only loop, L0–L5 audit, memory and separate guard hooks.
- `implementation/src/raven_m/official_qwen_mobile/working_memory.py` — A1 mechanism.
- `implementation/src/raven_m/official_qwen_mobile/progress_memory.py` — A2 memory and separate cost guard.
- `implementation/scripts/run_official_qwen_mobile.py` — common A0/A1/A2 runner.
- `implementation/scripts/preflight_a2_verified_progress.py` — zero-generation A2 gate.
- `implementation/scripts/run_a2_verified_progress.ps1` — scored A2 launcher.
- `implementation/configs/androidworld_hard_v2_instances.json` — frozen instances and native budgets.
- `implementation/configs/a2_verified_progress_memory_hard_seed20260806.json` — A2 experimental contract.

## Tests

- `implementation/tests/official_qwen_mobile/test_progress_memory.py`
- `implementation/tests/official_qwen_mobile/test_working_memory.py`
- `implementation/tests/official_qwen_mobile/test_official_qwen_controller.py`
- `implementation/tests/official_qwen_mobile/test_protocol.py`
- `implementation/tests/models/test_vllm_client.py`

## Deliberately absent

Superseded RAVEN-M revisions, public-framework selection materials, MobileUse/B2/C0 code, failed rescue packets, and earlier GPT planning documents were removed from this branch. They remain in Git history and are not evidence for the A2 audit.

The exact A1 implementation and source freeze are recoverable at commit `fbc25dc`; A2 deliberately modifies shared controller files on this branch.
