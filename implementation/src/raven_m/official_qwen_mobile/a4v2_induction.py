"""Build auditable offline-AWM induction packets from successful donors.

This module deliberately stops before the induction model call.  It validates
donor success/provenance, masks instance values, and emits the prompt and hashes
that a later GPU-backed induction call must consume unchanged.
"""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any


INDUCTION_INSTRUCTION = """Given successful Android navigation examples for one matched route, extract non-overlapping common workflows. Each workflow must be a reusable subroutine supported by at least two examples and contain at least two numbered steps. Preserve invariant app and UI semantics, but replace task-specific values with descriptive variables. Do not include coordinates, donor answers, evaluator information, or generic instructions such as 'perform the visible operation'. Return concise workflow text only."""


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _compact(value: Any) -> str:
    return " ".join(str(value).split()).strip()


def _goal_literals(goal: str) -> list[str]:
    literals: set[str] = set()
    literals.update(match.strip() for match in re.findall(r'["\']([^"\']{2,})["\']', goal))
    literals.update(re.findall(r"(?<![A-Za-z])\$?\d+(?:[.:/-]\d+)+(?![A-Za-z])", goal))
    for line in goal.splitlines():
        key, separator, value = line.partition(":")
        if separator and key.strip() and value.strip():
            literals.add(value.strip().strip(".,;"))
    return sorted((item for item in literals if len(item) >= 2), key=lambda item: (-len(item), item))


def _mask(text: str, literals: list[str]) -> str:
    output = str(text)
    for index, literal in enumerate(literals, start=1):
        output = re.sub(re.escape(literal), f"{{task_value_{index}}}", output, flags=re.IGNORECASE)
    # Coordinates are never part of an AWM semantic workflow input.
    output = re.sub(r"\b(?:x|y|x2|y2)\s*[=:]\s*\d+(?:\.\d+)?", "", output, flags=re.IGNORECASE)
    return _compact(output)


def _semantic_trace(episode: dict[str, Any], literals: list[str]) -> list[dict[str, str]]:
    trace: list[dict[str, str]] = []
    for step in episode.get("steps") or []:
        decision = step.get("decision") or {}
        action = decision.get("canonical_action") or decision.get("action") or {}
        action_type = _compact(action.get("type") or ((decision.get("tool") or {}).get("arguments") or {}).get("action"))
        thought = _mask(decision.get("thought") or "", literals)
        summary = _mask(
            decision.get("action_summary") or decision.get("decision_summary") or "",
            literals,
        )
        if thought or summary or action_type:
            trace.append({"thought": thought, "action_summary": summary, "action_type": action_type})
    if not trace:
        raise ValueError("successful donor has no semantic trace")
    return trace


def build_induction_packet(
    *,
    route_id: str,
    route: dict[str, str],
    donors: list[dict[str, Any]],
    repository_root: Path,
    scored_hard_manifest: Path,
) -> dict[str, Any]:
    """Validate two or more donor locks and build one immutable prompt packet."""
    if len(donors) < 2:
        raise ValueError("offline AWM induction needs at least two donors")
    hard_path = scored_hard_manifest.resolve()
    if not hard_path.is_file():
        raise ValueError("scored Hard manifest is missing")
    hard_payload = json.loads(hard_path.read_text(encoding="utf-8"))
    hard_classes = {str(item.get("task_class")) for item in hard_payload.get("instances") or []}
    try:
        hard_key = str(hard_path.relative_to(repository_root.resolve())).replace("\\", "/")
    except ValueError:
        hard_key = str(hard_path)
    examples: list[dict[str, Any]] = []
    source_lock: dict[str, str] = {hard_key: file_sha256(hard_path)}
    donor_ids: list[str] = []
    donor_seeds: list[int] = []
    masked_literals: list[str] = []
    for donor in donors:
        path = (repository_root / str(donor["episode_path"])).resolve()
        if not path.is_file():
            raise ValueError(f"donor episode is missing: {donor['episode_path']}")
        actual_sha = file_sha256(path)
        if actual_sha != donor.get("episode_sha256"):
            raise ValueError(f"donor episode hash drift: {donor['donor_id']}")
        episode = json.loads(path.read_text(encoding="utf-8"))
        checks = {
            "reward": episode.get("evaluator_reward") == 1.0,
            "success": episode.get("success") is True,
            "no_error": episode.get("error") is None,
            "task": episode.get("task_name") == donor.get("task_class"),
            "seed": int(episode.get("seed", -1)) == int(donor.get("task_seed", -2)),
            "nonhard": str(donor.get("difficulty", "")).lower() in {"easy", "medium"},
            "class_absent_from_scored_hard": str(donor.get("task_class")) not in hard_classes,
        }
        failed = [name for name, passed in checks.items() if not passed]
        if failed:
            raise ValueError(f"donor {donor['donor_id']} failed: {failed}")
        goal = str(episode.get("task_goal") or "")
        literals = _goal_literals(goal)
        masked_literals.extend(literals)
        donor_id = str(donor["donor_id"])
        donor_ids.append(donor_id)
        donor_seeds.append(int(donor["task_seed"]))
        source_lock[str(donor["episode_path"])] = actual_sha
        examples.append(
            {
                "donor_id": donor_id,
                "task_class": donor["task_class"],
                "task_seed": int(donor["task_seed"]),
                "query": _mask(goal, literals),
                "successful_trace": _semantic_trace(episode, literals),
            }
        )
    if len(set(donor_ids)) != len(donor_ids) or len(set(donor_seeds)) < 2:
        raise ValueError("donor IDs must be unique and at least two seeds independent")

    prompt = "\n\n".join(
        [
            INDUCTION_INSTRUCTION,
            f"Route: {json.dumps(route, ensure_ascii=False, sort_keys=True)}",
            "## Concrete successful examples\n" + json.dumps(examples, ensure_ascii=False, indent=2),
            "## Summary workflows",
        ]
    )
    return {
        "schema": "a4v2.awm_induction_packet.v1",
        "route_id": route_id,
        "route": route,
        "donor_ids": donor_ids,
        "donor_seeds": donor_seeds,
        "donor_task_classes": [str(item["task_class"]) for item in donors],
        "source_lock": dict(sorted(source_lock.items())),
        "source_lock_sha256": sha256(
            json.dumps(source_lock, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "masked_literal_sha256s": sorted(
            {sha256(item.encode("utf-8")).hexdigest() for item in masked_literals}
        ),
        "prompt": prompt,
        "prompt_sha256": sha256(prompt.encode("utf-8")).hexdigest(),
        "generation_calls": 0,
        "ready_for_induction": True,
    }
