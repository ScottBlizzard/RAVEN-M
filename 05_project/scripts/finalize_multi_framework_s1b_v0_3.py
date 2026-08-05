"""Qualify matched S1b evidence and freeze authorization for the Hard pulse."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = REPO_ROOT / "05_project"
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from raven_m.multi_framework_benchmark.capability_manifest import sha256_file, verify_protected  # noqa: E402


ARMS = ("CB-PX-B3", "CB-PX-M0", "NS-PX-GO15", "NS-PX-UIV4")
EXPECTED_TASKS = {"ClockTimerEntry", "MarkorCreateNote"}
OUTPUTS = PROJECT_ROOT / "outputs/multi_framework_s1b_v0_3"
DEST = PROJECT_ROOT / "metadata/multi_framework_s1b_v0_3/final"
S0_AUTH = PROJECT_ROOT / "metadata/multi_framework_s0_v0_2/final/s1_authorization.json"
S1B_MANIFEST = PROJECT_ROOT / "configs/task_manifests/multi_framework_s1b_v0_3.json"
PULSE_DIR = PROJECT_ROOT / "configs/task_manifests/hard_pulse_v0_3"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def goal_hash(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def raven(arm_id: str, directory: str, specs: dict[str, dict]) -> dict:
    path = OUTPUTS / directory / "s1_report.json"
    report = load(path)
    rows = []
    for item in report["results"]:
        summary = item["summary"]
        spec = specs[item["task_class"]]
        rows.append({
            "task": item["task_class"],
            "reward": summary["evaluator_reward"],
            "steps": summary["decision_count"],
            "model_calls": summary["model_call_count"],
            "parseable": item["parseable_decisions"],
            "actions": item["executed_nonterminal_actions"],
            "changes": item["observed_state_changes"],
            "error": summary["error"],
            "lifecycle": [item["task_initialization"], item["evaluator_calls"], item["task_teardown"], item["post_episode_reset"]],
            "goal_hash_ok": goal_hash(summary["task_goal"]) == spec["goal_hash"],
        })
    return {"arm_id": arm_id, "report": str(path.relative_to(REPO_ROOT)), "report_sha256": sha256_file(path), "rows": rows}


def external(arm_id: str, directory: str, specs: dict[str, dict]) -> dict:
    root = OUTPUTS / directory
    path = root / "summary.json"
    report = load(path)
    calls = load(root / "model_calls.json")
    events = [json.loads(line) for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines() if line]
    rows = []
    for item in report["tasks"]:
        spec = specs[item["task"]]
        task_events = [event for event in events if event["task_class"] == item["task"]]
        successful = sum(bool(call.get("ok")) for call in calls)
        rows.append({
            "task": item["task"], "reward": item["reward"], "steps": item["steps"],
            "model_calls": item["model_calls"], "parseable": item["parseable_decisions"],
            "actions": item["nonterminal_actions"], "changes": item["screen_changes"],
            "error": item["exception"],
            "lifecycle": [item["lifecycle"]["initialize"], item["lifecycle"]["evaluator"], item["lifecycle"]["tear_down"], 1],
            "task_hash_ok": bool(task_events) and all(event["task_params_hash"] == spec["task_params_hash"] for event in task_events),
            "successful_calls_cover_steps": successful >= sum(row["steps"] for row in report["tasks"]),
        })
    return {
        "arm_id": arm_id, "report": str(path.relative_to(REPO_ROOT)), "report_sha256": sha256_file(path),
        "successful_transport_calls": sum(bool(call.get("ok")) for call in calls),
        "failed_transport_calls": sum(not bool(call.get("ok")) for call in calls), "rows": rows,
    }


def qualify(arm: dict) -> bool:
    rows = arm["rows"]
    return (
        {row["task"] for row in rows} == EXPECTED_TASKS
        and len(rows) == 2
        and all(row["error"] is None and row["steps"] <= 12 for row in rows)
        and all(row["parseable"] >= 1 and row["actions"] >= 1 for row in rows)
        and sum(row["changes"] for row in rows) >= 1
        and all(row["lifecycle"] == [1, 1, 1, 1] for row in rows)
        and all(row.get("goal_hash_ok", True) for row in rows)
        and all(row.get("task_hash_ok", True) for row in rows)
        and all(row.get("successful_calls_cover_steps", True) for row in rows)
    )


def main() -> None:
    if DEST.exists():
        raise FileExistsError(f"Refusing to overwrite frozen qualification: {DEST}")
    protocol = load(PROJECT_ROOT / "configs/experiments/multi_framework_hard_benchmark_v0_2.json")
    verify_protected(REPO_ROOT, protocol["protected_paths"])
    manifest = load(S1B_MANIFEST)
    specs = {row["task_class"]: row for row in manifest["tasks"]}
    arms = {
        "CB-PX-B3": raven("CB-PX-B3", "01_b3", specs),
        "CB-PX-M0": raven("CB-PX-M0", "02_m0", specs),
        "NS-PX-GO15": external("NS-PX-GO15", "03_guiowl", specs),
        "NS-PX-UIV4": external("NS-PX-UIV4", "04_uivoyager", specs),
    }
    for arm in arms.values():
        arm["qualified"] = qualify(arm)
    qualified = [arm_id for arm_id in ARMS if arms[arm_id]["qualified"]]
    pulse = {path.stem: {"path": str(path.relative_to(REPO_ROOT)), "sha256": sha256_file(path)} for path in sorted(PULSE_DIR.glob("*.json"))}
    hard_ok = qualified == list(ARMS) and set(pulse) == {"H01", "H06", "H09", "H17"}
    attempts = {
        "CB-PX-B3": ["01_b3.infra_black_frame_20260806"],
        "CB-PX-M0": [],
        "NS-PX-GO15": ["03_guiowl.infra_gbk_stdout_20260806", "03_guiowl.infra_missing_suite_seed_20260806"],
        "NS-PX-UIV4": ["04_uivoyager.infra_double_v1_20260806"],
    }
    qualification = {
        "schema_version": "multi_framework_s1b_qualification.v0.3", "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if hard_ok else "FAIL", "classification": "MATCHED_DEV_QUALIFICATION",
        "task_manifest": str(S1B_MANIFEST.relative_to(REPO_ROOT)), "task_manifest_sha256": sha256_file(S1B_MANIFEST),
        "qualified_arms": qualified, "hard_model_calls_authorized": hard_ok,
        "invalid_infrastructure_attempts_preserved": attempts, "hard_pulse_manifests": pulse, "arms": arms,
    }
    DEST.mkdir(parents=True)
    qualification_path = DEST / "s1b_qualification.json"
    qualification_path.write_text(json.dumps(qualification, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    auth = load(S0_AUTH)
    auth.update({
        "schema_version": "multi_framework_hard_pulse_authorization.v0.3",
        "created_at": datetime.now(timezone.utc).isoformat(), "qualified_arms": qualified,
        "hard_model_calls_authorized": hard_ok, "hard_pulse_ids": ["H01", "H06", "H09", "H17"],
        "hard_pulse_manifests": pulse, "s1b_qualification": str(qualification_path.relative_to(REPO_ROOT)),
        "s1b_qualification_sha256": sha256_file(qualification_path),
    })
    auth_path = DEST / "hard_pulse_authorization.json"
    auth_path.write_text(json.dumps(auth, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": qualification["status"], "qualified_arms": qualified, "hard_model_calls_authorized": hard_ok, "authorization": str(auth_path.relative_to(REPO_ROOT))}, indent=2))
    if not hard_ok:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
