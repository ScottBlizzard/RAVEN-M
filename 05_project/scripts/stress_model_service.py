"""Run repeated near-cap multimodal requests against the fixed model backend."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from raven_m.actions.schema import ActionValidationError, parse_action_response  # noqa: E402
from raven_m.models.transformers_client import TransformersClient  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:18000")
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=10)
    parser.add_argument("--padding-words", type=int, default=9000)
    parser.add_argument("--context-cap", type=int, default=16384)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    client = TransformersClient(args.url)
    health = client.health()
    system_prompt = (
        PROJECT_ROOT / "prompts" / "executor_v0.md"
    ).read_text(encoding="utf-8")
    # "history" is a stable single-token-like fixture for this tokenizer. The
    # server-reported prompt_tokens remains the source of truth.
    padding = " ".join(["history"] * args.padding_words)
    user_prompt = (
        "TASK: Open the Contacts app.\n"
        "STEP/BUDGET: 1/10; model calls 0/20\n"
        "PREVIOUS_ACTION_AND_OBSERVED_OUTCOME: none\n"
        "MEMORY_CONTEXT: []\n"
        "CURRENT_SCREENSHOT: attached image\n"
        "The following inert text is a context-capacity fixture. Ignore its "
        "content when choosing the action:\n"
        f"{padding}\n"
        "Return one action.v1 JSON object now."
    )
    fixture_hash = sha256(user_prompt.encode("utf-8")).hexdigest()
    run_id = f"max_shape_{datetime.now().strftime('%Y%m%dT%H%M%S')}_{uuid4().hex[:8]}"
    calls = []
    for index in range(args.repeats):
        call = client.generate(
            image_path=args.image,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            episode_id=run_id,
            call_label=f"repeat_{index:02d}",
        )
        parse_status = "ok"
        first_pass = False
        try:
            parsed = parse_action_response(call.content)
            first_pass = parsed.first_pass
        except ActionValidationError as exc:
            parse_status = str(exc)
        calls.append(
            {
                "index": index,
                "prompt_tokens": call.usage.get("prompt_tokens"),
                "completion_tokens": call.usage.get("completion_tokens"),
                "latency_seconds": call.raven_meta.get("latency_seconds"),
                "peak_vram_bytes": call.raven_meta.get("peak_vram_bytes"),
                "response_sha256": call.response_sha256,
                "parse_status": parse_status,
                "first_pass": first_pass,
            }
        )
        print(
            json.dumps(
                {
                    "index": index,
                    "prompt_tokens": calls[-1]["prompt_tokens"],
                    "latency_seconds": calls[-1]["latency_seconds"],
                    "parse_status": parse_status,
                }
            ),
            flush=True,
        )

    prompt_tokens = [call["prompt_tokens"] for call in calls]
    result = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "status": (
            "ok"
            if len(calls) == args.repeats
            and all(
                isinstance(tokens, int) and tokens <= args.context_cap
                for tokens in prompt_tokens
            )
            else "failed"
        ),
        "model_service_health": health,
        "image": str(args.image.resolve()),
        "image_sha256": sha256(args.image.read_bytes()).hexdigest(),
        "prompt_fixture_sha256": fixture_hash,
        "padding_words": args.padding_words,
        "context_cap": args.context_cap,
        "repeats_requested": args.repeats,
        "repeats_completed": len(calls),
        "all_requests_without_oom": len(calls) == args.repeats,
        "max_prompt_tokens": max(prompt_tokens),
        "max_peak_vram_bytes": max(
            call["peak_vram_bytes"] or 0 for call in calls
        ),
        "calls": calls,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps({key: result[key] for key in (
        "status",
        "repeats_completed",
        "all_requests_without_oom",
        "max_prompt_tokens",
        "max_peak_vram_bytes",
    )}, indent=2))
    if result["status"] != "ok":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
