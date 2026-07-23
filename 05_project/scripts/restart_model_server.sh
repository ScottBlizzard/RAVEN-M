#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="${PROJECT_ROOT}/outputs/model_server.pid"
CONSOLE_LOG="${PROJECT_ROOT}/outputs/model_server_transformers_console.log"

if [[ -f "${PID_FILE}" ]]; then
  old_pid="$(cat "${PID_FILE}")"
  if kill -0 "${old_pid}" 2>/dev/null; then
    kill -TERM "${old_pid}"
    for _ in $(seq 1 60); do
      kill -0 "${old_pid}" 2>/dev/null || break
      sleep 1
    done
    if kill -0 "${old_pid}" 2>/dev/null; then
      echo "Model server ${old_pid} did not terminate cleanly." >&2
      exit 1
    fi
  fi
fi

cd "${PROJECT_ROOT}"
nohup env \
  CUDA_VISIBLE_DEVICES=0,1,2,3 \
  RAVEN_MODEL_MODE=transformers \
  RAVEN_MODEL_CACHE="${PROJECT_ROOT}/model_cache/huggingface" \
  RAVEN_LOCAL_FILES_ONLY=1 \
  RAVEN_SERVER_PORT=8000 \
  PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
  bash scripts/launch_model_server.sh \
  > "${CONSOLE_LOG}" 2>&1 &
echo "$!" > "${PID_FILE}"

for _ in $(seq 1 60); do
  if curl -fsS http://127.0.0.1:8000/health >/dev/null; then
    break
  fi
  sleep 1
done
curl -fsS http://127.0.0.1:8000/health >/dev/null
curl \
  --fail \
  --show-error \
  --max-time 3600 \
  --request POST \
  http://127.0.0.1:8000/load \
  > "${PROJECT_ROOT}/metadata/model_load_response_after_restart.json"
curl -fsS http://127.0.0.1:8000/health
