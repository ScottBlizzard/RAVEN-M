"""Run a frozen screenshot-only completion verifier diagnostic."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from raven_m.models.vllm_client import VLLMClient  # noqa: E402
from raven_m.official_qwen_mobile.completion_verifier import (  # noqa: E402
    COMPLETION_VERIFIER_SYSTEM_PROMPT,
    build_completion_verifier_user_prompt,
    parse_completion_verdict,
)


MODEL_ID = "Qwen/Qwen3-VL-32B-Instruct"
MODEL_REVISION = "0cfaf48183f594c314753d30a4c4974bc75f3ccb"
BACKEND_ID = "qwen3_vl_32b_vllm_bf16_1xrtxpro6000_completion_verifier_v1"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:18000")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=REPOSITORY_ROOT / "runs" / "completion_verifier")
    parser.add_argument("--request-timeout-seconds", type=float, default=120.0)
    args = parser.parse_args()

    manifest_path = args.manifest.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    run_id = f"completion_verifier_{datetime.now().strftime('%Y%m%dT%H%M%S')}_{uuid4().hex[:8]}"
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
    results: list[dict] = []
    events_path = run_dir / "events.jsonl"
    for index, record in enumerate(manifest["records"]):
        screenshot = REPOSITORY_ROOT / record["screenshot_path"]
        if sha256(screenshot.read_bytes()).hexdigest() != record["screenshot_sha256"]:
            raise RuntimeError(f"screenshot drift: {screenshot}")
        started = utc_now()
        call = client.generate(
            image_path=screenshot,
            system_prompt=COMPLETION_VERIFIER_SYSTEM_PROMPT,
            user_prompt=build_completion_verifier_user_prompt(record["task_goal"]),
            episode_id=f"completion_verifier::{record['episode_id']}",
            call_label="final_screenshot_verdict",
            max_tokens=512,
        )
        parse_error = None
        parsed = None
        try:
            parsed = parse_completion_verdict(call.content)
        except ValueError as exc:
            parse_error = str(exc)
        predicted_success = parsed is not None and parsed.verdict == "CONFIRMED"
        result = {
            "index": index,
            "source": record,
            "started_at": started,
            "finished_at": utc_now(),
            "raw_response": call.content,
            "verdict": parsed.verdict if parsed else None,
            "reason": parsed.reason if parsed else None,
            "visible_evidence": list(parsed.visible_evidence) if parsed else None,
            "parse_error": parse_error,
            "predicted_success": predicted_success,
            "correct": predicted_success == bool(record["evaluator_success"]),
            "model_call": call.audit_record(),
        }
        results.append(result)
        with events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")

    tp = sum(int(item["predicted_success"] and item["source"]["evaluator_success"]) for item in results)
    tn = sum(int((not item["predicted_success"]) and (not item["source"]["evaluator_success"])) for item in results)
    fp = sum(int(item["predicted_success"] and (not item["source"]["evaluator_success"])) for item in results)
    fn = sum(int((not item["predicted_success"]) and item["source"]["evaluator_success"]) for item in results)
    invalid = sum(int(item["parse_error"] is not None) for item in results)
    tpr = tp / (tp + fn)
    tnr = tn / (tn + fp)
    aggregate = {
        "run_id": run_id,
        "claim_class": "development_contaminated_offline_diagnostic_not_held_out_efficacy",
        "model_health": health,
        "manifest_sha256": sha256(manifest_path.read_bytes()).hexdigest(),
        "system_prompt_sha256": sha256(COMPLETION_VERIFIER_SYSTEM_PROMPT.encode("utf-8")).hexdigest(),
        "record_count": len(results),
        "true_positive": tp,
        "true_negative": tn,
        "false_positive": fp,
        "false_negative": fn,
        "invalid_output_count": invalid,
        "accuracy": (tp + tn) / len(results),
        "true_success_acceptance": tpr,
        "false_success_rejection": tnr,
        "balanced_accuracy": (tpr + tnr) / 2,
        "total_model_calls": len(results),
        "results": results,
    }
    (run_dir / "aggregate.json").write_text(
        json.dumps(aggregate, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"run_dir": str(run_dir), **{key: aggregate[key] for key in (
        "record_count", "true_positive", "true_negative", "false_positive",
        "false_negative", "invalid_output_count", "accuracy",
        "true_success_acceptance", "false_success_rejection", "balanced_accuracy"
    )}}, indent=2))


if __name__ == "__main__":
    main()
