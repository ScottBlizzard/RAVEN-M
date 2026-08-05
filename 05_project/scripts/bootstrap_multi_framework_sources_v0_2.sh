#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-/mnt/sdb/ccj/raven_m_research}"
SOURCE_ROOT="${ROOT}/03_code/third_party_v0_2"
EVIDENCE_ROOT="${ROOT}/05_project/metadata/multi_framework_s0_v0_2/sources"
mkdir -p "${SOURCE_ROOT}" "${EVIDENCE_ROOT}"

clone_exact() {
  local key="$1"
  local repo="$2"
  local revision="$3"
  local target="${SOURCE_ROOT}/${key}"

  if [[ ! -d "${target}/.git" ]]; then
    if [[ -e "${target}" ]]; then
      echo "Refusing non-git pre-existing source target: ${target}" >&2
      return 1
    fi
    git clone --filter=blob:none --no-checkout "${repo}" "${target}"
  fi
  git -C "${target}" fetch --no-tags origin "${revision}"
  git -C "${target}" switch --detach "${revision}"
  local actual
  actual="$(git -C "${target}" rev-parse HEAD)"
  [[ "${actual}" == "${revision}" ]]
  git -C "${target}" diff --quiet
  git -C "${target}" diff --cached --quiet

  local license_path=""
  for candidate in LICENSE LICENSE.md LICENSE.txt; do
    if [[ -f "${target}/${candidate}" ]]; then
      license_path="${target}/${candidate}"
      break
    fi
  done
  [[ -n "${license_path}" ]]
  {
    echo "repo=${repo}"
    echo "revision=${actual}"
    echo "license_path=${license_path#${ROOT}/}"
    echo "license_sha256=$(sha256sum "${license_path}" | cut -d' ' -f1)"
    echo "tracked_files=$(git -C "${target}" ls-files | wc -l)"
  } >"${EVIDENCE_ROOT}/${key}.source.txt"
}

clone_exact \
  UI-Voyager \
  https://github.com/ui-voyager/UI-Voyager.git \
  67b65e2be093753ecaa2964f48739339b870813e

clone_exact \
  ScaleCUA \
  https://github.com/OpenGVLab/ScaleCUA.git \
  5d92feea9f1e14b8303ce37da45b286fb1f4d3aa

echo "multi_framework_source_bootstrap_v0_2=complete"
