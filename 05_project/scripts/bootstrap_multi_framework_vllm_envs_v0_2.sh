#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-/mnt/sdb/ccj/raven_m_research}"
BASE_PYTHON="${MF_BASE_PYTHON:-/home/ccj/miniconda3/envs/ofw/bin/python}"
ENV_ROOT="${ROOT}/05_project/envs/multi_framework_v0_2"
SOURCE_ROOT="${ROOT}/03_code/third_party_v0_2"
DOWNLOAD_ROOT="${ROOT}/05_project/downloads/multi_framework_v0_2"
META="${ROOT}/05_project/metadata/multi_framework_s0_v0_2/environments"
VLLM_VERSION="0.12.0"
TORCH_INDEX="https://download.pytorch.org/whl/cu128"
INCLUDE_SCALECUA="${MF_INCLUDE_SCALECUA:-1}"
mkdir -p "${ENV_ROOT}" "${DOWNLOAD_ROOT}" "${META}"

[[ -x "${BASE_PYTHON}" ]]
"${BASE_PYTHON}" --version | grep -q '^Python 3\.11\.'

cat >"${META}/dependency_resolution_rule.txt" <<EOF
status=FROZEN_BEFORE_FORMAL_RESOLUTION
rule=highest_official_stable_vllm_with_official_cuda_12_8_binary_and_qwen3_vl_support_as_of_2026_08_05
vllm_version=${VLLM_VERSION}
torch_index=${TORCH_INDEX}
model_architecture=Qwen3VLForConditionalGeneration
official_cuda_12_8_install_doc=https://docs.vllm.ai/en/v0.12.0/getting_started/installation/gpu/
official_qwen3_vl_support_doc=https://docs.vllm.ai/en/v0.12.0/api/vllm/model_executor/models/qwen3_vl/
aborted_preflight_wheelhouse=${DOWNLOAD_ROOT}/vllm_0_26_0_cp311
aborted_preflight_reason=vllm_0_26_0_default_binary_targets_cuda_13_but_server_driver_supports_cuda_12_8
aborted_preflight_environment_created=false
aborted_preflight_model_load_attempted=false
EOF

prepare_wheelhouse() {
  local key="$1"
  local requirements="$2"
  local wheelhouse="${DOWNLOAD_ROOT}/${key}_vllm_${VLLM_VERSION//./_}_cu128_cp311"
  local evidence="${META}/${key}"
  mkdir -p "${evidence}"
  [[ -f "${requirements}" ]]
  cp "${requirements}" "${evidence}/official_requirements.txt"
  sha256sum "${evidence}/official_requirements.txt" >"${evidence}/official_requirements.sha256"
  if [[ ! -f "${wheelhouse}/manifest.sha256" ]]; then
    if [[ -e "${wheelhouse}" ]] && find "${wheelhouse}" -mindepth 1 -maxdepth 1 -type f | grep -q .; then
      echo "Refusing incomplete pre-existing wheelhouse: ${wheelhouse}" >&2
      return 1
    fi
    mkdir -p "${wheelhouse}"
    "${BASE_PYTHON}" -m pip download \
      --disable-pip-version-check \
      --extra-index-url "${TORCH_INDEX}" \
      --dest "${wheelhouse}" \
      -r "${requirements}" \
      "vllm==${VLLM_VERSION}" \
      >"${evidence}/dependency_resolution.log" 2>&1
    local manifest_tmp="${evidence}/wheelhouse.manifest.sha256.tmp"
    find "${wheelhouse}" -maxdepth 1 -type f ! -name 'manifest.sha256' -printf '%f\n' \
      | sort \
      | while read -r name; do sha256sum "${wheelhouse}/${name}"; done \
      >"${manifest_tmp}"
    mv "${manifest_tmp}" "${wheelhouse}/manifest.sha256"
  fi
  printf '%s\n' "${wheelhouse}"
}

build_env() {
  local name="$1"
  local requirements="$2"
  local wheelhouse="$3"
  local target="${ENV_ROOT}/${name}"
  local evidence="${META}/${name}"
  mkdir -p "${evidence}"
  if [[ -e "${target}" && ! -f "${evidence}/complete" ]]; then
    echo "Refusing incomplete pre-existing environment: ${target}" >&2
    return 1
  fi
  if [[ ! -f "${evidence}/complete" ]]; then
    "${BASE_PYTHON}" -m venv --copies "${target}"
    "${target}/bin/python" -m pip install \
      --disable-pip-version-check \
      --no-index \
      --find-links "${wheelhouse}" \
      -r "${requirements}" \
      "vllm==${VLLM_VERSION}"
    "${target}/bin/python" -m pip check
    "${target}/bin/python" -m pip freeze --all | LC_ALL=C sort >"${evidence}/pip.freeze.txt"
    "${target}/bin/python" -m pip inspect >"${evidence}/pip.inspect.json"
    "${target}/bin/python" --version >"${evidence}/python.txt" 2>&1
    "${target}/bin/python" -m pip show vllm torch transformers >"${evidence}/key_packages.txt"
    cp "${wheelhouse}/manifest.sha256" "${evidence}/wheelhouse.sha256"
    {
      sha256sum "${evidence}/pip.freeze.txt"
      sha256sum "${evidence}/pip.inspect.json"
      sha256sum "${evidence}/python.txt"
      sha256sum "${evidence}/key_packages.txt"
      sha256sum "${evidence}/wheelhouse.sha256"
    } >"${evidence}/environment.sha256"
    touch "${evidence}/complete"
  fi
}

MOBILEAGENT_REQUIREMENTS="${SOURCE_ROOT}/MobileAgent/Mobile-Agent-v3.5/android_world_v3.5/requirements.txt"
UIVOYAGER_REQUIREMENTS="${SOURCE_ROOT}/UI-Voyager/androidworld/requirements.txt"
SCALECUA_REQUIREMENTS="${SOURCE_ROOT}/ScaleCUA/evaluation/AndroidWorld/requirements.txt"
MOBILEAGENT_WHEELHOUSE="$(prepare_wheelhouse mobileagent "${MOBILEAGENT_REQUIREMENTS}")"
UIVOYAGER_WHEELHOUSE="$(prepare_wheelhouse uivoyager "${UIVOYAGER_REQUIREMENTS}")"

build_env mf_mobileagent_py311 "${MOBILEAGENT_REQUIREMENTS}" "${MOBILEAGENT_WHEELHOUSE}"
build_env mf_uivoyager_py311 "${UIVOYAGER_REQUIREMENTS}" "${UIVOYAGER_WHEELHOUSE}"
if [[ "${INCLUDE_SCALECUA}" == "1" ]]; then
  SCALECUA_WHEELHOUSE="$(prepare_wheelhouse scalecua "${SCALECUA_REQUIREMENTS}")"
  build_env mf_scalecua_py311 "${SCALECUA_REQUIREMENTS}" "${SCALECUA_WHEELHOUSE}"
elif [[ "${INCLUDE_SCALECUA}" != "0" ]]; then
  echo "MF_INCLUDE_SCALECUA must be 0 or 1" >&2
  exit 1
fi
echo "multi_framework_vllm_env_bootstrap_v0_2=complete"
