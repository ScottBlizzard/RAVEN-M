#!/usr/bin/env bash
set -euo pipefail
REPO_DIR="${RAVEN_REPO_DIR:-/root/autodl-tmp/RAVEN-M-A1}"
ENV_DIR="${RAVEN_ENV_DIR:-/root/autodl-tmp/envs/qwen_vllm}"
MODEL_DIR="${RAVEN_MODEL_SOURCE:-/root/autodl-tmp/models/Qwen3-VL-32B-Instruct-modelscope}"
PREFLIGHT="${A11_PREFLIGHT:-${REPO_DIR}/evidence/a11/A11_ZERO_GENERATION_PREFLIGHT.json}"
INTENT="${A11_SERVER_LAUNCH_INTENT:-${REPO_DIR}/evidence/a11/A11_SERVER_LAUNCH_INTENT.json}"
PORT="${RAVEN_SERVER_PORT:-18000}"
export PYTHONPATH="${REPO_DIR}/implementation/src"
ARM=a11 SCHEMA=a11_server_launch_intent_v1 PREFLIGHT="${PREFLIGHT}" INTENT="${INTENT}" MODEL_DIR="${MODEL_DIR}" ENV_DIR="${ENV_DIR}" PORT="${PORT}" "${ENV_DIR}/bin/python" - <<'PY'
import importlib.metadata, json, os
from hashlib import sha256
from pathlib import Path
from raven_m.official_qwen_mobile.a11_contract import MODEL_ID, MODEL_MANIFEST_SHA256, validate_preflight_report
p=Path(os.environ['PREFLIGHT']).resolve(); report=validate_preflight_report(p); model=str(Path(os.environ['MODEL_DIR']).resolve()); port=int(os.environ['PORT'])
cmd=[str(Path(os.environ['ENV_DIR'])/'bin/python'),str(Path(os.environ['ENV_DIR'])/'bin/vllm'),'serve',model,'--served-model-name',MODEL_ID,'--host','127.0.0.1','--port',str(port),'--tensor-parallel-size','1','--dtype','bfloat16','--gpu-memory-utilization',os.environ.get('RAVEN_GPU_MEMORY_UTILIZATION','0.92'),'--max-model-len',os.environ.get('RAVEN_MAX_MODEL_LEN','65536'),'--max-num-seqs','1','--limit-mm-per-prompt','{"image":1}','--generation-config','vllm','--no-enable-log-requests']
intent={'schema':os.environ['SCHEMA'],'status':'launch_pending_live_qualification','arm':os.environ['ARM'],'pid_before_exec':os.getppid(),'model_realpath':model,'model_manifest_sha256':MODEL_MANIFEST_SHA256,'preflight_sha256':sha256(p.read_bytes()).hexdigest(),'source_freeze_sha256':report['source_freeze_sha256'],'packages':{n:importlib.metadata.version(n) for n in ('vllm','torch','transformers')},'served_model_id':MODEL_ID,'port':port,'command':cmd}
Path(os.environ['INTENT']).write_text(json.dumps(intent,indent=2,sort_keys=True)+'\n')
PY
exec "${ENV_DIR}/bin/python" "${ENV_DIR}/bin/vllm" serve "$(realpath "${MODEL_DIR}")" --served-model-name Qwen/Qwen3-VL-32B-Instruct --host 127.0.0.1 --port "${PORT}" --tensor-parallel-size 1 --dtype bfloat16 --gpu-memory-utilization "${RAVEN_GPU_MEMORY_UTILIZATION:-0.92}" --max-model-len "${RAVEN_MAX_MODEL_LEN:-65536}" --max-num-seqs 1 --limit-mm-per-prompt '{"image":1}' --generation-config vllm --no-enable-log-requests
