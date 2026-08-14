#!/usr/bin/env python3
from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT),str(ROOT/"implementation/src")]
from implementation.scripts import replay_a1r6_goal_anchored_pending as base
from raven_m.official_qwen_mobile.a1r8_route_cycle_recovery_pending import RouteCycleRecoveryPendingMemory,MECHANISM_ID
def replay(s:Path)->dict:
 o=base.GoalAnchoredPendingMemory
 try:base.GoalAnchoredPendingMemory=RouteCycleRecoveryPendingMemory;r=base.replay(s)
 finally:base.GoalAnchoredPendingMemory=o
 r["schema"]="a1r8_route_cycle_recovery_pending_offline_replay_v1";r["mechanism_id"]=MECHANISM_ID;r["content_sha256"]=base.base.base._content_sha(r);return r
def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--suite-dir",type=Path,default=base.base.base.DEFAULT_SUITE);p.add_argument("--output",type=Path,default=ROOT/"evidence/a1r8/A1R8_RCRP_OFFLINE_REPLAY_REPORT.json");a=p.parse_args();r=replay(a.suite_dir.resolve());a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,sort_keys=True,indent=2)+"\n");print(r["status"],r["errors"]);return 0 if r["status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
