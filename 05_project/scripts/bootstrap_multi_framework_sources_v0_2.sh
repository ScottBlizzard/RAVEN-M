#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-/mnt/sdb/ccj/raven_m_research}"
SOURCE_ROOT="${ROOT}/03_code/third_party_v0_2"
ARCHIVE_ROOT="${SOURCE_ROOT}/archives"
EVIDENCE_ROOT="${ROOT}/05_project/metadata/multi_framework_s0_v0_2/sources"
mkdir -p "${SOURCE_ROOT}" "${ARCHIVE_ROOT}" "${EVIDENCE_ROOT}"

fetch_exact_archive() {
  local key="$1"
  local github_repo="$2"
  local revision="$3"
  local target="${SOURCE_ROOT}/${key}"
  local archive="${ARCHIVE_ROOT}/${key}-${revision}.tar.gz"
  local complete="${EVIDENCE_ROOT}/${key}.source.txt"
  local url="https://codeload.github.com/${github_repo}/tar.gz/${revision}"

  if [[ -f "${complete}" ]]; then
    [[ -d "${target}" ]]
    grep -q "^revision=${revision}$" "${complete}"
    grep -q "^archive_sha256=$(sha256sum "${archive}" | cut -d' ' -f1)$" "${complete}"
    return 0
  fi
  if [[ -e "${target}" ]]; then
    echo "Refusing pre-existing incomplete source target: ${target}" >&2
    return 1
  fi

  curl --fail --location --retry 3 --retry-all-errors --continue-at - \
    --output "${archive}" "${url}"

  local temp
  temp="$(mktemp -d "${SOURCE_ROOT}/.${key}.extract.XXXXXX")"
  tar -xzf "${archive}" --strip-components=1 -C "${temp}"

  local license_path=""
  for candidate in LICENSE LICENSE.md LICENSE.txt; do
    if [[ -f "${temp}/${candidate}" ]]; then
      license_path="${temp}/${candidate}"
      break
    fi
  done
  [[ -n "${license_path}" ]]

  mv "${temp}" "${target}"
  license_path="${target}/${license_path#${temp}/}"
  {
    echo "repo=https://github.com/${github_repo}.git"
    echo "revision=${revision}"
    echo "transport_url=${url}"
    echo "archive_path=${archive#${ROOT}/}"
    echo "archive_sha256=$(sha256sum "${archive}" | cut -d' ' -f1)"
    echo "license_path=${license_path#${ROOT}/}"
    echo "license_sha256=$(sha256sum "${license_path}" | cut -d' ' -f1)"
    echo "regular_files=$(find "${target}" -type f | wc -l)"
  } >"${complete}.tmp"
  mv "${complete}.tmp" "${complete}"
}

fetch_exact_archive \
  MobileAgent \
  X-PLUG/MobileAgent \
  11cea575561fb7800b5fb6b6cafa56f7a91de11f

fetch_exact_archive \
  UI-Voyager \
  ui-voyager/UI-Voyager \
  67b65e2be093753ecaa2964f48739339b870813e

fetch_exact_archive \
  ScaleCUA \
  OpenGVLab/ScaleCUA \
  5d92feea9f1e14b8303ce37da45b286fb1f4d3aa

echo "multi_framework_source_bootstrap_v0_2=complete"
