#!/usr/bin/env python3
"""Zero-generation replay and development audit for stabilized LRER V2."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "implementation/src")]

from implementation.scripts.materialize_sys_r2_lrer_v2_fixture import (  # noqa: E402
    CONFIG_PATH,
    OUTPUT_PATH as FIXTURE_PATH,
    content_sha256,
    file_sha256,
)
from implementation.scripts.replay_sys_r2_lrer import (  # noqa: E402
    _phrase_coverage,
    first_opportunity,
)
from raven_m.official_qwen_mobile.r15_derived_evidence_consolidation_v2 import (  # noqa: E402
    EXPERIMENT_ID,
    POST_ACTION_SETTLE_SECONDS,
    SYSTEM_ID,
    StabilizedLateRawEvidenceRehydrationPolicy,
)


OUTPUT_PATH = ROOT / "evidence/sys_r2_lrer_v2/SYS_R2_LRER_V2_OFFLINE_REPLAY_REPORT.json"


def replay(fixture_path: Path = FIXTURE_PATH) -> dict[str, Any]:
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    if fixture.get("schema") != "sys_r2_lrer_v2_replay_fixture_v1":
        errors.append("fixture_schema")
    if fixture.get("generation_calls") != 0:
        errors.append("fixture_generation_calls")
    if fixture.get("content_sha256") != content_sha256(fixture):
        errors.append("fixture_hash")
    if fixture.get("config_sha256") != file_sha256(CONFIG_PATH):
        errors.append("fixture_config_drift")

    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if config.get("system_id") != SYSTEM_ID:
        errors.append("config_system_id")
    if config.get("experiment_id") != EXPERIMENT_ID:
        errors.append("config_experiment_id")
    if config.get("post_action_settle_seconds") != POST_ACTION_SETTLE_SECONDS:
        errors.append("config_settle_seconds")
    if config.get("post_action_state_capture_count") != 1:
        errors.append("config_state_capture_count")

    r2_rows: list[dict[str, Any]] = []
    for episode in fixture.get("v1_r2_episodes") or []:
        opportunity = first_opportunity(episode)
        r2_rows.append(
            {
                "task_name": episode["task_name"],
                "episode_id": episode["episode_id"],
                "historical_reward": episode["historical_reward"],
                "opportunity": opportunity,
            }
        )
    if [row["task_name"] for row in r2_rows] != list(fixture.get("fixed_seven") or []):
        errors.append("r2_task_order")
    r2_browser = r2_rows[0] if r2_rows else None
    six = r2_rows[1:]
    if not r2_browser or r2_browser["task_name"] != "BrowserMultiply":
        errors.append("r2_browser_missing")
    elif not r2_browser["opportunity"].get("triggered"):
        errors.append("r2_browser_opportunity_missing")
    elif int(r2_browser["opportunity"].get("trigger_step") or -1) != 18:
        errors.append("r2_browser_trigger_step")
    if len(six) != 6 or any(row["opportunity"].get("triggered") for row in six):
        errors.append("r2_six_success_not_silent")

    r15 = dict(fixture.get("r15_browser") or {})
    r15_opportunity = first_opportunity(r15) if r15 else {}
    r15_coverage = _phrase_coverage(r15_opportunity)
    if not r15_opportunity.get("triggered"):
        errors.append("r15_opportunity_missing")
    if not r15_coverage.get("all_expected_values_rendered"):
        errors.append("r15_value_coverage")

    development = dict(fixture.get("development_audit") or {})
    expected_development = {
        "first_value_step": 15,
        "all_value_steps": [15, 16, 17, 18, 19],
        "first_result_action_step": 21,
        "first_result_remaining_slots": 0,
        "lrer_eligible_count": 0,
        "lrer_blocked_count": 0,
        "cross_activity_stale_capture_steps": [3, 7],
        "settle_policy_is_counterfactual": True,
    }
    if development != expected_development:
        errors.append("sealed_live_development_audit_drift")

    policy = StabilizedLateRawEvidenceRehydrationPolicy(
        text_delta_counter=lambda _base, _final: 1
    )
    policy_audit = policy.audit_record()
    if policy_audit.get("system_id") != SYSTEM_ID:
        errors.append("runtime_policy_system_id")
    if (policy_audit.get("visible_frame_settle") or {}).get("seconds") != 1.0:
        errors.append("runtime_policy_settle_identity")

    payload: dict[str, Any] = {
        "schema": "sys_r2_lrer_v2_offline_replay_v1",
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "analysis_type": "CPU_ONLY_ZERO_GENERATION_DEVELOPMENT_REPLAY",
        "generation_calls": 0,
        "system_id": SYSTEM_ID,
        "experiment_id": EXPERIMENT_ID,
        "fixed_seven": list(fixture.get("fixed_seven") or []),
        "fixture_content_sha256": fixture.get("content_sha256"),
        "inherited_v1_fixture_content_sha256": fixture.get(
            "inherited_v1_fixture_content_sha256"
        ),
        "runtime_policy_module": (
            "raven_m.official_qwen_mobile."
            "r15_derived_evidence_consolidation_v2"
        ),
        "visible_frame_settle": {
            "seconds": POST_ACTION_SETTLE_SECONDS,
            "single_capture_after_sleep": True,
            "uses_hidden_ui_or_activity": False,
            "additional_model_calls": 0,
            "additional_actions": 0,
            "historical_effect_claimed": False,
        },
        "development_live_browser": {
            "episode_id": (fixture.get("v1_live_browser") or {}).get("episode_id"),
            "historical_reward": (fixture.get("v1_live_browser") or {}).get(
                "historical_reward"
            ),
            "classification": "VALID_FAILURE_COMPONENT_SILENT_ZERO_OPPORTUNITY",
            **development,
        },
        "r2_browser": r2_browser,
        "r15_browser": {
            "episode_id": r15.get("episode_id"),
            "historical_reward": r15.get("historical_reward"),
            "opportunity": r15_opportunity,
            "value_coverage": r15_coverage,
        },
        "historical_successes": [
            {
                "task_name": row["task_name"],
                "episode_id": row["episode_id"],
                "historical_reward": row["historical_reward"],
                "lrer_opportunity_count": int(
                    bool(row["opportunity"].get("triggered"))
                ),
            }
            for row in six
        ],
        "totals": {
            "r2_episode_count": len(r2_rows),
            "r2_six_success_lrer_opportunity_count": sum(
                int(bool(row["opportunity"].get("triggered"))) for row in six
            ),
            "r2_browser_lrer_opportunity_count": int(
                bool(r2_browser and r2_browser["opportunity"].get("triggered"))
            ),
            "r15_browser_lrer_opportunity_count": int(
                bool(r15_opportunity.get("triggered"))
            ),
            "sealed_live_browser_lrer_opportunity_count": 0,
            "generation_calls": 0,
        },
    }
    return {**payload, "content_sha256": content_sha256(payload)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, default=FIXTURE_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()
    report = replay(args.fixture.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "errors": report["errors"],
                "totals": report["totals"],
                "content_sha256": report["content_sha256"],
            },
            indent=2,
        )
    )
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
