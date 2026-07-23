#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOWNLOAD_PID_FILE="${PROJECT_ROOT}/outputs/model_download.pid"
SERVER_PID_FILE="${PROJECT_ROOT}/outputs/model_server.pid"
MODEL_CACHE="${PROJECT_ROOT}/model_cache/huggingface"
MANIFEST="${PROJECT_ROOT}/metadata/model_snapshot_manifest.json"
FIXTURE="${PROJECT_ROOT}/fixtures/androidworld_smoke.png"

if [[ ! -f "${DOWNLOAD_PID_FILE}" ]]; then
  echo "Missing download PID file: ${DOWNLOAD_PID_FILE}" >&2
  exit 1
fi

download_pid="$(cat "${DOWNLOAD_PID_FILE}")"
while kill -0 "${download_pid}" 2>/dev/null; do
  echo "$(date --iso-8601=seconds) waiting_for_model_download pid=${download_pid}"
  du -sh "${MODEL_CACHE}" || true
  sleep 60
done

if [[ ! -f "${MANIFEST}" ]]; then
  echo "Model download ended without a manifest." >&2
  tail -n 100 "${PROJECT_ROOT}/outputs/model_download.log" || true
  exit 1
fi

if [[ -f "${SERVER_PID_FILE}" ]]; then
  server_pid="$(cat "${SERVER_PID_FILE}")"
  if kill -0 "${server_pid}" 2>/dev/null; then
    kill -TERM "${server_pid}"
    for _ in $(seq 1 30); do
      kill -0 "${server_pid}" 2>/dev/null || break
      sleep 1
    done
    if kill -0 "${server_pid}" 2>/dev/null; then
      echo "Existing model server did not terminate cleanly." >&2
      exit 1
    fi
  fi
fi

cd "${PROJECT_ROOT}"
nohup env \
  CUDA_VISIBLE_DEVICES=0,1,2,3 \
  RAVEN_MODEL_MODE=transformers \
  RAVEN_MODEL_CACHE="${MODEL_CACHE}" \
  RAVEN_LOCAL_FILES_ONLY=1 \
  RAVEN_SERVER_PORT=8000 \
  bash scripts/launch_model_server.sh \
  > outputs/model_server_transformers_console.log 2>&1 &
echo "$!" > "${SERVER_PID_FILE}"

for _ in $(seq 1 60); do
  if curl -fsS http://127.0.0.1:8000/health \
    > metadata/model_server_health_before_load.json; then
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
  > metadata/model_load_response.json

"${PROJECT_ROOT}/.venv-model-server/bin/python" \
  scripts/smoke_model_service.py \
  --url http://127.0.0.1:8000 \
  --image "${FIXTURE}" \
  --prompt 'Task: Create a new contact for Mariam Ferreira with phone number +13473004854. The screenshot is 1080 x 2400 pixels. Return exactly one JSON object: {"reason":"short visual justification","action":{"action_type":"click|input_text|keyboard_enter|navigate_home|navigate_back|scroll|open_app|wait|status","x":0,"y":0,"text":"","direction":"","app_name":"","goal_status":""}}. Emit one valid next AndroidWorld action only and omit unused fields.' \
  --timeout 600 \
  --output metadata/server_real_model_smoke.json

CUDA_VISIBLE_DEVICES=0,1,2,3 \
RAVEN_MODEL_MODE=transformers \
"${PROJECT_ROOT}/.venv-model-server/bin/python" \
  scripts/audit_model_host.py \
  --project-root /mnt/sdb/ccj/raven_m_research \
  --output metadata/server_audit_4090_post_model.json

echo "$(date --iso-8601=seconds) post_download_model_smoke=complete"
