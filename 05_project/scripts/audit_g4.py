"""Audit G4 baseline-family budgets, triggers, and leakage invariants."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
G4_ROOT = (
    REPOSITORY_ROOT
    / "runs"
    / "baseline_dev_g4"
    / "baseline_dev_g4_20260723"
)
G3_SUMMARY = (
    REPOSITORY_ROOT
    / "runs"
    / "dev_nonhard_g3"
    / "g3_b0_executor_v1_20260723"
    / "suite_summary.json"
)
OUTPUT = PROJECT_ROOT / "metadata" / "g4_audit.json"


def calls(summary: dict[str, Any]) -> list[dict[str, Any]]:
    values = []
    for step in summary["steps"]:
        values.extend(step.get("model_calls", []))
        values.extend(step.get("history_update", {}).get("model_calls", []))
    return values


def main() -> None:
    suite = json.loads(
        (G4_ROOT / "suite_summary.json").read_text(encoding="utf-8")
    )
    g3 = json.loads(G3_SUMMARY.read_text(encoding="utf-8"))
    errors: list[str] = []
    audits = []
    episode_ids = {item["episode_id"] for item in suite["episodes"]}
    episode_dirs = sorted((G4_ROOT / "episodes").iterdir())
    for episode_dir in episode_dirs:
        if not episode_dir.is_dir() or not (
            episode_dir / "episode.json"
        ).exists():
            continue
        episode = json.loads(
            (episode_dir / "episode.json").read_text(encoding="utf-8")
        )
        variant = episode["variant"]
        if episode["history_variant"] != variant:
            errors.append(f"{episode['episode_id']}: history variant mismatch")
        prompt_tokens = [
            int(call.get("usage", {}).get("prompt_tokens", 0))
            for call in calls(episode)
        ]
        if any(value + 256 > 8192 for value in prompt_tokens):
            errors.append(f"{episode['episode_id']}: context cap exceeded")
        for step in episode["steps"]:
            if len(step.get("model_calls", [])) > 2:
                errors.append(
                    f"{episode['episode_id']}: >1 executor repair at "
                    f"step {step['step']}"
                )
            history_calls = step.get("history_update", {}).get(
                "model_calls", []
            )
            if len(history_calls) > 2:
                errors.append(
                    f"{episode['episode_id']}: >1 history repair at "
                    f"step {step['step']}"
                )
            if variant in {"B1", "B2"} and history_calls:
                errors.append(
                    f"{episode['episode_id']}: unexpected history model call"
                )
            if (
                variant == "B3"
                and history_calls
                and (step["step"] + 1) % 5 != 0
            ):
                errors.append(
                    f"{episode['episode_id']}: B3 summary off frozen trigger"
                )
            prompt = step.get("user_prompt", "")
            forbidden = {
                "evaluator_reward",
                "evaluator_result",
                "official evaluator output",
            }
            if any(term in prompt.lower() for term in forbidden):
                errors.append(
                    f"{episode['episode_id']}: evaluator leakage in prompt"
                )
            other_ids = episode_ids - {episode["episode_id"]}
            if any(other_id in prompt for other_id in other_ids):
                errors.append(
                    f"{episode['episode_id']}: cross-episode ID in prompt"
                )
            for image in step.get("history_context", {}).get("images", []):
                if not (episode_dir / image["path"]).is_file() and not (
                    episode_dir / "history_thumbnails" / image["path"]
                ).is_file():
                    errors.append(
                        f"{episode['episode_id']}: missing history image "
                        f"{image['path']}"
                    )
        audits.append(
            {
                "episode_id": episode["episode_id"],
                "variant": variant,
                "success": episode["success"],
                "decision_attempt_count": episode["decision_attempt_count"],
                "model_call_count": episode["model_call_count"],
                "history_model_call_count": episode[
                    "history_model_call_count"
                ],
                "max_prompt_tokens": max(prompt_tokens, default=0),
            }
        )
    if not suite["g4_history_baselines_passed"]:
        errors.append("G4 suite acceptance flag is false.")
    if not (
        g3["variant"] == "B0"
        and g3["episode_count"] >= 5
        and g3["parse_gate_passed"]
        and g3["infrastructure_or_controller_error_count"] == 0
    ):
        errors.append("B0 G3 evidence does not satisfy the G4 prerequisite.")
    reset = json.loads(
        (
            PROJECT_ROOT
            / "metadata"
            / "reset_determinism_g4_final.json"
        ).read_text(encoding="utf-8")
    )
    if reset["status"] != "passed":
        errors.append("Reset audit is not passed.")
    result = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if not errors else "failed",
        "g4_suite_id": suite["suite_id"],
        "b0_suite_id": g3["suite_id"],
        "b0_episode_count": g3["episode_count"],
        "history_episode_count": suite["episode_count"],
        "reset_lifecycle_runs": reset["lifecycle_runs"],
        "checks": {
            "context_cap": "prompt_tokens + 256 <= 8192 for every call",
            "repair_limit": "at most one repair per executor/history decision",
            "summary_trigger": "B3 only at completed steps 5, 10, ...",
            "evaluator_leakage": "forbidden evaluator fields absent from prompts",
            "cross_episode_leakage": "other episode IDs absent from prompts",
            "history_images": "every referenced image exists in episode dir",
        },
        "variant_results": suite["variant_results"],
        "episodes": audits,
        "errors": errors,
    }
    OUTPUT.write_text(
        json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if errors:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
