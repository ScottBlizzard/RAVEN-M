"""Replay contaminated v0.2.1 Q-SWIPE outputs under the v0.2.2 envelope."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from raven_m.eest_ac.action_contract_v0_2_2 import parse_decision_v0_2_2  # noqa: E402


EXPECTED_INPUT_SHA256 = "63b08898e4434045c77a044ffdc6ae55e4b695b4b5dd59d63077666c580ad238"


def _hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=Path,
        default=REPOSITORY_ROOT / "runs/eest_ac_v0_2_1_action_qualification_20260804/probes/01_Q-SWIPE/model_calls.jsonl",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if _hash(args.input) != EXPECTED_INPUT_SHA256:
        raise RuntimeError("Contaminated v0.2.1 Q-SWIPE corpus hash changed.")
    records = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines()]
    if len(records) != 2:
        raise RuntimeError("Expected exactly the contaminated initial and repair outputs.")
    rows = []
    for record in records:
        parsed = parse_decision_v0_2_2(record["content"])
        rows.append({
            "role": record["role"],
            "call_id": record["call_id"],
            "raw_response_sha256": record["response_sha256"],
            "semantic_action_category": parsed.decision["action"]["type"],
            "canonical_action": parsed.decision["action"],
            "canonicalization": parsed.canonicalization.record() if parsed.canonicalization else None,
            "intent_metadata": parsed.intent_metadata.record(),
            "control_plane_valid": parsed.control_plane_valid,
            "live_evidence_eligible": False,
        })
    if {row["semantic_action_category"] for row in rows} != {"swipe"}:
        raise RuntimeError("Contaminated outputs did not recover the same swipe category.")
    result = {
        "schema_version": "eest_ac_v0_2_1_contaminated_envelope_replay.v0_2_2",
        "status": "pass",
        "zero_model_generation_calls": 0,
        "input": str(args.input.resolve()),
        "input_sha256": _hash(args.input),
        "development_contaminated": True,
        "live_evidence_eligible": False,
        "rows": rows,
        "confusion": {
            "inputs": 2,
            "valid_complete_envelope": sum(row["control_plane_valid"] for row in rows),
            "semantic_swipe": sum(row["semantic_action_category"] == "swipe" for row in rows),
            "metadata_only_repair_calls": 0,
        },
    }
    _write(args.output, result)
    print(json.dumps({"status": "pass", "rows": len(rows), "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
