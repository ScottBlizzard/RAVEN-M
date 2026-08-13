#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${RAVEN_REPO_DIR:-/root/autodl-tmp/RAVEN-M-DIAG6}"
ENV_DIR="${RAVEN_ENV_DIR:-/root/autodl-tmp/envs/qwen_vllm}"
MODEL_DIR="${RAVEN_MODEL_SOURCE:-/root/autodl-tmp/models/Qwen3-VL-32B-Instruct-modelscope}"
PREFLIGHT="${DIAG6_PREFLIGHT:-${REPO_DIR}/evidence/diag6/ENRICHED_MEMORY_DIAGNOSTIC6_ZERO_GENERATION_PREFLIGHT.json}"
RUNTIME_DIR="${DIAG6_RUNTIME_DIR:-/root/autodl-tmp/runs/enriched_diag6_server}"
INTENT="${DIAG6_LAUNCH_INTENT:-${RUNTIME_DIR}/ENRICHED_MEMORY_DIAGNOSTIC6_SERVER_LAUNCH_INTENT.json}"
PORT="${RAVEN_SERVER_PORT:-18000}"
mkdir -p "${RUNTIME_DIR}"
export PYTHONPATH="${REPO_DIR}/implementation/src"

REPO_DIR="${REPO_DIR}" ENV_DIR="${ENV_DIR}" MODEL_DIR="${MODEL_DIR}" PREFLIGHT="${PREFLIGHT}" INTENT="${INTENT}" PORT="${PORT}" "${ENV_DIR}/bin/python" - <<'PY'
import importlib.metadata
import json
import os
from pathlib import Path
from raven_m.official_qwen_mobile import enriched_diagnostic_contract as contract

preflight_path = Path(os.environ["PREFLIGHT"]).resolve()
preflight = contract.validate_preflight_report(preflight_path)
model = str(Path(os.environ["MODEL_DIR"]).resolve())
if model != contract.MODEL_REALPATH:
    raise RuntimeError("diagnostic model path drift")
model_manifest = Path(model + ".sha256")
if not model_manifest.is_file() or contract.file_sha256(model_manifest) != contract.MODEL_MANIFEST_SHA256:
    raise RuntimeError("diagnostic model manifest drift")
port = int(os.environ["PORT"])
if port != contract.PORT:
    raise RuntimeError("diagnostic server port drift")
env_dir = Path(os.environ["ENV_DIR"])
command = [
    str(env_dir / "bin/python"), str(env_dir / "bin/vllm"), "serve", model,
    "--served-model-name", contract.MODEL_ID, "--host", "127.0.0.1",
    "--port", str(port), "--tensor-parallel-size", "1", "--dtype", "bfloat16",
    "--gpu-memory-utilization", os.environ.get("RAVEN_GPU_MEMORY_UTILIZATION", "0.92"),
    "--max-model-len", os.environ.get("RAVEN_MAX_MODEL_LEN", "65536"),
    "--max-num-seqs", "1", "--limit-mm-per-prompt", '{"image":1}',
    "--generation-config", "vllm", "--no-enable-log-requests",
]
intent = {
    "schema": contract.INTENT_SCHEMA,
    "status": "launch_pending_live_qualification",
    "protocol_id": contract.PROTOCOL_ID,
    "preflight_sha256": contract.file_sha256(preflight_path),
    "implementation_commit": preflight["implementation_commit"],
    "served_model_id": contract.MODEL_ID,
    "model_realpath": model,
    "model_manifest_sha256": contract.MODEL_MANIFEST_SHA256,
    "process_pid": os.getppid(),
    "process_cmdline": command,
    "port": port,
    "packages": {name: importlib.metadata.version(name) for name in ("vllm", "torch", "transformers")},
}
Path(os.environ["INTENT"]).write_text(json.dumps(intent, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

exec "${ENV_DIR}/bin/python" "${ENV_DIR}/bin/vllm" serve "$(realpath "${MODEL_DIR}")" \
  --served-model-name Qwen/Qwen3-VL-32B-Instruct --host 127.0.0.1 --port "${PORT}" \
  --tensor-parallel-size 1 --dtype bfloat16 \
  --gpu-memory-utilization "${RAVEN_GPU_MEMORY_UTILIZATION:-0.92}" \
  --max-model-len "${RAVEN_MAX_MODEL_LEN:-65536}" --max-num-seqs 1 \
  --limit-mm-per-prompt '{"image":1}' --generation-config vllm --no-enable-log-requests
