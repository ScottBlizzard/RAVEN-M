#!/usr/bin/env python3
"""Compare bounded source-stage baseline and executable coverage-gate runs."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
from typing import Any


DOCUMENT_ACTIVITY = "net.gsantner.markor/net.gsantner.markor.activity.DocumentActivity"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def source_metrics(suite_dir: Path) -> dict[str, Any]:
    suite = load(suite_dir / "aggregate.json")
    episodes = []
    for row in suite["episodes"]:
        episode_dir = suite_dir / "episodes" / row["episode_id"]
        episode = load(episode_dir / "episode.json")
        log = [
            json.loads(line)
            for line in (episode_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        opened = False
        forward = 0
        for event in log:
            if event.get("event") != "step":
                continue
            before = event.get("before") or {}
            before_activity = ((before.get("foreground") or {}).get("activity"))
            if before_activity != DOCUMENT_ACTIVITY:
                continue
            opened = True
            action = (
                ((event.get("layers") or {}).get("L2_protocol_coordinate") or {}).get(
                    "executed_canonical_action"
                )
                or ((event.get("decision") or {}).get("canonical_action"))
                or {}
            )
            if action.get("type") == "swipe":
                dx = float(action.get("x2", 0)) - float(action.get("x", 0))
                dy = float(action.get("y2", 0)) - float(action.get("y", 0))
                if abs(dy) >= abs(dx) and dy < 0:
                    forward += 1
        gate = episode.get("source_document_coverage_gate") or {}
        usage_steps = episode.get("steps") or []
        episodes.append(
            {
                "episode_id": row["episode_id"],
                "task_name": row["task_name"],
                "opened_document": opened,
                "forward_scrolls": forward,
                "bottom_attested": bool(gate.get("bottom_attested")),
                "override_count": int(gate.get("override_count", 0)),
                "termination_reason": episode["termination_reason"],
                "model_calls": episode["model_call_count"],
                "prompt_tokens": sum(
                    int(((step.get("model_call") or {}).get("usage") or {}).get("prompt_tokens", 0))
                    for step in usage_steps
                ),
                "completion_tokens": sum(
                    int(((step.get("model_call") or {}).get("usage") or {}).get("completion_tokens", 0))
                    for step in usage_steps
                ),
            }
        )
    return {
        "suite_id": suite["suite_id"],
        "episode_count": len(episodes),
        "opened_documents": sum(row["opened_document"] for row in episodes),
        "episodes_with_forward_scroll": sum(row["forward_scrolls"] > 0 for row in episodes),
        "bottom_attested_episodes": sum(row["bottom_attested"] for row in episodes),
        "forward_scrolls": sum(row["forward_scrolls"] for row in episodes),
        "model_calls": sum(row["model_calls"] for row in episodes),
        "prompt_tokens": sum(row["prompt_tokens"] for row in episodes),
        "completion_tokens": sum(row["completion_tokens"] for row in episodes),
        "episodes": episodes,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-suite", required=True, type=Path)
    parser.add_argument("--gate-suite", required=True, type=Path)
    parser.add_argument("--baseline-extractor", required=True, type=Path)
    parser.add_argument("--gate-extractor", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    baseline_source = source_metrics(args.baseline_suite.resolve())
    gate_source = source_metrics(args.gate_suite.resolve())
    baseline_extract = load(args.baseline_extractor)
    gate_extract = load(args.gate_extractor)
    recall_gain = gate_extract["micro_recall"] - baseline_extract["micro_recall"]
    gates = {
        "gate_opens_document_3_of_3": gate_source["opened_documents"] == 3,
        "gate_forward_scroll_3_of_3": gate_source["episodes_with_forward_scroll"] == 3,
        "gate_bottom_attested_3_of_3": gate_source["bottom_attested_episodes"] == 3,
        "all_gate_extractor_outputs_valid": (
            gate_extract["valid_output_count"] == gate_extract["record_count"]
        ),
        "gate_micro_precision_1_00": gate_extract["micro_precision"] == 1.0,
        "gate_micro_recall_at_least_0_75": gate_extract["micro_recall"] >= 0.75,
        "absolute_recall_gain_at_least_0_20": recall_gain >= 0.20,
        "gate_full_recall_at_least_2_of_3": gate_extract["full_recall_episode_count"] >= 2,
    }
    result = {
        "claim_class": "new_instance_development_matched_source_stage_pilot_not_held_out",
        "baseline_source": baseline_source,
        "gate_source": gate_source,
        "baseline_extractor": {
            key: baseline_extract[key]
            for key in (
                "record_count", "valid_output_count", "true_positive", "false_positive",
                "false_negative", "micro_precision", "micro_recall", "full_recall_episode_count",
            )
        },
        "gate_extractor": {
            key: gate_extract[key]
            for key in (
                "record_count", "valid_output_count", "true_positive", "false_positive",
                "false_negative", "micro_precision", "micro_recall", "full_recall_episode_count",
            )
        },
        "absolute_recall_gain": recall_gain,
        "qualification": gates,
        "qualification_pass": all(gates.values()),
        "inputs": {
            "baseline_aggregate_sha256": digest(args.baseline_suite / "aggregate.json"),
            "gate_aggregate_sha256": digest(args.gate_suite / "aggregate.json"),
            "baseline_extractor_sha256": digest(args.baseline_extractor),
            "gate_extractor_sha256": digest(args.gate_extractor),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
