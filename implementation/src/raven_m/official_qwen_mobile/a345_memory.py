"""Three isolated public-memory kernels for the A3/A4/A5 experiment.

The classes in this module are *adaptations*, not claims of byte-for-byte
reproduction of the upstream systems.  They preserve the distinct memory
operation that is under test while keeping the Qwen backbone, AndroidWorld
task, action protocol, observation, sampling, evaluator, and one-call-per-step
controller fixed.

* A3: MemGUI ConAct-style proactive folded context (memory-as-action).
* A4: AWM-style frozen procedural workflow retrieval (cross-task memory).
* A5: HyMEM-style online page/transition graph with visual-state retrieval.

No class calls a model, reads the Android UI tree, sees the task evaluator, or
blocks/repairs an action.  All active inputs come from model prose and pixels
that were already visible to the policy.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import re
from typing import Any

import numpy as np


def _compact(value: Any) -> str:
    return " ".join(str(value).split()).strip()


def _parse_prefix(text: str, *, name: str, fields: tuple[str, ...]) -> dict[str, Any]:
    pattern = re.compile(rf"^\s*{re.escape(name)}\[(?P<payload>.*?)\]\s*\|", re.DOTALL)
    match = pattern.search(str(text))
    values: dict[str, str] = {}
    payload = ""
    if match is not None:
        payload = _compact(match.group("payload"))
        for part in payload.split(";"):
            key, separator, value = part.partition("=")
            key = key.strip().lower()
            if separator and key in fields and key not in values:
                values[key] = _compact(value) or "none"
    complete = set(values) == set(fields)
    return {
        "prefix": name,
        "prefix_present": match is not None,
        "fields_complete": complete,
        "payload_chars": len(payload),
        "parse_reason": "valid" if complete else (
            "prefix_missing" if match is None else "fields_missing_or_duplicate"
        ),
        "fields": values if complete else None,
        "prefix_end": match.end() if match is not None else None,
    }


class _AuditedMemory:
    prefix_name: str
    prefix_fields: tuple[str, ...]
    mechanism_id: str

    def __init__(self, *, max_chars: int) -> None:
        self.max_chars = max(256, int(max_chars))
        self.write_attempt_count = 0
        self.write_success_count = 0
        self.read_count = 0
        self.nonempty_read_count = 0
        self.protocol_valid_count = 0

    def parse(self, action_summary: str) -> dict[str, Any]:
        return _parse_prefix(
            action_summary, name=self.prefix_name, fields=self.prefix_fields
        )

    def record_protocol(self, action_summary: str) -> dict[str, Any]:
        parsed = self.parse(action_summary)
        self.write_attempt_count += 1
        if parsed["fields_complete"]:
            self.protocol_valid_count += 1
        return {key: value for key, value in parsed.items() if key not in {"fields", "prefix_end"}}

    def history_summary(self, action_summary: str) -> str:
        parsed = self.parse(action_summary)
        end = parsed.get("prefix_end")
        return _compact(str(action_summary)[int(end):]) if end is not None else _compact(action_summary)

    def _read_record(self, rendered: str, selected_ids: list[str]) -> tuple[str, dict[str, Any]]:
        rendered = rendered[: self.max_chars]
        self.read_count += 1
        if rendered:
            self.nonempty_read_count += 1
        return rendered, {
            "mechanism_id": self.mechanism_id,
            "nonempty": bool(rendered),
            "rendered_chars": len(rendered),
            "rendered_sha256": sha256(rendered.encode("utf-8")).hexdigest(),
            "retrieved_ids": selected_ids,
            "retrieved_count": len(selected_ids),
        }

    def _base_audit(self) -> dict[str, Any]:
        return {
            "mechanism_id": self.mechanism_id,
            "max_chars": self.max_chars,
            "write_attempt_count": self.write_attempt_count,
            "write_success_count": self.write_success_count,
            "protocol_valid_count": self.protocol_valid_count,
            "read_count": self.read_count,
            "nonempty_read_count": self.nonempty_read_count,
            "active": self.write_success_count > 0 and self.nonempty_read_count > 0,
            "model_calls_added": 0,
            "hidden_state_used_for_decision": False,
            "evaluator_used_for_decision": False,
            "action_override_count": 0,
        }


@dataclass(frozen=True)
class FoldedContext:
    source_step: int
    folded_history: str
    ui_state: str
    recent: str
    observable_outcome: str


class ProactiveFoldedContextMemory(_AuditedMemory):
    """A3: MemGUI ConAct-style policy-authored, replace-in-place context."""

    mechanism_id = "a3_memgui_conact_folded_context_v1"
    prefix_name = "CONTEXT"
    prefix_fields = ("folded_history", "ui_state", "recent")

    def __init__(self, *, max_chars: int = 1800) -> None:
        super().__init__(max_chars=max_chars)
        self._state: FoldedContext | None = None

    def read(self, context: dict[str, Any] | None = None) -> tuple[str, dict[str, Any]]:
        del context
        if self._state is None:
            return self._read_record("", [])
        state = self._state
        rendered = "\n".join(
            [
                "Proactively folded context from your own previous response:",
                f"- folded action history: {state.folded_history}",
                f"- persistent UI/task state: {state.ui_state}",
                f"- recent step record: {state.recent}",
                f"- observed screenshot outcome: {state.observable_outcome}",
                "Update this compact context in the next Action; current pixels override stale content.",
            ]
        )
        return self._read_record(rendered, [f"a3s_{state.source_step:03d}"])

    def observe_step(self, **kwargs: Any) -> dict[str, Any]:
        parsed = self.parse(str(kwargs["action_summary"]))
        fields = parsed.get("fields")
        if fields is None:
            return {"written": False, "reason": "context_prefix_missing_or_malformed"}
        transition = kwargs.get("transition") or {}
        self._state = FoldedContext(
            source_step=int(kwargs["source_step"]),
            folded_history=fields["folded_history"],
            ui_state=fields["ui_state"],
            recent=fields["recent"],
            observable_outcome=(
                "no_exact_visible_change"
                if transition.get("exactly_unchanged") is True
                else "visible_change_or_ambiguous"
            ),
        )
        self.write_success_count += 1
        return {"written": True, "state": asdict(self._state)}

    def audit_record(self) -> dict[str, Any]:
        return {**self._base_audit(), "state": asdict(self._state) if self._state else None}


@dataclass(frozen=True)
class WorkflowRecord:
    workflow_id: str
    donor_task: str
    donor_seed: int
    donor_family: str
    keywords: tuple[str, ...]
    workflow: str
    source_episode_sha256: str
    source_evaluator_reward: float


def _terms(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9_]+", str(value).lower())
        if len(token) > 2
    }


class FrozenWorkflowMemory:
    """A4: frozen donor-only procedural memory following AWM's read path.

    The scored Hard suite never updates this bank.  Every record must originate
    from a successful, preregistered Easy/Medium donor episode outside the 19
    scored Hard tasks.  A deterministic lexical retriever is used so retrieval
    adds no model/planner/critic call.  This is an AWM-style Android adaptation,
    not a claim that WebArena/Mind2Web workflows can be copied verbatim.
    """

    mechanism_id = "a4_awm_frozen_donor_workflow_memory_v1"

    def __init__(self, *, bank: list[dict[str, Any]], max_chars: int = 1800) -> None:
        self.max_chars = max(256, int(max_chars))
        self._records: list[WorkflowRecord] = []
        for raw in bank:
            record = WorkflowRecord(
                workflow_id=str(raw["workflow_id"]),
                donor_task=str(raw["donor_task"]),
                donor_seed=int(raw["donor_seed"]),
                donor_family=str(raw["donor_family"]),
                keywords=tuple(str(item).lower() for item in raw["keywords"]),
                workflow=_compact(raw["workflow"]),
                source_episode_sha256=str(raw["source_episode_sha256"]),
                source_evaluator_reward=float(raw["source_evaluator_reward"]),
            )
            if record.source_evaluator_reward != 1.0:
                raise ValueError("A4 workflow bank accepts evaluator-confirmed donor successes only")
            self._records.append(record)
        if not self._records:
            raise ValueError("A4 requires a non-empty frozen donor workflow bank")
        if len({item.workflow_id for item in self._records}) != len(self._records):
            raise ValueError("A4 workflow ids must be unique")
        self.read_count = 0
        self.nonempty_read_count = 0
        self.retrievals: list[dict[str, Any]] = []

    def read(self, context: dict[str, Any] | None = None) -> tuple[str, dict[str, Any]]:
        context = context or {}
        goal = str(context.get("goal") or "")
        query = _terms(goal)
        ranked: list[tuple[WorkflowRecord, float]] = []
        for record in self._records:
            candidates = set(record.keywords) | _terms(record.donor_family)
            overlap = len(query & candidates)
            union = max(1, len(query | candidates))
            score = overlap / union
            ranked.append((record, score))
        ranked.sort(key=lambda item: (-item[1], item[0].workflow_id))
        selected, score = ranked[0]
        # A zero-overlap workflow is deliberately not injected; unrelated
        # procedural memory is more likely to harm than inform.
        rendered = ""
        selected_ids: list[str] = []
        if score > 0:
            rendered = "\n".join(
                [
                    "Frozen procedural workflow retrieved from an independent successful donor task:",
                    f"- workflow id: {selected.workflow_id}",
                    f"- reusable procedure: {selected.workflow}",
                    "Adapt it only where the current screenshot supports the same operation; never copy donor values.",
                ]
            )[: self.max_chars]
            selected_ids = [selected.workflow_id]
        self.read_count += 1
        if rendered:
            self.nonempty_read_count += 1
        event = {
            "query_goal_sha256": sha256(goal.encode("utf-8")).hexdigest(),
            "workflow_id": selected.workflow_id,
            "score": score,
            "injected": bool(rendered),
            "source_episode_sha256": selected.source_episode_sha256,
        }
        self.retrievals.append(event)
        return rendered, {
            "mechanism_id": self.mechanism_id,
            "nonempty": bool(rendered),
            "rendered_chars": len(rendered),
            "rendered_sha256": sha256(rendered.encode("utf-8")).hexdigest(),
            "retrieved_ids": selected_ids,
            "retrieved_count": len(selected_ids),
            "retrieval": event,
        }

    def audit_record(self) -> dict[str, Any]:
        return {
            "mechanism_id": self.mechanism_id,
            "bank_size": len(self._records),
            "max_chars": self.max_chars,
            "write_attempt_count": 0,
            "write_success_count": 0,
            "read_count": self.read_count,
            "nonempty_read_count": self.nonempty_read_count,
            "active": self.nonempty_read_count > 0,
            "model_calls_added": 0,
            "hidden_state_used_for_decision": False,
            "evaluator_used_during_scored_decision": False,
            "scored_suite_updates_bank": False,
            "records": [asdict(item) for item in self._records],
            "retrievals": list(self.retrievals),
        }


def _visual_fingerprint(snapshot: dict[str, Any]) -> str:
    """64-bit average hash derived only from model-visible screenshot pixels."""
    pixels = np.asarray(snapshot.get("pixels"))
    if pixels.ndim != 3 or pixels.shape[0] < 8 or pixels.shape[1] < 8:
        raise RuntimeError("A5 requires model-visible RGB screenshot pixels")
    # Remove thin system bars, then deterministically sample an 8x8 grayscale grid.
    top = max(0, int(round(pixels.shape[0] * 0.04)))
    bottom = min(pixels.shape[0], int(round(pixels.shape[0] * 0.96)))
    crop = pixels[top:bottom]
    ys = np.linspace(0, crop.shape[0] - 1, 8).round().astype(int)
    xs = np.linspace(0, crop.shape[1] - 1, 8).round().astype(int)
    sample = crop[np.ix_(ys, xs)].astype(np.float32)
    gray = sample[..., :3].mean(axis=2)
    bits = (gray >= float(gray.mean())).reshape(-1)
    value = 0
    for bit in bits:
        value = (value << 1) | int(bool(bit))
    return f"{value:016x}"


def _hamming(left: str, right: str) -> int:
    return (int(left, 16) ^ int(right, 16)).bit_count()


@dataclass(frozen=True)
class GraphEdge:
    edge_id: str
    source_step: int
    source_fingerprint: str
    destination_fingerprint: str
    node: str
    relation: str
    facts: str
    avoid: str
    canonical_action_sha256: str
    observable_outcome: str


class OnlinePageGraphMemory(_AuditedMemory):
    """A5: an episode-local HyMEM-style visual/symbolic transition graph.

    Full HyMEM uses learned continuous trajectory embeddings and an offline
    evolving graph.  For causal isolation and zero extra models, this arm uses
    a deterministic perceptual fingerprint as the continuous key and the
    policy-authored GRAPH fields as the symbolic node/edge content.
    """

    mechanism_id = "a5_hymem_online_visual_symbolic_graph_v1"
    prefix_name = "GRAPH"
    prefix_fields = ("node", "relation", "facts", "avoid")

    def __init__(self, *, max_edges: int = 12, max_chars: int = 1800, max_hamming: int = 6) -> None:
        super().__init__(max_chars=max_chars)
        self.max_edges = max(1, int(max_edges))
        self.max_hamming = max(0, int(max_hamming))
        self._edges: list[GraphEdge] = []
        self.near_match_read_count = 0

    def read(self, context: dict[str, Any] | None = None) -> tuple[str, dict[str, Any]]:
        context = context or {}
        before = context.get("before") or {}
        current = _visual_fingerprint(before)
        ranked = sorted(
            ((edge, _hamming(current, edge.source_fingerprint)) for edge in self._edges),
            key=lambda pair: (pair[1], -pair[0].source_step),
        )
        selected = [(edge, distance) for edge, distance in ranked if distance <= self.max_hamming][:4]
        if not selected:
            rendered, audit = self._read_record("", [])
            audit.update({"query_fingerprint": current, "max_hamming": self.max_hamming, "matches": []})
            return rendered, audit
        if any(distance > 0 for _, distance in selected):
            self.near_match_read_count += 1
        lines = ["Retrieved online page-transition graph memory from earlier visible states:"]
        for edge, distance in selected:
            lines.append(
                f"- {edge.edge_id} (visual distance {distance}): page={edge.node}; "
                f"relation={edge.relation}; facts={edge.facts}; avoid={edge.avoid}; "
                f"outcome={edge.observable_outcome}"
            )
        lines.append("Use only matching page knowledge; current pixels override every retrieved edge.")
        rendered, audit = self._read_record("\n".join(lines), [edge.edge_id for edge, _ in selected])
        audit.update(
            {
                "query_fingerprint": current,
                "max_hamming": self.max_hamming,
                "matches": [
                    {"edge_id": edge.edge_id, "hamming": distance}
                    for edge, distance in selected
                ],
            }
        )
        return rendered, audit

    def observe_step(self, **kwargs: Any) -> dict[str, Any]:
        parsed = self.parse(str(kwargs["action_summary"]))
        fields = parsed.get("fields")
        if fields is None:
            return {"written": False, "reason": "graph_prefix_missing_or_malformed"}
        before = kwargs.get("before") or {}
        after = kwargs.get("after") or {}
        source = _visual_fingerprint(before)
        destination = _visual_fingerprint(after)
        canonical = json.dumps(
            kwargs.get("canonical_action") or {}, sort_keys=True, separators=(",", ":")
        )
        step = int(kwargs["source_step"])
        edge = GraphEdge(
            edge_id=f"a5e_{step:03d}_{sha256((source + destination + canonical).encode('utf-8')).hexdigest()[:10]}",
            source_step=step,
            source_fingerprint=source,
            destination_fingerprint=destination,
            node=fields["node"],
            relation=fields["relation"],
            facts=fields["facts"],
            avoid=fields["avoid"],
            canonical_action_sha256=sha256(canonical.encode("utf-8")).hexdigest(),
            observable_outcome=(
                "no_exact_visible_change"
                if (kwargs.get("transition") or {}).get("exactly_unchanged") is True
                else "visible_change_or_ambiguous"
            ),
        )
        self._edges = [item for item in self._edges if item.edge_id != edge.edge_id]
        self._edges.append(edge)
        self._edges = self._edges[-self.max_edges :]
        self.write_success_count += 1
        return {"written": True, "edge": asdict(edge)}

    def audit_record(self) -> dict[str, Any]:
        return {
            **self._base_audit(),
            "max_edges": self.max_edges,
            "max_hamming": self.max_hamming,
            "near_match_read_count": self.near_match_read_count,
            "edges": [asdict(item) for item in self._edges],
            "continuous_key": "deterministic_64bit_average_hash_of_model_visible_pixels",
            "adaptation_limit": "no_learned_embedding_or_offline_memory_bank",
        }
