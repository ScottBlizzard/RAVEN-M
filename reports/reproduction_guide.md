# RAVEN-M reproduction guide

## Scope

This repository uses one Windows AndroidWorld host and one private four-RTX
4090 model host. Raw runs stay under `runs/`; all protocol-critical source,
configuration, schemas, hashes, and small audits are versioned in Git.

## Locked environment

- AndroidWorld commit:
  `3e50888527ef9f29b9157ecd537e408008bb1c85`
- Qwen/Qwen3-VL-32B-Instruct revision:
  `0cfaf48183f594c314753d30a4c4974bc75f3ccb`
- Model backend: Transformers BF16, SDPA, GPUs 0–3, deterministic generation
- Total context cap: 8192; maximum new tokens: 256
- Emulator: Android API 33, Pixel 6 profile, console 5554, gRPC 8554

The authoritative machine lock is `04_protocols/environment_lock.yaml`.

## Local services

From the repository root:

```powershell
.\05_project\scripts\start_model_tunnel.ps1
.\06_local_runtime\scripts\start_emulator.ps1
```

Confirm `http://127.0.0.1:18000/health` reports the exact model revision and
backend. The server itself binds only to `127.0.0.1` on the model host.

## Development gates

```powershell
$python = ".\06_local_runtime\envs\androidworld\Scripts\python.exe"
$env:PYTHONPATH = (Resolve-Path ".\05_project\src").Path
& $python -m pytest .\05_project\tests -q
& $python .\05_project\scripts\audit_protocol.py
& $python .\05_project\scripts\audit_g6.py
& $python .\05_project\scripts\run_corruption_stress.py
```

G7 uses only the non-Hard manifest:

```powershell
.\05_project\scripts\start_method_dev_suite.ps1 `
  -SuiteId method_dev_g6_g7_v8_20260723
```

After it finishes, create the fixed 50-event review packet, complete its manual
labels, and run:

```powershell
& $python .\05_project\scripts\sample_retrieval_audit.py `
  --suite-dir .\runs\method_dev_g6_g7\method_dev_g6_g7_v8_20260723
& $python .\05_project\scripts\audit_g7.py `
  --suite-summary .\runs\method_dev_g6_g7\method_dev_g6_g7_v8_20260723\suite_summary.json
```

## Freeze and scored execution

The final preregistration generator refuses to run without a passed G7 audit.
The scored runner independently rechecks every recorded hash, the environment
permission flag, protocol audit, model identity, free disk, and Git tag before
creating an episode.

Once those freeze artifacts exist, the full sequential launcher is:

```powershell
.\05_project\scripts\start_frozen_pipeline.ps1
```

It resumes completed result cells and runs:

1. 95 breadth episodes;
2. 19 full-set S0 controls;
3. 114 additional confirmatory episodes;
4. 136 ablation and budget-control episodes;
5. frozen statistical analysis.

The ordered schedule is
`05_project/configs/experiments/hard_schedule_v1.json`. Do not hand-edit,
reorder, skip, or selectively rerun scored agent failures.

## Results

The analyzer writes:

- `reports/generated/table_main.csv`
- `reports/generated/table_efficiency.csv`
- `reports/generated/table_ablation.csv`
- `reports/generated/bootstrap_replicates.csv`
- `reports/generated/statistics.json`
- `reports/generated/figure_tsr_wilson.png`
- `reports/generated/figure_efficiency_pareto.png`
- `reports/generated/results_report.md`

Every TSR includes numerator and denominator. Primary uncertainty uses 10,000
task-clustered bootstrap replicates at seed 20260723; Wilson intervals and exact
McNemar statistics are reported as specified in the frozen protocol.
