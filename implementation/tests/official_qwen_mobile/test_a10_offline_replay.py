from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import numpy as np

from raven_m.official_qwen_mobile.a10_obligation_branch_frontier import (
    EvidenceCalibratedObligationBranchFrontierMemory,
)


def page(marker: int) -> np.ndarray:
    pixels = np.zeros((96, 64, 3), dtype=np.uint8)
    pixels[10:86, 8:56] = marker
    pixels[20 + marker % 20:30 + marker % 20, 16:48, 1] = 255
    return pixels


ROOT = Path(__file__).resolve().parents[3]


def test_real_trace_manifest_freezes_every_required_role() -> None:
    manifest = json.loads(
        (ROOT / "evidence/a10/A10_OFFLINE_TRACE_MANIFEST.json").read_text(
            encoding="utf-8"
        )
    )
    records = manifest["records"]
    assert manifest["schema"] == "a10_offline_trace_manifest_v1"
    assert manifest["generation_calls"] == 0
    assert manifest["episode_count"] == len(records) == 27
    assert {item["role"] for item in records} == {
        "a0",
        "a1_recipe",
        "a6",
        "a8v2_expense",
        "a9_retro",
    }
    assert manifest["file_count"] == sum(len(item["files"]) for item in records) + len(
        manifest["suite_files"]
    )
    assert all(len(item["episode_json_sha256"]) == 64 for item in records)


def test_committed_full_replay_report_does_not_hide_a_failed_gate() -> None:
    report = json.loads(
        (ROOT / "evidence/a10/A10_OFFLINE_REPLAY_REPORT.json").read_text(
            encoding="utf-8"
        )
    )
    assert report["schema"] == "a10_offline_replay_report_v1"
    assert report["generation_calls"] == 0
    assert report["episode_count"] == 27
    assert report["replay_source_sha256"] == sha256(
        (ROOT / "implementation/scripts/replay_a10_offline_traces.py").read_bytes()
    ).hexdigest()
    assert report["mechanism_source_sha256"] == sha256(
        (
            ROOT
            / "implementation/src/raven_m/official_qwen_mobile/a10_obligation_branch_frontier.py"
        ).read_bytes()
    ).hexdigest()
    assert report["status"] == ("pass" if not report["errors"] else "fail")
    a0_success = [
        item
        for item in report["episodes"]
        if item["role"] == "a0"
        and item["task_name"] != "RecipeDeleteMultipleRecipesWithConstraint"
    ]
    assert len(a0_success) == 4
    if any(item["nonempty_reads"] for item in a0_success):
        assert "a0_success_silence_gate_failed" in report["errors"]


def replay(memory, goal, transitions):
    rendered = []
    first = transitions[0][0]
    rendered.append(memory.read({"goal": goal, "before": {"pixels": first}})[0])
    for step, (before, after, summary, action) in enumerate(transitions):
        memory.observe_step(source_step=step, action_summary=summary, canonical_action=action, before={"pixels": before}, after={"pixels": after})
        rendered.append(memory.read({"goal": goal, "before": {"pixels": after}})[0])
    return rendered


def test_competent_forward_trajectory_remains_silent() -> None:
    screens = [page(value) for value in (10, 40, 70, 100, 130)]
    transitions = [(screens[i], screens[i + 1], "Open and inspect the next distinct item", {"type": "tap", "x": .2 + i * .1, "y": .4}) for i in range(4)]
    reads = replay(EvidenceCalibratedObligationBranchFrontierMemory(), "Open the report and inspect its entries", transitions)
    assert all(not item for item in reads)


def test_repeated_stationary_branch_activates_before_full_cycle() -> None:
    pixels = page(20)
    transitions = [(pixels, pixels, "Tap the lower-middle delete control", {"type": "tap", "x": .5, "y": .6}) for _ in range(2)]
    reads = replay(EvidenceCalibratedObligationBranchFrontierMemory(), "Delete the following: Bike Repairs, Tuition Fees", transitions)
    assert sum(bool(item) for item in reads) == 1
    assert "no/negligible" in next(item for item in reads if item)


def test_normal_multi_object_same_coordinate_different_anchor_is_not_same_branch() -> None:
    pixels = page(30)
    transitions = [
        (pixels, pixels, "Delete Bike Repairs", {"type": "tap", "x": .5, "y": .6}),
        (pixels, pixels, "Delete Tuition Fees", {"type": "tap", "x": .5, "y": .6}),
    ]
    reads = replay(EvidenceCalibratedObligationBranchFrontierMemory(), "Delete the following: Bike Repairs, Tuition Fees", transitions)
    assert all(not item for item in reads)


def test_value_reentry_requires_bad_prior_outcome() -> None:
    pixels = page(40)
    other = page(160)
    bad = [(pixels, pixels, "Type the value", {"type": "type_text", "text": "Bike Repairs", "clear_text": False}), (pixels, pixels, "Type the value again", {"type": "type_text", "text": "Bike Repairs", "clear_text": False})]
    memory = EvidenceCalibratedObligationBranchFrontierMemory()
    reads = replay(memory, "Find Bike Repairs", bad)
    assert memory.audit_record()["triggers"]["created_counts_by_kind"].get("VALUE_REENTRY_AFTER_BAD_OUTCOME", 0) == 1
    good = [(pixels, other, "Type the value", {"type": "type_text", "text": "Bike Repairs", "clear_text": False}), (other, page(200), "Type the value again", {"type": "type_text", "text": "Bike Repairs", "clear_text": False})]
    memory2 = EvidenceCalibratedObligationBranchFrontierMemory()
    replay(memory2, "Find Bike Repairs", good)
    assert memory2.audit_record()["triggers"]["created_counts_by_kind"].get("VALUE_REENTRY_AFTER_BAD_OUTCOME", 0) == 0
