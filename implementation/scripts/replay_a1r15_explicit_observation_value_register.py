#!/usr/bin/env python3
"""Zero-generation replay for A1-R15."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "implementation/src")]
from raven_m.official_qwen_mobile.a1r15_explicit_observation_value_register import (  # noqa: E402
    EXPERIMENT_ID, MECHANISM_ID, ExplicitObservationValueRegisterMemory,
)
from raven_m.official_qwen_mobile import a1r13_contract as order_contract  # noqa: E402
from raven_m.official_qwen_mobile import a1r13d_contract as digest_contract  # noqa: E402


def replay(fixture_path: Path) -> dict:
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    errors = []
    if fixture.get("schema") != "a1r15_eovr_replay_fixture_v1" or fixture.get("content_sha256") != digest_contract.content_sha256(fixture):
        errors.append("fixture_invalid")
    rows = []
    for episode in fixture.get("episodes") or []:
        memory = ExplicitObservationValueRegisterMemory()
        rendered = []
        for step in episode.get("steps") or []:
            text, read = memory.read({"goal": episode["goal"]})
            if text:
                rendered.append({"request_step": step["step"], "text": text})
                memory.commit_injection(read["ticket_id"], f"offline-{episode['episode_id']}-{step['step']}")
            memory.write(
                source_step=step["step"], action_summary=step["action_summary"],
                source_call_id=step["source_call_id"], source_response_sha256=step["source_response_sha256"],
                source_screenshot_sha256=step["source_screenshot_sha256"],
            )
            memory.write_model_response(
                source_step=step["step"], model_response=step["model_response"], action_summary=step["action_summary"],
                source_call_id=step["source_call_id"], source_response_sha256=step["source_response_sha256"],
                source_screenshot_sha256=step["source_screenshot_sha256"],
            )
        audit = memory.audit_record()
        values = [atom["value"] for atom in (audit.get("evidence_register") or {}).get("values") or []]
        counters = (audit.get("evidence_register") or {}).get("counters") or {}
        response_counters = (audit.get("response_grounding") or {}).get("counters") or {}
        rows.append({
            "task_name": episode["task_name"], "episode_id": episode["episode_id"],
            "historical_reward": episode["historical_reward"],
            "activation_count": int(counters.get("activation_count") or 0),
            "append_count": int(counters.get("append_count") or 0),
            "response_append_count": int(response_counters.get("append_count") or 0),
            "render_count": int(counters.get("render_count") or 0),
            "final_values": values, "rendered_reads": rendered,
            "serialized_audit_bytes": len(json.dumps(audit, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")),
        })
    active = [row for row in rows if row["activation_count"]]
    target = next((row for row in rows if row["task_name"] == order_contract.TARGET_GATE_TASK), {})
    success_active = [row for row in rows if row["task_name"] in order_contract.CAPABILITY_GATE_TASKS and row["activation_count"]]
    if len(rows) != 19 or [row["task_name"] for row in rows] != list(order_contract.FULL_TASK_ORDER): errors.append("task_order")
    if [row["task_name"] for row in active] != [order_contract.TARGET_GATE_TASK]: errors.append("activation_specificity")
    if success_active: errors.append("success_silence")
    if target.get("final_values") != ["1", "8", "10", "7", "2"]: errors.append("target_values")
    if int(target.get("response_append_count") or 0) != 5: errors.append("target_response_append_count")
    if not any("observed integer sequence = [1, 8, 10, 7, 2]." in row["text"] for row in target.get("rendered_reads") or []): errors.append("target_exact_read")
    totals = {
        "episode_count": len(rows), "step_count": sum(len(row.get("steps") or []) for row in fixture.get("episodes") or []),
        "active_episode_count": len(active), "six_success_active_count": len(success_active),
        "target_response_append_count": int(target.get("response_append_count") or 0),
        "target_render_count": int(target.get("render_count") or 0),
        "max_serialized_audit_bytes": max((row["serialized_audit_bytes"] for row in rows), default=0),
    }
    payload = {
        "schema": "a1r15_eovr_offline_replay_v1", "status": "PASS" if not errors else "FAIL", "errors": errors,
        "generation_calls": 0, "mechanism_id": MECHANISM_ID, "experiment_id": EXPERIMENT_ID,
        "fixture_content_sha256": fixture.get("content_sha256"), "totals": totals, "target": target, "episodes": rows,
    }
    return {**payload, "content_sha256": digest_contract.content_sha256(payload)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, default=ROOT / "evidence/a1r15/A1R15_EOVR_REPLAY_FIXTURE.json")
    parser.add_argument("--output", type=Path, default=ROOT / "evidence/a1r15/A1R15_EOVR_OFFLINE_REPLAY_REPORT.json")
    args = parser.parse_args()
    result = replay(args.fixture)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "errors": result["errors"], "totals": result["totals"], "content_sha256": result["content_sha256"]}, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
