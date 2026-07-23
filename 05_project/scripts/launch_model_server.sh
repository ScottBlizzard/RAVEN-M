#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_ROOT="${RAVEN_SERVER_VENV:-${PROJECT_ROOT}/.venv-model-server}"

if [[ ! -x "${VENV_ROOT}/bin/uvicorn" ]]; then
  echo "Run scripts/bootstrap_model_host.sh first." >&2
  exit 1
fi

export PYTHONPATH="${PROJECT_ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"
export RAVEN_MODEL_ID="${RAVEN_MODEL_ID:-Qwen/Qwen3-VL-32B-Instruct}"
export RAVEN_MODEL_REVISION="${RAVEN_MODEL_REVISION:-0cfaf48183f594c314753d30a4c4974bc75f3ccb}"
export RAVEN_BACKEND_ID="${RAVEN_BACKEND_ID:-qwen3_vl_32b_transformers_bf16_4x4090_v1}"
export RAVEN_MODEL_MODE="${RAVEN_MODEL_MODE:-mock}"
export RAVEN_MODEL_CACHE="${RAVEN_MODEL_CACHE:-${PROJECT_ROOT}/model_cache/huggingface}"
export HF_HOME="${HF_HOME:-${RAVEN_MODEL_CACHE}}"
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0,1,2,3}"
export RAVEN_LOCAL_FILES_ONLY="${RAVEN_LOCAL_FILES_ONLY:-1}"
export RAVEN_GPU_MAX_MEMORY="${RAVEN_GPU_MAX_MEMORY:-0:22GiB,1:22GiB,2:22GiB,3:22GiB}"
export RAVEN_SERVER_LOG="${RAVEN_SERVER_LOG:-${PROJECT_ROOT}/outputs/model_server.jsonl}"

exec "${VENV_ROOT}/bin/uvicorn" \
  raven_m.models.server:app \
  --host 127.0.0.1 \
  --port "${RAVEN_SERVER_PORT:-8000}" \
  --workers 1 \
  --log-level info
