from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "implementation" / "scripts" / "audit_p1_tcra_r2.py"
REPORT = ROOT / "evidence" / "p1_failure_recovery" / "P1_TCRA_R2_ZERO_GENERATION_AUDIT.json"


def _module():
    spec = importlib.util.spec_from_file_location("audit_p1_tcra_r2", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_checked_in_p1_audit_is_self_bound_and_invalid() -> None:
    module = _module()
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    content_sha = report.pop("content_sha256")
    assert content_sha == hashlib.sha256(module.canonical_bytes(report)).hexdigest()
    assert report["generation_calls"] == 0
    assert report["status"] == "PREFLIGHT_INVALID_NO_LIVE"
    assert report["summary"]["live_authorized"] is False
    assert report["errors"] == ["r2_success_call_gated_ere_nonzero"]


def test_calendar_is_the_only_success_hard_negative() -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    positives = [row for row in report["label_join"] if row["success"] and row["event_count"]]
    assert len(positives) == 1
    assert positives[0]["task_name"] == "SimpleCalendarAddOneEvent"
    assert [event["eligible_step"] for event in positives[0]["events"]] == [13, 14]
    assert report["summary"]["failed_task_event_count"] == 6
    assert len(report["summary"]["failed_task_families"]) == 4
