"""A1-R8: bounded two-action route-cycle recovery memory."""
from __future__ import annotations
from typing import Any
from .a1r3_stale_resistant_pending import _digest
from .a1r7_grounding_recovery_pending import GroundingRecoveryPendingMemory,WRITER_REMINDER,canonical_action_family,parse_memory_prefix
MECHANISM_ID="a1r8_route_cycle_recovery_pending_v1";EXPERIMENT_ID="A1R8_RCRP_QWEN3VL32B_AW_HARD_T20260806_G3407_V1"
ROUTE_RECOVERY=("ROUTE CYCLE RECOVERY: alternating between {first} and {second} returned through the same two-step route twice without completing the pending work. "
"Do not repeat the same second coordinate. If the item must be reopened, reopen it once, then choose a visibly different exact second control after recalibrating y over the full phone screenshot. Require visible completion before continuing.")
class RouteCycleRecoveryPendingMemory(GroundingRecoveryPendingMemory):
 mechanism_id=MECHANISM_ID
 def __init__(self,**kwargs:Any)->None:
  super().__init__(**kwargs);self._route_trace:list[tuple[str,str]]=[];self._pending_cycle:tuple[str,str,str]|None=None;self._prepared_cycle:str|None=None;self._delivered_cycles:set[str]=set();self.counters["route_cycle_count"]=0;self.counters["route_cycle_recovery_read_count"]=0
 def read(self,context:dict[str,Any]|None=None)->tuple[str,dict[str,Any]]:
  text,audit=super().read(context);audit["mechanism_id"]=MECHANISM_ID;self._prepared_cycle=None
  if text and self.pending_ticket is not None and self._pending_cycle is not None:
   sig,first,second=self._pending_cycle;addition=ROUTE_RECOVERY.format(first=first,second=second);text=text+"\n"+addition
   if len(text)<=self.max_render_chars:
    self.pending_ticket.text=text;self.pending_ticket.text_sha256=_digest(text);self._prepared_cycle=sig;audit.update({"rendered_chars":len(text),"rendered_sha256":self.pending_ticket.text_sha256,"route_cycle_recovery_injected":True,"route_cycle_signature":sig})
  return text,audit
 def commit_injection(self,ticket_id:str,final_prompt_sha256:str)->dict[str,Any]:
  sig=self._prepared_cycle;event=super().commit_injection(ticket_id,final_prompt_sha256)
  if sig:
   if len(self._delivered_cycles)>=8:self._delivered_cycles.remove(sorted(self._delivered_cycles)[0])
   self._delivered_cycles.add(sig);self._pending_cycle=None;self.counters["route_cycle_recovery_read_count"]+=1
  self._prepared_cycle=None;event.update({"mechanism_id":MECHANISM_ID,"route_cycle_recovery_injected":sig is not None});return event
 def observe_step(self,**kwargs:Any)->dict[str,Any]:
  return self._observe_route(**kwargs)
 def _observe_route(self,**kwargs:Any)->dict[str,Any]:
  event=super().observe_step(**kwargs);event["mechanism_id"]=MECHANISM_ID;transition=kwargs.get("transition") or {};family=canonical_action_family(kwargs.get("canonical_action"))
  try:material=transition.get("same_shape") is True and float(transition.get("changed_pixel_fraction_gt_5"))>self.no_progress_pixel_fraction
  except (TypeError,ValueError):material=False
  if material and family is not None:
   self._route_trace.append(family);self._route_trace=self._route_trace[-4:]
   if len(self._route_trace)==4:
    a,b,c,d=self._route_trace;sig=_digest(a[0]+"|"+b[0])
    if a[0]==c[0] and b[0]==d[0] and a[0]!=b[0] and sig not in self._delivered_cycles:
     self._pending_cycle=(sig,a[1],b[1]);self.counters["route_cycle_count"]+=1;event.update({"route_cycle_created":True,"route_cycle_signature":sig})
  return event
 def audit_record(self)->dict[str,Any]:
  a=super().audit_record();a.update({"schema":"a1r8_route_cycle_recovery_pending_audit_v1","mechanism_id":MECHANISM_ID,"route_trace":[x[0] for x in self._route_trace],"pending_cycle":self._pending_cycle});return a
__all__=["EXPERIMENT_ID","MECHANISM_ID","ROUTE_RECOVERY","RouteCycleRecoveryPendingMemory","WRITER_REMINDER","canonical_action_family","parse_memory_prefix"]
