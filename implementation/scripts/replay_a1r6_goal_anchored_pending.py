#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]; sys.path[:0]=[str(ROOT),str(ROOT/"implementation/src")]
from implementation.scripts import replay_a1r5_transition_invalidated_pending as base
from raven_m.official_qwen_mobile.a1r6_goal_anchored_pending import GoalAnchoredPendingMemory,MECHANISM_ID

def replay(suite_dir:Path)->dict:
    original=base.TransitionInvalidatedPendingMemory
    checkpoint=json.loads((suite_dir/"checkpoint.json").read_text(encoding="utf-8"))
    goals=[str(item.get("task_goal") or "") for item in (checkpoint.get("valid_summaries") or [])]
    try:
        class ReplayMemory(GoalAnchoredPendingMemory):
            def __init__(self):
                super().__init__(); self._replay_goal=goals.pop(0)
            def read(self,context=None):
                return super().read({"goal": getattr(self,"_replay_goal","")})
        base.TransitionInvalidatedPendingMemory=ReplayMemory
        report=base.replay(suite_dir)
    finally: base.TransitionInvalidatedPendingMemory=original
    report["schema"]="a1r6_goal_anchored_pending_offline_replay_v1"; report["mechanism_id"]=MECHANISM_ID; report["content_sha256"]=base.base._content_sha(report); return report

def main()->int:
    p=argparse.ArgumentParser(); p.add_argument("--suite-dir",type=Path,default=base.base.DEFAULT_SUITE); p.add_argument("--output",type=Path,default=ROOT/"evidence/a1r6/A1R6_GAPL_OFFLINE_REPLAY_REPORT.json"); a=p.parse_args(); r=replay(a.suite_dir.resolve()); a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(r,ensure_ascii=True,sort_keys=True,indent=2)+"\n",encoding="utf-8"); print(json.dumps({"status":r["status"],"errors":r["errors"],"totals":r["totals"]},indent=2)); return 0 if r["status"]=="PASS" else 1
if __name__=="__main__": raise SystemExit(main())
