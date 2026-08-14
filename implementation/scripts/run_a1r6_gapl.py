#!/usr/bin/env python3
from __future__ import annotations
import argparse,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; PYTHON=ROOT/"06_local_runtime/envs/androidworld/Scripts/python.exe"
def main()->int:
    p=argparse.ArgumentParser(); p.add_argument("--adb-path",required=True); p.add_argument("--launch-receipt",type=Path,required=True); p.add_argument("--url",default="http://127.0.0.1:18000"); p.add_argument("--console-port",type=int,default=5554); p.add_argument("--grpc-port",type=int,default=8554); p.add_argument("--execute",action="store_true"); a=p.parse_args(); cmd=[str(PYTHON),str(ROOT/"implementation/scripts/run_official_qwen_mobile.py"),"--adb-path",a.adb_path,"--manifest",str(ROOT/"implementation/configs/androidworld_hard_v2_instances.json"),"--url",a.url,"--console-port",str(a.console_port),"--grpc-port",str(a.grpc_port),"--a1r6-gapl","--a1r6-preflight-report",str(ROOT/"evidence/a1r6/A1R6_GAPL_ZERO_GENERATION_PREFLIGHT.json"),"--a1r6-launch-receipt",str(a.launch_receipt.resolve()),"--output-root",str(ROOT/"runs/a1r6_gapl")]; print(subprocess.list2cmdline(cmd)); return subprocess.call(cmd) if a.execute else 0
if __name__=="__main__": raise SystemExit(main())
