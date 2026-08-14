"""A1-R11: pending ledger plus an explicit per-tap coordinate self-check."""
from __future__ import annotations
from typing import Any
from .a1r3_stale_resistant_pending import _digest
from .a1r10_pre_action_calibrated_pending import PreActionCalibratedPendingMemory,CALIBRATION,WRITER_REMINDER,canonical_action_family,parse_memory_prefix

MECHANISM_ID="a1r11_coordinate_self_check_pending_v1"
EXPERIMENT_ID="A1R11_CSCP_QWEN3VL32B_AW_HARD_T20260806_G3407_V1"
SELF_CHECK="COORDINATE SELF-CHECK FOR EVERY TAP: In Thought, first state the target center as percentages (x% from left, y% from top) of the entire phone screenshot, then compute tool coordinates [round(10*x%), round(10*y%)] on the 0-1000 grid. Verify the point lies on the visible control before issuing the tap."

class CoordinateSelfCheckPendingMemory(PreActionCalibratedPendingMemory):
 mechanism_id=MECHANISM_ID
 def __init__(self,**kwargs:Any)->None:
  super().__init__(**kwargs);self.counters["coordinate_self_check_read_count"]=0;self._prepared_self_check=False
 def read(self,context:dict[str,Any]|None=None)->tuple[str,dict[str,Any]]:
  text,audit=super().read(context);audit["mechanism_id"]=MECHANISM_ID;self._prepared_self_check=False
  if text and self.pending_ticket is not None and CALIBRATION in text:
   text=text.replace(CALIBRATION,SELF_CHECK)
   self.pending_ticket.text=text;self.pending_ticket.text_sha256=_digest(text);self._prepared_self_check=True
   audit.update({"rendered_chars":len(text),"rendered_sha256":self.pending_ticket.text_sha256,"pre_action_calibration_injected":False,"coordinate_self_check_injected":True})
  return text,audit
 def commit_injection(self,ticket_id:str,final_prompt_sha256:str)->dict[str,Any]:
  active=self._prepared_self_check;event=super().commit_injection(ticket_id,final_prompt_sha256)
  if active:
   self.counters["pre_action_calibration_read_count"]-=1;self.counters["coordinate_self_check_read_count"]+=1
  self._prepared_self_check=False;event.update({"mechanism_id":MECHANISM_ID,"pre_action_calibration_injected":False,"coordinate_self_check_injected":active});return event
 def observe_step(self,**kwargs:Any)->dict[str,Any]:
  event=super().observe_step(**kwargs);event["mechanism_id"]=MECHANISM_ID;return event
 def audit_record(self)->dict[str,Any]:
  audit=super().audit_record();audit.update({"schema":"a1r11_coordinate_self_check_pending_audit_v1","mechanism_id":MECHANISM_ID});return audit

__all__=["CoordinateSelfCheckPendingMemory","EXPERIMENT_ID","MECHANISM_ID","SELF_CHECK","WRITER_REMINDER","canonical_action_family","parse_memory_prefix"]
