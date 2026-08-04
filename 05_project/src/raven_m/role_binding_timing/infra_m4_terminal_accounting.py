"""Locally owned terminal accounting, journal, and fault-test harness for INFRA-M4."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
from typing import Any, Iterable
from uuid import uuid4

from raven_m.role_binding_timing.infra_m3_log_lifecycle import seal_live_logs


PHASES = ("launch", "boot", "framework", "burn_in", "settings", "grid", "cleanup", "seal")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_write_bytes(path: Path, payload: bytes, *, replace: bool = True) -> dict[str, Any]:
    """Write bytes durably through a same-directory temporary file and atomic replace."""
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not replace and path.exists():
        raise FileExistsError(path)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.partial")
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if not replace and path.exists():
            raise FileExistsError(path)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()
    return {"path": str(path), "bytes": len(payload), "sha256": sha256(payload).hexdigest()}


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def atomic_write_json(path: Path, value: Any, *, replace: bool = True) -> dict[str, Any]:
    return atomic_write_bytes(path, json_bytes(value), replace=replace)


def safe_jsonable(value: Any, *, depth: int = 0) -> Any:
    """Losslessly preserve normal JSON data and safely summarize hostile rich values."""
    if depth > 12:
        return {"safe_type": type(value).__name__, "reason": "DEPTH_LIMIT"}
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, bytes):
        return {"safe_type": "bytes", "bytes": len(value), "sha256": sha256(value).hexdigest()}
    if isinstance(value, BaseException):
        return {"safe_type": "exception", "type": type(value).__name__, "message": str(value)}
    if isinstance(value, dict):
        return {str(key): safe_jsonable(item, depth=depth + 1) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [safe_jsonable(item, depth=depth + 1) for item in value]
    try:
        representation = repr(value)
    except Exception:
        representation = "<repr failed>"
    return {"safe_type": type(value).__name__, "repr": representation[:512]}


class PhaseJournal:
    """Append-only phase entries plus a write-once first-broken-edge checkpoint."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.entries = self.root / "entries"
        self.ndjson = self.root / "journal.ndjson"
        self.first_edge_path = self.root / "first_broken_edge.json"
        self.entries.mkdir(parents=True, exist_ok=True)
        existing = sorted(self.entries.glob("*.json"))
        self.sequence = len(existing)

    def _entry_path(self, sequence: int) -> Path:
        return self.entries / f"{sequence:06d}.json"

    def record(
        self,
        *,
        phase: str,
        event: str,
        status: str,
        first_broken_edge: str | None = None,
        details: Any = None,
    ) -> dict[str, Any]:
        self.sequence += 1
        entry = {
            "schema_version": "role_binding_timing.infra_m4.phase_entry.v1",
            "sequence": self.sequence,
            "recorded_at": utc_now(),
            "phase": phase,
            "event": event,
            "status": status,
            "first_broken_edge": first_broken_edge,
            "details": safe_jsonable(details),
        }
        payload = json_bytes(entry)
        atomic_write_bytes(self._entry_path(self.sequence), payload, replace=False)
        self.ndjson.parent.mkdir(parents=True, exist_ok=True)
        with self.ndjson.open("ab") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False, sort_keys=True).encode("utf-8") + b"\n")
            handle.flush()
            os.fsync(handle.fileno())
        if first_broken_edge:
            self.set_first_edge(first_broken_edge, phase=phase, sequence=self.sequence)
        return entry

    def set_first_edge(self, edge: str, *, phase: str, sequence: int | None = None) -> dict[str, Any]:
        if self.first_edge_path.exists():
            return json.loads(self.first_edge_path.read_text(encoding="utf-8"))
        record = {
            "schema_version": "role_binding_timing.infra_m4.first_edge.v1",
            "first_broken_edge": edge,
            "phase": phase,
            "sequence": sequence,
            "recorded_at": utc_now(),
        }
        atomic_write_json(self.first_edge_path, record, replace=False)
        return record

    def first_edge(self) -> str | None:
        if not self.first_edge_path.exists():
            return None
        return json.loads(self.first_edge_path.read_text(encoding="utf-8"))["first_broken_edge"]

    def read_entries(self) -> list[dict[str, Any]]:
        return [json.loads(path.read_text(encoding="utf-8")) for path in sorted(self.entries.glob("*.json"))]

    def last_completed_phase(self) -> str | None:
        passed = [entry["phase"] for entry in self.read_entries() if entry["event"] == "end" and entry["status"] == "PASS"]
        return passed[-1] if passed else None


def minimal_completion(
    *, journal: PhaseJournal, status: str, run_id: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    entries = journal.read_entries()
    first_edge = journal.first_edge()
    value: dict[str, Any] = {
        "schema_version": "role_binding_timing.infra_m4.completion.v1",
        "terminal_mode": "minimal_fallback",
        "status": status,
        "run_id": run_id,
        "completed_at": utc_now(),
        "first_broken_edge": first_edge,
        "last_completed_phase": journal.last_completed_phase(),
        "journal_entry_count": len(entries),
        "journal_terminal_event_present": any(entry["phase"] == "terminal" for entry in entries),
        "generation_calls": 0,
        "model_tokens": 0,
        "held_out_captures": 0,
        "development_contaminated": True,
        "held_out_eligible": False,
        "runtime": {},
        "burn_in": {"passed": False, "required_cycles": 24, "completed_cycles": 0, "passed_cycles": 0, "elapsed_seconds": 0.0, "records": []},
        "a11y": {"authorized": False, "settings": {"required": 3, "completed": 0, "passed": 0}, "grid": {"required": 12, "completed": 0, "passed": 0}},
        "cleanup": {},
        "log_seal": {"passed": False, "records": [], "temporary_root_removed": False},
        "protected_wip_unchanged": True,
        "claim_evidence": {
            "exclusive_5038_registration": False,
            "burn_in_qualified": False,
            "a11y_tested": False,
            "a11y_qualified": False,
            "v0_3_preparation_authorized": False,
            "held_out_tested": False,
            "role_binding_hypothesis_tested": False,
        },
    }
    if extra:
        value["fallback_context"] = safe_jsonable(extra)
    return value


def finalize_completion(
    *,
    output_root: Path,
    journal: PhaseJournal,
    status: str,
    run_id: str,
    rich_completion: Any | None,
    inject_rich_serialization_failure: bool = False,
) -> dict[str, Any]:
    """Always leave one canonical completion, falling back if rich JSON fails."""
    canonical = output_root / "qualification_completion.json"
    receipt = output_root / "terminal_writer_receipt.json"
    if canonical.exists():
        raise RuntimeError("DUPLICATE_TERMINAL_COMPLETION")
    journal.record(phase="terminal", event="start", status="RUNNING", details={"requested_status": status})
    fallback = minimal_completion(journal=journal, status=status, run_id=run_id)
    if status != "PASS_12_OF_12_DEV" and fallback["first_broken_edge"] is None:
        fallback["first_broken_edge"] = f"TERMINAL_STATUS_WITHOUT_EDGE:{status}"
    atomic_write_json(canonical, fallback, replace=False)
    rich_error = None
    mode = "minimal_fallback"
    if rich_completion is not None:
        try:
            if inject_rich_serialization_failure:
                raise TypeError("INJECTED_RICH_JSON_SERIALIZATION_FAILURE")
            enriched = dict(rich_completion)
            enriched.update(
                {
                    "schema_version": "role_binding_timing.infra_m4.completion.v1",
                    "terminal_mode": "rich",
                    "status": status,
                    "run_id": run_id,
                    "completed_at": utc_now(),
                    "first_broken_edge": journal.first_edge(),
                    "last_completed_phase": journal.last_completed_phase(),
                    "journal_entry_count": len(journal.read_entries()),
                    "generation_calls": 0,
                    "model_tokens": 0,
                    "held_out_captures": 0,
                }
            )
            atomic_write_bytes(canonical, json_bytes(enriched), replace=True)
            mode = "rich"
        except Exception as exc:
            rich_error = {"type": type(exc).__name__, "message": str(exc)}
            edge = f"TERMINAL_RICH_SERIALIZATION:{type(exc).__name__}:{exc}"
            journal.record(
                phase="terminal", event="rich_serialization", status="FAIL",
                first_broken_edge=edge, details=rich_error,
            )
    if status != "PASS_12_OF_12_DEV" and journal.first_edge() is None:
        journal.record(
            phase="terminal", event="status_without_edge", status="FAIL",
            first_broken_edge=f"TERMINAL_STATUS_WITHOUT_EDGE:{status}",
        )
    journal.record(
        phase="terminal", event="end", status="PASS",
        details={"terminal_mode": mode, "rich_error": rich_error},
    )
    final = json.loads(canonical.read_text(encoding="utf-8"))
    final["first_broken_edge"] = journal.first_edge()
    final["journal_entry_count"] = len(journal.read_entries())
    final["journal_terminal_event_present"] = True
    final["terminal_mode"] = mode
    if rich_error is not None:
        final["rich_serialization_error"] = rich_error
    atomic_write_json(canonical, final, replace=True)
    atomic_write_json(
        receipt,
        {
            "schema_version": "role_binding_timing.infra_m4.terminal_receipt.v1",
            "terminal_mode": mode,
            "canonical_path": str(canonical),
            "canonical_sha256": sha256(canonical.read_bytes()).hexdigest(),
            "first_broken_edge": journal.first_edge(),
            "journal_entry_count": len(journal.read_entries()),
            "rich_error": rich_error,
        },
        replace=False,
    )
    return final


class InjectedFailure(RuntimeError):
    pass


def run_fault_injected_lifecycle(
    *,
    root: Path,
    inject_phase: str,
    repository_root: Path,
    rich_serialization_failure: bool = False,
) -> dict[str, Any]:
    """Model-free harness proving evidence survival across every frozen failure edge."""
    output = repository_root / "result"
    output.mkdir(parents=True)
    journal = PhaseJournal(output / "phase_journal")
    live = root / "external_live"
    live.mkdir()
    stdout = live / "emulator.stdout.bin"
    stderr = live / "emulator.stderr.bin"
    stdout_handle = stdout.open("xb")
    stderr_handle = stderr.open("xb")
    stdout_handle.write(b"dev stdout")
    stderr_handle.write(b"")
    canary = repository_root / "old_artifact.bin"
    canary.parent.mkdir(parents=True, exist_ok=True)
    canary.write_bytes(b"immutable-old-artifact")
    canary_before = sha256(canary.read_bytes()).hexdigest()
    first_edge = None
    owner_running = True
    sealed_records: list[dict[str, Any]] = []
    temp_removed = False
    cleanup_issue = None
    try:
        for phase in PHASES[:-2]:
            journal.record(phase=phase, event="start", status="RUNNING")
            if inject_phase == "missing_helper" and phase == "framework":
                raise AttributeError("MISSING_HELPER_ATTRIBUTE_ERROR")
            if inject_phase == phase:
                if phase == "boot" and inject_phase == "boot":
                    raise InjectedFailure("PROCESS_TIMEOUT:BOOT")
                raise InjectedFailure(f"INJECTED:{phase.upper()}")
            journal.record(phase=phase, event="end", status="PASS")
    except Exception as exc:
        first_edge = str(exc)
        phase = next((item for item in PHASES if item.upper() in first_edge), "framework" if isinstance(exc, AttributeError) else "unknown")
        journal.record(phase=phase, event="end", status="FAIL", first_broken_edge=first_edge, details=exc)
    finally:
        journal.record(phase="cleanup", event="start", status="RUNNING")
        try:
            if inject_phase == "cleanup":
                raise InjectedFailure("INJECTED:CLEANUP")
        except Exception as exc:
            cleanup_issue = str(exc)
            if first_edge is None:
                first_edge = cleanup_issue
                journal.record(phase="cleanup", event="end", status="FAIL", first_broken_edge=first_edge, details=exc)
            else:
                journal.record(phase="cleanup", event="end", status="SECONDARY_FAIL", details=exc)
        finally:
            stdout_handle.close()
            stderr_handle.close()
            owner_running = False
            if cleanup_issue is None:
                journal.record(phase="cleanup", event="end", status="PASS")

        journal.record(phase="seal", event="start", status="RUNNING")
        try:
            if inject_phase == "seal":
                raise InjectedFailure("INJECTED:SEAL")
            sealed_records = seal_live_logs(
                live_root=live, result_root=output / "sealed_logs",
                names=("emulator.stdout.bin", "emulator.stderr.bin"),
                repository_root=repository_root, forbidden_roots=[repository_root],
                required_temp_parent=root, owners_gone=not owner_running,
                parent_handles_closed=True,
            )
            shutil.rmtree(live)
            temp_removed = True
            journal.record(phase="seal", event="end", status="PASS")
        except Exception as exc:
            if first_edge is None:
                first_edge = str(exc)
                journal.record(phase="seal", event="end", status="FAIL", first_broken_edge=first_edge, details=exc)
            else:
                journal.record(phase="seal", event="end", status="SECONDARY_FAIL", details=exc)
            if (output / "sealed_logs").exists():
                shutil.rmtree(output / "sealed_logs")
            sealed_records = seal_live_logs(
                live_root=live, result_root=output / "sealed_logs",
                names=("emulator.stdout.bin", "emulator.stderr.bin"),
                repository_root=repository_root, forbidden_roots=[repository_root],
                required_temp_parent=root, owners_gone=True, parent_handles_closed=True,
            )
            shutil.rmtree(live)
            temp_removed = True
            journal.record(phase="seal_fallback", event="end", status="PASS")

    rich = {
        "runtime": {},
        "burn_in": {"passed": False, "required_cycles": 24, "completed_cycles": 0, "passed_cycles": 0, "elapsed_seconds": 0.0, "records": []},
        "a11y": {"authorized": False, "settings": {"required": 3, "completed": 0, "passed": 0}, "grid": {"required": 12, "completed": 0, "passed": 0}},
        "cleanup": {"passed": cleanup_issue is None, "issue": cleanup_issue},
        "log_seal": {"passed": True, "records": sealed_records, "temporary_root_removed": temp_removed},
        "protected_wip_unchanged": True,
        "claim_evidence": {"exclusive_5038_registration": False, "burn_in_qualified": False, "a11y_tested": False, "a11y_qualified": False, "v0_3_preparation_authorized": False, "held_out_tested": False, "role_binding_hypothesis_tested": False},
    }
    completion = finalize_completion(
        output_root=output, journal=journal, status="FAULT_INJECTED",
        run_id=f"fault-{inject_phase}", rich_completion=rich,
        inject_rich_serialization_failure=rich_serialization_failure,
    )
    return {
        "completion": completion,
        "journal": journal.read_entries(),
        "first_edge": journal.first_edge(),
        "sealed_records": sealed_records,
        "temp_removed": temp_removed,
        "canary_unchanged": sha256(canary.read_bytes()).hexdigest() == canary_before,
        "output": output,
    }
