# A4-v2 execution runbook

This runbook starts only after the active LRER suite releases the shared GPU
and emulator. Do not run donor collection concurrently with LRER.

## 1. Collect the required donor panel

Use `implementation/configs/a4v2_awm_donor_acquisition_plan.json`. Run every
non-optional slot with the A0 official screenshot-only controller, its declared
seed and budget. Keep valid failures; do not rerun them under the same seed.
If a route has fewer than two evaluator-confirmed successes, append a new seed
under a new acquisition-plan version and collect it. Optional third slots are
run only if the required 14 slots leave a route short or time permits.

Each successful donor lock must record donor ID, task class, difficulty, seed,
episode path and episode SHA-256. Assemble the exact seven route groups as
`evidence/a4v2/A4V2_DONOR_SOURCE_LOCK.json` with schema
`a4v2.donor_source_lock.v1`. No scored Hard episode is admissible.

## 2. Build the seven induction packets

```powershell
$env:PYTHONPATH='implementation/src'
python implementation/scripts/build_a4v2_induction_packets.py `
  --source-lock evidence/a4v2/A4V2_DONOR_SOURCE_LOCK.json
```

The builder validates success, hashes, independent seeds, Easy/Medium labels
and absence from the 19-Hard manifest. It masks task literals and removes
coordinates before emitting one official-AWM-style prompt per route.

## 3. Run offline induction and freeze the bank

With the qualified model available on local port 18000:

```powershell
python implementation/scripts/run_a4v2_offline_induction.py `
  --induction-index evidence/a4v2/induction_packets/index.json `
  --responses-dir evidence/a4v2/induction_responses `
  --checkpoint evidence/a4v2/A4V2_INDUCTION_CHECKPOINT.json

python implementation/scripts/freeze_a4v2_workflow_bank.py `
  --induction-index evidence/a4v2/induction_packets/index.json `
  --responses-dir evidence/a4v2/induction_responses `
  --model-id Qwen/Qwen3-VL-32B-Instruct
```

The induction runner performs exactly one single-transport text call per route,
checkpoints after every call, and resumes without duplicating completed calls.
The freeze script rejects missing, one-step, generic or insufficiently sourced
workflows.

## 4. Preflight and live receipt

```powershell
python implementation/scripts/preflight_a4v2_awm.py
```

The preflight must be `pass`, generation calls must be zero, and all source and
bank hashes must be frozen. After starting or reusing the live server, run
`implementation/scripts/qualify_a4v2_live_server.py` with the current launch
intent, preflight, bank and output receipt. A receipt from A345 or LRER is not
reused.

## 5. Run the fixed seven

Invoke the official runner with the frozen 19-task manifest (the A4-v2 runner
selects the preregistered seven in its own order):

```powershell
python implementation/scripts/run_official_qwen_mobile.py `
  --url http://127.0.0.1:18000 `
  --adb-path <ABSOLUTE_ADB_PATH> `
  --manifest implementation/configs/androidworld_hard_v2_instances.json `
  --a345-arm a4v2 `
  --a4v2-workflow-bank evidence/a4v2/A4V2_FROZEN_WORKFLOW_BANK.json `
  --a4v2-preflight-report evidence/a4v2/A4V2_ZERO_GENERATION_PREFLIGHT.json `
  --a4v2-launch-receipt evidence/a4v2/A4V2_LIVE_SERVER_RECEIPT.json `
  --run-stage observed_seed_fixed_seven
```

All seven valid episodes run without scientific fail-fast. If the result is
below 7/7, stop this identity after the complete route-level L0--L6 analysis.
If it is 7/7, freeze an expansion amendment and run the remaining twelve under
the same bank/model/controller identity. The current runner intentionally does
not auto-release the twelve before that observed gate exists.

## 6. Attribution

For every task, report opportunity, workflow match, retrieved IDs, read count,
first useful divergence, reward, cost and earliest L0--L6 break. Silent success
is preservation only. Any paired gain requires the separately named shuffled-
content ablation specified in the preregistration.

