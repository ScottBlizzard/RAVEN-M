#!/usr/bin/env bash
set -euo pipefail

ENV_DIR="${RAVEN_ENV_DIR:-/root/autodl-tmp/envs/qwen_vllm}"
MODEL_DIR="${RAVEN_MODEL_SOURCE:-/root/autodl-tmp/models/Qwen3-VL-32B-Instruct-modelscope}"
RUN_DIR="${RAVEN_RUN_DIR:-/root/autodl-tmp/runs/official_qwen_mobile_server}"

mkdir -p "${RUN_DIR}"
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}"
# FlashInfer 0.6.6 mis-detects Blackwell SM 12.0 during sampler JIT even
# though this environment uses CUDA 13.0.  vLLM's own documented switch keeps
# attention unchanged and falls back only the top-k/top-p sampler to PyTorch.
export VLLM_USE_FLASHINFER_SAMPLER="${VLLM_USE_FLASHINFER_SAMPLER:-0}"
exec "${ENV_DIR}/bin/vllm" serve "${MODEL_DIR}" \
  --served-model-name Qwen/Qwen3-VL-32B-Instruct \
  --host 127.0.0.1 \
  --port "${RAVEN_SERVER_PORT:-18000}" \
  --tensor-parallel-size 1 \
  --dtype bfloat16 \
  --gpu-memory-utilization "${RAVEN_GPU_MEMORY_UTILIZATION:-0.92}" \
  --max-model-len "${RAVEN_MAX_MODEL_LEN:-65536}" \
  --max-num-seqs 1 \
  --limit-mm-per-prompt '{"image":1}' \
  --generation-config vllm \
  --no-enable-log-requests
