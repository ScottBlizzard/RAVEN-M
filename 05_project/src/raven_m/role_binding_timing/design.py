"""Blinding and frozen factorial cell construction."""

from __future__ import annotations

from hashlib import sha256
import hmac
from typing import Any


CONDITIONS = (
    ("early", "low"),
    ("late", "low"),
    ("early", "high"),
    ("late", "high"),
)


def blind_cell_id(
    *,
    base_family_id: str,
    fact_timing: str,
    role_ambiguity: str,
    secret: bytes,
) -> str:
    if not secret:
        raise ValueError("A nonempty external blinding secret is required.")
    message = f"{base_family_id}\0{fact_timing}\0{role_ambiguity}".encode()
    digest = hmac.new(secret, message, sha256).hexdigest()[:16]
    return f"RB-{digest}"


def build_blinded_cells(
    base_family_ids: list[str],
    *,
    secret: bytes,
) -> tuple[list[dict[str, str]], dict[str, dict[str, str]]]:
    public: list[dict[str, str]] = []
    private: dict[str, dict[str, str]] = {}
    for base_family_id in sorted(base_family_ids):
        for timing, ambiguity in CONDITIONS:
            cell_id = blind_cell_id(
                base_family_id=base_family_id,
                fact_timing=timing,
                role_ambiguity=ambiguity,
                secret=secret,
            )
            public.append(
                {"cell_id": cell_id, "base_family_id": base_family_id}
            )
            private[cell_id] = {
                "base_family_id": base_family_id,
                "fact_timing": timing,
                "role_ambiguity": ambiguity,
            }
    if len({item["cell_id"] for item in public}) != len(public):
        raise ValueError("Blinded condition IDs collided.")
    return public, private
