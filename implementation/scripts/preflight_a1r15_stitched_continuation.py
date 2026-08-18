#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/"implementation/src")]
from raven_m.official_qwen_mobile import a1r15_stitched_continuation_contract as contract

def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8"); tmp.replace(path)

def main():
    p=argparse.ArgumentParser(); p.add_argument("--implementation-commit"); p.add_argument("--validate-existing",action="store_true"); a=p.parse_args()
    if a.validate_existing:
        contract.validate_preflight_report(); print('{"status":"PASS"}'); return 0
    if not a.implementation_commit: p.error("--implementation-commit required")
    errors=[]; checks={}
    head=subprocess.check_output(["git","-C",str(ROOT),"rev-parse","HEAD"],text=True).strip()
    dirty=subprocess.check_output(["git","-C",str(ROOT),"status","--porcelain","--untracked-files=all"],text=True).splitlines()
    checks["git"]={"head":head,"worktree_status":dirty}
    if head!=a.implementation_commit: errors.append("implementation_commit_not_head")
    if dirty: errors.append("worktree_dirty")
    try: parent=contract.parent_browser_binding(); checks["parent_browser"]={"status":"PASS","episode_json_sha256":parent["episode_json_sha256"]}
    except Exception as exc: errors.append(f"parent:{exc}")
    env=dict(os.environ,PYTHONPATH=os.pathsep.join([str(ROOT),str(ROOT/"implementation/src")]),PYTHONDONTWRITEBYTECODE="1")
    tests=subprocess.run([sys.executable,"-m","pytest","-q","-p","no:cacheprovider","implementation/tests/official_qwen_mobile/test_a1r15_stitched_continuation.py","implementation/tests/official_qwen_mobile/test_a1r15_explicit_observation_value_register.py","implementation/tests/official_qwen_mobile/test_a1r15_controller_integration.py"],cwd=ROOT,env=env,capture_output=True,text=True)
    checks["focused_tests"]={"returncode":tests.returncode,"passed":tests.returncode==0}; checks["test_tail"]=(tests.stdout+tests.stderr)[-3000:]
    if tests.returncode: errors.append("focused_tests_failed")
    try: freeze=contract.source_freeze_payload(a.implementation_commit)
    except Exception as exc: freeze={}; errors.append(f"source_freeze:{exc}")
    if freeze: write(contract.SOURCE_FREEZE_PATH,freeze)
    payload={"schema":contract.PREFLIGHT_SCHEMA,"status":"PASS" if not errors else "FAIL","errors":errors,"generation_calls":0,"live_generation_authorized":not errors,"mechanism_id":contract.MECHANISM_ID,"experiment_id":contract.EXPERIMENT_ID,"implementation_commit":a.implementation_commit,"source_freeze_content_sha256":freeze.get("content_sha256"),"checks":checks,"created_at":datetime.now(timezone.utc).isoformat()}
    report={**payload,"content_sha256":contract.content_sha256(payload)}; write(contract.PREFLIGHT_PATH,report)
    print(json.dumps({"status":report["status"],"errors":errors},indent=2)); return 0 if not errors else 1
if __name__=="__main__": raise SystemExit(main())
