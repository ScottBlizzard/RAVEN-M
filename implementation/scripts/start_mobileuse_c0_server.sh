#!/usr/bin/env bash
set -euo pipefail

ENV_DIR="${RAVEN_ENV_DIR:-/root/autodl-tmp/envs/qwen_vllm}"
MODEL_DIR="${RAVEN_MODEL_SOURCE:-/root/autodl-tmp/models/Qwen3-VL-32B-Instruct-modelscope}"
RUN_DIR="${RAVEN_RUN_DIR:-/root/autodl-tmp/runs/mobileuse_c0_server}"
PORT="${RAVEN_SERVER_PORT:-18000}"
VERIFY_STAMP="${RAVEN_MODEL_VERIFY_STAMP:-/root/autodl-tmp/models/C0_QWEN32B_VERIFIED.sha256}"
EXPECTED_MODEL_MANIFEST_SHA="d18f8e731880a2263b68ff2d565db711e6cf1585755f9ae78fcafcd5d4a77227"
EXPECTED_VLLM="0.26.0"
EXPECTED_TORCH="2.11.0"
EXPECTED_TRANSFORMERS="5.14.1"

test -x "${ENV_DIR}/bin/vllm" || { echo "Missing vLLM executable" >&2; exit 2; }
test -d "${MODEL_DIR}" || { echo "Missing model directory" >&2; exit 2; }
test -f "${VERIFY_STAMP}" || { echo "No no-GPU model verification stamp" >&2; exit 2; }
test "$(head -n 1 "${VERIFY_STAMP}")" = "${EXPECTED_MODEL_MANIFEST_SHA}" || {
  echo "Model verification stamp drift" >&2; exit 2;
}
if find "${MODEL_DIR}" -type f -newer "${VERIFY_STAMP}" -print -quit | grep -q .; then
  echo "Model files changed after no-GPU checksum verification" >&2
  exit 2
fi

readarray -t VERSIONS < <("${ENV_DIR}/bin/python" - <<'PY'
import importlib.metadata as m
for name in ('vllm', 'torch', 'transformers'):
    print(m.version(name))
PY
)
test "${VERSIONS[0]}" = "${EXPECTED_VLLM}"
test "${VERSIONS[1]}" = "${EXPECTED_TORCH}"
test "${VERSIONS[2]}" = "${EXPECTED_TRANSFORMERS}"
command -v nvidia-smi >/dev/null 2>&1
nvidia-smi -L | grep -q '^GPU '
GPU_NAME="$(nvidia-smi --query-gpu=name --format=csv,noheader | head -n 1 | xargs)"
DRIVER_VERSION="$(nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -n 1 | xargs)"
CUDA_VERSION="$(nvidia-smi | sed -n 's/.*CUDA Version: \([0-9.]*\).*/\1/p' | head -n 1)"

mkdir -p "${RUN_DIR}"
cat > "${RUN_DIR}/launch_manifest.json" <<EOF
{
  "arm": "C0_NATIVE_MOBILEUSE_QWEN3VL32B_AW_HARD_S20260806_V1",
  "environment": "${ENV_DIR}",
  "model_source": "${MODEL_DIR}",
  "model_manifest_sha256": "${EXPECTED_MODEL_MANIFEST_SHA}",
  "served_model": "Qwen/Qwen3-VL-32B-Instruct",
  "port": ${PORT},
  "tensor_parallel_size": 1,
  "dtype": "bfloat16",
  "gpu_memory_utilization": 0.92,
  "max_model_len": 65536,
  "max_num_seqs": 1,
  "limit_images_per_prompt": 3,
  "vllm": "${VERSIONS[0]}",
  "torch": "${VERSIONS[1]}",
  "transformers": "${VERSIONS[2]}"
  ,"gpu_name": "${GPU_NAME}"
  ,"driver_version": "${DRIVER_VERSION}"
  ,"cuda_version": "${CUDA_VERSION}"
}
EOF

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}"
export VLLM_USE_FLASHINFER_SAMPLER="${VLLM_USE_FLASHINFER_SAMPLER:-0}"

exec "${ENV_DIR}/bin/vllm" serve "${MODEL_DIR}" \
  --served-model-name Qwen/Qwen3-VL-32B-Instruct \
  --host 127.0.0.1 --port "${PORT}" --tensor-parallel-size 1 \
  --dtype bfloat16 --gpu-memory-utilization 0.92 --max-model-len 65536 \
  --max-num-seqs 1 --limit-mm-per-prompt '{"image":3}' \
  --generation-config vllm --no-enable-log-requests
