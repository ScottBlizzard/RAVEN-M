#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "implementation/src")]
from implementation.scripts import qualify_a1r5_tipl_server as base
from raven_m.official_qwen_mobile import a1r14_contract as contract
base.contract = contract
if __name__ == "__main__":
    raise SystemExit(base.main())
