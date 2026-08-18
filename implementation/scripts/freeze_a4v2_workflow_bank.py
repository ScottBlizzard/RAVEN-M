#!/usr/bin/env python3
"""Freeze seven completed induction responses into the scored A4-v2 bank."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--induction-index", type=Path, required=True)
    parser.add_argument("--responses-dir", type=Path, required=True)
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
        response = " ".join(response_path.read_text(encoding="utf-8").split()).strip()
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

