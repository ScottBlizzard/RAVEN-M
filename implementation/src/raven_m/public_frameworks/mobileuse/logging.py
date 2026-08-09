"""Append-only role-aware L0-L5 event logging."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from hashlib import sha256
import json
from pathlib import Path
import threading
import time
from typing import Any


LEVELS = frozenset({"L0", "L1", "L2", "L3", "L4", "L5"})


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)


class LayeredEventLog:
    """Write canonical JSONL events with a tamper-evident hash chain."""

    def __init__(self, path: Path, *, arm_id: str, episode_id: str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.arm_id = arm_id
        self.episode_id = episode_id
        self._lock = threading.Lock()
        self._sequence = 0
        self._previous_sha256 = "0" * 64

    def write(self, level: str, event: str, **fields: Any) -> dict[str, Any]:
        if level not in LEVELS:
            raise ValueError(f"Unknown diagnostic level: {level!r}")
        if not isinstance(event, str) or not event:
            raise ValueError("event must be a non-empty string")
        with self._lock:
            record = {
                "schema": "raven_m.mobileuse.layered_event.v1",
                "arm_id": self.arm_id,
                "episode_id": self.episode_id,
                "sequence": self._sequence,
                "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "level": level,
                "event": event,
                "previous_sha256": self._previous_sha256,
                **_jsonable(fields),
            }
            canonical = json.dumps(
                record, sort_keys=True, ensure_ascii=False, separators=(",", ":")
            )
            digest = sha256(canonical.encode("utf-8")).hexdigest()
            record["record_sha256"] = digest
            with self.path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
                handle.write("\n")
                handle.flush()
            self._previous_sha256 = digest
            self._sequence += 1
            return record

    @staticmethod
    def validate(path: Path) -> list[str]:
        errors: list[str] = []
        previous = "0" * 64
        for expected_sequence, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines()):
            record = json.loads(line)
            digest = record.pop("record_sha256", None)
            if record.get("sequence") != expected_sequence:
                errors.append(f"sequence:{expected_sequence}")
            if record.get("previous_sha256") != previous:
                errors.append(f"chain:{expected_sequence}")
            canonical = json.dumps(
                record, sort_keys=True, ensure_ascii=False, separators=(",", ":")
            )
            computed = sha256(canonical.encode("utf-8")).hexdigest()
            if digest != computed:
                errors.append(f"digest:{expected_sequence}")
            previous = digest or ""
        return errors
