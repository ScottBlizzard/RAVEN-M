"""A1-R12: R11 with deterministic consecutive-history deduplication."""
from __future__ import annotations
import re
from typing import Any,Iterable
from .a1r11_coordinate_self_check_pending import CoordinateSelfCheckPendingMemory,SELF_CHECK,WRITER_REMINDER,canonical_action_family,parse_memory_prefix

MECHANISM_ID="a1r12_compacted_history_pending_v1"
EXPERIMENT_ID="A1R12_CHP_QWEN3VL32B_AW_HARD_T20260806_G3407_V1"

def _history_key(text:str)->str:
 return re.sub(r"\s+"," ",str(text).strip().strip('"').strip()).casefold()

class CompactedHistoryPendingMemory(CoordinateSelfCheckPendingMemory):
 mechanism_id=MECHANISM_ID
 def __init__(self,**kwargs:Any)->None:
  super().__init__(**kwargs);self.counters["history_items_removed_count"]=0;self.counters["history_compaction_call_count"]=0
 def prompt_history(self,history:Iterable[str])->list[str]:
  source=list(history);result:list[str]=[];last_key=None
  for item in source:
   key=_history_key(item)
   if result and key==last_key:
    result[-1]=item;self.counters["history_items_removed_count"]+=1
   else:result.append(item);last_key=key
  self.counters["history_compaction_call_count"]+=1;return result
 def read(self,context:dict[str,Any]|None=None)->tuple[str,dict[str,Any]]:
  text,audit=super().read(context);audit["mechanism_id"]=MECHANISM_ID;audit["history_items_removed_total"]=self.counters["history_items_removed_count"];return text,audit
 def commit_injection(self,ticket_id:str,final_prompt_sha256:str)->dict[str,Any]:
  event=super().commit_injection(ticket_id,final_prompt_sha256);event["mechanism_id"]=MECHANISM_ID;return event
 def observe_step(self,**kwargs:Any)->dict[str,Any]:
  event=super().observe_step(**kwargs);event["mechanism_id"]=MECHANISM_ID;return event
 def audit_record(self)->dict[str,Any]:
  audit=super().audit_record();audit.update({"schema":"a1r12_compacted_history_pending_audit_v1","mechanism_id":MECHANISM_ID});return audit

__all__=["CompactedHistoryPendingMemory","EXPERIMENT_ID","MECHANISM_ID","SELF_CHECK","WRITER_REMINDER","canonical_action_family","parse_memory_prefix"]
