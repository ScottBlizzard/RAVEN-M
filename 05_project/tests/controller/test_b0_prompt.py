from raven_m.controller.episode_controller import EpisodeController


def test_b0_prompt_excludes_hidden_state_and_memory() -> None:
    prompt = EpisodeController._user_prompt(
        goal="Create a contact.",
        step=0,
        max_steps=8,
        model_calls=0,
        max_model_calls=16,
        screen_width=1080,
        screen_height=2400,
        previous_outcome="none",
    )
    assert "MEMORY_CONTEXT: []" in prompt
    assert "evaluator" not in prompt.lower()
    assert "package" not in prompt.lower()
    assert "activity" not in prompt.lower()
