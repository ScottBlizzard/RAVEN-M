#!/usr/bin/env python3
import argparse,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];PYTHON=ROOT/"06_local_runtime/envs/androidworld/Scripts/python.exe"
def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--adb-path",required=True);p.add_argument("--launch-receipt",type=Path,required=True);p.add_argument("--execute",action="store_true");a=p.parse_args();cmd=[str(PYTHON),str(ROOT/"implementation/scripts/run_official_qwen_mobile.py"),"--adb-path",a.adb_path,"--manifest",str(ROOT/"implementation/configs/androidworld_hard_v2_instances.json"),"--url","http://127.0.0.1:18000","--console-port","5554","--grpc-port","8554","--a1r8-rcrp","--a1r8-preflight-report",str(ROOT/"evidence/a1r8/A1R8_RCRP_ZERO_GENERATION_PREFLIGHT.json"),"--a1r8-launch-receipt",str(a.launch_receipt.resolve()),"--output-root",str(ROOT/"runs/a1r8_rcrp")];print(subprocess.list2cmdline(cmd));return subprocess.call(cmd) if a.execute else 0
if __name__=="__main__":raise SystemExit(main())
