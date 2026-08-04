"""Zero-generation-call qualification of the frozen v0.2.2 settling window."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
LOCAL_RUNTIME = REPOSITORY_ROOT / "06_local_runtime"
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(LOCAL_RUNTIME / "scripts"))

import androidworld_compat  # noqa: E402,F401
from raven_m.eest_ac.action_adapter_v0_2_2 import EestActionAdapterV022  # noqa: E402
from raven_m.eest_ac.action_contract_v0_2_2 import load_contract  # noqa: E402
from raven_m.eest_ac.observation_policy_v0_2_2 import (  # noqa: E402
    QualificationObservationStabilizerV022,
    audit_stable_change_v0_2_2,
)
from raven_m.eest_ac.observation_v0_2 import (  # noqa: E402
    CapturedObservation,
    ObservationStabilizer,
)
from raven_m.eest_ac.runtime_v0_2_2 import (  # noqa: E402
    assert_frozen_adb_server_port,
    load_and_setup_env,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _capture(env: Any) -> CapturedObservation:
    return ObservationStabilizer.capture(env.get_state(wait_to_stabilize=True))


def _execute(
    *,
    env: Any,
    adapter: EestActionAdapterV022,
    stabilizer: ObservationStabilizer,
    action: dict[str, Any],
    before: CapturedObservation,
) -> tuple[CapturedObservation, dict[str, Any]]:
    height, width = before.state.pixels.shape[:2]
    mapped = adapter.map_action(action, screen_width=int(width), screen_height=int(height))
    adapter.execute(env, mapped)
    transition = stabilizer.observe_after(env=env, before=before)
    return transition.final_observation, {
        "action": action,
        "adapter": mapped.audit_record(),
        "transition": transition.audit_record(),
    }


def _setup(
    *,
    env: Any,
    adapter: EestActionAdapterV022,
    stabilizer: ObservationStabilizer,
    actions: list[dict[str, Any]],
) -> tuple[CapturedObservation, list[dict[str, Any]]]:
    current = _capture(env)
    records = []
    for action in actions:
        current, record = _execute(
            env=env,
            adapter=adapter,
            stabilizer=stabilizer,
            action=action,
            before=current,
        )
        records.append(record)
    return current, records


def _case(
    *,
    env: Any,
    adapter: EestActionAdapterV022,
    stabilizer: ObservationStabilizer,
    case_id: str,
    setup_actions: list[dict[str, Any]],
    test_action: dict[str, Any],
    expected_stable_change: bool,
    expected_reason: str | None,
) -> dict[str, Any]:
    before, setup = _setup(
        env=env,
        adapter=adapter,
        stabilizer=stabilizer,
        actions=[{"type": "press_home"}, *setup_actions],
    )
    height, width = before.state.pixels.shape[:2]
    mapped = adapter.map_action(test_action, screen_width=int(width), screen_height=int(height))
    adapter.execute(env, mapped)
    transition = stabilizer.observe_after(env=env, before=before)
    audit = audit_stable_change_v0_2_2(before=before, transition=transition)
    passed = audit.stable_change is expected_stable_change
    if expected_reason is not None:
        passed = passed and expected_reason in audit.reasons
    return {
        "case_id": case_id,
        "development_measurement_evidence_only": True,
        "live_evidence_eligible": False,
        "setup": setup,
        "before": before.fingerprint.record(),
        "test_action": test_action,
        "adapter": mapped.audit_record(),
        "raw_transition": transition.audit_record(),
        "settling_audit": audit.record(),
        "expected_stable_change": expected_stable_change,
        "expected_reason": expected_reason,
        "passed": passed,
    }


def _adb_serial(adb_path: str, port: int) -> str:
    result = subprocess.run(
        [adb_path, "-P", str(port), "-s", "emulator-5554", "get-serialno"],
        capture_output=True,
        text=True,
        check=True,
        timeout=20,
    )
    return result.stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--adb-path", required=True)
    parser.add_argument("--adb-server-port", type=int, required=True)
    parser.add_argument("--console-port", type=int, default=5554)
    parser.add_argument("--grpc-port", type=int, default=8554)
    args = parser.parse_args()
    contract = load_contract()
    observation = contract["qualification_observation_contract"]
    assert_frozen_adb_server_port(configured=5038, supplied=args.adb_server_port)
    adb_binary = Path(args.adb_path).resolve()
    env = load_and_setup_env(
        console_port=args.console_port,
        emulator_setup=False,
        freeze_datetime=True,
        adb_path=str(adb_binary),
        adb_server_port=args.adb_server_port,
        grpc_port=args.grpc_port,
    )
    adapter = EestActionAdapterV022()
    stabilizer = QualificationObservationStabilizerV022()
    try:
        cases = [
            _case(
                env=env,
                adapter=adapter,
                stabilizer=stabilizer,
                case_id="stable_positive_settings_scroll",
                setup_actions=[
                    {"type": "open_app", "app_name": "Settings"},
                    {"type": "swipe", "x": 0.5, "y": 0.22, "x2": 0.5, "y2": 0.82, "duration_ms": 500},
                    {"type": "swipe", "x": 0.5, "y": 0.22, "x2": 0.5, "y2": 0.82, "duration_ms": 500},
                ],
                test_action={"type": "swipe", "x": 0.5, "y": 0.8, "x2": 0.5, "y2": 0.2, "duration_ms": 500},
                expected_stable_change=True,
                expected_reason=None,
            ),
            _case(
                env=env,
                adapter=adapter,
                stabilizer=stabilizer,
                case_id="dynamic_negative_camera",
                setup_actions=[{"type": "open_app", "app_name": "camera"}],
                test_action={"type": "wait", "duration_ms": 1000},
                expected_stable_change=False,
                expected_reason="terminal_pixels_unsettled",
            ),
            _case(
                env=env,
                adapter=adapter,
                stabilizer=stabilizer,
                case_id="a11y_missing_negative_notification_shade",
                setup_actions=[{"type": "open_app", "app_name": "dialer"}],
                test_action={"type": "swipe", "x": 0.5, "y": 0.0, "x2": 0.5, "y2": 0.82, "duration_ms": 500},
                expected_stable_change=False,
                expected_reason="terminal_a11y_unavailable",
            ),
        ]
        _, final_reset = _setup(
            env=env,
            adapter=adapter,
            stabilizer=stabilizer,
            actions=[{"type": "press_home"}],
        )
    finally:
        env.close()
    if not all(item["passed"] for item in cases):
        _write(args.output, {
            "schema_version": "eest_ac_settling_window_qualification.v0_2_2",
            "status": "fail",
            "zero_model_generation_calls": 0,
            "cases": cases,
        })
        raise RuntimeError("Frozen settling-window scene qualification failed.")
    result = {
        "schema_version": "eest_ac_settling_window_qualification.v0_2_2",
        "status": "pass",
        "created_at_utc": _utc_now(),
        "zero_model_generation_calls": 0,
        "measurement_definition_issue_discovered_during_zero_call_qualification": True,
        "settings_precheck_counts_as_live_evidence": False,
        "policy": observation,
        "runtime": {
            "adb_server_port": args.adb_server_port,
            "fallback_to_default_port": False,
            "adb_binary": str(adb_binary),
            "adb_binary_sha256": _hash(adb_binary),
            "device_serial": _adb_serial(str(adb_binary), args.adb_server_port),
        },
        "cases": cases,
        "final_reset": final_reset,
    }
    _write(args.output, result)
    print(json.dumps({
        "status": "pass",
        "zero_model_generation_calls": 0,
        "cases": [item["case_id"] for item in cases],
        "output": str(args.output),
    }, indent=2))


if __name__ == "__main__":
    main()
