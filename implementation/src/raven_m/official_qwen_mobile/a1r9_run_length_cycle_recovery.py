"""A1-R9: run-length-tolerant two-action cycle recovery."""
from __future__ import annotations
from typing import Any
from .a1r3_stale_resistant_pending import _digest
from .a1r8_route_cycle_recovery_pending import RouteCycleRecoveryPendingMemory,WRITER_REMINDER,canonical_action_family,parse_memory_prefix
MECHANISM_ID="a1r9_run_length_cycle_recovery_v1";EXPERIMENT_ID="A1R9_RLCR_QWEN3VL32B_AW_HARD_T20260806_G3407_V1"
class RunLengthCycleRecoveryMemory(RouteCycleRecoveryPendingMemory):
 mechanism_id=MECHANISM_ID
 def __init__(self,**kwargs:Any)->None:
  super().__init__(**kwargs);self._run_trace:list[tuple[str,str]]=[];self.counters["run_length_cycle_count"]=0
 def observe_step(self,**kwargs:Any)->dict[str,Any]:
  event=super().observe_step(**kwargs);event["mechanism_id"]=MECHANISM_ID;tr=kwargs.get("transition") or {};fam=canonical_action_family(kwargs.get("canonical_action"))
  try:material=tr.get("same_shape") is True and float(tr.get("changed_pixel_fraction_gt_5"))>self.no_progress_pixel_fraction
  except (TypeError,ValueError):material=False
  if material and fam is not None:
   self._run_trace.append(fam);self._run_trace=self._run_trace[-8:];current=fam[0]
   for distance in range(2,min(6,len(self._run_trace))):
    prior=self._run_trace[-distance-1];between=self._run_trace[-distance:-1];middle={x[0] for x in between}
    if prior[0]==current and len(middle)==1 and current not in middle:
     mid=between[0];sig=_digest(mid[0]+"|"+current)
     if sig not in self._delivered_cycles:
      self._pending_cycle=(sig,mid[1],fam[1]);self.counters["run_length_cycle_count"]+=1;event.update({"run_length_cycle_created":True,"route_cycle_signature":sig,"intervening_run_length":len(between)})
     break
  return event
 def read(self,context:dict[str,Any]|None=None)->tuple[str,dict[str,Any]]:
  t,a=super().read(context);a["mechanism_id"]=MECHANISM_ID;return t,a
 def commit_injection(self,ticket_id:str,final_prompt_sha256:str)->dict[str,Any]:
  e=super().commit_injection(ticket_id,final_prompt_sha256);e["mechanism_id"]=MECHANISM_ID;return e
 def audit_record(self)->dict[str,Any]:
  a=super().audit_record();a.update({"schema":"a1r9_run_length_cycle_recovery_audit_v1","mechanism_id":MECHANISM_ID,"run_trace":[x[0] for x in self._run_trace]});return a
__all__=["EXPERIMENT_ID","MECHANISM_ID","RunLengthCycleRecoveryMemory","WRITER_REMINDER","canonical_action_family","parse_memory_prefix"]
