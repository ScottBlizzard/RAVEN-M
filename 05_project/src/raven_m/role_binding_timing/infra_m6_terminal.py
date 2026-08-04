"""Independent exactly-once terminal completion for INFRA-M6."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from raven_m.role_binding_timing.infra_m4_terminal_accounting import atomic_write_json, utc_now


def minimal_completion(*, run_id: str, status: str, first_edge: str | None) -> dict[str, Any]:
    return {
        "schema_version": "role_binding_timing.infra_m6.completion.v1",
        "terminal_mode": "minimal_fallback",
        "run_id": run_id,
        "status": status,
        "first_broken_edge": first_edge,
        "completed_at": utc_now(),
        "generation_calls": 0,
        "model_tokens": 0,
        "held_out_captures": 0,
        "development_contaminated": True,
        "held_out_eligible": False,
        "process_identity": {},
        "runtime": {},
        "burn_in": {"passed": False, "required_cycles": 24, "completed_cycles": 0, "passed_cycles": 0, "elapsed_seconds": 0.0, "records": []},
        "a11y": {"authorized": False, "passed": False, "settings": {"required": 3, "completed": 0, "passed": 0}, "grid": {"required": 12, "completed": 0, "passed": 0}},
        "cleanup": {},
        "log_seal": {"passed": False, "records": [], "temporary_root_removed": False},
        "protected_wip_unchanged": True,
        "claim_evidence": {
            "display_quorum_qualified": False,
            "process_identity_qualified": False,
            "exclusive_5038_registration": False,
            "burn_in_qualified": False,
            "a11y_tested": False,
            "a11y_qualified": False,
            "v0_3_preparation_authorized": False,
            "held_out_tested": False,
            "role_binding_hypothesis_tested": False,
        },
    }


def finalize_completion(
    *, output_root: Path, journal: Any, run_id: str, status: str,
    rich_completion: dict[str, Any] | None,
) -> dict[str, Any]:
    canonical = output_root / "qualification_completion.json"
    if canonical.exists():
        raise RuntimeError("DUPLICATE_TERMINAL_COMPLETION")
    journal.record(phase="terminal", event="start", status="RUNNING", details={"requested_status": status})
    first_edge = journal.first_edge()
    fallback = minimal_completion(run_id=run_id, status=status, first_edge=first_edge)
    if status != "PASS_12_OF_12_DEV" and not first_edge:
        first_edge = f"TERMINAL_STATUS_WITHOUT_EDGE:{status}"
        journal.record(phase="terminal", event="status_without_edge", status="FAIL", first_broken_edge=first_edge)
        fallback["first_broken_edge"] = first_edge
    atomic_write_json(canonical, fallback, replace=False)
    mode = "minimal_fallback"
    rich_error = None
    if rich_completion is not None:
        try:
            rich = dict(rich_completion)
            runtime = rich.get("runtime", {})
            framework = runtime.get("framework", {}) if isinstance(runtime, dict) else {}
            burn = rich.get("burn_in", {})
            claims = dict(rich.get("claim_evidence", {}))
            claims["display_quorum_qualified"] = bool(framework.get("passed") and burn.get("passed"))
            rich.update({
                "schema_version": "role_binding_timing.infra_m6.completion.v1",
                "terminal_mode": "rich",
                "run_id": run_id,
                "status": status,
                "first_broken_edge": journal.first_edge(),
                "completed_at": utc_now(),
                "generation_calls": 0,
                "model_tokens": 0,
                "held_out_captures": 0,
                "claim_evidence": claims,
            })
            atomic_write_json(canonical, rich, replace=True)
            mode = "rich"
        except Exception as exc:
            rich_error = {"type": type(exc).__name__, "message": str(exc)}
            journal.record(
                phase="terminal", event="rich_serialization", status="FAIL",
                first_broken_edge=f"TERMINAL_RICH_SERIALIZATION:{type(exc).__name__}:{exc}",
                details=rich_error,
            )
    journal.record(phase="terminal", event="end", status="PASS", details={"terminal_mode": mode, "rich_error": rich_error})
    final = json.loads(canonical.read_text(encoding="utf-8"))
    final.update({
        "terminal_mode": mode,
        "first_broken_edge": journal.first_edge(),
        "last_completed_phase": journal.last_completed_phase(),
        "journal_entry_count": len(journal.read_entries()),
        "journal_terminal_event_present": True,
    })
    if rich_error:
        final["rich_serialization_error"] = rich_error
    atomic_write_json(canonical, final, replace=True)
    atomic_write_json(output_root / "terminal_writer_receipt.json", {
        "schema_version": "role_binding_timing.infra_m6.terminal_receipt.v1",
        "terminal_mode": mode,
        "canonical_path": str(canonical),
        "canonical_sha256": sha256(canonical.read_bytes()).hexdigest(),
        "first_broken_edge": journal.first_edge(),
        "journal_entry_count": len(journal.read_entries()),
        "rich_error": rich_error,
    }, replace=False)
    return final
