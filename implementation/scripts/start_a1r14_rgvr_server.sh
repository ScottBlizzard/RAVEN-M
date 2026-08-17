#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_DIR="${RAVEN_ENV_DIR:-/root/autodl-tmp/envs/qwen_vllm}"
MODEL_DIR="${RAVEN_MODEL_SOURCE:-/root/autodl-tmp/models/Qwen3-VL-32B-Instruct-modelscope}"
export PYTHONPATH="$ROOT/implementation/src"
"$ENV_DIR/bin/python" "$ROOT/implementation/scripts/preflight_a1r14_rgvr.py" --validate-existing
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
exec "$ENV_DIR/bin/python" "$ENV_DIR/bin/vllm" serve "$(realpath "$MODEL_DIR")" \
  --served-model-name Qwen/Qwen3-VL-32B-Instruct --host 127.0.0.1 --port 18000 \
  --tensor-parallel-size 1 --dtype bfloat16 --gpu-memory-utilization 0.92 \
  --max-model-len 65536 --max-num-seqs 1 --limit-mm-per-prompt '{"image":1}' \
  --generation-config vllm --no-enable-log-requests
