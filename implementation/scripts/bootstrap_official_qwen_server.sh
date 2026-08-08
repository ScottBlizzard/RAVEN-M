#!/usr/bin/env bash
set -euo pipefail

ENV_DIR="${RAVEN_ENV_DIR:-/root/autodl-tmp/envs/qwen_vllm}"
PROJECT_DIR="${RAVEN_PROJECT_DIR:-/root/autodl-tmp/RAVEN-M/05_project}"
PIP_CACHE_DIR="${RAVEN_PIP_CACHE_DIR:-/root/autodl-tmp/pip-cache}"
export PIP_CACHE_DIR

"${ENV_DIR}/bin/python" -m pip install --upgrade pip
"${ENV_DIR}/bin/python" -m pip install \
  accelerate==1.13.0 \
  pytest \
  qwen-vl-utils==0.0.14 \
  requests \
  vllm==0.26.0
"${ENV_DIR}/bin/python" -m pip install -e "${PROJECT_DIR}"

"${ENV_DIR}/bin/python" - <<'PY'
import torch
import vllm
import qwen_vl_utils
from raven_m.official_qwen_mobile.protocol import OFFICIAL_QWEN_COMMIT

print({
    "torch": torch.__version__,
    "vllm": vllm.__version__,
    "qwen_mobile_commit": OFFICIAL_QWEN_COMMIT,
    "cuda_available": torch.cuda.is_available(),
})
PY
