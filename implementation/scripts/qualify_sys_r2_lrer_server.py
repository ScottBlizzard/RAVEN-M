#!/usr/bin/env python3
"""Issue a fresh zero-generation live receipt for SYS-R2-LRER."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "implementation/src")]

from implementation.scripts import qualify_a1r5_tipl_server as base  # noqa: E402
from raven_m.official_qwen_mobile import sys_r2_lrer_contract as contract  # noqa: E402

base.contract = contract


if __name__ == "__main__":
    raise SystemExit(base.main())
