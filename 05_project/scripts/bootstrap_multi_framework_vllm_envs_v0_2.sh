#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-/mnt/sdb/ccj/raven_m_research}"
BASE_PYTHON="${MF_BASE_PYTHON:-/home/ccj/miniconda3/envs/ofw/bin/python}"
ENV_ROOT="${ROOT}/05_project/envs/multi_framework_v0_2"
WHEELHOUSE="${ROOT}/05_project/downloads/multi_framework_v0_2/vllm_0_26_0_cp311"
META="${ROOT}/05_project/metadata/multi_framework_s0_v0_2/environments"
VLLM_VERSION="0.26.0"
mkdir -p "${ENV_ROOT}" "${WHEELHOUSE}" "${META}"

[[ -x "${BASE_PYTHON}" ]]
"${BASE_PYTHON}" --version | grep -q '^Python 3\.11\.'

if [[ ! -f "${WHEELHOUSE}/manifest.sha256" ]]; then
  if find "${WHEELHOUSE}" -mindepth 1 -maxdepth 1 -type f | grep -q .; then
    echo "Refusing incomplete pre-existing wheelhouse: ${WHEELHOUSE}" >&2
    exit 1
  fi
  "${BASE_PYTHON}" -m pip download \
    --disable-pip-version-check \
    --dest "${WHEELHOUSE}" \
    "vllm==${VLLM_VERSION}"
  manifest_tmp="${META}/wheelhouse.manifest.sha256.tmp"
  find "${WHEELHOUSE}" -maxdepth 1 -type f ! -name 'manifest.sha256' -printf '%f\n' \
    | sort \
    | while read -r name; do sha256sum "${WHEELHOUSE}/${name}"; done \
    >"${manifest_tmp}"
  mv "${manifest_tmp}" "${WHEELHOUSE}/manifest.sha256"
fi

build_env() {
  local name="$1"
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
      --find-links "${WHEELHOUSE}" \
      "vllm==${VLLM_VERSION}"
    "${target}/bin/python" -m pip check
    "${target}/bin/python" -m pip freeze --all | LC_ALL=C sort >"${evidence}/pip.freeze.txt"
    "${target}/bin/python" -m pip inspect >"${evidence}/pip.inspect.json"
    "${target}/bin/python" --version >"${evidence}/python.txt" 2>&1
    "${target}/bin/python" -m pip show vllm torch transformers >"${evidence}/key_packages.txt"
    cp "${WHEELHOUSE}/manifest.sha256" "${evidence}/wheelhouse.sha256"
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

build_env mf_mobileagent_py311
build_env mf_uivoyager_py311
echo "multi_framework_vllm_env_bootstrap_v0_2=complete"
