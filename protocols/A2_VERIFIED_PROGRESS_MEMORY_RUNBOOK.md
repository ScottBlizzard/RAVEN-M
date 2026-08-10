# A2 Verified Progress Memory — Runbook

## No-GPU preparation

From the repository root:

```powershell
$python = "06_local_runtime\envs\androidworld\Scripts\python.exe"
& $python implementation\scripts\preflight_a2_verified_progress.py
```

Do not start a scored run unless `evidence/a2/A2_ZERO_GENERATION_PREFLIGHT.json` says `status: pass`, `generation_calls: 0`, and its source freeze still matches.

## GPU server

Use the already qualified official Qwen launcher and the frozen Qwen3-VL-32B model revision. The local tunnel must expose its OpenAI-compatible endpoint at `http://127.0.0.1:18000`.

## Scored suite

```powershell
implementation\scripts\run_a2_verified_progress.ps1
```

The runner uses exactly the 19 Hard instances with task seed 20260806 and their native action budgets. It checkpoints after every valid task.

If an infrastructure-invalid task stops the suite, diagnose the recorded invalid attempt and resume only that suite:

```powershell
implementation\scripts\run_a2_verified_progress.ps1 -ResumeSuiteDir <suite-directory>
```

Do not rerun already valid tasks and do not change A2 thresholds, prompt, task order, model parameters, or source files after preflight. Any such change requires a new named arm and a new preflight.

## After completion

Generate a paired A0/A1/A2 report. Keep memory attribution and cost-guard attribution in separate columns. Do not describe a guard-only runtime saving as evidence that memory improved task reasoning.
