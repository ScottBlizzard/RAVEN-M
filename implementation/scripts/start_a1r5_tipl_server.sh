#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_DIR="${RAVEN_ENV_DIR:-/root/autodl-tmp/envs/qwen_vllm}"
MODEL_DIR="${RAVEN_MODEL_SOURCE:-/root/autodl-tmp/models/Qwen3-VL-32B-Instruct-modelscope}"
export PYTHONPATH="$ROOT/implementation/src"
"$ENV_DIR/bin/python" "$ROOT/implementation/scripts/preflight_a1r5_tipl.py" --validate-existing
"$ENV_DIR/bin/python" - "$MODEL_DIR" <<'PY'
from hashlib import sha256
from pathlib import Path
import sys
manifest=Path(sys.argv[1]+".sha256")
assert manifest.is_file()
assert sha256(manifest.read_bytes()).hexdigest()=="18e0909c7d993853d6d0f62443461a74009754f90db026a1723cab80121c7872"
print("A1-R5 preflight and model manifest accepted; starting zero-request server")
PY
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}"
export VLLM_USE_FLASHINFER_SAMPLER="${VLLM_USE_FLASHINFER_SAMPLER:-0}"
exec "$ENV_DIR/bin/python" "$ENV_DIR/bin/vllm" serve "$(realpath "$MODEL_DIR")" \
  --served-model-name Qwen/Qwen3-VL-32B-Instruct --host 127.0.0.1 --port 18000 \
  --tensor-parallel-size 1 --dtype bfloat16 --gpu-memory-utilization 0.92 \
  --max-model-len 65536 --max-num-seqs 1 --limit-mm-per-prompt '{"image":1}' \
  --generation-config vllm --no-enable-log-requests
