#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE_PYTHON="${RAVEN_BASE_PYTHON:-/home/ccj/miniconda3/envs/ofw/bin/python}"
VENV_ROOT="${RAVEN_SERVER_VENV:-${PROJECT_ROOT}/.venv-model-server}"

if [[ ! -x "${BASE_PYTHON}" ]]; then
  echo "Base Python does not exist: ${BASE_PYTHON}" >&2
  exit 1
fi

if [[ ! -x "${VENV_ROOT}/bin/python" ]]; then
  "${BASE_PYTHON}" -m venv --system-site-packages "${VENV_ROOT}"
fi

"${VENV_ROOT}/bin/python" -m pip install \
  --disable-pip-version-check \
  --no-cache-dir \
  -r "${PROJECT_ROOT}/requirements/model_server_overlay.txt"

"${VENV_ROOT}/bin/python" - <<'PY'
import fastapi
import torch
import transformers
import uvicorn

print(f"torch={torch.__version__}")
print(f"transformers={transformers.__version__}")
print(f"fastapi={fastapi.__version__}")
print(f"uvicorn={uvicorn.__version__}")
print(f"cuda_available={torch.cuda.is_available()}")
print(f"cuda_devices={torch.cuda.device_count()}")
PY
