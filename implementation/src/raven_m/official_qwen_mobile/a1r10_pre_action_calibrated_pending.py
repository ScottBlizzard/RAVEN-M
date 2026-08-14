"""A1-R10: pending ledger plus pre-action full-screen coordinate calibration."""
from __future__ import annotations
from typing import Any
from .a1r3_stale_resistant_pending import _digest
from .a1r9_run_length_cycle_recovery import RunLengthCycleRecoveryMemory,WRITER_REMINDER,canonical_action_family,parse_memory_prefix
MECHANISM_ID="a1r10_pre_action_calibrated_pending_v1";EXPERIMENT_ID="A1R10_PACP_QWEN3VL32B_AW_HARD_T20260806_G3407_V1"
CALIBRATION="SPATIAL CALIBRATION BEFORE ANY TAP: coordinates are normalized over the entire phone screenshot, with y=0 at the top edge and y=1 at the bottom edge including system bars. Locate the visible control center using the full image; do not estimate y from a cropped list or dialog."
class PreActionCalibratedPendingMemory(RunLengthCycleRecoveryMemory):
 mechanism_id=MECHANISM_ID
 def __init__(self,**kwargs:Any)->None:super().__init__(**kwargs);self.counters["pre_action_calibration_read_count"]=0;self._prepared_calibration=False
 def read(self,context:dict[str,Any]|None=None)->tuple[str,dict[str,Any]]:
  t,a=super().read(context);a["mechanism_id"]=MECHANISM_ID;self._prepared_calibration=False
  if t and self.pending_ticket is not None:
   t=t+"\n"+CALIBRATION
   if len(t)<=self.max_render_chars:self.pending_ticket.text=t;self.pending_ticket.text_sha256=_digest(t);self._prepared_calibration=True;a.update({"rendered_chars":len(t),"rendered_sha256":self.pending_ticket.text_sha256,"pre_action_calibration_injected":True})
  return t,a
 def commit_injection(self,ticket_id:str,final_prompt_sha256:str)->dict[str,Any]:
  active=self._prepared_calibration;e=super().commit_injection(ticket_id,final_prompt_sha256);self.counters["pre_action_calibration_read_count"]+=int(active);self._prepared_calibration=False;e.update({"mechanism_id":MECHANISM_ID,"pre_action_calibration_injected":active});return e
 def observe_step(self,**kwargs:Any)->dict[str,Any]:e=super().observe_step(**kwargs);e["mechanism_id"]=MECHANISM_ID;return e
 def audit_record(self)->dict[str,Any]:
  a=super().audit_record();a.update({"schema":"a1r10_pre_action_calibrated_pending_audit_v1","mechanism_id":MECHANISM_ID});return a
__all__=["CALIBRATION","EXPERIMENT_ID","MECHANISM_ID","PreActionCalibratedPendingMemory","WRITER_REMINDER","canonical_action_family","parse_memory_prefix"]
