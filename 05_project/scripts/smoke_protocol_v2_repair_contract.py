"""No-GUI live-model smoke for the protocol-v2 bounded repair contract."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from raven_m.actions.schema import parse_action_response  # noqa: E402
from raven_m.controller.episode_controller import EpisodeController  # noqa: E402
from raven_m.controller.protocol_v2_guard import (  # noqa: E402
    ProtocolV2DecisionGuard,
)
from raven_m.models.transformers_client import TransformersClient  # noqa: E402


SCHEMA = PROJECT_ROOT / "schemas/action.raven.v2.schema.json"
SYSTEM_PROMPT = PROJECT_ROOT / "prompts/executor_raven_v2.md"


CASES = (
    {
        "name": "missing_required_fields",
        "goal": "Report the title visible on the current screen.",
        "original_prompt": (
            "TASK: Report the title visible on the current screen. This is an "
            "information-return task. Return one action.raven.v2 object."
        ),
        "invalid_content": (
            '{"status":"done","action":{"type":"answer","text":"visible '
            'title","text_origin":"current_screen","source_memory_ids":[]},'
            '"decision_summary":"The visible title is ready.",'
            '"state_delta":[],"completion_evidence":[{"claim":"The title is '
            'visible.","evidence":"direct_screen","memory_ids":[]}]}'
        ),
        "error": (
            "$: 'expected_outcome' is a required property; "
            "$: 'memory_citations' is a required property"
        ),
        "forbid_answer": False,
    },
    {
        "name": "ordinary_completion_forbidden_answer",
        "goal": "Create the requested item in the application.",
        "original_prompt": (
            "TASK: Create the requested item in the application. This is an "
            "ordinary GUI task, not an information-return task. The current "
            "screen is the post-save result. Return one action.raven.v2 object."
        ),
        "invalid_content": (
            '{"status":"done","action":{"type":"answer","text":"saved",'
            '"text_origin":"current_screen","source_memory_ids":[]},'
            '"expected_outcome":"The saved result remains visible.",'
            '"decision_summary":"The requested item is saved.",'
            '"state_delta":[],"memory_citations":[],'
            '"completion_evidence":[{"claim":"The requested item is saved.",'
            '"evidence":"direct_screen","memory_ids":[]}]}'
        ),
        "error": "answer is permitted only for an information-return goal.",
        "forbid_answer": True,
    },
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:18000")
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    client = TransformersClient(args.url)
    health = client.health()
    system_prompt = SYSTEM_PROMPT.read_text(encoding="utf-8")
    page_sha = sha256(args.image.read_bytes()).hexdigest()
    records = []
    for case in CASES:
        repair_prompt = EpisodeController._repair_prompt(
            case["original_prompt"],
            case["invalid_content"],
            case["error"],
            protocol_v2=True,
        )
        call = client.generate(
            image_path=args.image,
            system_prompt=system_prompt,
            user_prompt=repair_prompt,
            episode_id=f"protocol_v2_repair_smoke_{case['name']}",
            call_label="bounded_repair",
            max_tokens=256,
        )
        parsed = parse_action_response(call.content, schema_path=SCHEMA)
        guard = ProtocolV2DecisionGuard()
        guard.reset(goal=case["goal"])
        guard.validate_decision(parsed.decision, page_sha256=page_sha)
        action = parsed.decision.get("action")
        action_type = action.get("type") if isinstance(action, dict) else None
        if case["forbid_answer"] and action_type == "answer":
            raise RuntimeError(
                "Ordinary-completion repair repeated a forbidden answer."
            )
        records.append(
            {
                "name": case["name"],
                "passed": True,
                "response": call.content,
                "decision": parsed.decision,
                "strict_json_first_pass": parsed.first_pass,
                "extraction_used": parsed.extraction_used,
                "call_id": call.call_id,
                "prompt_sha256": call.prompt_sha256,
                "response_sha256": call.response_sha256,
                "usage": call.usage,
            }
        )

    result = {
        "schema_version": "protocol_v2_repair_contract_smoke.v1",
        "started_and_finished_at": utc_now(),
        "passed": all(item["passed"] for item in records),
        "model_health": health,
        "image": str(args.image.resolve()),
        "image_sha256": page_sha,
        "gui_actions_executed": 0,
        "evaluator_accessed": False,
        "cases": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
