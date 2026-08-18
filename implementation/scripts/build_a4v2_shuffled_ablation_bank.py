#!/usr/bin/env python3
"""Deterministically derange A4-v2 workflow content for the active control."""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "implementation/src"))
from raven_m.official_qwen_mobile.a4v2_faithful_awm import json_sha256, validate_bank  # noqa: E402


def _match_word_count(text: str, count: int) -> str:
    words = text.split()
    if not words:
        raise RuntimeError("cannot shuffle an empty workflow")
    output = [words[index % len(words)] for index in range(count)]
    if count < 4:
        raise RuntimeError("workflow is too short for a two-step matched control")
    output[0] = "1."
    if "2." not in output:
        output[count // 2] = "2."
    return " ".join(output)


def _match_word_count_with_suffix(text: str, count: int, suffix: str) -> str:
    suffix_words = suffix.split()
    if count <= len(suffix_words):
        raise RuntimeError("OsmAnd workflow is too short for the frozen boundary receipt")
    prefix = _match_word_count(text, count - len(suffix_words))
    return prefix + " " + suffix


def build(primary: dict) -> dict:
    validate_bank(primary)
    result = deepcopy(primary)
    workflows = result["workflows"]
    ordered = sorted(range(len(workflows)), key=lambda index: workflows[index]["workflow_id"])
    source_for = {ordered[index]: ordered[(index + 1) % len(ordered)] for index in range(len(ordered))}
    mapping = []
    for target_index, source_index in source_for.items():
        target = workflows[target_index]
        source = workflows[source_index]
        target_count = len(str(target["text"]).split())
        if (target.get("route") or {}).get("operation") == "open_location_result":
            target["text"] = _match_word_count_with_suffix(
                str(source["text"]), target_count,
                "Stop when the location-result choice surface is visible; do not select any final option.",
            )
        else:
            target["text"] = _match_word_count(str(source["text"]), target_count)
        target["induction_response_sha256"] = source["induction_response_sha256"]
        mapping.append(
            {
                "target_workflow_id": target["workflow_id"],
                "content_source_workflow_id": source["workflow_id"],
                "matched_word_count": target_count,
            }
        )
    result["ablation"] = {
        "identity": "A4V2_SHUFFLED_INCOMPATIBLE_CONTENT_ACTIVE_CONTROL_V1",
        "construction": "workflow_id_sorted_cyclic_derangement_word_count_matched",
        "primary_bank_sha256": json_sha256(primary),
        "mapping": sorted(mapping, key=lambda row: row["target_workflow_id"]),
    }
    result["bank_sha256"] = json_sha256(workflows)
    validate_bank(result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--primary-bank", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "evidence/a4v2/A4V2_SHUFFLED_ABLATION_BANK.json")
    args = parser.parse_args()
    primary = json.loads(args.primary_bank.read_text(encoding="utf-8"))
    result = build(primary)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ready", "output": str(args.output), "bank_sha256": result["bank_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
