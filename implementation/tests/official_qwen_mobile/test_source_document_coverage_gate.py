from raven_m.official_qwen_mobile.source_document_coverage_gate import (
    FORCED_FORWARD_SWIPE,
    MARKOR_DOCUMENT_ACTIVITY,
    SourceDocumentCoverageGate,
    is_forward_vertical_swipe,
)


def unchanged_transition() -> dict:
    return {
        "changed_pixel_fraction_gt_5": 0.0,
        "activity_changed": False,
        "ui_sha_changed": False,
    }


def changed_transition() -> dict:
    return {
        "changed_pixel_fraction_gt_5": 0.35,
        "activity_changed": False,
        "ui_sha_changed": True,
    }


def test_forward_swipe_direction_is_strict() -> None:
    assert is_forward_vertical_swipe(FORCED_FORWARD_SWIPE)
    assert not is_forward_vertical_swipe(
        {"type": "swipe", "x": 0.5, "y": 0.2, "x2": 0.5, "y2": 0.8}
    )
    assert not is_forward_vertical_swipe({"type": "press_home"})


def test_gate_is_inactive_outside_document() -> None:
    gate = SourceDocumentCoverageGate()
    action = {"type": "press_home"}
    effective, audit = gate.filter_action(
        before_activity="launcher", proposed_action=action, terminal_status=None
    )
    assert effective == action
    assert audit["active"] is False
    assert gate.audit_record()["override_count"] == 0


def test_gate_blocks_exit_and_terminal_until_bottom() -> None:
    gate = SourceDocumentCoverageGate()
    effective, audit = gate.filter_action(
        before_activity=MARKOR_DOCUMENT_ACTIVITY,
        proposed_action={"type": "press_home"},
        terminal_status=None,
    )
    assert effective == FORCED_FORWARD_SWIPE
    assert audit["overridden"] is True
    observed = gate.observe(
        before_activity=MARKOR_DOCUMENT_ACTIVITY,
        executed_action=effective,
        transition=changed_transition(),
    )
    assert observed["bottom_attested"] is False
    effective, audit = gate.filter_action(
        before_activity=MARKOR_DOCUMENT_ACTIVITY,
        proposed_action=None,
        terminal_status="success",
    )
    assert effective == FORCED_FORWARD_SWIPE
    assert audit["terminal_status_blocked"] == "success"


def test_unchanged_forward_scan_attests_bottom_and_releases_next_action() -> None:
    gate = SourceDocumentCoverageGate()
    effective, _ = gate.filter_action(
        before_activity=MARKOR_DOCUMENT_ACTIVITY,
        proposed_action={"type": "tap", "x": 0.2, "y": 0.2},
        terminal_status=None,
    )
    gate.observe(
        before_activity=MARKOR_DOCUMENT_ACTIVITY,
        executed_action=effective,
        transition=unchanged_transition(),
    )
    assert gate.bottom_attested is True
    leave = {"type": "press_home"}
    effective, audit = gate.filter_action(
        before_activity=MARKOR_DOCUMENT_ACTIVITY,
        proposed_action=leave,
        terminal_status=None,
    )
    assert effective == leave
    assert audit["overridden"] is False
    assert audit["reason"] == "bottom_attested"


def test_model_forward_swipe_is_counted_without_override() -> None:
    gate = SourceDocumentCoverageGate()
    proposed = {"type": "swipe", "x": 0.4, "y": 0.8, "x2": 0.4, "y2": 0.3}
    effective, audit = gate.filter_action(
        before_activity=MARKOR_DOCUMENT_ACTIVITY,
        proposed_action=proposed,
        terminal_status=None,
    )
    assert effective == proposed
    assert audit["overridden"] is False
    gate.observe(
        before_activity=MARKOR_DOCUMENT_ACTIVITY,
        executed_action=effective,
        transition=changed_transition(),
    )
    assert gate.forward_swipe_count == 1
