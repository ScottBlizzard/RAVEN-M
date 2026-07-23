from raven_m.controller.episode_controller import classify_failure_code


def test_native_success_overrides_model_output_failure_code() -> None:
    code = classify_failure_code(
        error_record=None,
        model_output_error={"type": "ActionValidationError"},
        evaluator_reward=1.0,
        termination_reason="model_output_invalid_after_repair",
    )
    assert code is None


def test_infrastructure_error_remains_primary() -> None:
    code = classify_failure_code(
        error_record={"type": "RuntimeError"},
        model_output_error=None,
        evaluator_reward=None,
        termination_reason="infrastructure_or_controller_error",
    )
    assert code == "INFRA_OR_CONTROLLER"
