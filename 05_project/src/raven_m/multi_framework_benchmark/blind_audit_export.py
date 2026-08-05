"""Deterministic arm blinding for manual destination/wrong-target audit."""

from __future__ import annotations

from hashlib import sha256
from typing import Any, Iterable


def blind_label(arm_id: str, salt: str) -> str:
    return "ARM-" + sha256(f"{salt}|{arm_id}".encode("utf-8")).hexdigest()[:10].upper()


def blind_rows(rows: Iterable[dict[str, Any]], salt: str) -> tuple[list[dict[str, Any]], dict[str, str]]:
    output: list[dict[str, Any]] = []
    mapping: dict[str, str] = {}
    for source in rows:
        arm_id = source["arm_id"]
        label = mapping.setdefault(arm_id, blind_label(arm_id, salt))
        row = dict(source)
        row["arm_id"] = label
        row.pop("system", None)
        row.pop("checkpoint_id", None)
        row.pop("source_repo", None)
        output.append(row)
    return output, mapping
