"""Fail-closed A1-R7 contract using the path-independent R6 validator."""
from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
from typing import Any,Iterator
from . import a1r6_contract as engine
from .a1r7_grounding_recovery_pending import EXPERIMENT_ID,MECHANISM_ID
MODEL_ID=engine.MODEL_ID;MODEL_REVISION=engine.MODEL_REVISION;MODEL_REALPATH=engine.MODEL_REALPATH;MODEL_MANIFEST_SHA256=engine.MODEL_MANIFEST_SHA256;TASK_SEED=engine.TASK_SEED;GENERATION_SEED=engine.GENERATION_SEED;PORT=engine.PORT
PARENT_EVIDENCE_COMMIT="bfafa3c3461af400463d172adbe9bfd6aaa5d0af";CONFIG_SCHEMA="a1r7_grounding_recovery_pending_config_v1";OFFLINE_REPLAY_SCHEMA="a1r7_grounding_recovery_pending_offline_replay_v1";PREFLIGHT_SCHEMA="a1r7_grpl_zero_generation_preflight_v1";LIVE_RECEIPT_SCHEMA="a1r7_grpl_live_server_receipt_v1";RESULT_SCHEMA="a1r7_grpl_result_v1";CHECKPOINT_SCHEMA="a1r7_grpl_checkpoint_v1";REPOSITORY_ROOT=engine.REPOSITORY_ROOT
CONFIG_PATH=REPOSITORY_ROOT/"implementation/configs/a1r7_grounding_recovery_pending_hard_seed20260806.json";OFFLINE_REPLAY_PATH=REPOSITORY_ROOT/"evidence/a1r7/A1R7_GRPL_OFFLINE_REPLAY_REPORT.json";SOURCE_FREEZE_PATH=REPOSITORY_ROOT/"evidence/a1r7/A1R7_GRPL_SOURCE_FREEZE.json";PREFLIGHT_PATH=REPOSITORY_ROOT/"evidence/a1r7/A1R7_GRPL_ZERO_GENERATION_PREFLIGHT.json"
A0_PRESERVATION_TASKS=engine.A0_PRESERVATION_TASKS;RECIPE_TASK=engine.RECIPE_TASK;A1R2_GAIN_TASK=engine.A1R2_GAIN_TASK;CAPABILITY_GATE_TASKS=engine.CAPABILITY_GATE_TASKS;FULL_TASK_ORDER=engine.FULL_TASK_ORDER
SOURCE_FILES=("protocols/A1R7_GROUNDING_RECOVERY_PENDING_PREREG_2026-08-15.md","implementation/configs/a1r7_grounding_recovery_pending_hard_seed20260806.json","implementation/configs/androidworld_hard_v2_instances.json","implementation/src/raven_m/official_qwen_mobile/a1r7_grounding_recovery_pending.py","implementation/src/raven_m/official_qwen_mobile/a1r6_goal_anchored_pending.py","implementation/src/raven_m/official_qwen_mobile/a1r5_transition_invalidated_pending.py","implementation/src/raven_m/official_qwen_mobile/a1r4_writer_resilient_pending.py","implementation/src/raven_m/official_qwen_mobile/a1r3_stale_resistant_pending.py","implementation/src/raven_m/official_qwen_mobile/a1r7_contract.py","implementation/src/raven_m/official_qwen_mobile/a1r6_contract.py","implementation/src/raven_m/official_qwen_mobile/controller.py","implementation/src/raven_m/official_qwen_mobile/protocol.py","implementation/src/raven_m/official_qwen_mobile/working_memory.py","implementation/src/raven_m/models/vllm_client.py","implementation/src/raven_m/env/androidworld_adapter.py","implementation/src/raven_m/multi_framework_benchmark/task_instances.py","implementation/scripts/run_official_qwen_mobile.py","implementation/scripts/run_a1r7_grpl.py","implementation/scripts/replay_a1r7_grounding_recovery_pending.py","implementation/scripts/preflight_a1r7_grpl.py","implementation/scripts/qualify_a1r7_grpl_server.py","implementation/scripts/start_a1r7_grpl_server.sh","implementation/tests/official_qwen_mobile/test_a1r7_grounding_recovery_pending.py","implementation/tests/official_qwen_mobile/test_a1r7_contract.py","implementation/tests/official_qwen_mobile/test_a1r7_controller_integration.py","implementation/tests/official_qwen_mobile/test_a1r7_offline_replay.py","evidence/a1r7/A1R7_GRPL_OFFLINE_REPLAY_REPORT.json","evidence/a1r6/A1R6_GAPL_PRIMARY_GATE_RESULT_2026-08-15.json","evidence/a1r6/A1R6_GAPL_PRIMARY_GATE_RESULT_2026-08-15.md")
file_sha256=engine.file_sha256;canonical_sha256=engine.canonical_sha256;content_sha256=engine.content_sha256
_PATCH={n:globals()[n] for n in ("MECHANISM_ID","EXPERIMENT_ID","PARENT_EVIDENCE_COMMIT","CONFIG_SCHEMA","OFFLINE_REPLAY_SCHEMA","PREFLIGHT_SCHEMA","LIVE_RECEIPT_SCHEMA","RESULT_SCHEMA","CHECKPOINT_SCHEMA","CONFIG_PATH","OFFLINE_REPLAY_PATH","SOURCE_FREEZE_PATH","PREFLIGHT_PATH","SOURCE_FILES")}
@contextmanager
def _patched()->Iterator[None]:
 old={k:getattr(engine,k) for k in _PATCH}
 try:
  for k,v in _PATCH.items():setattr(engine,k,v)
  yield
 finally:
  for k,v in old.items():setattr(engine,k,v)
def source_freeze_payload(commit:str)->dict[str,Any]:
 with _patched():return engine.source_freeze_payload(commit)
def validate_source_freeze(path:Path=SOURCE_FREEZE_PATH)->dict[str,Any]:
 with _patched():return engine.validate_source_freeze(path)
def validate_preflight_report(path:Path=PREFLIGHT_PATH)->dict[str,Any]:
 with _patched():return engine.validate_preflight_report(path)
def validate_launch_receipt(path:Path,*,preflight_path:Path=PREFLIGHT_PATH)->dict[str,Any]:
 with _patched():return engine.validate_launch_receipt(path,preflight_path=preflight_path)
def preservation_report(rows:list[dict[str,Any]])->dict[str,Any]:return engine.preservation_report(rows)
def exact_completion_errors(**kwargs:Any)->list[str]:return engine.exact_completion_errors(**kwargs)
__all__=[n for n in globals() if n.isupper()]+["canonical_sha256","content_sha256","exact_completion_errors","file_sha256","preservation_report","source_freeze_payload","validate_launch_receipt","validate_preflight_report","validate_source_freeze"]
