#!/usr/bin/env python3
"""Run the frozen screenshot-only visible-object extraction diagnostic."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import sys
import unicodedata
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from raven_m.models.vllm_client import VLLMClient  # noqa: E402
from raven_m.official_qwen_mobile.visible_object_extractor import (  # noqa: E402
    VISIBLE_OBJECT_EXTRACTOR_SYSTEM_PROMPT,
    build_visible_object_extractor_user_prompt,
    parse_visible_object_extraction,
)


MODEL_ID = "Qwen/Qwen3-VL-32B-Instruct"
MODEL_REVISION = "0cfaf48183f594c314753d30a4c4974bc75f3ccb"
BACKEND_ID = "qwen3_vl_32b_vllm_bf16_1xrtxpro6000_visible_object_extractor_v1"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(re.findall(r"[^\W_]+", value, flags=re.UNICODE))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:18000")
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=REPOSITORY_ROOT / "runs" / "visible_object_extractor",
    )
    parser.add_argument("--request-timeout-seconds", type=float, default=180.0)
    args = parser.parse_args()

    manifest_path = args.manifest.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    run_id = f"visible_object_extractor_{datetime.now().strftime('%Y%m%dT%H%M%S')}_{uuid4().hex[:8]}"
    run_dir = args.output_root.resolve() / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    shutil.copy2(manifest_path, run_dir / "manifest.snapshot.json")

    client = VLLMClient(
        args.url,
        model_id=MODEL_ID,
        model_revision=MODEL_REVISION,
        backend_id=BACKEND_ID,
        temperature=0.7,
        top_p=0.8,
        top_k=20,
        presence_penalty=1.5,
        repetition_penalty=1.0,
        seed=3407,
        timeout_seconds=args.request_timeout_seconds,
    )
    health = client.health()
    frame_results: list[dict] = []
    events_path = run_dir / "events.jsonl"

    for index, record in enumerate(manifest["records"]):
        screenshot = REPOSITORY_ROOT / record["screenshot_path"]
        screenshot_hash = sha256(screenshot.read_bytes()).hexdigest()
        if screenshot_hash != record["screenshot_sha256"]:
            raise RuntimeError(f"screenshot drift: {screenshot}")
        call = client.generate(
            image_path=screenshot,
            system_prompt=VISIBLE_OBJECT_EXTRACTOR_SYSTEM_PROMPT,
            user_prompt=build_visible_object_extractor_user_prompt(
                record["task_goal"], record["extraction_rule"]
            ),
            episode_id=f"visible_object_extractor::{record['record_id']}",
            call_label="source_frame_extract",
            max_tokens=512,
        )
        parsed = None
        parse_error = None
        try:
            parsed = parse_visible_object_extraction(call.content)
        except ValueError as exc:
            parse_error = str(exc)
        result = {
            "index": index,
            "record": record,
            "finished_at": utc_now(),
            "raw_response": call.content,
            "identifiers": list(parsed.identifiers) if parsed else [],
            "parse_error": parse_error,
            "model_call": call.audit_record(),
        }
        frame_results.append(result)
        with events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")

    by_episode: dict[str, list[dict]] = {}
    for result in frame_results:
        by_episode.setdefault(result["record"]["episode_id"], []).append(result)

    episode_results: list[dict] = []
    total_tp = total_fp = total_fn = 0
    full_recall_count = 0
    for episode in manifest["episodes"]:
        expected = episode["expected_identifiers_hidden_for_scoring_only"]
        expected_by_normalized = {normalize(item): item for item in expected}
        predicted_by_normalized: dict[str, str] = {}
        for frame in by_episode.get(episode["episode_id"], []):
            for identifier in frame["identifiers"]:
                predicted_by_normalized.setdefault(normalize(identifier), identifier)
        expected_keys = set(expected_by_normalized)
        predicted_keys = set(predicted_by_normalized)
        matched_keys = expected_keys & predicted_keys
        false_keys = predicted_keys - expected_keys
        missed_keys = expected_keys - predicted_keys
        tp = len(matched_keys)
        fp = len(false_keys)
        fn = len(missed_keys)
        total_tp += tp
        total_fp += fp
        total_fn += fn
        full_recall = fn == 0
        full_recall_count += int(full_recall)
        episode_results.append(
            {
                **episode,
                "predicted_identifiers_union": [predicted_by_normalized[key] for key in sorted(predicted_keys)],
                "matched_identifiers": [expected_by_normalized[key] for key in sorted(matched_keys)],
                "false_positive_identifiers": [predicted_by_normalized[key] for key in sorted(false_keys)],
                "missed_identifiers": [expected_by_normalized[key] for key in sorted(missed_keys)],
                "true_positive": tp,
                "false_positive": fp,
                "false_negative": fn,
                "full_recall": full_recall,
            }
        )

    precision = total_tp / (total_tp + total_fp) if total_tp + total_fp else 0.0
    recall = total_tp / (total_tp + total_fn) if total_tp + total_fn else 0.0
    valid_outputs = sum(int(result["parse_error"] is None) for result in frame_results)
    total_prompt_tokens = sum(
        int((result["model_call"].get("usage") or {}).get("prompt_tokens", 0))
        for result in frame_results
    )
    total_completion_tokens = sum(
        int((result["model_call"].get("usage") or {}).get("completion_tokens", 0))
        for result in frame_results
    )
    total_latency_seconds = sum(
        float((result["model_call"].get("raven_meta") or {}).get("latency_seconds", 0.0))
        for result in frame_results
    )
    if manifest.get("manifest_version") == "visible_object_extractor_markor_v1":
        gate = {
            "exact_output_13_of_13": valid_outputs == 13,
            "micro_precision_at_least_0_80": precision >= 0.80,
            "micro_recall_at_least_0_60": recall >= 0.60,
            "full_recall_episodes_at_least_4_of_8": full_recall_count >= 4,
        }
        gate_pass: bool | None = all(gate.values())
    else:
        gate = {}
        gate_pass = None
    aggregate = {
        "run_id": run_id,
        "claim_class": manifest["claim_class"],
        "model_health": health,
        "manifest_sha256": sha256(manifest_path.read_bytes()).hexdigest(),
        "system_prompt_sha256": sha256(VISIBLE_OBJECT_EXTRACTOR_SYSTEM_PROMPT.encode("utf-8")).hexdigest(),
        "record_count": len(frame_results),
        "episode_count": len(episode_results),
        "valid_output_count": valid_outputs,
        "true_positive": total_tp,
        "false_positive": total_fp,
        "false_negative": total_fn,
        "micro_precision": precision,
        "micro_recall": recall,
        "full_recall_episode_count": full_recall_count,
        "gate": gate,
        "gate_pass": gate_pass,
        "usage": {
            "prompt_tokens": total_prompt_tokens,
            "completion_tokens": total_completion_tokens,
            "total_tokens": total_prompt_tokens + total_completion_tokens,
            "summed_model_latency_seconds": total_latency_seconds,
        },
        "episode_results": episode_results,
        "frame_results": frame_results,
    }
    (run_dir / "aggregate.json").write_text(
        json.dumps(aggregate, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "run_dir": str(run_dir),
                "valid_output_count": valid_outputs,
                "true_positive": total_tp,
                "false_positive": total_fp,
                "false_negative": total_fn,
                "micro_precision": precision,
                "micro_recall": recall,
                "full_recall_episode_count": full_recall_count,
                "gate_pass": aggregate["gate_pass"],
                "usage": aggregate["usage"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
