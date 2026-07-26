from raven_m.controller.episode_controller import action_authority_record


def test_authority_record_conservatively_classes_commit_like_actions() -> None:
    value = action_authority_record(
        {
            "status": "continue",
            "action": {"type": "tap", "x": 0.5, "y": 0.5},
            "memory_citations": ["m_0001"],
        }
    )
    assert value["risk_class"] == "irreversible_commit"
    assert value["authority_sources"] == [
        "current_screen",
        "routed_memory",
    ]


def test_authority_record_marks_terminal_critic_adjudication() -> None:
    value = action_authority_record(
        {
            "status": "done",
            "action": {
                "type": "answer",
                "text_origin": "current_screen",
                "source_memory_ids": [],
            },
            "memory_citations": [],
        },
        completion_adjudications=[{"output": {"verdict": "proceed"}}],
    )
    assert value["risk_class"] == "terminal_answer_or_completion"
    assert "same_turn_critic" in value["authority_sources"]
