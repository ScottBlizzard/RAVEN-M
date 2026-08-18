# A4-v2 execution runbook

This runbook starts only after the active LRER suite releases the shared GPU
and emulator. Do not run donor collection concurrently with LRER.

## 1. Collect the required donor panel

Start the exact server with `start_a4v2_acquisition_server.sh`, then create
`A4V2_ACQUISITION_SERVER_RECEIPT.json` using
`qualify_a4v2_acquisition_server.py`. Materialize and run the required panel:

```powershell
python implementation/scripts/materialize_a4v2_donor_manifest.py
python implementation/scripts/run_a4v2_donor_acquisition.py `
  --server-receipt evidence/a4v2/A4V2_ACQUISITION_SERVER_RECEIPT.json
```

Use `implementation/configs/a4v2_awm_donor_acquisition_plan.json`. Run every
non-optional slot with the A0 official screenshot-only controller, its declared
seed and budget. Keep valid failures; do not rerun them under the same seed.
If a route has fewer than two evaluator-confirmed successes after all 14, run
the optional slot and then the single final fallback already frozen for that
route in plan v2. Do not invent more seeds after those finite supplements.

Seal the required panel and inspect `route_deficits`:

```powershell
python implementation/scripts/build_a4v2_donor_source_lock.py `
  --suite-dir <REQUIRED_PANEL_SUITE>
```

For every listed deficient route, materialize one immutable supplement manifest
(it contains that route's optional slot plus its final fallback), run it, then
rebuild the lock with both manifests and suites. Every selected supplement is
run even when the optional slot succeeds:

```powershell
python implementation/scripts/materialize_a4v2_donor_manifest.py `
  --supplement-route <ROUTE_ID> `
  --output evidence/a4v2/A4V2_DONOR_ACQUISITION_MANIFEST_SUPPLEMENT_<ROUTE_ID>.json
python implementation/scripts/run_a4v2_donor_acquisition.py `
  --manifest evidence/a4v2/A4V2_DONOR_ACQUISITION_MANIFEST_SUPPLEMENT_<ROUTE_ID>.json `
  --server-receipt evidence/a4v2/A4V2_ACQUISITION_SERVER_RECEIPT.json
```

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
  --checkpoint evidence/a4v2/induction_responses/checkpoint.json `
  --server-receipt evidence/a4v2/A4V2_ACQUISITION_SERVER_RECEIPT.json

python implementation/scripts/freeze_a4v2_workflow_bank.py `
  --induction-index evidence/a4v2/induction_packets/index.json `
  --responses-dir evidence/a4v2/induction_responses `
  --checkpoint evidence/a4v2/induction_responses/checkpoint.json `
  --model-id Qwen/Qwen3-VL-32B-Instruct
```

The induction runner performs exactly one single-transport text call per route,
checkpoints after every call, and resumes without duplicating completed calls.
The freeze script rejects missing, one-step, generic or insufficiently sourced
workflows.

## 4. Preflight and live receipt

```powershell
python implementation/scripts/preflight_a4v2_awm.py `
  --acquisition-receipt evidence/a4v2/A4V2_ACQUISITION_SERVER_RECEIPT.json
```

The preflight must be `pass`, generation calls must be zero, and all source and
bank hashes must be frozen. After starting or reusing the live server, run
`implementation/scripts/qualify_a4v2_live_server.py` with the current launch
intent, preflight, bank and output receipt. A receipt from A345 or LRER is not
reused.

Before primary scoring, also build the pre-frozen deranged bank and its own
zero-generation preflight. It is not run unless the sealed primary result
contains a paired gain:

```powershell
python implementation/scripts/build_a4v2_shuffled_ablation_bank.py `
  --primary-bank evidence/a4v2/A4V2_FROZEN_WORKFLOW_BANK.json `
  --output evidence/a4v2/A4V2_SHUFFLED_ABLATION_BANK.json
python implementation/scripts/preflight_a4v2_awm.py `
  --bank evidence/a4v2/A4V2_SHUFFLED_ABLATION_BANK.json `
  --acquisition-receipt evidence/a4v2/A4V2_ACQUISITION_SERVER_RECEIPT.json `
  --source-freeze-output evidence/a4v2/A4V2_SHUFFLED_ABLATION_SOURCE_FREEZE.json `
  --output evidence/a4v2/A4V2_SHUFFLED_ABLATION_PREFLIGHT.json
```

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
If it is 7/7, run the remaining twelve under the same frozen bank, model and
controller with `--a4v2-remaining12 --a4v2-seven-aggregate <SEALED_AGGREGATE>`.
The runner validates that the parent aggregate is exactly the fixed seven at
7/7, binds its hash, and never repeats those seven.
`run_a4v2_campaign.py` performs this release automatically. If the primary
formal result contains a paired gain, it signs a fresh shuffled-bank receipt,
runs only those gain tasks under the new active-control identity, and seals
`A4V2_SHUFFLED_ACTIVE_CONTROL_RESULT.json`; it never changes the primary bank
or result.

## 6. Attribution

For every task, report opportunity, workflow match, retrieved IDs, read count,
first useful divergence, reward, cost and earliest L0--L6 break. Silent success
is preservation only. Any paired gain requires the separately named shuffled-
content ablation specified in the preregistration.
