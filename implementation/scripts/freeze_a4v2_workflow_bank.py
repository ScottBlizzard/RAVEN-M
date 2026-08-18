#!/usr/bin/env python3
"""Freeze seven completed induction responses into the scored A4-v2 bank."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from raven_m.official_qwen_mobile.a4v2_faithful_awm import (  # noqa: E402
    SCHEMA,
    UPSTREAM_COMMIT,
    json_sha256,
    validate_bank,
)


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _literal_leaks(text: str, literals: list[str]) -> list[str]:
    leaks: list[str] = []
    for literal in literals:
        value = str(literal).strip()
        if not value:
            continue
        pattern = re.escape(value)
        if value[0].isalnum() and value[-1].isalnum():
            pattern = rf"(?<![A-Za-z0-9_]){pattern}(?![A-Za-z0-9_])"
        if re.search(pattern, text, re.IGNORECASE):
            leaks.append(value)
    return leaks


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--induction-index", type=Path, required=True)
    parser.add_argument("--responses-dir", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--model-id", required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=REPOSITORY_ROOT / "evidence/a4v2/A4V2_FROZEN_WORKFLOW_BANK.json",
    )
    args = parser.parse_args()
    index = json.loads(args.induction_index.read_text(encoding="utf-8"))
    rows = index.get("packets") or []
    if index.get("schema") != "a4v2.awm_induction_index.v1" or len(rows) != 7:
        raise RuntimeError("induction index is incomplete")
    checkpoint = json.loads(args.checkpoint.read_text(encoding="utf-8"))
    checkpoint_body = {key: value for key, value in checkpoint.items() if key != "content_sha256"}
    checkpoint_content = sha256(
        json.dumps(checkpoint_body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if (
        checkpoint.get("schema") != "a4v2.awm_induction_checkpoint.v1"
        or checkpoint.get("status") != "complete"
        or checkpoint.get("generation_calls") != 7
        or checkpoint.get("induction_index_sha256") != _sha(args.induction_index)
        or checkpoint.get("model_id") != args.model_id
        or checkpoint.get("content_sha256") != checkpoint_content
        or checkpoint.get("pending_call") is not None
    ):
        raise RuntimeError("induction checkpoint is incomplete or drifted")
    call_by_route = {str(item["route_id"]): item for item in checkpoint.get("calls") or []}
    if len(call_by_route) != 7:
        raise RuntimeError("induction checkpoint call closure failed")
    workflows = []
    prompt_hashes: dict[str, str] = {}
    for row in rows:
        packet_path = REPOSITORY_ROOT / row["packet_path"]
        if not packet_path.is_file() or _sha(packet_path) != row["packet_sha256"]:
            raise RuntimeError(f"induction packet drift: {row['route_id']}")
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        response_path = args.responses_dir / f"{row['route_id']}.txt"
        if not response_path.is_file():
            raise RuntimeError(f"induction response missing: {row['route_id']}")
        call = call_by_route.get(str(row["route_id"]))
        if (
            not call
            or call.get("content_sha256") != _sha(response_path)
            or call.get("prompt_sha256") != packet.get("prompt_sha256")
            or call.get("transport_attempts") != 1
            or call.get("response_model") != args.model_id
            or not isinstance(call.get("usage"), dict)
            or int((call.get("usage") or {}).get("prompt_tokens", -1)) < 0
            or int((call.get("usage") or {}).get("completion_tokens", -1)) < 0
            or int((call.get("usage") or {}).get("total_tokens", -1))
            != int((call.get("usage") or {}).get("prompt_tokens", -1))
            + int((call.get("usage") or {}).get("completion_tokens", -1))
        ):
            raise RuntimeError(f"induction checkpoint response binding failed: {row['route_id']}")
        response = " ".join(response_path.read_text(encoding="utf-8").split()).strip()
        literal_leaks = _literal_leaks(response, list(packet.get("literal_denylist") or []))
        if literal_leaks:
            raise RuntimeError(
                f"induction response leaked donor literals for {row['route_id']}: "
                f"{[sha256(item.encode('utf-8')).hexdigest() for item in literal_leaks]}"
            )
        if re.search(r"\b(?:x|y|x2|y2)\s*[=:]\s*\d|\(\s*\d+(?:\.\d+)?\s*,\s*\d+(?:\.\d+)?\s*\)", response, re.IGNORECASE):
            raise RuntimeError(f"induction response contains coordinates: {row['route_id']}")
        if row["route_id"] == "osmand_open_location_result":
            exact_stop = "Stop when the location-result choice surface is visible; do not select any final option."
            if not response.endswith(exact_stop):
                raise RuntimeError("OsmAnd prefix workflow lacks the exact terminal boundary receipt")
            numbered = re.findall(
                r"(?:^|\s)\d+\.\s+(.+?)(?=(?:\s\d+\.\s)|$)",
                response,
            )
            if not numbered or numbered[-1].strip() != exact_stop:
                raise RuntimeError("OsmAnd prefix workflow final numbered step crossed the choice boundary")
            without_stop = response[: -len(exact_stop)]
            if re.search(
                r"\b(?:favorite|favourite|marker|star|flag|final option|left option|right option)\b",
                without_stop,
                re.IGNORECASE,
            ):
                raise RuntimeError("OsmAnd prefix workflow crossed the frozen pre-final-choice boundary")
        workflows.append(
            {
                "workflow_id": f"a4v2_{row['route_id']}_v1",
                "route": packet["route"],
                "donor_ids": packet["donor_ids"],
                "donor_task_classes": packet["donor_task_classes"],
                "donor_seeds": packet["donor_seeds"],
                "text": response,
                "induction_response_sha256": _sha(response_path),
            }
        )
        prompt_hashes[str(row["route_id"])] = str(packet["prompt_sha256"])
    combined_prompt_sha = sha256(
        json.dumps(prompt_hashes, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    payload = {
        "schema": SCHEMA,
        "status": "ready",
        "frozen": True,
        "scored_hard_inputs_used": False,
        "induction": {
            "mode": "offline_model_induced",
            "generation_calls": 7,
            "upstream_commit": UPSTREAM_COMMIT,
            "model_id": args.model_id,
            "prompt_sha256": combined_prompt_sha,
            "packet_index_sha256": _sha(args.induction_index),
            "checkpoint_sha256": _sha(args.checkpoint),
            "checkpoint_content_sha256": checkpoint["content_sha256"],
        },
        "workflows": workflows,
        "bank_sha256": json_sha256(workflows),
    }
    validate_bank(payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ready", "workflow_count": len(workflows), "output": str(args.output), "sha256": _sha(args.output)}, indent=2))


if __name__ == "__main__":
    main()
