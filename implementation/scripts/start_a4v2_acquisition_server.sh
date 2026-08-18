#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${RAVEN_REPO_DIR:-/root/autodl-tmp/RAVEN-M-AWM-Audit}"
ENV_DIR="${RAVEN_ENV_DIR:-/root/autodl-tmp/envs/qwen_vllm}"
MODEL_DIR="${RAVEN_MODEL_SOURCE:-/root/autodl-tmp/models/Qwen3-VL-32B-Instruct-modelscope}"
QUALIFICATION="${A4V2_REMOTE_QUALIFICATION:-/root/autodl-tmp/a2_qualification/A2_RUNTIME_REMOTE_MODEL.json}"
INTENT="${A4V2_ACQUISITION_LAUNCH_INTENT:-${REPO_DIR}/evidence/a4v2/A4V2_ACQUISITION_SERVER_LAUNCH_INTENT.json}"

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}"
export VLLM_USE_FLASHINFER_SAMPLER="${VLLM_USE_FLASHINFER_SAMPLER:-0}"

REPO_DIR="${REPO_DIR}" ENV_DIR="${ENV_DIR}" MODEL_DIR="${MODEL_DIR}" \
QUALIFICATION="${QUALIFICATION}" INTENT="${INTENT}" "${ENV_DIR}/bin/python" - <<'PY'
import importlib.metadata, json, os, subprocess
from hashlib import sha256
from pathlib import Path

repo = Path(os.environ["REPO_DIR"]).resolve()
qualification_path = Path(os.environ["QUALIFICATION"]).resolve()
qualification = json.loads(qualification_path.read_text(encoding="utf-8"))
model = str(Path(os.environ["MODEL_DIR"]).resolve())
if qualification.get("status") != "pass" or qualification.get("generation_calls") != 0:
    raise SystemExit("remote model qualification did not pass")
if qualification.get("model_realpath") != model:
    raise SystemExit("model realpath differs from qualification")
packages = {name: importlib.metadata.version(name) for name in ("vllm", "torch", "transformers")}
if any(packages[name] != qualification["packages"].get(name) for name in packages):
    raise SystemExit("runtime package drift")
command = [
    str(Path(os.environ["ENV_DIR"]) / "bin/python"),
    str(Path(os.environ["ENV_DIR"]) / "bin/vllm"), "serve", model,
    "--served-model-name", "Qwen/Qwen3-VL-32B-Instruct", "--host", "127.0.0.1",
    "--port", "18000", "--tensor-parallel-size", "1", "--dtype", "bfloat16",
    "--gpu-memory-utilization", os.environ.get("RAVEN_GPU_MEMORY_UTILIZATION", "0.92"),
    "--max-model-len", "65536", "--max-num-seqs", "1",
    "--limit-mm-per-prompt", '{"image":1}', "--generation-config", "vllm",
    "--no-enable-log-requests",
]
intent = {
    "schema": "a4v2.acquisition_server_launch_intent.v1",
    "status": "launch_pending_live_qualification",
    "pid_before_exec": os.getppid(),
    "repository_commit": subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip(),
    "model_realpath": model,
    "model_manifest_sha256": qualification["model_manifest_sha256"],
    "remote_qualification_sha256": sha256(qualification_path.read_bytes()).hexdigest(),
    "packages": packages,
    "served_model_id": "Qwen/Qwen3-VL-32B-Instruct",
    "host": "127.0.0.1", "port": 18000, "command": command,
}
path = Path(os.environ["INTENT"]); path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(intent, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

exec "${ENV_DIR}/bin/python" "${ENV_DIR}/bin/vllm" serve "$(realpath "${MODEL_DIR}")" \
  --served-model-name Qwen/Qwen3-VL-32B-Instruct --host 127.0.0.1 --port 18000 \
  --tensor-parallel-size 1 --dtype bfloat16 \
  --gpu-memory-utilization "${RAVEN_GPU_MEMORY_UTILIZATION:-0.92}" \
  --max-model-len 65536 --max-num-seqs 1 --limit-mm-per-prompt '{"image":1}' \
  --generation-config vllm --no-enable-log-requests
