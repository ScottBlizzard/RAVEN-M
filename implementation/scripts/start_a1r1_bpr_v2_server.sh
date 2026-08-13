#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MODE="${BPR_V2_MODE:?set BPR_V2_MODE to primary or empty_read}"
[[ "$MODE" == "primary" || "$MODE" == "empty_read" ]] || { echo "invalid BPR_V2_MODE" >&2; exit 2; }
PREFLIGHT="$ROOT/evidence/a1r1_v2/A1R1_BPR_V2_ZERO_GENERATION_PREFLIGHT.json"
python "$ROOT/implementation/scripts/preflight_a1r1_bpr_v2.py" --validate-existing
python - "$PREFLIGHT" "$MODE" <<'PY'
import json, sys
p=json.load(open(sys.argv[1], encoding="utf-8"))
assert p["status"] == "PASS" and p["errors"] == [] and p["live_generation_authorized"] is True
print(f"BPR-v2 {sys.argv[2]} preflight accepted; starting zero-request server")
PY
exec python -m vllm.entrypoints.openai.api_server \
  --model /root/autodl-tmp/models/Qwen3-VL-32B-Instruct-modelscope \
  --served-model-name Qwen/Qwen3-VL-32B-Instruct \
  --port 18000 --dtype bfloat16 --seed 3407
