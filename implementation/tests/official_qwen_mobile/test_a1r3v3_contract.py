from raven_m.official_qwen_mobile import a1r3v3_contract as contract


def test_identity_order_and_gates_are_frozen() -> None:
    assert contract.MECHANISM_ID == "a1r3v3_one_shot_controller_nonprogress_receipt_v1"
    assert contract.EXPERIMENT_ID == "A1R3V3_OSCNR_QWEN3VL32B_AW_HARD_T20260806_G3407_V1"
    assert len(contract.CAPABILITY_GATE_TASKS) == 6
    assert len(contract.FULL_TASK_ORDER) == 19
    assert contract.FULL_TASK_ORDER[:6] == contract.CAPABILITY_GATE_TASKS


def test_source_closure_is_exact_and_generated_evidence_is_excluded() -> None:
    assert len(contract.SOURCE_FILES) == len(set(contract.SOURCE_FILES))
    assert all((contract.REPOSITORY_ROOT / name).is_file() for name in contract.SOURCE_FILES)
    generated = {
        "evidence/a1r3_v3/A1R3V3_OSCNR_SOURCE_FREEZE.json",
        "evidence/a1r3_v3/A1R3V3_OSCNR_ZERO_GENERATION_PREFLIGHT.json",
    }
    assert generated.isdisjoint(contract.SOURCE_FILES)
    assert "implementation/scripts/run_official_qwen_mobile.py" in contract.SOURCE_FILES
    assert "implementation/src/raven_m/official_qwen_mobile/controller.py" in contract.SOURCE_FILES


def test_replay_gate_requires_exact_calibrated_totals() -> None:
    replay = {
        "schema": contract.OFFLINE_REPLAY_SCHEMA,
        "status": "PASS",
        "errors": [],
        "generation_calls": 0,
        "development_calibration_not_confirmation": True,
        "mechanism_id": contract.MECHANISM_ID,
        "totals": {
            "valid_episode_count": 19,
            "invalid_attempt_count": 1,
            "model_calls": 603,
            "executed_actions": 595,
            "a1r2_actual_rendered_chars": 108423,
            "a1r2_actual_rendered_tokens": 21710,
            "projected_nonempty_reads": 436,
            "projected_rendered_chars": 109185,
            "projected_rendered_tokens": 21870,
            "cnr_receipt_creation_count": 8,
            "cnr_receipt_committed_read_count": 8,
            "success_task_receipt_creation_count": 0,
            "success_task_receipt_read_count": 0,
            "failure_tasks_with_receipt": 8,
        },
    }
    replay["content_sha256"] = contract.content_sha256(replay)
    assert contract._validate_replay(replay) == []
    replay["totals"]["cnr_receipt_creation_count"] = 7
    replay["content_sha256"] = contract.content_sha256(replay)
    assert "replay_total_cnr_receipt_creation_count" in contract._validate_replay(replay)


def test_completion_requires_exact_order_single_transport_and_closed_tickets() -> None:
    summaries = []
    for task in contract.FULL_TASK_ORDER:
        summaries.append(
            {
                "task_name": task,
                "seed": contract.TASK_SEED,
                "evaluator_reward": 0.0,
                "steps": [{"model_call": {"raven_meta": {"transport_attempts": 1}}}],
                "memory_mechanism": {
                    "pending_ticket": None,
                    "decision_boundary": {
                        "extra_model_calls": 0,
                        "action_override_count": 0,
                        "forced_termination_count": 0,
                    },
                },
            }
        )
    assert contract.exact_completion_errors(summaries=summaries, invalid_attempts=[], lifecycle_errors=[]) == []
    summaries[0]["memory_mechanism"]["pending_ticket"] = {"ticket_id": "open"}
    assert "unclosed_read_ticket" in contract.exact_completion_errors(summaries=summaries, invalid_attempts=[], lifecycle_errors=[])
