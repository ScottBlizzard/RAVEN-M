"""Zero-generation audit for B2 Clean MobileUse."""

from __future__ import annotations

import ast
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
CONFIG = PROJECT_ROOT / "configs/b2_clean_mobileuse_qwen3_vl_32b_diagnostic_seed20260806.yaml"
MANIFEST = PROJECT_ROOT / "configs/b2_clean_mobileuse_diagnostic_seed20260806.final.json"
PREREG_JSON = REPOSITORY_ROOT / "protocols/B2_CLEAN_MOBILEUSE_DIAGNOSTIC_PREREG.json"
PREREG_MD = REPOSITORY_ROOT / "protocols/B2_CLEAN_MOBILEUSE_DIAGNOSTIC_PREREG.md"
CONTROLLER = PROJECT_ROOT / "src/raven_m/public_frameworks/mobileuse/clean_controller.py"
RUNNER = PROJECT_ROOT / "scripts/run_clean_mobileuse_b2.py"
SELF = Path(__file__).resolve()
MASTER_MANIFEST = PROJECT_ROOT / "configs/androidworld_hard_v2_instances.json"
OUTPUT = REPOSITORY_ROOT / "evidence/public_framework/mobileuse_b2/B2_ZERO_GENERATION_PREFLIGHT.json"
ARM_ID = "B2_CLEAN_MOBILEUSE_QWEN3VL32B_AW_HARD_DEV_S20260806_V1"
TASK_ORDER = ["H12", "H08", "H05", "H01", "H14"]


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def main() -> None:
    errors: list[str] = []
    for path in (CONFIG, MANIFEST, PREREG_JSON, PREREG_MD, CONTROLLER, RUNNER):
        if not path.is_file():
            errors.append(f"missing:{path}")

    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    prereg = json.loads(PREREG_JSON.read_text(encoding="utf-8"))
    master = json.loads(MASTER_MANIFEST.read_text(encoding="utf-8"))
    if config.get("arm_id") != ARM_ID or manifest.get("arm_id") != ARM_ID or prereg.get("arm_id") != ARM_ID:
        errors.append("arm_id_drift")
    if config.get("b2_changes", {}).get("memory_representation") != "unchanged_free_text_history_and_progress":
        errors.append("memory_boundary_drift")
    if prereg.get("memory_intervention") is not False:
        errors.append("memory_intervention_must_be_false")
    if config.get("diagnostic_task_order") != TASK_ORDER:
        errors.append("config_task_order_drift")
    if [item.get("task_id") for item in manifest.get("instances", [])] != TASK_ORDER:
        errors.append("manifest_task_order_drift")

    master_by_key = {
        (item["task_id"], int(item["task_seed"])): item
        for item in master.get("instances", [])
    }
    for item in manifest.get("instances", []):
        expected = master_by_key.get((item.get("task_id"), int(item.get("task_seed", -1))))
        if expected is None:
            errors.append(f"missing_master_instance:{item.get('task_id')}")
        elif item != expected:
            errors.append(f"instance_drift:{item.get('task_id')}")

    for path in (CONTROLLER, RUNNER):
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            errors.append(f"syntax:{path.name}:{exc}")

    controller_text = CONTROLLER.read_text(encoding="utf-8")
    prohibited_literals = [
        "BrowserMultiply", "RetroSavePlaylist", "OsmAndMarker",
        "MarkorCreateNoteAndSms", "RecipeAddMultipleRecipesFromMarkor2",
    ]
    leaked = [value for value in prohibited_literals if value in controller_text]
    if leaked:
        errors.append(f"task_specific_controller_literals:{leaked}")

    test_command = [sys.executable, "-m", "pytest", "-q"]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(PROJECT_ROOT / "src")
    completed = subprocess.run(
        test_command,
        cwd=PROJECT_ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=180,
    )
    if completed.returncode != 0:
        errors.append("offline_tests_failed")

    files = [CONFIG, MANIFEST, PREREG_JSON, PREREG_MD, CONTROLLER, RUNNER, SELF]
    report = {
        "schema": "raven_m.b2_clean_mobileuse.zero_generation_preflight.v1",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "arm_id": ARM_ID,
        "status": "pass" if not errors else "fail",
        "generation_calls": 0,
        "errors": errors,
        "task_order": TASK_ORDER,
        "memory_intervention": False,
        "file_sha256": {
            str(path.relative_to(REPOSITORY_ROOT)).replace("\\", "/"): digest(path)
            for path in files
        },
        "tests": {
            "command": test_command,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        },
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
