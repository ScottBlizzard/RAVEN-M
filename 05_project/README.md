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

The mock service verifies serialization, image hashing, identifiers, tunnel
transport, response shape, and server logging. It is never a benchmark result.
Only the exact pinned Qwen checkpoint may satisfy the model gate.
