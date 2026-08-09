#!/usr/bin/env bash
set -euo pipefail

ENV_DIR="${RAVEN_ENV_DIR:-/root/autodl-tmp/envs/qwen_vllm}"
MODEL_DIR="${RAVEN_MODEL_SOURCE:-/root/autodl-tmp/models/Qwen3-VL-32B-Instruct-modelscope}"
RUN_DIR="${RAVEN_RUN_DIR:-/root/autodl-tmp/runs/mobileuse_pf01_server}"
PORT="${RAVEN_SERVER_PORT:-18000}"

test -x "${ENV_DIR}/bin/vllm" || { echo "Missing vLLM executable: ${ENV_DIR}/bin/vllm" >&2; exit 2; }
test -d "${MODEL_DIR}" || { echo "Missing model directory: ${MODEL_DIR}" >&2; exit 2; }
command -v nvidia-smi >/dev/null 2>&1 || { echo "GPU mode is not enabled" >&2; exit 3; }
nvidia-smi -L | grep -q '^GPU ' || { echo "No visible GPU; refusing to start vLLM" >&2; exit 3; }

mkdir -p "${RUN_DIR}"
cat > "${RUN_DIR}/launch_manifest.txt" <<EOF
arm=PF01_MOBILEUSE_HR_QWEN3VL32B_AW_HARD_S20260806_V1
environment=${ENV_DIR}
model_source=${MODEL_DIR}
served_model=Qwen/Qwen3-VL-32B-Instruct
port=${PORT}
tensor_parallel_size=1
dtype=bfloat16
gpu_memory_utilization=0.92
max_model_len=65536
max_num_seqs=1
limit_mm_per_prompt.image=3
generation_config=vllm
EOF

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}"
export VLLM_USE_FLASHINFER_SAMPLER="${VLLM_USE_FLASHINFER_SAMPLER:-0}"

exec "${ENV_DIR}/bin/vllm" serve "${MODEL_DIR}" \
  --served-model-name Qwen/Qwen3-VL-32B-Instruct \
  --host 127.0.0.1 \
  --port "${PORT}" \
  --tensor-parallel-size 1 \
  --dtype bfloat16 \
  --gpu-memory-utilization 0.92 \
  --max-model-len 65536 \
  --max-num-seqs 1 \
  --limit-mm-per-prompt '{"image":3}' \
  --generation-config vllm \
  --no-enable-log-requests
