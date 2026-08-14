#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT),str(ROOT/"implementation/src"),str(ROOT/"implementation/scripts")]
from implementation.scripts import preflight_a1r5_tipl as base
from implementation.scripts.replay_a1r8_route_cycle_recovery_pending import replay
from raven_m.official_qwen_mobile import a1r8_contract as contract
from raven_m.official_qwen_mobile.a1r8_route_cycle_recovery_pending import RouteCycleRecoveryPendingMemory
base.contract=contract;base.TransitionInvalidatedPendingMemory=RouteCycleRecoveryPendingMemory;base.replay=replay
if __name__=="__main__":raise SystemExit(base.main())
