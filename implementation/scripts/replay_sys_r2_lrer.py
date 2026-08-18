#!/usr/bin/env python3
"""Replay SYS-R2-LRER trigger timing and source windows without generation."""

from __future__ import annotations

import argparse
import inspect
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "implementation/src")]

from implementation.scripts.materialize_sys_r2_lrer_fixture import (  # noqa: E402
    CONFIG_PATH,
    canonical_sha256,
    file_sha256,
)
from raven_m.official_qwen_mobile.r15_derived_evidence_consolidation import (  # noqa: E402
    EXPERIMENT_ID,
    EvidenceRehydrationIntegrityError,
    MAX_RAW_ACTIONS,
    SYSTEM_ID,
    LateRawEvidenceRehydrationPolicy,
)


FIXTURE_PATH = ROOT / "evidence/sys_r2_lrer/SYS_R2_LRER_REPLAY_FIXTURE.json"
OUTPUT_PATH = ROOT / "evidence/sys_r2_lrer/SYS_R2_LRER_OFFLINE_REPLAY_REPORT.json"
EXPECTED_BROWSER_VALUES = ("1", "8", "10", "7", "2")
EXPECTED_BROWSER_PHRASES = tuple(f"number {value} displayed" for value in EXPECTED_BROWSER_VALUES)


def _review(policy: LateRawEvidenceRehydrationPolicy, kwargs: dict[str, Any]) -> dict[str, Any]:
    """Pass every context field accepted by the frozen runtime policy."""

    parameters = inspect.signature(policy.review_result_action).parameters
    supported = {key: value for key, value in kwargs.items() if key in parameters}
    return dict(policy.review_result_action(**supported))


def _source_row(step: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_step": int(step["step"]),
        "thought": str(step.get("thought") or ""),
        "action_summary": str(step["action_summary"]),
        "source_response_sha256": str(step["source_response_sha256"]),
    }


def first_opportunity(episode: dict[str, Any]) -> dict[str, Any]:
    policy = LateRawEvidenceRehydrationPolicy(text_delta_counter=lambda _a, _b: 0)
    prior_executed: list[dict[str, Any]] = []
    native_max_steps = int(episode["native_max_steps"])
    for step in episode["steps"]:
        request_step = int(step["step"])
        canonical = step.get("canonical_action")
        assessment = _review(
            policy,
            {
                "proposed_action": canonical if isinstance(canonical, dict) else None,
                "terminal_status": step.get("terminal_status"),
                "executed_action_count": len(prior_executed),
                "native_max_steps": native_max_steps,
                "remaining_native_decision_slots": native_max_steps - request_step - 1,
                "request_step": request_step,
                "goal": episode["task_goal"],
            },
        )
        if bool(assessment.get("blocked")):
            source_window = prior_executed[-MAX_RAW_ACTIONS:]
            deferred_hash = str(step["source_response_sha256"])
            deferred_summary = str(step["action_summary"])
            source_hashes = [str(row["source_response_sha256"]) for row in source_window]
            source_actions = [str(row["action_summary"]) for row in source_window]
            preparation_error = None
            try:
                prepared = policy.prepare_direct_injection(
                    {
                        "request_step": request_step + 1,
                        "recent_prior_executed_responses": [
                            {
                                "source_step": row["source_step"],
                                "thought": row["thought"],
                                "action_summary": row["action_summary"],
                                "response_sha256": row["source_response_sha256"],
                            }
                            for row in source_window
                        ],
                    }
                )
                if prepared is None:
                    raise EvidenceRehydrationIntegrityError("prepare_returned_none")
            except EvidenceRehydrationIntegrityError as exc:
                prepared = None
                preparation_error = f"{type(exc).__name__}:{exc}"
            injection_text = str((prepared or {}).get("injection_text") or "")
            return {
                "triggered": True,
                "trigger_step": request_step,
                "assessment": assessment,
                "deferred_proposal": {
                    "action_family": (
                        str(canonical.get("type"))
                        if isinstance(canonical, dict)
                        else step.get("terminal_status")
                    ),
                    "action_summary": deferred_summary,
                    "response_sha256": deferred_hash,
                },
                "source_window_count": len(source_window),
                "source_steps": [int(row["source_step"]) for row in source_window],
                "source_response_sha256s": source_hashes,
                "source_action_summaries": source_actions,
                "prepared_injection": {
                    "ticket_id": (prepared or {}).get("ticket_id"),
                    "text": injection_text,
                    "text_sha256": (prepared or {}).get("exact_injected_text_sha256"),
                    "source_steps": (prepared or {}).get("source_steps"),
                    "source_response_sha256s": (prepared or {}).get(
                        "source_response_sha256s"
                    ),
                    "preparation_error": preparation_error,
                },
                "deferred_proposal_excluded": bool(
                    deferred_hash not in source_hashes
                    and deferred_summary not in source_actions
                    and deferred_summary not in injection_text
                ),
            }
        if bool(step.get("executed")):
            prior_executed.append(_source_row(step))
    return {
        "triggered": False,
        "trigger_step": None,
        "assessment": None,
        "deferred_proposal": None,
        "source_window_count": 0,
        "source_steps": [],
        "source_response_sha256s": [],
        "source_action_summaries": [],
        "prepared_injection": None,
        "deferred_proposal_excluded": True,
    }


def _phrase_coverage(opportunity: dict[str, Any]) -> dict[str, Any]:
    source = "\n".join(opportunity.get("source_action_summaries") or []).casefold()
    rendered = str(
        (opportunity.get("prepared_injection") or {}).get("text") or ""
    ).casefold()
    found = [
        value
        for value, phrase in zip(EXPECTED_BROWSER_VALUES, EXPECTED_BROWSER_PHRASES, strict=True)
        if phrase in source
    ]
    rendered_found = [
        value
        for value, phrase in zip(EXPECTED_BROWSER_VALUES, EXPECTED_BROWSER_PHRASES, strict=True)
        if phrase in rendered
    ]
    return {
        "expected_values": list(EXPECTED_BROWSER_VALUES),
        "exact_observation_phrases": list(EXPECTED_BROWSER_PHRASES),
        "found_values": found,
        "all_expected_values_covered": found == list(EXPECTED_BROWSER_VALUES),
        "rendered_found_values": rendered_found,
        "all_expected_values_rendered": rendered_found
        == list(EXPECTED_BROWSER_VALUES),
    }


def replay(fixture_path: Path = FIXTURE_PATH) -> dict[str, Any]:
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    if fixture.get("schema") != "sys_r2_lrer_replay_fixture_v1":
        errors.append("fixture_schema")
    if fixture.get("generation_calls") != 0:
        errors.append("fixture_generation_calls")
    if fixture.get("content_sha256") != canonical_sha256(fixture):
        errors.append("fixture_hash")
    if fixture.get("config_sha256") != file_sha256(CONFIG_PATH):
        errors.append("fixture_config_drift")

    r2_rows: list[dict[str, Any]] = []
    for episode in fixture.get("r2_episodes") or []:
        opportunity = first_opportunity(episode)
        r2_rows.append(
            {
                "task_name": episode["task_name"],
                "episode_id": episode["episode_id"],
                "historical_reward": episode["historical_reward"],
                "opportunity": opportunity,
            }
        )
    r15_episode = dict(fixture.get("r15_browser") or {})
    r15_opportunity = first_opportunity(r15_episode) if r15_episode else {}
    r15_coverage = _phrase_coverage(r15_opportunity)

    task_order = list(fixture.get("task_order") or [])
    if [row["task_name"] for row in r2_rows] != task_order:
        errors.append("r2_task_order")
    browser = next((row for row in r2_rows if row["task_name"] == "BrowserMultiply"), None)
    if browser is None or not browser["opportunity"]["triggered"]:
        errors.append("r2_browser_trigger_missing")
    elif int(browser["opportunity"]["trigger_step"]) != 18:
        errors.append("r2_browser_trigger_step")
    elif not browser["opportunity"]["deferred_proposal_excluded"]:
        errors.append("r2_deferred_proposal_leaked")
    if browser and browser["opportunity"]["prepared_injection"].get(
        "preparation_error"
    ):
        errors.append("r2_browser_injection_prepare")
    six = [row for row in r2_rows if row["task_name"] != "BrowserMultiply"]
    six_triggered = [row["task_name"] for row in six if row["opportunity"]["triggered"]]
    if len(six) != 6:
        errors.append("r2_six_panel_size")
    if six_triggered:
        errors.append("r2_six_success_triggered")
    if not r15_opportunity.get("triggered"):
        errors.append("r15_browser_trigger_missing")
    elif int(r15_opportunity.get("trigger_step")) != 18:
        errors.append("r15_browser_trigger_step")
    if int(r15_opportunity.get("source_window_count") or 0) != MAX_RAW_ACTIONS:
        errors.append("r15_prior_window_count")
    if not r15_opportunity.get("deferred_proposal_excluded"):
        errors.append("r15_deferred_proposal_leaked")
    if (r15_opportunity.get("prepared_injection") or {}).get("preparation_error"):
        errors.append("r15_injection_prepare")
    if not r15_coverage["all_expected_values_covered"]:
        errors.append("r15_value_coverage")
    if not r15_coverage["all_expected_values_rendered"]:
        errors.append("r15_rendered_value_coverage")

    payload: dict[str, Any] = {
        "schema": "sys_r2_lrer_offline_replay_v1",
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "analysis_type": "CPU_ONLY_ZERO_GENERATION_DEVELOPMENT_REPLAY",
        "generation_calls": 0,
        "system_id": SYSTEM_ID,
        "experiment_id": EXPERIMENT_ID,
        "fixed_seven": task_order,
        "fixture_content_sha256": fixture.get("content_sha256"),
        "runtime_policy_module": (
            "raven_m.official_qwen_mobile.r15_derived_evidence_consolidation"
        ),
        "expectation": {
            "r2_browser_trigger_step": 18,
            "r2_six_success_trigger_count": 0,
            "r15_prior_raw_action_count": MAX_RAW_ACTIONS,
            "r15_expected_values": list(EXPECTED_BROWSER_VALUES),
            "deferred_proposal_must_be_excluded": True,
        },
        "totals": {
            "r2_episode_count": len(r2_rows),
            "r2_trigger_count": sum(
                int(row["opportunity"]["triggered"]) for row in r2_rows
            ),
            "r2_six_success_trigger_count": len(six_triggered),
            "r15_trigger_count": int(bool(r15_opportunity.get("triggered"))),
            "generation_calls": 0,
        },
        "r2_browser": browser,
        "r2_six_successes": six,
        "browser": {
            "r2_opportunity_count": int(
                bool(browser and browser["opportunity"]["triggered"])
            ),
            "r2_trigger_step": (
                browser["opportunity"]["trigger_step"] if browser else None
            ),
            "r15_opportunity_count": int(bool(r15_opportunity.get("triggered"))),
            "r15_trigger_step": r15_opportunity.get("trigger_step"),
            "r15_source_steps": r15_opportunity.get("source_steps") or [],
            "r15_all_five_observations_present": r15_coverage[
                "all_expected_values_covered"
            ] and r15_coverage[
                "all_expected_values_rendered"
            ],
            "r15_found_values": r15_coverage["found_values"],
            "deferred_response_excluded": bool(
                r15_opportunity.get("deferred_proposal_excluded")
            ),
        },
        "historical_successes": [
            {
                "task_name": row["task_name"],
                "episode_id": row["episode_id"],
                "historical_reward": row["historical_reward"],
                "opportunity_count": int(row["opportunity"]["triggered"]),
                "trigger_step": row["opportunity"]["trigger_step"],
            }
            for row in six
        ],
        "r15_browser": {
            "task_name": r15_episode.get("task_name"),
            "episode_id": r15_episode.get("episode_id"),
            "historical_reward": r15_episode.get("historical_reward"),
            "opportunity": r15_opportunity,
            "value_coverage": r15_coverage,
        },
    }
    return {**payload, "content_sha256": canonical_sha256(payload)}


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
