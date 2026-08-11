#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${RAVEN_REPO_DIR:-/root/autodl-tmp/RAVEN-M-A7-GATED}"
ENV_DIR="${RAVEN_ENV_DIR:-/root/autodl-tmp/envs/qwen_vllm}"
MODEL_DIR="${RAVEN_MODEL_SOURCE:-/root/autodl-tmp/models/Qwen3-VL-32B-Instruct-modelscope}"
QUALIFICATION="${A7_REMOTE_QUALIFICATION:-/root/autodl-tmp/a2_qualification/A2_RUNTIME_REMOTE_MODEL.json}"
PREFLIGHT="${A7_PREFLIGHT:-${REPO_DIR}/evidence/a678/A678_ZERO_GENERATION_PREFLIGHT.json}"
DRY_RUN="${A7_LAUNCH_DRY_RUN:-0}"
if [[ "${DRY_RUN}" == "1" ]]; then
  DEFAULT_INTENT="${REPO_DIR}/evidence/a678/A7_GATED_SERVER_LAUNCH_INTENT_DRY_RUN.json"
else
  DEFAULT_INTENT="${REPO_DIR}/evidence/a678/A7_GATED_SERVER_LAUNCH_INTENT.json"
fi
INTENT="${A7_SERVER_LAUNCH_INTENT:-${DEFAULT_INTENT}}"
PORT="${RAVEN_SERVER_PORT:-18000}"

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}"
export VLLM_USE_FLASHINFER_SAMPLER="${VLLM_USE_FLASHINFER_SAMPLER:-0}"
export PYTHONPATH="${REPO_DIR}/implementation/src"

QUALIFICATION="${QUALIFICATION}" MODEL_DIR="${MODEL_DIR}" PORT="${PORT}" \
PREFLIGHT="${PREFLIGHT}" INTENT="${INTENT}" ENV_DIR="${ENV_DIR}" \
DRY_RUN="${DRY_RUN}" \
  "${ENV_DIR}/bin/python" - <<'PY'
import importlib.metadata
import json
import os
from hashlib import sha256
from pathlib import Path

from raven_m.official_qwen_mobile.a678_contract import validate_preflight_report

qualification_path = Path(os.environ["QUALIFICATION"]).resolve()
qualification = json.loads(qualification_path.read_text(encoding="utf-8"))
preflight_path = Path(os.environ["PREFLIGHT"]).resolve()
validate_preflight_report(preflight_path)
model_realpath = str(Path(os.environ["MODEL_DIR"]).resolve())
if qualification.get("status") != "pass" or qualification.get("generation_calls") != 0:
    raise SystemExit("remote model qualification did not pass")
if qualification.get("model_realpath") != model_realpath:
    raise SystemExit("launcher model path differs from qualified realpath")
versions = {
    name: importlib.metadata.version(name)
    for name in ("vllm", "torch", "transformers")
}
if any(versions[name] != qualification["packages"].get(name) for name in versions):
    raise SystemExit("launcher package versions differ from qualified runtime")
port = int(os.environ["PORT"])
command = [
    str(Path(os.environ["ENV_DIR"]) / "bin" / "vllm"),
    "serve",
    model_realpath,
    "--served-model-name",
    "Qwen/Qwen3-VL-32B-Instruct",
    "--host",
    "127.0.0.1",
    "--port",
    str(port),
    "--tensor-parallel-size",
    "1",
    "--dtype",
    "bfloat16",
    "--gpu-memory-utilization",
    os.environ.get("RAVEN_GPU_MEMORY_UTILIZATION", "0.92"),
    "--max-model-len",
    os.environ.get("RAVEN_MAX_MODEL_LEN", "65536"),
    "--max-num-seqs",
    "1",
    "--limit-mm-per-prompt",
    '{"image":1}',
    "--generation-config",
    "vllm",
    "--no-enable-log-requests",
]
intent = {
    "schema": "a7_gated_server_launch_intent_v1",
    "status": (
        "dry_run_only_no_live_process"
        if os.environ["DRY_RUN"] == "1"
        else "launch_pending_live_qualification"
    ),
    "pid_before_exec": None if os.environ["DRY_RUN"] == "1" else os.getppid(),
    "model_realpath": model_realpath,
    "model_manifest_sha256": qualification["model_manifest_sha256"],
    "remote_qualification_sha256": sha256(qualification_path.read_bytes()).hexdigest(),
    "a678_preflight_sha256": sha256(preflight_path.read_bytes()).hexdigest(),
    "packages": versions,
    "served_model_id": "Qwen/Qwen3-VL-32B-Instruct",
    "host": "127.0.0.1",
    "port": port,
    "command": command,
}
intent_path = Path(os.environ["INTENT"])
intent_path.parent.mkdir(parents=True, exist_ok=True)
intent_path.write_text(
    json.dumps(intent, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
PY

if [[ "${DRY_RUN}" == "1" ]]; then
  echo "A7 launcher dry run passed; no vLLM process was started."
  exit 0
fi

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
