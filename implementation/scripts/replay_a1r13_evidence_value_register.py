#!/usr/bin/env python3
"""Zero-generation replay for A1-R13 EVR over the committed V4 fixture."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "implementation/src"))

from raven_m.official_qwen_mobile.a1r2_compact_verified_pending import (  # noqa: E402
    CompactVerifiedPendingMemory,
)
from raven_m.official_qwen_mobile.a1r13_evidence_value_register import (  # noqa: E402
    EXPERIMENT_ID,
    MECHANISM_ID,
    EvidenceValueRegisterMemory,
)
from raven_m.official_qwen_mobile.a1r3_contract import (  # noqa: E402
    CAPABILITY_GATE_TASKS,
    FULL_TASK_ORDER,
)


FIXTURE = ROOT / "evidence/a1r13/A1R13_EVR_REPLAY_FIXTURE.json"
DEFAULT_OUTPUT = ROOT / "evidence/a1r13/A1R13_EVR_OFFLINE_REPLAY_REPORT.json"


def canonical_sha256(value: Any) -> str:
    return sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def content_sha256(value: dict[str, Any]) -> str:
    payload = dict(value)
    payload.pop("content_sha256", None)
    return canonical_sha256(payload)


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def replay(fixture_path: Path = FIXTURE) -> dict[str, Any]:
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    if fixture.get("schema") != "a1r13_evr_replay_fixture_v1":
        errors.append("fixture_schema")
    if fixture.get("content_sha256") != content_sha256(fixture):
        errors.append("fixture_content_hash")
    episodes = list(fixture.get("episodes") or [])
    if [row.get("task_name") for row in episodes] != list(FULL_TASK_ORDER):
        errors.append("fixture_task_order")
    rows: list[dict[str, Any]] = []
    total_r2_chars = total_v5_chars = 0
    max_v5_render_chars = max_added_chars = 0
    for episode in episodes:
        base = CompactVerifiedPendingMemory(ttl_requests=8, max_render_chars=1100)
        memory = EvidenceValueRegisterMemory(
            ttl_requests=8,
            max_render_chars=1100,
            evidence_ttl_requests=8,
            max_evidence_values=6,
            min_values_to_render=2,
        )
        read_rows: list[dict[str, Any]] = []
        for step in episode.get("steps") or []:
            request_step = int(step["source_step"])
            base_text, base_audit = base.read(context={})
            v5_text, v5_audit = memory.read(context={})
            if v5_text != base_text and not v5_text.startswith(base_text + "\n"):
                errors.append(f"r2_prefix_drift:{episode['task_name']}:{request_step}")
            if base_text:
                base.commit_injection(str(base_audit["ticket_id"]), f"base-prompt-{request_step}")
            if v5_text:
                memory.commit_injection(str(v5_audit["ticket_id"]), f"v5-prompt-{request_step}")
            added = len(v5_text) - len(base_text)
            if added < 0:
                errors.append(f"negative_render_delta:{episode['task_name']}:{request_step}")
            total_r2_chars += len(base_text)
            total_v5_chars += len(v5_text)
            max_v5_render_chars = max(max_v5_render_chars, len(v5_text))
            max_added_chars = max(max_added_chars, added)
            evidence = v5_audit.get("evidence_value_register") or {}
            if evidence.get("rendered"):
                read_rows.append(
                    {
                        "request_step": request_step,
                        "value_count": evidence["rendered_value_count"],
                        "exact_text": evidence["exact_text"],
                        "exact_text_sha256": evidence["exact_text_sha256"],
                        "combined_render_sha256": v5_audit["rendered_sha256"],
                        "added_chars": added,
                    }
                )
            if step.get("write_observed"):
                kwargs = {
                    "source_step": request_step,
                    "action_summary": step["action_summary"],
                    "source_call_id": step["source_call_id"],
                    "source_response_sha256": step["source_response_sha256"],
                    "source_screenshot_sha256": step["source_screenshot_sha256"],
                }
                base.write(**kwargs)
                memory.write(**kwargs)
        audit = memory.audit_record()
        evidence_audit = audit["evidence_register"]
        audit_bytes = len(
            json.dumps(audit, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        )
        rows.append(
            {
                "task_name": episode["task_name"],
                "episode_id": episode["episode_id"],
                "historical_success": episode["success"],
                "activation_count": evidence_audit["counters"]["activation_count"],
                "append_count": evidence_audit["counters"]["append_count"],
                "render_count": evidence_audit["counters"]["render_count"],
                "final_values": [item["value"] for item in evidence_audit["values"]],
                "reads": read_rows,
                "serialized_audit_bytes": audit_bytes,
            }
        )

    active = [row for row in rows if row["activation_count"]]
    browser = next((row for row in rows if row["task_name"] == "BrowserMultiply"), None)
    if len(active) != 1 or active[0]["task_name"] != "BrowserMultiply":
        errors.append("exact_activation_set")
    if browser is None or browser["final_values"] != ["1", "8", "10", "7", "2"]:
        errors.append("browser_value_sequence")
    browser_read_18 = next(
        (row for row in (browser or {}).get("reads") or [] if row["request_step"] == 18),
        None,
    )
    if (
        browser_read_18 is None
        or browser_read_18.get("exact_text")
        != "TRANSIENT MODEL-AUTHORED EVIDENCE (unverified; current screenshot remains authoritative): observed integer sequence = [1, 8, 10, 7, 2]."
    ):
        errors.append("browser_pre_product_exact_render")
    success_rows = [row for row in rows if row["task_name"] in CAPABILITY_GATE_TASKS]
    if len(success_rows) != 6 or any(row["activation_count"] or row["render_count"] for row in success_rows):
        errors.append("six_success_silence")
    if max((row["serialized_audit_bytes"] for row in rows), default=0) > 131_072:
        errors.append("audit_capacity")
    report: dict[str, Any] = {
        "schema": "a1r13_evr_offline_replay_v1",
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "generation_calls": 0,
        "mechanism_id": MECHANISM_ID,
        "experiment_id": EXPERIMENT_ID,
        "source": {
            "fixture_file_sha256": file_sha256(fixture_path),
            "fixture_content_sha256": fixture.get("content_sha256"),
            "classification": fixture.get("source_classification"),
        },
        "totals": {
            "episode_count": len(rows),
            "step_count": sum(len(row.get("steps") or []) for row in episodes),
            "active_episode_count": len(active),
            "activation_count": sum(row["activation_count"] for row in rows),
            "append_count": sum(row["append_count"] for row in rows),
            "render_count": sum(row["render_count"] for row in rows),
            "six_success_active_count": sum(bool(row["activation_count"]) for row in success_rows),
            "r2_rendered_chars": total_r2_chars,
            "v5_rendered_chars": total_v5_chars,
            "added_rendered_chars": total_v5_chars - total_r2_chars,
            "max_v5_render_chars": max_v5_render_chars,
            "max_added_chars_per_read": max_added_chars,
            "max_serialized_audit_bytes": max((row["serialized_audit_bytes"] for row in rows), default=0),
        },
        "browser_target": {
            "task_name": "BrowserMultiply",
            "historical_reward": 0.0,
            "expected_model_authored_values": ["1", "8", "10", "7", "2"],
            "mathematical_product_for_audit_only_not_runtime_action": 1120,
            "pre_product_request_step": 18,
            "pre_product_exact_render": browser_read_18,
        },
        "episodes": rows,
        "claim_boundary": {
            "posthoc_development_trace": True,
            "held_out": False,
            "offline_pass_does_not_predict_live_success": True,
            "runtime_ocr_or_ui_tree": False,
            "runtime_arithmetic_or_action_override": False,
        },
    }
    report["content_sha256"] = content_sha256(report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=FIXTURE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = replay(args.fixture)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "output": str(args.output.resolve()),
        "status": report["status"],
        "errors": report["errors"],
        "totals": report["totals"],
        "content_sha256": report["content_sha256"],
    }, ensure_ascii=False, indent=2))
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
