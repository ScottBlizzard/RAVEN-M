#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-/mnt/sdb/ccj/raven_m_research}"
PROJECT="${ROOT}/05_project"
ENV_ROOT="${PROJECT}/envs/multi_framework_v0_2"
MODEL_META="${PROJECT}/metadata/multi_framework_s0_v0_2"
OUT="${PROJECT}/outputs/multi_framework_s0_v0_2/model_load_checks"
INCLUDE_SCALECUA="${MF_INCLUDE_SCALECUA:-1}"
ARM_FILTER=",${MF_S0_ARMS:-gui_owl,ui_voyager,scalecua},"
mkdir -p "${OUT}"

selected() {
  [[ "${ARM_FILTER}" == *",$1,"* ]]
}

snapshot_path() {
  local manifest="$1"
  [[ -f "${manifest}" ]]
  python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["snapshot_path"])' "${manifest}"
}

launch_and_check() {
  local key="$1"
  local env_name="$2"
  local manifest="$3"
  local served_name="$4"
  local devices="$5"
  local tp="$6"
  local port="$7"
  shift 7
  local env_path="${ENV_ROOT}/${env_name}"
  local snapshot
  snapshot="$(snapshot_path "${manifest}")"
  [[ -x "${env_path}/bin/vllm" ]]
  [[ -d "${snapshot}" ]]
  if [[ -f "${OUT}/${key}.pid" ]] && kill -0 "$(cat "${OUT}/${key}.pid")" 2>/dev/null; then
    echo "Refusing to replace running ${key} server" >&2
    return 1
  fi
  nohup env CUDA_VISIBLE_DEVICES="${devices}" \
    "${env_path}/bin/vllm" serve "${snapshot}" \
      --served-model-name "${served_name}" \
      --host 127.0.0.1 \
      --port "${port}" \
      --tensor-parallel-size "${tp}" \
      --dtype bfloat16 \
      "$@" \
      >"${OUT}/${key}.log" 2>&1 &
  echo "$!" >"${OUT}/${key}.pid"

  for _ in $(seq 1 180); do
    if ! kill -0 "$(cat "${OUT}/${key}.pid")" 2>/dev/null; then
      tail -n 100 "${OUT}/${key}.log" >&2
      return 1
    fi
    if curl --fail --silent --show-error \
      "http://127.0.0.1:${port}/v1/models" \
      >"${OUT}/${key}.models.json"; then
      break
    fi
    sleep 10
  done
  [[ -s "${OUT}/${key}.models.json" ]]
  {
    echo "key=${key}"
    echo "env_name=${env_name}"
    echo "checkpoint_manifest=${manifest}"
    echo "checkpoint_snapshot=${snapshot}"
    echo "served_model_name=${served_name}"
    echo "cuda_visible_devices=${devices}"
    echo "tensor_parallel_size=${tp}"
    echo "port=${port}"
    echo "generation_calls=0"
    echo "endpoint_checked=/v1/models"
    echo "models_response_sha256=$(sha256sum "${OUT}/${key}.models.json" | cut -d' ' -f1)"
  } >"${OUT}/${key}.qualification.txt"
}

if selected gui_owl; then
  launch_and_check \
    gui_owl \
    mf_mobileagent_py311 \
    "${MODEL_META}/gui_owl.checkpoint_manifest.json" \
    GUI-Owl-1.5-8B-Think \
    4,5 \
    2 \
    8101 \
    --max-model-len 32768
fi

if selected ui_voyager; then
  launch_and_check \
    ui_voyager \
    mf_uivoyager_py311 \
    "${MODEL_META}/ui_voyager.checkpoint_manifest.json" \
    UI-Voyager \
    6 \
    1 \
    8102 \
    --max-model-len 32768
fi

if [[ "${INCLUDE_SCALECUA}" != "0" && "${INCLUDE_SCALECUA}" != "1" ]]; then
  echo "MF_INCLUDE_SCALECUA must be 0 or 1" >&2
  exit 1
fi
if [[ "${INCLUDE_SCALECUA}" == "1" ]] && selected scalecua; then
  launch_and_check \
    scalecua \
    mf_scalecua_py311 \
    "${MODEL_META}/scalecua.checkpoint_manifest.json" \
    ScaleCUA-32B \
    0,1,2,3 \
    4 \
    8103 \
    --max-model-len 32768
fi

echo "multi_framework_s0_model_load_checks_v0_2=complete"
