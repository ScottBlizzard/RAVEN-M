#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-/mnt/sdb/ccj/raven_m_research}"
PYTHON="${MF_COMMON_PYTHON:-${ROOT}/05_project/.venv-model-server/bin/python}"
EVIDENCE="${ROOT}/05_project/metadata/multi_framework_s0_v0_2/environments/common_qwen"
mkdir -p "${EVIDENCE}"

[[ -x "${PYTHON}" ]]
"${PYTHON}" - <<'PY' >"${EVIDENCE}/runtime_versions.txt"
import platform
import sys
import torch
import transformers

assert sys.version_info[:3] == (3, 11, 15), sys.version
assert torch.__version__ == "2.8.0+cu128", torch.__version__
assert torch.version.cuda == "12.8", torch.version.cuda
assert transformers.__version__ == "5.10.2", transformers.__version__
print(f"python={platform.python_version()}")
print(f"torch={torch.__version__}")
print(f"torch_cuda={torch.version.cuda}")
print(f"transformers={transformers.__version__}")
PY

"${PYTHON}" -m pip freeze --all | LC_ALL=C sort >"${EVIDENCE}/pip.freeze.txt"
"${PYTHON}" -m pip inspect >"${EVIDENCE}/pip.inspect.json"
nvidia-smi >"${EVIDENCE}/nvidia-smi.txt"
{
  sha256sum "${EVIDENCE}/runtime_versions.txt"
  sha256sum "${EVIDENCE}/pip.freeze.txt"
  sha256sum "${EVIDENCE}/pip.inspect.json"
  sha256sum "${EVIDENCE}/nvidia-smi.txt"
} >"${EVIDENCE}/environment_components.sha256"
sha256sum "${EVIDENCE}/environment_components.sha256" \
  >"${EVIDENCE}/environment_manifest.sha256"
touch "${EVIDENCE}/complete"
echo "common_qwen_runtime_freeze_v0_2=complete"
