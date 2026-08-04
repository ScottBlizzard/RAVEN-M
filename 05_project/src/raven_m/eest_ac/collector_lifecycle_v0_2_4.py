"""General collector-lifecycle invariants for EEST-AC v0.2.4."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import time
from typing import Any, Callable
from uuid import uuid4

from jsonschema import Draft202012Validator


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONTRACT_PATH = PROJECT_ROOT / "contracts/eest_ac_collector_lifecycle.v0_2_4.json"
DEFAULT_SCHEMA_PATH = PROJECT_ROOT / "schemas/eest_ac_collector_completion.v0_2_4.schema.json"


class CollectorLifecycleError(RuntimeError):
    """Fail-closed lifecycle error with a stable code/layer."""

    def __init__(self, code: str, message: str, layer: str):
        super().__init__(message)
        self.code = code
        self.layer = layer

    def record(self) -> dict[str, str]:
        return {"code": self.code, "message": str(self), "layer": self.layer}


class DuplicateTerminalRecordError(CollectorLifecycleError):
    def __init__(self, message: str = "Terminal completion record already exists."):
        super().__init__("DUPLICATE_TERMINAL_RECORD", message, "completion")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def load_contract(path: Path = DEFAULT_CONTRACT_PATH) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema_version") != "eest_ac_collector_lifecycle.v0_2_4":
        raise CollectorLifecycleError("CONTRACT_VERSION", "Unexpected lifecycle contract version.", "contract")
    if value["generation_calls"] != 0 or value["held_out_traces"] != 0 or value["oracle_efficacy_evaluations"] != 0:
        raise CollectorLifecycleError("CONTRACT_SCOPE", "Zero-call/zero-held-out scope changed.", "contract")
    readiness = value["readiness"]
    if (readiness["max_attempts"], readiness["delay_seconds"], readiness["stable_consecutive_observations"]) != (5, 1.0, 2):
        raise CollectorLifecycleError("READINESS_POLICY_DRIFT", "Frozen readiness policy changed.", "contract")
    cleanup = value["cleanup"]
    if cleanup["adb_server_port"] != 5038 or cleanup["fallback_to_5037"] is not False:
        raise CollectorLifecycleError("ADB_ISOLATION_DRIFT", "Explicit ADB isolation changed.", "contract")
    return value


def build_completion_schema(contract: dict[str, Any] | None = None) -> dict[str, Any]:
    return (contract or load_contract())["completion_schema"]


def validate_completion(record: dict[str, Any], schema_path: Path = DEFAULT_SCHEMA_PATH) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(record), key=lambda item: list(item.absolute_path))
    if errors:
        path = ".".join(str(part) for part in errors[0].absolute_path) or "$"
        raise CollectorLifecycleError("COMPLETION_SCHEMA_INVALID", f"{path}: {errors[0].message}", "completion")


@dataclass(frozen=True)
class ReadinessResult:
    qualified: bool
    snapshot: Any | None
    audit: dict[str, Any]


def _observation(snapshot: Any) -> dict[str, Any]:
    if isinstance(snapshot, dict) and "oracle_observation" in snapshot:
        return snapshot["oracle_observation"]
    return getattr(snapshot, "oracle_observation", snapshot)


def readiness_errors(observation: dict[str, Any], required_fields: list[str]) -> list[str]:
    errors: list[str] = []
    if observation.get("a11y_available") is not True:
        errors.append("a11y_available")
    for field in required_fields:
        value = observation.get(field)
        if value is None or value == "" or value == []:
            errors.append(field)
    return sorted(set(errors))


def acquire_pre_action_readiness(
    capture: Callable[[int], Any],
    *,
    contract: dict[str, Any] | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> ReadinessResult:
    """Acquire two consecutive valid, semantically stable pre observations."""
    contract = contract or load_contract()
    policy = contract["readiness"]
    attempts: list[dict[str, Any]] = []
    previous_valid: tuple[Any, dict[str, Any]] | None = None
    stable_fields = policy["stable_fields"]
    for index in range(1, int(policy["max_attempts"]) + 1):
        snapshot = capture(index)
        observation = _observation(snapshot)
        errors = readiness_errors(observation, policy["required_nonempty_fields"])
        stable_with_previous = bool(
            not errors
            and previous_valid is not None
            and all(previous_valid[1].get(field) == observation.get(field) for field in stable_fields)
        )
        attempts.append({
            "attempt": index,
            "qualified_fields": not errors,
            "readiness_errors": errors,
            "stable_with_previous": stable_with_previous,
            "a11y_sha256": observation.get("a11y_sha256"),
            "page_content_sha256": observation.get("page_content_sha256"),
            "package_names": observation.get("package_names", []),
            "activity": observation.get("activity"),
            "route_signature": observation.get("route_signature"),
        })
        if stable_with_previous:
            return ReadinessResult(True, snapshot, {
                "qualified": True,
                "attempt_count": index,
                "max_attempts": policy["max_attempts"],
                "delay_seconds": policy["delay_seconds"],
                "stable_consecutive_required": policy["stable_consecutive_observations"],
                "attempts": attempts,
            })
        previous_valid = (snapshot, observation) if not errors else None
        if index < int(policy["max_attempts"]):
            sleep_fn(float(policy["delay_seconds"]))
    return ReadinessResult(False, None, {
        "qualified": False,
        "attempt_count": len(attempts),
        "max_attempts": policy["max_attempts"],
        "delay_seconds": policy["delay_seconds"],
        "stable_consecutive_required": policy["stable_consecutive_observations"],
        "attempts": attempts,
    })


CommandRunner = Callable[[list[str], int], subprocess.CompletedProcess[str]]


def _run_command(command: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False, timeout=timeout)


def _command_record(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    return {"returncode": result.returncode, "stdout": result.stdout.strip(), "stderr": result.stderr.strip()}


def _listener_present(stdout: str, listener: str) -> bool:
    return any(listener in line.split() for line in stdout.splitlines())


def cleanup_reverse_listener(
    *,
    adb_path: str,
    port: int,
    serial: str,
    listener: str,
    runner: CommandRunner = _run_command,
) -> dict[str, Any]:
    """Remove an owned reverse listener idempotently and verify absence."""
    base = [adb_path, "-P", str(port), "-s", serial, "reverse"]
    try:
        before = runner([*base, "--list"], 10)
    except BaseException as exc:
        return {
            "listener": listener,
            "before": None,
            "remove": None,
            "after": None,
            "status": "failed",
            "verified_absent": False,
            "error": "reverse_list_before_exception",
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
        }
    audit: dict[str, Any] = {"listener": listener, "before": _command_record(before), "remove": None, "after": None}
    if before.returncode:
        audit.update({"status": "failed", "verified_absent": False, "error": "reverse_list_before_failed"})
        return audit
    present = _listener_present(before.stdout, listener)
    if not present:
        try:
            after = runner([*base, "--list"], 10)
        except BaseException as exc:
            audit.update({
                "status": "failed", "verified_absent": False,
                "error": "reverse_absence_verification_exception",
                "exception_type": type(exc).__name__, "exception_message": str(exc),
            })
            return audit
        audit["after"] = _command_record(after)
        verified = after.returncode == 0 and not _listener_present(after.stdout, listener)
        audit.update({"status": "already_absent" if verified else "failed", "verified_absent": verified})
        if not verified:
            audit["error"] = "reverse_absence_verification_failed"
        return audit
    try:
        remove = runner([*base, "--remove", listener], 10)
    except BaseException as exc:
        audit.update({
            "status": "failed", "verified_absent": False,
            "error": "reverse_remove_exception",
            "exception_type": type(exc).__name__, "exception_message": str(exc),
        })
        return audit
    audit["remove"] = _command_record(remove)
    listener_not_found = remove.returncode != 0 and "listener" in remove.stderr.casefold() and "not found" in remove.stderr.casefold()
    if remove.returncode != 0 and not listener_not_found:
        audit.update({"status": "failed", "verified_absent": False, "error": "reverse_remove_failed"})
        return audit
    try:
        after = runner([*base, "--list"], 10)
    except BaseException as exc:
        audit.update({
            "status": "failed", "verified_absent": False,
            "error": "reverse_verification_exception",
            "exception_type": type(exc).__name__, "exception_message": str(exc),
        })
        return audit
    audit["after"] = _command_record(after)
    verified = after.returncode == 0 and not _listener_present(after.stdout, listener)
    if not verified:
        audit.update({"status": "failed", "verified_absent": False, "error": "reverse_residue"})
    else:
        audit.update({"status": "already_absent_after_race" if listener_not_found else "removed", "verified_absent": True})
    return audit


def audit_owned_helpers(pids: list[int], process_alive: Callable[[int], bool]) -> dict[str, Any]:
    residues = sorted(pid for pid in pids if process_alive(pid))
    return {"owned_pids": sorted(pids), "residual_pids": residues, "passed": not residues}


def preserve_primary_error(
    primary_error: dict[str, Any] | None,
    cleanup_errors: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Keep the collection error authoritative while retaining cleanup evidence."""
    return primary_error, list(cleanup_errors)


class AtomicCompletionWriter:
    """Publish exactly one schema-valid completion record without overwrite."""

    def __init__(self, path: Path, schema_path: Path = DEFAULT_SCHEMA_PATH):
        self.path = path
        self.schema_path = schema_path
        self._written = False

    def write_once(self, record: dict[str, Any]) -> str:
        if self._written or self.path.exists():
            raise DuplicateTerminalRecordError()
        validate_completion(record, self.schema_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_name(f".{self.path.name}.{os.getpid()}.{uuid4().hex}.tmp")
        payload = json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        try:
            with temp.open("x", encoding="utf-8", newline="\n") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.link(temp, self.path)
            except FileExistsError as exc:
                raise DuplicateTerminalRecordError() from exc
        finally:
            temp.unlink(missing_ok=True)
        self._written = True
        return file_sha256(self.path)
