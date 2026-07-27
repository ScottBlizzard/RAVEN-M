"""Auditable startup recovery helpers for protocol-v2.1 runners."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Callable


STARTUP_SCHEMA = "protocol_v2_startup_environment_audit.v1"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    temporary.replace(path)


def load_startup_audit(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "schema_version": STARTUP_SCHEMA,
            "events": [],
            "failure_count": 0,
            "recovery_success_count": 0,
            "last_status": None,
        }
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema_version") != STARTUP_SCHEMA:
        raise RuntimeError("Unknown startup environment audit schema.")
    if not isinstance(value.get("events"), list):
        raise RuntimeError("Startup environment audit events are invalid.")
    return value


def _error_record(
    *,
    phase: str,
    attempt: int,
    error: Exception,
) -> dict[str, Any]:
    return {
        "event": "failure",
        "phase": phase,
        "attempt": attempt,
        "code": "INFRA_ENVIRONMENT_CONSTRUCTION",
        "checked_at": utc_now(),
        "error": {
            "type": type(error).__name__,
            "message": str(error),
        },
    }


def initialize_androidworld_environment(
    *,
    audit_path: Path,
    load_fn: Callable[[], Any],
    recover_fn: Callable[[], Any],
) -> tuple[Any, dict[str, Any]]:
    """Load once, then cold-recover once; persist every startup outcome."""
    audit = load_startup_audit(audit_path)
    invocation = 1 + sum(
        event.get("event") == "invocation_started"
        for event in audit["events"]
    )
    audit["events"].append(
        {
            "event": "invocation_started",
            "invocation": invocation,
            "checked_at": utc_now(),
        }
    )
    write_json(audit_path, audit)
    try:
        env = load_fn()
    except Exception as load_error:
        audit["events"].append(
            _error_record(
                phase="initial_load",
                attempt=1,
                error=load_error,
            )
        )
        audit["failure_count"] = int(audit["failure_count"]) + 1
        audit["last_status"] = "recovering"
        write_json(audit_path, audit)
        try:
            env = recover_fn()
        except Exception as recovery_error:
            audit["events"].append(
                _error_record(
                    phase="cold_recovery",
                    attempt=2,
                    error=recovery_error,
                )
            )
            audit["failure_count"] = int(audit["failure_count"]) + 1
            audit["last_status"] = "failed"
            write_json(audit_path, audit)
            raise RuntimeError(
                "AndroidWorld startup failed twice; continuation is "
                f"forbidden. See {audit_path}."
            ) from recovery_error
        audit["events"].append(
            {
                "event": "success",
                "phase": "cold_recovery",
                "attempt": 2,
                "checked_at": utc_now(),
            }
        )
        audit["recovery_success_count"] = (
            int(audit["recovery_success_count"]) + 1
        )
        audit["last_status"] = "recovered"
        write_json(audit_path, audit)
        return env, audit
    audit["events"].append(
        {
            "event": "success",
            "phase": "initial_load",
            "attempt": 1,
            "checked_at": utc_now(),
        }
    )
    audit["last_status"] = "clean"
    write_json(audit_path, audit)
    return env, audit
