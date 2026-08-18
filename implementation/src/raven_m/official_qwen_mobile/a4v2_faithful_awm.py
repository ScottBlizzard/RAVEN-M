"""Faithful offline Agent Workflow Memory adapter for AndroidWorld.

Unlike the historical A4 deterministic single-trace port, this module consumes
only a pre-induced, frozen bank whose entries summarize common subroutines from
multiple independently successful non-Hard donor episodes.  Scored execution
is read-only and adds no model call or action intervention.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import re
from typing import Any


SCHEMA = "a4v2.faithful_offline_awm_bank.v1"
MECHANISM_ID = "a4v2_faithful_offline_awm_memory_v1"
UPSTREAM_COMMIT = "8c0ff8cd11d648c8fceb99e4e42f37e3b75381b1"


def json_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


def _compact(value: Any) -> str:
    return " ".join(str(value).split()).strip()


@dataclass(frozen=True)
class RouteSignature:
    app: str
    operation: str
    object_family: str = "*"
    constraint_family: str = "*"


@dataclass(frozen=True)
class InducedWorkflow:
    workflow_id: str
    route: RouteSignature
    donor_ids: tuple[str, ...]
    donor_task_classes: tuple[str, ...]
    donor_seeds: tuple[int, ...]
    text: str
    induction_response_sha256: str


def classify_goal(goal: str) -> RouteSignature | None:
    """Map the seven preregistered task families to exact retrieval routes."""
    value = _compact(goal).lower()
    if "task.html" in value and ("product" in value or "multiply" in value):
        return RouteSignature("browser", "open_local_task", "interactive_html", "*")
    if "expense" in value and any(term in value for term in ("delete", "remove")):
        return RouteSignature("pro_expense", "delete", "expense_record", "multiple")
    if "retro" in value and "playlist" in value and any(
        term in value for term in ("create", "save", "export")
    ):
        return RouteSignature("retro_music", "create_playlist", "playlist", "ordered_items")
    if "calendar" in value and any(term in value for term in ("create", "add")) and "event" in value:
        return RouteSignature("simple_calendar_pro", "add_event", "calendar_event", "time_fields")
    if ("opentracks" in value or "sports" in value) and "duration" in value:
        return RouteSignature("opentracks", "retrieve_duration", "activity", "aggregate")
    if ("broccoli" in value or "recipe" in value) and any(
        term in value for term in ("delete", "remove")
    ):
        constraint = "content_constraint" if any(
            term in value for term in ("ingredient", "direction", "constraint", "use ")
        ) else "multiple"
        return RouteSignature("broccoli", "delete_recipe", "recipe", constraint)
    if "osmand" in value and any(term in value for term in ("marker", "favorite", "location")):
        return RouteSignature("osmand", "add_location_marker", "location", "*")
    return None


def _route_from_raw(raw: Any) -> RouteSignature:
    if not isinstance(raw, dict):
        raise ValueError("workflow route must be an object")
    required = ("app", "operation", "object_family", "constraint_family")
    values = {key: _compact(raw.get(key)) for key in required}
    if any(not values[key] for key in required):
        raise ValueError("workflow route fields must be non-empty")
    return RouteSignature(**values)


def validate_bank(payload: Any) -> list[InducedWorkflow]:
    """Validate provenance and return the exact immutable runtime records."""
    if not isinstance(payload, dict) or payload.get("schema") != SCHEMA:
        raise ValueError("A4-v2 bank has the wrong schema")
    if payload.get("status") != "ready" or payload.get("frozen") is not True:
        raise ValueError("A4-v2 bank is not ready and frozen")
    if payload.get("scored_hard_inputs_used") is not False:
        raise ValueError("A4-v2 bank provenance permits scored Hard leakage")
    induction = payload.get("induction") or {}
    if (
        induction.get("mode") != "offline_model_induced"
        or int(induction.get("generation_calls") or 0) < 1
        or induction.get("upstream_commit") != UPSTREAM_COMMIT
        or not re.fullmatch(r"[0-9a-f]{64}", str(induction.get("prompt_sha256") or ""))
    ):
        raise ValueError("A4-v2 bank lacks faithful offline induction provenance")
    raw_workflows = payload.get("workflows")
    if not isinstance(raw_workflows, list) or not raw_workflows:
        raise ValueError("A4-v2 bank has no induced workflows")
    if payload.get("bank_sha256") != json_sha256(raw_workflows):
        raise ValueError("A4-v2 workflow payload hash drifted")

    records: list[InducedWorkflow] = []
    seen: set[str] = set()
    for raw in raw_workflows:
        workflow_id = _compact(raw.get("workflow_id"))
        if not workflow_id or workflow_id in seen:
            raise ValueError("A4-v2 workflow IDs must be non-empty and unique")
        seen.add(workflow_id)
        donor_ids = tuple(_compact(item) for item in raw.get("donor_ids") or ())
        donor_tasks = tuple(_compact(item) for item in raw.get("donor_task_classes") or ())
        donor_seeds = tuple(int(item) for item in raw.get("donor_seeds") or ())
        if len(set(donor_ids)) < 2 or len(set(donor_seeds)) < 2:
            raise ValueError(f"{workflow_id} needs at least two independent donors")
        if not donor_tasks or len(donor_ids) != len(donor_seeds):
            raise ValueError(f"{workflow_id} donor provenance is incomplete")
        text = _compact(raw.get("text"))
        numbered_steps = re.findall(r"(?:^|\s)(\d+)\.\s+", text)
        if len(set(numbered_steps)) < 2:
            raise ValueError(f"{workflow_id} must contain at least two induced steps")
        if "perform the visible done operation" in text.lower():
            raise ValueError(f"{workflow_id} contains the forbidden A4-v1 fallback")
        response_sha = str(raw.get("induction_response_sha256") or "")
        if not re.fullmatch(r"[0-9a-f]{64}", response_sha):
            raise ValueError(f"{workflow_id} lacks induction response provenance")
        records.append(
            InducedWorkflow(
                workflow_id=workflow_id,
                route=_route_from_raw(raw.get("route")),
                donor_ids=donor_ids,
                donor_task_classes=donor_tasks,
                donor_seeds=donor_seeds,
                text=text,
                induction_response_sha256=response_sha,
            )
        )
    return records


def _compatible(query: RouteSignature, candidate: RouteSignature) -> bool:
    if query.app != candidate.app or query.operation != candidate.operation:
        return False
    if candidate.object_family not in {"*", query.object_family}:
        return False
    if candidate.constraint_family not in {"*", query.constraint_family}:
        return False
    return True


class FaithfulOfflineWorkflowMemory:
    """Read-only, exact-route workflow context for scored execution."""

    mechanism_id = MECHANISM_ID

    def __init__(self, *, bank_payload: dict[str, Any], max_chars: int = 1800, max_workflows: int = 3):
        self._records = validate_bank(bank_payload)
        self.max_chars = max(256, int(max_chars))
        self.max_workflows = max(1, int(max_workflows))
        self.read_count = 0
        self.nonempty_read_count = 0
        self.retrievals: list[dict[str, Any]] = []

    def read(self, context: dict[str, Any] | None = None) -> tuple[str, dict[str, Any]]:
        goal = str((context or {}).get("goal") or "")
        query = classify_goal(goal)
        compatible = [record for record in self._records if query and _compatible(query, record.route)]
        compatible.sort(
            key=lambda item: (
                -(item.route.object_family != "*"),
                -(item.route.constraint_family != "*"),
                item.workflow_id,
            )
        )
        selected = compatible[: self.max_workflows]
        rendered = ""
        if selected:
            lines = [
                "Offline workflows induced from multiple independent successful non-Hard examples:",
                "Use only subroutines supported by current pixels; never copy donor values or coordinates.",
            ]
            for record in selected:
                lines.append(f"- {record.workflow_id}: {record.text}")
            lines.append("These are optional memory, not proof of completion; current pixels override them.")
            rendered = "\n".join(lines)[: self.max_chars]
        self.read_count += 1
        if rendered:
            self.nonempty_read_count += 1
        event = {
            "goal_sha256": sha256(goal.encode("utf-8")).hexdigest(),
            "query_route": asdict(query) if query else None,
            "retrieved_ids": [item.workflow_id for item in selected],
            "injected": bool(rendered),
            "match_policy": "exact_app_and_operation_then_object_constraint_compatibility",
        }
        self.retrievals.append(event)
        return rendered, {
            "mechanism_id": self.mechanism_id,
            "nonempty": bool(rendered),
            "rendered_chars": len(rendered),
            "rendered_sha256": sha256(rendered.encode("utf-8")).hexdigest(),
            "retrieved_ids": event["retrieved_ids"],
            "retrieved_count": len(selected),
            "retrieval": event,
        }

    def observe_step(self, **kwargs: Any) -> dict[str, Any]:
        del kwargs
        return {"written": False, "bank_updated": False, "reason": "frozen_offline_bank"}

    def audit_record(self) -> dict[str, Any]:
        return {
            "mechanism_id": self.mechanism_id,
            "bank_size": len(self._records),
            "read_count": self.read_count,
            "nonempty_read_count": self.nonempty_read_count,
            "active": self.nonempty_read_count > 0,
            "model_calls_added_during_scoring": 0,
            "action_override_count": 0,
            "scored_suite_updates_bank": False,
            "evaluator_used_during_scored_decision": False,
            "retrievals": list(self.retrievals),
        }

