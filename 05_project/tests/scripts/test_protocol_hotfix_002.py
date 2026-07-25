from pathlib import Path
import sys


SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import run_frozen_hard_suite_hotfix_002 as hotfix  # noqa: E402


def test_authorization_requires_three_matching_model_outages() -> None:
    manifest = {
        "authorized_schedule_cell": {
            "suite_id": "suite",
            "sequence": 13,
            "pair_id": "pair",
            "variant": "B2",
            "task_class": "Task",
        }
    }
    schedule = {
        "sequence": 13,
        "pair_id": "pair",
        "variant": "B2",
        "task_class": "Task",
    }
    attempts = [
        {
            "attempt": number,
            "code": "INFRA_MODEL_UNAVAILABLE",
            "goal_sha256": "goal",
            "params_sha256": "params",
        }
        for number in (1, 2, 3)
    ]
    assert hotfix.validate_authorized_exhaustion(
        manifest,
        suite_id="suite",
        schedule_record=schedule,
        attempts=attempts,
    ) == ("goal", "params")


def test_stability_gate_requires_consecutive_health(
    tmp_path: Path,
    monkeypatch,
) -> None:
    health = {
        "status": "ok",
        "loaded": True,
        "backend": hotfix.frozen.EXPECTED_BACKEND,
        "revision": hotfix.frozen.EXPECTED_REVISION,
    }

    class FlappingClient:
        def __init__(self) -> None:
            self.responses = iter(
                [
                    ConnectionError("flap"),
                    health,
                    health,
                    health,
                ]
            )

        def health(self):
            response = next(self.responses)
            if isinstance(response, Exception):
                raise response
            return response

    monkeypatch.setattr(
        hotfix,
        "ORIGINAL_WAIT_FOR_MODEL_SERVICE",
        lambda *args, **kwargs: health,
    )
    result = hotfix.wait_for_model_service_stable(
        FlappingClient(),
        recovery_dir=tmp_path,
        max_wait_seconds=100,
        poll_seconds=1,
        sleep_fn=lambda _: None,
        monotonic_fn=lambda: 0.0,
        stable_checks=3,
    )
    assert result["backend"] == hotfix.frozen.EXPECTED_BACKEND
    audit = (tmp_path / "model_stability_gate.json").read_text(
        encoding="utf-8"
    )
    assert '"status": "stable"' in audit
    assert '"healthy": false' in audit
