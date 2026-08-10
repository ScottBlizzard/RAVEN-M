#!/usr/bin/env bash
set -euo pipefail

ENV_DIR="${RAVEN_ENV_DIR:-/root/autodl-tmp/envs/qwen_vllm}"
MODEL_DIR="${RAVEN_MODEL_SOURCE:-/root/autodl-tmp/models/Qwen3-VL-32B-Instruct-modelscope}"
QUALIFICATION="${A2_REMOTE_QUALIFICATION:-/root/autodl-tmp/a2_qualification/A2_RUNTIME_REMOTE_MODEL.json}"
RUN_DIR="${RAVEN_RUN_DIR:-/root/autodl-tmp/runs/a2_verified_progress_server}"
PORT="${RAVEN_SERVER_PORT:-18000}"
RECEIPT="${A2_SERVER_LAUNCH_RECEIPT:-${RUN_DIR}/A2_SERVER_LAUNCH_RECEIPT.json}"

mkdir -p "${RUN_DIR}"
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}"
export VLLM_USE_FLASHINFER_SAMPLER="${VLLM_USE_FLASHINFER_SAMPLER:-0}"

QUALIFICATION="${QUALIFICATION}" MODEL_DIR="${MODEL_DIR}" PORT="${PORT}" RECEIPT="${RECEIPT}" ENV_DIR="${ENV_DIR}" \
  "${ENV_DIR}/bin/python" - <<'PY'
import importlib.metadata
import json
import os
from pathlib import Path

qualification_path = Path(os.environ["QUALIFICATION"]).resolve()
qualification = json.loads(qualification_path.read_text(encoding="utf-8"))
model_realpath = str(Path(os.environ["MODEL_DIR"]).resolve())
if qualification.get("status") != "pass" or qualification.get("generation_calls") != 0:
    raise SystemExit("remote A2 model qualification did not pass")
if qualification.get("model_realpath") != model_realpath:
    raise SystemExit("launcher model path differs from qualified realpath")
versions = {}
for name in ("vllm", "torch", "transformers"):
    versions[name] = importlib.metadata.version(name)
if any(versions[name] != qualification["packages"].get(name) for name in versions):
    raise SystemExit("launcher package versions differ from qualified runtime")
port = int(os.environ["PORT"])
command = [
    str(Path(os.environ["ENV_DIR"]) / "bin" / "vllm"), "serve", model_realpath,
    "--served-model-name", "Qwen/Qwen3-VL-32B-Instruct", "--host", "127.0.0.1",
    "--port", str(port), "--tensor-parallel-size", "1", "--dtype", "bfloat16",
    "--gpu-memory-utilization", os.environ.get("RAVEN_GPU_MEMORY_UTILIZATION", "0.92"),
    "--max-model-len", os.environ.get("RAVEN_MAX_MODEL_LEN", "65536"),
    "--max-num-seqs", "1", "--limit-mm-per-prompt", '{"image":1}',
    "--generation-config", "vllm", "--no-enable-log-requests",
]
receipt = {
    "schema": "a2_v1r1_server_launch_intent_v1",
    "status": "launch_pending_live_qualification",
    "pid_before_exec": os.getppid(),
    "model_realpath": model_realpath,
    "model_manifest_sha256": qualification["model_manifest_sha256"],
    "remote_qualification_sha256": __import__("hashlib").sha256(qualification_path.read_bytes()).hexdigest(),
    "packages": versions,
    "served_model_id": "Qwen/Qwen3-VL-32B-Instruct",
    "host": "127.0.0.1",
    "port": port,
    "command": command,
}
Path(os.environ["RECEIPT"]).write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

exec "${ENV_DIR}/bin/vllm" serve "$(realpath "${MODEL_DIR}")" \
  --served-model-name Qwen/Qwen3-VL-32B-Instruct \
  --host 127.0.0.1 \
  --port "${PORT}" \
  --tensor-parallel-size 1 \
  --dtype bfloat16 \
  --gpu-memory-utilization "${RAVEN_GPU_MEMORY_UTILIZATION:-0.92}" \
  --max-model-len "${RAVEN_MAX_MODEL_LEN:-65536}" \
  --max-num-seqs 1 \
  --limit-mm-per-prompt '{"image":1}' \
  --generation-config vllm \
  --no-enable-log-requests
