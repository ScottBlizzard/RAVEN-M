"""Read-only preflight for the multi-framework Hard benchmark audit package."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "05_project/configs/experiments/multi_framework_hard_benchmark_v0_1.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_head(path: Path) -> str | None:
    if not (path / ".git").exists():
        return None
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--verify", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    config = json.loads(CONFIG.read_text(encoding="utf-8"))

    if config["status"] != "draft_for_gptpro_audit_generation_forbidden":
        errors.append("unexpected protocol status")
    if config["authorization"]["model_generation_allowed_before_gptpro_audit"]:
        errors.append("generation must remain forbidden before GPT Pro audit")
    if config["authorization"]["android_episode_allowed_before_gptpro_audit"]:
        errors.append("Android episodes must remain forbidden before GPT Pro audit")

    task_info = config["source_task_manifest"]
    task_path = ROOT / task_info["path"]
    if not task_path.exists():
        errors.append(f"missing task manifest: {task_info['path']}")
    else:
        if sha256(task_path) != task_info["sha256"]:
            errors.append("Hard task manifest hash mismatch")
        tasks = json.loads(task_path.read_text(encoding="utf-8"))["tasks"]
        if len(tasks) != task_info["expected_task_count"]:
            errors.append("Hard task count mismatch")
        ids = [task["id"] for task in tasks]
        classes = [task["class_name"] for task in tasks]
        if len(ids) != len(set(ids)) or len(classes) != len(set(classes)):
            errors.append("Hard task IDs or class names are not unique")

    candidate_path = ROOT / config["candidate_manifest"]["path"]
    if not candidate_path.exists():
        errors.append("candidate manifest missing")
        candidates: dict[str, dict[str, str]] = {}
    else:
        with candidate_path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        candidates = {row["candidate_id"]: row for row in rows}
        if len(candidates) != len(rows):
            errors.append("duplicate candidate_id in candidate manifest")

    referenced: set[str] = set()
    for lane in config["lanes"].values():
        for key, value in lane.items():
            if key.endswith("arm_ids_pending_audit"):
                referenced.update(value)
    missing_candidates = sorted(referenced - set(candidates))
    if missing_candidates:
        errors.append(f"lane references missing candidates: {missing_candidates}")

    for candidate_id, row in candidates.items():
        local_rel = row["androidworld_path"]
        state = row["local_state_2026_08_05"]
        if state == "ready" and not (ROOT / local_rel).exists():
            errors.append(f"{candidate_id} claims ready but path is missing: {local_rel}")
        if state.startswith("code_ready"):
            if not (ROOT / local_rel).exists():
                errors.append(f"{candidate_id} code-ready path is missing: {local_rel}")
        if state == "official_support_verified_clone_incomplete":
            warnings.append(f"{candidate_id} remains blocked on source/model completion")

    local_git_expectations = {
        "03_code/third_party/android_world": "3e50888527ef9f29b9157ecd537e408008bb1c85",
        "03_code/third_party/MobileAgent": "11cea575561fb7800b5fb6b6cafa56f7a91de11f",
        "03_code/third_party/mobile-use": "babec07fd0e5faa7e7bcc7d3d0ee2320f6b83347",
        "03_code/third_party/droidrun-android-world": "5090130394bc93a6e2bd8069e4c2d6b9c05aa112",
    }
    for rel, expected in local_git_expectations.items():
        actual = git_head(ROOT / rel)
        if actual != expected:
            errors.append(f"repository HEAD mismatch for {rel}: {actual!r} != {expected}")

    for rel, expected in config["protected_preexisting_paths"].items():
        path = ROOT / rel
        if not path.exists():
            errors.append(f"protected path missing: {rel}")
        elif sha256(path) != expected:
            errors.append(f"protected path hash changed: {rel}")

    result = {
        "status": "PASS" if not errors else "FAIL",
        "generation_authorized": False,
        "candidate_count": len(candidates),
        "referenced_arm_count": len(referenced),
        "hard_task_count": task_info["expected_task_count"],
        "warnings": warnings,
        "errors": errors,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
