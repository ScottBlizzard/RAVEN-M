from __future__ import annotations

from pathlib import Path

from PIL import Image

from raven_m.history.policies import (
    HistoryEntry,
    RawFullHistoryPolicy,
    SimpleSummaryPolicy,
    SlidingWindowPolicy,
)
from raven_m.models.transformers_client import ModelCall


def _image(path: Path, color: int) -> Path:
    Image.new("RGB", (120, 240), (color, color, color)).save(path)
    return path


def _entry(tmp_path: Path, step: int) -> HistoryEntry:
    path = _image(tmp_path / f"{step}.png", 20 + step)
    return HistoryEntry(
        step=step,
        decision_summary=f"decision {step}",
        action={"type": "tap", "x": 0.5, "y": 0.5},
        observed_outcome=f"outcome {step}",
        screenshot_path=path,
        screenshot_sha256=f"sha{step}",
    )


def _call(content: str, label: str) -> ModelCall:
    return ModelCall(
        call_id=label,
        episode_id="episode",
        idempotency_key=label,
        image_sha256="current",
        image_sha256s=("current",),
        prompt_sha256=label,
        request_sha256=label,
        response_sha256=label,
        content=content,
        usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        raven_meta={},
    )


class FakeClient:
    def generate(self, **kwargs) -> ModelCall:
        return _call(
            (
                '{"summary":"Observed five actions.","completed":[],'
                '"pending":["Finish the task."]}'
            ),
            kwargs["call_label"],
        )


def test_sliding_window_keeps_exactly_last_three(tmp_path: Path) -> None:
    policy = SlidingWindowPolicy(k=3)
    episode_dir = tmp_path / "episode"
    episode_dir.mkdir()
    policy.reset(episode_dir=episode_dir, goal="task")
    for step in range(5):
        policy.observe(
            _entry(tmp_path, step),
            episode_id="episode",
            remaining_model_calls=10,
        )
    context = policy.context()
    assert '"step":2' in context.rendered
    assert '"step":1' not in context.rendered
    assert len(context.images) == 3


def test_raw_history_applies_fifo_image_cap(tmp_path: Path) -> None:
    policy = RawFullHistoryPolicy(max_chars=10000, max_images=2)
    episode_dir = tmp_path / "episode"
    episode_dir.mkdir()
    policy.reset(episode_dir=episode_dir, goal="task")
    for step in range(4):
        policy.observe(
            _entry(tmp_path, step),
            episode_id="episode",
            remaining_model_calls=10,
        )
    context = policy.context()
    assert '"step":2' in context.rendered
    assert '"step":3' in context.rendered
    assert '"step":1' not in context.rendered
    assert len(context.images) == 2


def test_simple_summary_triggers_at_five_and_keeps_two_recent(
    tmp_path: Path,
) -> None:
    policy = SimpleSummaryPolicy(
        client=FakeClient(),  # type: ignore[arg-type]
        system_prompt="summary",
        trigger_every=5,
        keep_recent=2,
    )
    episode_dir = tmp_path / "episode"
    episode_dir.mkdir()
    policy.reset(episode_dir=episode_dir, goal="task")
    update = None
    for step in range(5):
        update = policy.observe(
            _entry(tmp_path, step),
            episode_id="episode",
            remaining_model_calls=10,
        )
    assert update is not None and update.summary_updated
    assert len(update.calls) == 1
    context = policy.context()
    assert "Observed five actions." in context.rendered
    assert '"step":3' in context.rendered
    assert '"step":2' not in context.rendered
    assert len(context.images) == 2
