"""A1-R7 goal ledger with evidence-triggered grounding recovery."""
from __future__ import annotations
from typing import Any
from .a1r3_stale_resistant_pending import _FAILURE_LINE, _digest
from .a1r6_goal_anchored_pending import GoalAnchoredPendingMemory, WRITER_REMINDER, canonical_action_family, parse_memory_prefix

MECHANISM_ID="a1r7_grounding_recovery_pending_v1"
EXPERIMENT_ID="A1R7_GRPL_QWEN3VL32B_AW_HARD_T20260806_G3407_V1"
RECOVERY=("RECOVERY REQUIRED FOR THE NEXT ACTION: {label} produced no visible progress at least twice. "
          "Do not repeat that action family or coordinate region. Reinspect the current screenshot and choose a visibly different control or route. "
          "Tap coordinates are normalized over the entire phone screenshot: y=0 is the top edge and y=1 is the bottom edge, including system bars.")

class GroundingRecoveryPendingMemory(GoalAnchoredPendingMemory):
    mechanism_id=MECHANISM_ID
    def __init__(self,**kwargs:Any)->None:
        super().__init__(**kwargs); self.counters["strong_recovery_read_count"]=0; self._prepared_strong_recovery=False
    def read(self,context:dict[str,Any]|None=None)->tuple[str,dict[str,Any]]:
        text,audit=super().read(context); audit["mechanism_id"]=MECHANISM_ID; self._prepared_strong_recovery=False
        if text and self.pending_ticket is not None and self.failed_attempt is not None and audit.get("failure_evidence_injected") is True:
            old=_FAILURE_LINE.strip().format(label=self.failed_attempt.label); strong=RECOVERY.format(label=self.failed_attempt.label)
            text=text.replace(old,strong); self.pending_ticket.text=text; self.pending_ticket.text_sha256=_digest(text); self._prepared_strong_recovery=True
            audit.update({"rendered_chars":len(text),"rendered_sha256":self.pending_ticket.text_sha256,"strong_recovery_injected":True})
        return text,audit
    def commit_injection(self,ticket_id:str,final_prompt_sha256:str)->dict[str,Any]:
        strong=self._prepared_strong_recovery; event=super().commit_injection(ticket_id,final_prompt_sha256); self.counters["strong_recovery_read_count"]+=int(strong); self._prepared_strong_recovery=False; event.update({"mechanism_id":MECHANISM_ID,"strong_recovery_injected":strong}); return event
    def cancel_injection(self,ticket_id:str,reason:str)->dict[str,Any]:
        self._prepared_strong_recovery=False; return super().cancel_injection(ticket_id,reason)
    def observe_step(self,**kwargs:Any)->dict[str,Any]:
        event=super().observe_step(**kwargs);event["mechanism_id"]=MECHANISM_ID;return event
    def audit_record(self)->dict[str,Any]:
        audit=super().audit_record();audit.update({"schema":"a1r7_grounding_recovery_pending_audit_v1","mechanism_id":MECHANISM_ID});
        if audit.get("last_committed_read"):audit["last_committed_read"]["mechanism_id"]=MECHANISM_ID
        return audit
__all__=["EXPERIMENT_ID","MECHANISM_ID","RECOVERY","GroundingRecoveryPendingMemory","WRITER_REMINDER","canonical_action_family","parse_memory_prefix"]
