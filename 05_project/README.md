# RAVEN-M implementation

This directory contains project-owned code. Third-party benchmarks and model
weights remain outside it.

The 4090 host uses the dedicated data disk:

```text
physical project root: /mnt/sdb/ccj/raven_m_research
compatibility symlink: /home/ccj/workspace_1/raven_m_research
model cache:           /mnt/sdb/ccj/raven_m_research/05_project/model_cache/huggingface
```

Do not place model weights in `/home`, the root filesystem, or `/dev/shm`.

The first implemented slice is the split-host model-serving path:

```text
Windows Android host                     4090 model host
AndroidWorld + controller  --SSH tunnel-->  Qwen3-VL service
authoritative episode logs                 request/VRAM logs
```

## Model-service smoke

Prepare the server overlay environment:

```bash
bash scripts/bootstrap_model_host.sh
```

Start the no-GPU connectivity service:

```bash
RAVEN_MODEL_MODE=mock bash scripts/launch_model_server.sh
```

Start the pinned Transformers backend after the model snapshot is present:

```bash
RAVEN_MODEL_MODE=transformers \
bash scripts/launch_model_server.sh
```

The service binds `127.0.0.1:8000`; it is not exposed publicly. From Windows,
create an SSH tunnel:

```powershell
ssh -N -L 18000:127.0.0.1:8000 ccj@10.10.217.244
```

Then send a real AndroidWorld screenshot:

```powershell
python .\05_project\scripts\smoke_model_service.py `
  --url http://127.0.0.1:18000 `
  --image .\06_local_runtime\metadata\androidworld_smoke.png
```

## B0 excluded dry run

Start the private tunnel and the project-local emulator:

```powershell
.\05_project\scripts\start_model_tunnel.ps1
.\06_local_runtime\scripts\start_emulator.ps1
```

Run one non-scored B0 trajectory:

```powershell
$python = ".\06_local_runtime\envs\androidworld\Scripts\python.exe"
$adb = ".\06_local_runtime\android\sdk\platform-tools\adb.exe"
& $python .\05_project\scripts\run_b0_dry_run.py `
  --url http://127.0.0.1:18000 `
  --adb-path $adb `
  --task ContactsAddContact `
  --seed 20260723 `
  --max-steps 10 `
  --max-model-calls 20
```

Raw screenshots and trajectories are written under
`runs/excluded_protocol_dry_run/` and are deliberately excluded from Git and
all scored results. Every episode records model/revision/backend hashes,
first-pass and repaired action validity, normalized and pixel coordinates,
official evaluator output, teardown and reset.

## G3 non-Hard development suite

Run or resume the frozen executor-v1 G3 suite:

```powershell
.\05_project\scripts\start_g3_dev_suite.ps1 `
  -SuiteId g3_b0_executor_v1_20260723 `
  -Manifest D:\ZJU\Summer_Camp\RAVEN-M-Research\05_project\configs\task_manifests\dev_nonhard_v2.json
```

Rebuild the aggregate without reconnecting AndroidWorld:

```powershell
$python = ".\06_local_runtime\envs\androidworld\Scripts\python.exe"
$adb = ".\06_local_runtime\android\sdk\platform-tools\adb.exe"
& $python .\05_project\scripts\run_g3_dev_suite.py `
  --adb-path $adb `
  --suite-id g3_b0_executor_v1_20260723 `
  --manifest .\05_project\configs\task_manifests\dev_nonhard_v2.json `
  --aggregate-only
```

This is development-only. Raw G3 trajectories remain under
`runs/dev_nonhard_g3/` and are excluded from Git and scored results. The
measured gate report is `reports/g3_dev_gate.md`.

The first reference backend is frozen at an 8,192-token total context cap after
ten consecutive 7,704-token multimodal requests passed without OOM. See
`05_project/metadata/model_max_shape_stress.json` and
`reports/first_72_hours.md`.

The mock service verifies serialization, image hashing, identifiers, tunnel
transport, response shape, and server logging. It is never a benchmark result.
Only the exact pinned Qwen checkpoint may satisfy the model gate.
