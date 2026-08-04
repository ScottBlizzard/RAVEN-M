"""Frozen bytes-to-text contract for B2.9 command preflight output."""

from __future__ import annotations

from hashlib import sha256
from typing import Any


ENCODING = "utf-8"
ERROR_POLICY = "strict"


def _sha256(value: bytes) -> str:
    return sha256(value).hexdigest()


def decode_command_stream(value: bytes, *, stream_name: str) -> dict[str, Any]:
    """Decode exactly once; reject type ambiguity and malformed UTF-8."""
    if type(value) is not bytes:  # subclasses are rejected to avoid hidden text-like behavior
        raise TypeError(f"COMMAND_STREAM_TYPE:{stream_name}:{type(value).__name__}")
    try:
        text = value.decode(ENCODING, errors=ERROR_POLICY)
    except UnicodeDecodeError as exc:
        raise ValueError(
            f"COMMAND_STREAM_DECODE:{stream_name}:{exc.start}:{exc.end}:{exc.reason}"
        ) from exc
    if "\x00" in text:
        raise ValueError(f"COMMAND_STREAM_NUL:{stream_name}")
    normalized = " ".join(text.split())
    return {
        "stream_name": stream_name,
        "encoding": ENCODING,
        "error_policy": ERROR_POLICY,
        "raw_bytes": len(value),
        "raw_sha256": _sha256(value),
        "decoded_text": text,
        "whitespace_normalized": normalized,
        "casefolded": normalized.casefold(),
    }


def qualify_framework_service_check(
    *,
    expected_service: str,
    returncode: int | None,
    timed_out: bool,
    stdout: bytes,
    stderr: bytes,
) -> dict[str, Any]:
    """Accept only the generic, exact `Service <name>: found` grammar."""
    issues: list[str] = []
    stdout_record = None
    stderr_record = None
    try:
        stdout_record = decode_command_stream(stdout, stream_name="stdout")
    except (TypeError, ValueError) as exc:
        issues.append(str(exc))
    try:
        stderr_record = decode_command_stream(stderr, stream_name="stderr")
    except (TypeError, ValueError) as exc:
        issues.append(str(exc))
    if timed_out:
        issues.append("SERVICE_CHECK_TIMEOUT")
    if returncode != 0:
        issues.append(f"SERVICE_CHECK_RETURNCODE:{returncode}")
    if stderr_record is not None and stderr_record["whitespace_normalized"]:
        issues.append("SERVICE_CHECK_STDERR_NONEMPTY")
    expected = f"service {expected_service}: found".casefold()
    if stdout_record is None or stdout_record["casefolded"] != expected:
        issues.append("SERVICE_CHECK_STDOUT_GRAMMAR")
    return {
        "passed": not issues,
        "issues": issues,
        "expected_service": expected_service,
        "expected_casefolded": expected,
        "stdout": stdout_record,
        "stderr": stderr_record,
    }
