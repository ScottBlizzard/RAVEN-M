"""Minimal within-episode working memory for the A1 experiment.

A1 intentionally keeps the official Qwen controller, action protocol, model,
and current-screenshot-only observation unchanged.  The model writes a compact
``MEMORY[...]`` payload in its ordinary Action sentence.  This module stores a
bounded number of those payloads and renders them into the next user prompt.
It performs no model call, hidden-state read, or evaluator read.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import re
from typing import Any


_MEMORY_PAYLOAD = re.compile(r"^\s*MEMORY\[(?P<payload>.*?)\]\s*\|", re.DOTALL)


@dataclass(frozen=True)
class WorkingMemoryRecord:
    memory_id: str
    source_step: int
    payload: str
    source_call_id: str
    source_response_sha256: str
    source_screenshot_sha256: str

    def audit_record(self) -> dict[str, Any]:
        return asdict(self)


class ActionWorkingMemory:
    """Bounded raw working memory sourced only from model Action prose."""

    mechanism_id = "a1_action_working_memory_v1"

    def __init__(self, *, max_items: int = 6, max_chars: int = 3000) -> None:
        self.max_items = max(1, int(max_items))
        self.max_chars = max(1, int(max_chars))
        self._records: list[WorkingMemoryRecord] = []
        self.write_attempt_count = 0
        self.write_success_count = 0
        self.read_count = 0
        self.nonempty_read_count = 0

    @staticmethod
    def extract_payload(action_summary: str) -> str | None:
        match = _MEMORY_PAYLOAD.search(str(action_summary))
        if match is None:
            return None
        payload = " ".join(match.group("payload").split()).strip()
        return payload or None

    def write(
        self,
        *,
        source_step: int,
        action_summary: str,
        source_call_id: str,
        source_response_sha256: str,
        source_screenshot_sha256: str,
    ) -> dict[str, Any]:
        self.write_attempt_count += 1
        payload = self.extract_payload(action_summary)
        if payload is None:
            return {
                "written": False,
                "reason": "memory_prefix_missing_or_empty",
                "source_step": int(source_step),
            }

        # A1 is deliberately a raw, recency-bounded mechanism.  Exact duplicate
        # payloads are refreshed rather than consuming another slot.
        self._records = [item for item in self._records if item.payload != payload]
        memory_id = f"a1m_{int(source_step):03d}_{sha256(payload.encode('utf-8')).hexdigest()[:12]}"
        record = WorkingMemoryRecord(
            memory_id=memory_id,
            source_step=int(source_step),
            payload=payload,
            source_call_id=str(source_call_id),
            source_response_sha256=str(source_response_sha256),
            source_screenshot_sha256=str(source_screenshot_sha256),
        )
        self._records.append(record)
        self._records = self._records[-self.max_items :]
        self.write_success_count += 1
        return {"written": True, "record": record.audit_record()}

    def read(self, context: dict[str, Any] | None = None) -> tuple[str, dict[str, Any]]:
        del context
        self.read_count += 1
        selected: list[WorkingMemoryRecord] = []
        used_chars = 0
        for record in reversed(self._records):
            rendered = f"- {record.memory_id} (source step {record.source_step + 1}): {record.payload}"
            if selected and used_chars + len(rendered) > self.max_chars:
                continue
            if not selected and len(rendered) > self.max_chars:
                rendered = rendered[: self.max_chars]
                record = WorkingMemoryRecord(
                    memory_id=record.memory_id,
                    source_step=record.source_step,
                    payload=rendered.split(": ", 1)[-1],
                    source_call_id=record.source_call_id,
                    source_response_sha256=record.source_response_sha256,
                    source_screenshot_sha256=record.source_screenshot_sha256,
                )
            selected.append(record)
            used_chars += len(rendered)
        selected.reverse()

        if not selected:
            rendered_block = ""
        else:
            lines = [
                "Explicit working memory from your own earlier Action records:",
                *[
                    f"- {item.memory_id} (source step {item.source_step + 1}): {item.payload}"
                    for item in selected
                ],
                "The current screenshot overrides any stale or conflicting memory.",
            ]
            rendered_block = "\n".join(lines)
            self.nonempty_read_count += 1

        audit = {
            "mechanism_id": self.mechanism_id,
            "retrieved_ids": [item.memory_id for item in selected],
            "retrieved_count": len(selected),
            "rendered_chars": len(rendered_block),
            "rendered_sha256": sha256(rendered_block.encode("utf-8")).hexdigest(),
            "nonempty": bool(rendered_block),
        }
        return rendered_block, audit

    def audit_record(self) -> dict[str, Any]:
        return {
            "mechanism_id": self.mechanism_id,
            "max_items": self.max_items,
            "max_chars": self.max_chars,
            "write_attempt_count": self.write_attempt_count,
            "write_success_count": self.write_success_count,
            "read_count": self.read_count,
            "nonempty_read_count": self.nonempty_read_count,
            "active": self.write_success_count > 0 and self.nonempty_read_count > 0,
            "records": [item.audit_record() for item in self._records],
        }


def append_working_memory(base_prompt: str, rendered_memory: str) -> str:
    """Append A1 memory without changing the official baseline template."""
    if not rendered_memory:
        return base_prompt
    return f"{base_prompt}\n{rendered_memory}\n"
