from __future__ import annotations

from pathlib import Path

from raven_m.role_binding_timing.dev_pilot_v0_1 import (
    build_call_1,
    build_call_2,
    build_cells,
    load_dev_config,
    prompt_certificate,
    summarize,
)
from raven_m.role_binding_timing.token_audit import WhitespaceTokenCounter


def test_dev_config_builds_eight_by_four_without_missing_targets() -> None:
    config = load_dev_config()
    cells = build_cells(config)
    assert len(cells) == 32
    assert len({cell.base_family_id for cell in cells}) == 8
    assert all(cell.image_path.is_file() for cell in cells)
    assert all(
        cell.destination_target_id in {item["target_id"] for item in cell.candidates}
        for cell in cells
    )
    assert all(
        cell.source_target_id in {item["target_id"] for item in cell.candidates}
        for cell in cells
    )


def test_each_action_transcript_contains_fact_once() -> None:
    counter = WhitespaceTokenCounter()
    for cell in build_cells(load_dev_config()):
        fact, neutral, first = build_call_1(cell, counter=counter)
        second = build_call_2(
            cell,
            call_1_prompt=first,
            fact=fact,
            neutral=neutral,
            grounding_commitment={
                "destination_entity_id": "E2",
                "destination_target_id": cell.destination_target_id,
                "source_entity_id": "E1",
            },
        )
        assert second.count(fact) == 1
        assert cell.value not in neutral


def test_whitespace_prompt_certificate_matches_early_late() -> None:
    certificates = prompt_certificate(
        load_dev_config(), counter=WhitespaceTokenCounter()
    )
    assert len(certificates) == 16
    assert all(item["absolute_total_difference"] == 0 for item in certificates)


def test_v0_2_hides_semantic_candidate_labels_but_keeps_bounds() -> None:
    config = load_dev_config(
        Path(__file__).resolve().parents[2]
        / "configs/role_binding_timing/stage1_dev_pilot_v0_2.json"
    )
    cells = build_cells(config)
    assert len(cells) == 32
    assert all(cell.candidate_prompt_fields == ("target_id", "bounds") for cell in cells)
    counter = WhitespaceTokenCounter()
    _, _, prompt = build_call_1(cells[0], counter=counter)
    assert '"visible_label"' not in prompt
    assert '"bounds"' in prompt


def test_v0_3_restores_only_visible_labels_without_visual_cues() -> None:
    config = load_dev_config(
        Path(__file__).resolve().parents[2]
        / "configs/role_binding_timing/stage1_dev_pilot_v0_3.json"
    )
    cells = build_cells(config)
    assert len(cells) == 32
    assert all(
        cell.candidate_prompt_fields == ("target_id", "visible_label", "bounds")
        for cell in cells
    )
    counter = WhitespaceTokenCounter()
    _, _, prompt = build_call_1(cells[0], counter=counter)
    assert '"visible_label"' in prompt
    assert '"visual_cue"' not in prompt


def test_summary_requires_qualification_and_predicted_interaction() -> None:
    records = []
    for cell in build_cells(load_dev_config()):
        is_high_early = (
            cell.role_ambiguity == "high" and cell.fact_timing == "early"
        )
        records.append(
            {
                "valid": True,
                "cell": {
                    "role_ambiguity": cell.role_ambiguity,
                    "fact_timing": cell.fact_timing,
                },
                "metrics": {
                    "wrong_target_first_targeting_action": is_high_early,
                    "action_target_correct": not is_high_early,
                    "exact_value_recall": True,
                    "source_as_target": is_high_early,
                    "post_grounding_drift": False,
                },
                "grounding_call": {"usage": {}},
                "action_call": {"usage": {}},
                "wall_time_seconds": 0.1,
            }
        )
    summary = summarize(records, load_dev_config()["gates"])
    assert summary["qualification_pass"]
    assert summary["dev_signal_pass"]
