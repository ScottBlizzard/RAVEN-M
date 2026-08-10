# A2-v1r1 Verified Progress Memory — Runbook

## No-GPU preparation

From the repository root:

```powershell
$python = "06_local_runtime\envs\androidworld\Scripts\python.exe"
& $python implementation\scripts\preflight_a2_verified_progress.py
```

Do not start a scored run unless `evidence/a2/A2_ZERO_GENERATION_PREFLIGHT.json` says `status: pass`, `generation_calls: 0`, `errors: []`, and its source freeze still matches. The A0/A1 ledger, corrected A1 guard replay, combined runtime qualification, and full tests are mandatory parts of this gate.

## GPU server and live receipt

Start `implementation/scripts/start_a2_verified_progress_server.sh` on the qualified server. After `/v1/models` becomes healthy, run in a second server shell:

```bash
/root/autodl-tmp/envs/qwen_vllm/bin/python implementation/scripts/qualify_a2_live_server.py \
  --launch-intent /root/autodl-tmp/runs/a2_verified_progress_server/A2_SERVER_LAUNCH_RECEIPT.json \
  --output /root/autodl-tmp/runs/a2_verified_progress_server/A2_SERVER_LIVE_RECEIPT.json
```

Copy the live receipt to the local machine. Only `status: pass` is accepted; it binds the actual process ID, command line, served model, model realpath, manifest, port, and package versions.

## Scored suite

```powershell
implementation\scripts\run_a2_verified_progress.ps1 -LaunchReceipt <copied-live-server-receipt.json>
```

The runner uses exactly the ordered 19 Hard instances with task seed 20260806 and their native action budgets. Each model call has one HTTP transport attempt. It checkpoints an immutable hashed episode reference after every valid task.

If an infrastructure-invalid task stops the suite, diagnose the recorded invalid attempt and resume the same suite:

```powershell
implementation\scripts\run_a2_verified_progress.ps1 -LaunchReceipt <same-live-receipt.json> -ResumeSuiteDir <suite-directory>
```

Resume never reruns a valid completed task. Every reference is rehashed and reread; an unknown status, foreign/duplicate key, corrupt episode, signature mismatch, invalid attempt, lifecycle error, or orphan evidence prevents final aggregation.

Do not change thresholds, prompt, task order, model parameters, or source files after preflight. Any such change requires a new named arm and new qualification.

## After completion

```powershell
$python implementation\scripts\validate_a2_paired_suite.py \
  --suite-dir <suite-directory> \
  --ledger evidence\a2\A0_A1_PAIRED_REFERENCE_20260810.json \
  --json-output <suite-directory>\A2_PAIRED_VALIDATION.json \
  --md-output <suite-directory>\A2_PAIRED_VALIDATION.md
```

Report A2-v1r1 as a compound package. Keep memory exposure, guard exposure, and manual support review separate. Do not describe guard-only runtime savings as memory reasoning gains.
