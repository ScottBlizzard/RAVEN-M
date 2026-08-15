import json

from raven_m.official_qwen_mobile import sys_nag_contract as contract


def test_identity_and_config_are_independent() -> None:
    config = json.loads(contract.CONFIG_PATH.read_text(encoding="utf-8"))
    assert contract.EXPERIMENT_ID.startswith("SYS_NAG_V3_R2_")
    assert config["schema"] == contract.CONFIG_SCHEMA
    assert config["mechanism_id"] == contract.MECHANISM_ID
    assert config["system_id"] == contract.SYSTEM_ID
    assert config["decision_boundary"]["auxiliary_model_calls"] == 0
    assert config["decision_boundary"]["max_guard_induced_continuation_normal_requests"] == 1
    assert config["pending_terminal_guard"]["max_blocks_per_episode"] == 1


def test_source_closure_is_exact_and_present() -> None:
    assert len(contract.SOURCE_FILES) == len(set(contract.SOURCE_FILES))
    missing = [
        name for name in contract.SOURCE_FILES
        if not (contract.REPOSITORY_ROOT / name).is_file()
    ]
    assert missing == []


def test_gate_order_keeps_numeric_sentinel_as_fourth_task() -> None:
    assert contract.CAPABILITY_GATE_TASKS[3] == (
        "SportsTrackerTotalDurationForCategoryThisWeek"
    )
    assert len(contract.CAPABILITY_GATE_TASKS) == 6
    assert len(contract.FULL_TASK_ORDER) == 19
