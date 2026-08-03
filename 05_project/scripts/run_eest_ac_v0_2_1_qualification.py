"""Run at most three frozen non-scoring v0.2.1 action-contract probes."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import random
import sys
import time
import traceback
from typing import Any

import numpy as np
from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
LOCAL_RUNTIME = REPOSITORY_ROOT / "06_local_runtime"
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(LOCAL_RUNTIME / "scripts"))

import androidworld_compat  # noqa: E402,F401
from android_world.env import env_launcher  # noqa: E402
from raven_m.eest_ac.action_adapter_v0_2_1 import EestActionAdapterV021  # noqa: E402
from raven_m.eest_ac.action_contract_v0_2_1 import DEFAULT_PROMPT_PATH  # noqa: E402
from raven_m.eest_ac.observation_v0_2 import (  # noqa: E402
    CapturedObservation,
    ObservationStabilizer,
)
from raven_m.eest_ac.qualification_v0_2_1 import (  # noqa: E402
    ActionQualificationDeciderV021,
    QualificationDecisionFailure,
)
from raven_m.models.transformers_client import TransformersClient  # noqa: E402


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _append(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(_canonical(value) + "\n")


def _load_preflight(path: Path, config_path: Path, config: dict[str, Any]) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if (
        value.get("status") != "pass"
        or value.get("study_id") != config["study_id"]
        or value.get("zero_model_generation_calls") != 0
        or value.get("runtime", {}).get("status") == "not_checked"
        or value.get("config_sha256") != _hash(config_path)
    ):
        raise RuntimeError("Passing frozen real-runtime zero-call preflight is required.")
    for item in value["locked_files"]:
        if _hash(REPOSITORY_ROOT / item["path"]) != item["sha256"]:
            raise RuntimeError(f"Implementation changed after preflight: {item['path']}")
    return value


def _save_observation(path: Path, observation: CapturedObservation) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(observation.state.pixels).save(path)


def _capture(env: Any) -> CapturedObservation:
    return ObservationStabilizer.capture(env.get_state(wait_to_stabilize=True))


def _execute(
    *,
    env: Any,
    adapter: EestActionAdapterV021,
    stabilizer: ObservationStabilizer,
    action: dict[str, Any],
    before: CapturedObservation,
) -> tuple[Any, Any]:
    height, width = before.state.pixels.shape[:2]
    mapped = adapter.map_action(action, screen_width=int(width), screen_height=int(height))
    adapter.execute(env, mapped)
    transition = stabilizer.observe_after(env=env, before=before)
    return mapped, transition


def _semantic_reset_match(reference: CapturedObservation, current: CapturedObservation) -> bool:
    left, right = reference.fingerprint, current.fingerprint
    return bool(
        left.a11y_available
        and right.a11y_available
        and left.a11y_sha256 == right.a11y_sha256
        and left.package_names == right.package_names
    )


def _reset(
    *,
    env: Any,
    adapter: EestActionAdapterV021,
    stabilizer: ObservationStabilizer,
    action: dict[str, Any],
    reference: CapturedObservation | None,
) -> tuple[CapturedObservation, dict[str, Any]]:
    before = _capture(env)
    mapped, transition = _execute(
        env=env,
        adapter=adapter,
        stabilizer=stabilizer,
        action=action,
        before=before,
    )
    final = transition.final_observation
    match = True if reference is None else _semantic_reset_match(reference, final)
    return final, {
        "action": action,
        "adapter": mapped.audit_record(),
        "transition": transition.audit_record(),
        "semantic_reference_match": match,
        "final": final.fingerprint.record(),
    }


def _prompt(probe: dict[str, Any]) -> str:
    return "\n".join(
        (
            "MODE:ACTION_CONTRACT_QUALIFICATION_V0_2_1",
            f"PROBE_ID:{probe['probe_id']}",
            f"REQUIRED_COVERAGE_CATEGORY:{probe['coverage_category']}",
            "INSTRUCTION:" + probe["instruction"],
            "Return status=continue, evidence=[], citations=[], and an intent of at most 24 characters.",
            "This is one reversible non-scoring syntax/execution probe, not a task-completion or memory experiment.",
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--adb-path", default="adb")
    parser.add_argument("--console-port", type=int, default=5554)
    parser.add_argument("--grpc-port", type=int, default=8554)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    preflight = _load_preflight(args.preflight, args.config, config)
    run_root = REPOSITORY_ROOT / config["run_root"]
    run_root.mkdir(parents=True, exist_ok=True)
    if any(run_root.iterdir()):
        raise RuntimeError("Qualification run root must be empty at launch.")
    _write(
        run_root / "qualification_start.json",
        {
            "schema_version": "eest_ac_action_qualification_start.v0_2_1",
            "study_id": config["study_id"],
            "started_at_utc": _utc_now(),
            "config_sha256": _hash(args.config),
            "preflight_sha256": _hash(args.preflight),
            "locked_files": preflight["locked_files"],
            "maximum_cells": 3,
            "auto_start_efficacy": False,
        },
    )
    random.seed(config["model"]["seed"])
    np.random.seed(config["model"]["seed"])
    client = TransformersClient(args.url)
    health = client.health()
    expected = config["model"]
    if any(health.get(key) != expected[config_key] for key, config_key in (("model", "id"), ("revision", "revision"), ("backend", "backend"))):
        raise RuntimeError("Model runtime drifted after preflight.")
    adapter = EestActionAdapterV021()
    stabilizer = ObservationStabilizer(
        delay_seconds=config["observation"]["delay_seconds"],
        max_post_observations=config["observation"]["max_post_observations"],
    )
    decider = ActionQualificationDeciderV021(
        client=client,
        system_prompt=DEFAULT_PROMPT_PATH.read_text(encoding="utf-8"),
        max_new_tokens=config["model"]["max_new_tokens"],
    )
    env = env_launcher.load_and_setup_env(
        console_port=args.console_port,
        emulator_setup=False,
        freeze_datetime=True,
        adb_path=args.adb_path,
        grpc_port=args.grpc_port,
    )
    results: list[dict[str, Any]] = []
    hard_stop = False
    stop_reason = "three_probe_limit_reached"
    try:
        home_reference, initial_reset = _reset(
            env=env,
            adapter=adapter,
            stabilizer=stabilizer,
            action=config["reset"]["action"],
            reference=None,
        )
        _write(run_root / "home_reference.json", {"observation": home_reference.fingerprint.record(), "reset": initial_reset})
        _save_observation(run_root / "home_reference.png", home_reference)
        for probe in config["probes"]:
            if hard_stop or len(results) >= 3:
                break
            random.seed(probe["seed"])
            np.random.seed(probe["seed"])
            probe_started = time.monotonic()
            cell_dir = run_root / "probes" / f"{probe['cell']:02d}_{probe['probe_id']}"
            cell_dir.mkdir(parents=True, exist_ok=False)
            _write(cell_dir / "probe_spec.json", probe)
            calls: list[dict[str, Any]] = []
            attempts: list[dict[str, Any]] = []
            failure: dict[str, Any] | None = None
            decision_record = None
            adapter_record = None
            transition_record = None
            environment_executed = False
            state_changed = False
            coverage_pass = False
            reset_record = None
            reset_pass = False
            before = None
            try:
                current, start_reset = _reset(
                    env=env,
                    adapter=adapter,
                    stabilizer=stabilizer,
                    action=config["reset"]["action"],
                    reference=home_reference,
                )
                if not start_reset["semantic_reference_match"]:
                    raise RuntimeError("START_RESET_REFERENCE_MISMATCH")
                setup_record = None
                if probe["setup_action"] is not None:
                    mapped_setup, setup_transition = _execute(
                        env=env,
                        adapter=adapter,
                        stabilizer=stabilizer,
                        action=probe["setup_action"],
                        before=current,
                    )
                    current = setup_transition.final_observation
                    setup_record = {
                        "action": probe["setup_action"],
                        "adapter": mapped_setup.audit_record(),
                        "transition": setup_transition.audit_record(),
                    }
                before = current
                _save_observation(cell_dir / "before.png", before)
                _write(
                    cell_dir / "before.json",
                    {
                        "start_reset": start_reset,
                        "setup": setup_record,
                        "observation": before.fingerprint.record(),
                    },
                )
                qualified = decider.decide(
                    image_path=cell_dir / "before.png",
                    user_prompt=_prompt(probe),
                    episode_id=f"{config['study_id']}_{probe['probe_id']}",
                    calls=calls,
                    attempts=attempts,
                    record_call=lambda record: _append(cell_dir / "model_calls.jsonl", record),
                )
                decision_record = qualified.record()
                action = qualified.parsed.decision.get("action")
                if qualified.parsed.decision.get("status") != "continue" or not isinstance(action, dict):
                    raise QualificationDecisionFailure("NO_EXECUTABLE_ACTION", "Probe did not return one continue action.")
                coverage_pass = action["type"] in probe["allowed_action_types"]
                mapped, transition = _execute(
                    env=env,
                    adapter=adapter,
                    stabilizer=stabilizer,
                    action=action,
                    before=before,
                )
                adapter_record = mapped.audit_record()
                transition_record = transition.audit_record()
                environment_executed = True
                state_changed = transition.final_observation.fingerprint.state_signature != before.fingerprint.state_signature
                _save_observation(cell_dir / "after.png", transition.final_observation)
                if config["observation"]["require_state_change"] and not state_changed:
                    raise RuntimeError("ENVIRONMENT_ACTION_NO_OBSERVED_EFFECT")
            except Exception as exc:
                code = exc.code if isinstance(exc, QualificationDecisionFailure) else str(exc) if str(exc).isupper() else type(exc).__name__
                failure = {
                    "code": code,
                    "type": type(exc).__name__,
                    "message": str(exc),
                    "traceback": traceback.format_exc(),
                }
            finally:
                try:
                    reset_observation, reset_record = _reset(
                        env=env,
                        adapter=adapter,
                        stabilizer=stabilizer,
                        action=config["reset"]["action"],
                        reference=home_reference,
                    )
                    reset_pass = bool(reset_record["semantic_reference_match"])
                    _save_observation(cell_dir / "after_reset.png", reset_observation)
                    if not reset_pass and failure is None:
                        failure = {"code": "RESET_REFERENCE_MISMATCH", "type": "ResetFailure", "message": "Reset did not match frozen home a11y state."}
                except Exception as reset_exc:
                    reset_pass = False
                    reset_record = {"error_type": type(reset_exc).__name__, "error": str(reset_exc)}
                    if failure is None:
                        failure = {"code": "RESET_EXECUTION_FAILED", "type": type(reset_exc).__name__, "message": str(reset_exc)}
            max_token_hits = sum(int(record["usage"].get("completion_tokens", 0)) >= 256 for record in calls)
            schema_truncations = max_token_hits if failure and failure["code"] in {"NO_JSON_OBJECT", "MALFORMED_JSON"} else 0
            accounting_valid = len(calls) == len(attempts) and all(item.get("completed") for item in attempts)
            hard_failure = bool(
                failure is not None
                or not environment_executed
                or not reset_pass
                or not accounting_valid
                or schema_truncations
                or adapter_record is None
            )
            result = {
                "cell": probe["cell"],
                "probe_id": probe["probe_id"],
                "coverage_category": probe["coverage_category"],
                "allowed_action_types": probe["allowed_action_types"],
                "decision": decision_record,
                "coverage_pass": coverage_pass,
                "adapter": adapter_record,
                "environment_executed": environment_executed,
                "state_changed": state_changed,
                "transition": transition_record,
                "reset": reset_record,
                "reset_pass": reset_pass,
                "model_calls": len(calls),
                "model_call_records": len(calls),
                "model_call_attempts": len(attempts),
                "model_call_accounting_valid": accounting_valid,
                "prompt_tokens": sum(int(item["usage"].get("prompt_tokens", 0)) for item in calls),
                "completion_tokens": sum(int(item["usage"].get("completion_tokens", 0)) for item in calls),
                "total_tokens": sum(int(item["usage"].get("total_tokens", 0)) for item in calls),
                "max_token_hits": max_token_hits,
                "schema_truncation_count": schema_truncations,
                "wall_time_seconds": time.monotonic() - probe_started,
                "failure": failure,
                "hard_failure": hard_failure,
            }
            _write(cell_dir / "attempts.json", attempts)
            _write(cell_dir / "probe_result.json", result)
            results.append(result)
            if hard_failure:
                hard_stop = True
                stop_reason = f"hard_failure_after_{probe['probe_id']}"
        covered = {item["coverage_category"] for item in results if item["coverage_pass"]}
        passed = bool(
            len(results) == 3
            and not hard_stop
            and covered == {"swipe", "app_navigation", "navigation_press"}
            and all(
                item["decision"] is not None
                and item["environment_executed"]
                and item["state_changed"]
                and item["reset_pass"]
                and item["schema_truncation_count"] == 0
                and item["model_call_accounting_valid"]
                and item["model_calls"] <= 2
                for item in results
            )
        )
        complete = {
            "schema_version": "eest_ac_action_qualification_complete.v0_2_1",
            "study_id": config["study_id"],
            "completed_at_utc": _utc_now(),
            "qualification_pass": passed,
            "executed_cells": len(results),
            "maximum_cells": 3,
            "covered_categories": sorted(covered),
            "hard_stop": hard_stop,
            "stop_reason": stop_reason,
            "results": results,
            "auto_started_efficacy": False,
            "next": "stop_and_analyze_only",
        }
        _write(run_root / "qualification_complete.json", complete)
        print(json.dumps({"status": "PASS" if passed else "FAIL", "cells": len(results), "stop_reason": stop_reason, "next": complete["next"]}, indent=2))
    finally:
        env.close()


if __name__ == "__main__":
    main()
