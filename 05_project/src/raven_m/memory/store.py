"""Append-only, replayable memory store with strict episode isolation."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any, Iterable

from raven_m.memory.models import ALL_STATUSES, MemoryItem


class EpisodeMemoryStore:
    def __init__(
        self,
        *,
        episode_id: str,
        event_path: Path | None = None,
    ) -> None:
        self.episode_id = episode_id
        self.event_path = event_path
        self.items: dict[str, MemoryItem] = {}
        self.events: list[dict[str, Any]] = []
        self._next_id = 1
        if event_path:
            event_path.parent.mkdir(parents=True, exist_ok=True)
            # The empty file is itself audit evidence that episode-local
            # memory was initialized even when no material state delta was
            # written before an early termination.
            event_path.touch(exist_ok=True)

    def _append(self, event: dict[str, Any], *, persist: bool = True) -> None:
        record = {
            "schema_version": "memory_event.v1",
            "event_index": len(self.events),
            "episode_id": self.episode_id,
            **event,
        }
        self.events.append(record)
        if persist and self.event_path:
            with self.event_path.open("a", encoding="utf-8") as stream:
                stream.write(
                    json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
                )

    def allocate_id(self, prefix: str = "m") -> str:
        while True:
            memory_id = f"{prefix}_{self._next_id:04d}"
            self._next_id += 1
            if memory_id not in self.items:
                return memory_id

    def write(self, item: MemoryItem) -> MemoryItem:
        item.validate(self.episode_id)
        if item.memory_id in self.items:
            raise ValueError(f"Duplicate memory ID: {item.memory_id}")
        stored = deepcopy(item)
        self.items[stored.memory_id] = stored
        self._append({"event": "write", "item": stored.to_dict()})
        return deepcopy(stored)

    def get(self, memory_id: str) -> MemoryItem:
        if memory_id not in self.items:
            raise KeyError(memory_id)
        item = self.items[memory_id]
        item.validate(self.episode_id)
        return deepcopy(item)

    def all_items(self) -> list[MemoryItem]:
        return [self.get(memory_id) for memory_id in sorted(self.items)]

    def active_items(self) -> list[MemoryItem]:
        return [
            item
            for item in self.all_items()
            if item.verification_status
            not in {"revoked", "superseded", "archived"}
        ]

    def transition(
        self,
        memory_id: str,
        *,
        status: str,
        step: int,
        reason: str,
        patch: dict[str, Any] | None = None,
    ) -> MemoryItem:
        if status not in ALL_STATUSES:
            raise ValueError(f"Unknown memory status: {status}")
        item = self.items[memory_id]
        before = item.verification_status
        item.verification_status = status
        if status in {"observed", "verified"}:
            item.last_confirmed_step = max(item.last_confirmed_step, step)
        for key, value in (patch or {}).items():
            if key in {"memory_id", "episode_id", "schema_version"}:
                raise ValueError(f"Immutable memory field: {key}")
            if not hasattr(item, key):
                raise ValueError(f"Unknown memory field: {key}")
            setattr(item, key, deepcopy(value))
        item.validate(self.episode_id)
        self._append(
            {
                "event": "transition",
                "memory_id": memory_id,
                "from_status": before,
                "to_status": status,
                "step": step,
                "reason": reason,
                "item": item.to_dict(),
            }
        )
        return deepcopy(item)

    def add_route(
        self,
        memory_id: str,
        *,
        step: int,
        route: str,
        score: float,
        reliability: float,
        used_by: str = "executor",
    ) -> None:
        item = self.items[memory_id]
        route_event = {
            "step": step,
            "route": route,
            "score": round(score, 8),
            "reliability": round(reliability, 8),
            "used_by": used_by,
        }
        item.routing_history.append(route_event)
        item.reliability_score = reliability
        self._append(
            {
                "event": "route",
                "memory_id": memory_id,
                **route_event,
            }
        )

    def mark_contradiction(
        self,
        first_id: str,
        second_id: str,
        *,
        step: int,
        reason: str = "conflicting_structured_value",
    ) -> None:
        if first_id == second_id:
            raise ValueError("A memory cannot contradict itself.")
        first = self.items[first_id]
        second = self.items[second_id]
        for item, other in ((first, second_id), (second, first_id)):
            related = item.relations.setdefault("contradicts", [])
            if other not in related:
                related.append(other)
                related.sort()
            item.verification_status = "contradicted"
        self._append(
            {
                "event": "contradiction",
                "memory_ids": sorted([first_id, second_id]),
                "step": step,
                "reason": reason,
                "items": [first.to_dict(), second.to_dict()],
            }
        )

    def supersede(
        self,
        older_id: str,
        newer_id: str,
        *,
        step: int,
        reason: str,
    ) -> None:
        older = self.items[older_id]
        newer = self.items[newer_id]
        older.verification_status = "superseded"
        older.relations["superseded_by"] = newer_id
        newer.relations["supersedes"] = older_id
        self._append(
            {
                "event": "supersede",
                "older_id": older_id,
                "newer_id": newer_id,
                "step": step,
                "reason": reason,
                "items": [older.to_dict(), newer.to_dict()],
            }
        )

    def find_conflicts(self, item: MemoryItem) -> list[MemoryItem]:
        conflicts = []
        for existing in self.active_items():
            same_key = (
                existing.content["subject"] == item.content["subject"]
                and existing.content["predicate"] == item.content["predicate"]
                and existing.validity.get("scope") == item.validity.get("scope")
            )
            compatible_page = (
                not existing.page_signature
                or not item.page_signature
                or existing.page_signature == item.page_signature
            )
            if (
                same_key
                and compatible_page
                and existing.content["object"] != item.content["object"]
            ):
                conflicts.append(existing)
        return conflicts

    def invalidate_page_local(
        self,
        *,
        current_page_signature: str | None,
        step: int,
    ) -> list[str]:
        invalidated = []
        for item in self.active_items():
            page_local = "same_page" in item.validity.get("preconditions", [])
            incompatible = (
                page_local
                and item.page_signature
                and current_page_signature
                and item.page_signature != current_page_signature
            )
            if incompatible:
                self.transition(
                    item.memory_id,
                    status="stale",
                    step=step,
                    reason="page_signature_changed",
                )
                invalidated.append(item.memory_id)
        return invalidated

    def verify_provenance(self, root: Path) -> list[str]:
        errors: list[str] = []
        from hashlib import sha256

        for item in self.all_items():
            for relative, expected in zip(
                item.source.screenshot_paths,
                item.source.screenshot_sha256,
                strict=True,
            ):
                path = root / relative
                if not path.is_file():
                    errors.append(f"{item.memory_id}:missing:{relative}")
                    continue
                actual = sha256(path.read_bytes()).hexdigest()
                if actual != expected:
                    errors.append(f"{item.memory_id}:hash_mismatch:{relative}")
        return errors

    @classmethod
    def replay(
        cls,
        *,
        episode_id: str,
        events: Iterable[dict[str, Any]],
    ) -> "EpisodeMemoryStore":
        store = cls(episode_id=episode_id)
        for expected_index, record in enumerate(events):
            if record["episode_id"] != episode_id:
                raise ValueError("Cross-episode event found during replay.")
            if record["event_index"] != expected_index:
                raise ValueError("Memory event indices are not contiguous.")
            event = record["event"]
            if event == "write":
                item = MemoryItem.from_dict(record["item"])
                item.validate(episode_id)
                store.items[item.memory_id] = item
            elif event in {"transition"}:
                item = MemoryItem.from_dict(record["item"])
                item.validate(episode_id)
                store.items[item.memory_id] = item
            elif event in {"contradiction", "supersede"}:
                for raw in record["items"]:
                    item = MemoryItem.from_dict(raw)
                    item.validate(episode_id)
                    store.items[item.memory_id] = item
            elif event == "route":
                item = store.items[record["memory_id"]]
                item.routing_history.append(
                    {
                        "step": record["step"],
                        "route": record["route"],
                        "score": record["score"],
                        "reliability": record["reliability"],
                        "used_by": record["used_by"],
                    }
                )
                item.reliability_score = record["reliability"]
            else:
                raise ValueError(f"Unknown memory event: {event}")
            store.events.append(deepcopy(record))
        numeric_ids = [
            int(memory_id.split("_")[-1])
            for memory_id in store.items
            if memory_id.split("_")[-1].isdigit()
        ]
        store._next_id = max(numeric_ids, default=0) + 1
        return store
