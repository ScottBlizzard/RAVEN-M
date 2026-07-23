from __future__ import annotations

from pathlib import Path

from raven_m.models.transformers_client import ModelCall
from raven_m.roles.orchestrator import RoleOrchestrator


def call(content: str, label: str) -> ModelCall:
    return ModelCall(
        call_id=label,
        episode_id="episode-a",
        idempotency_key=label,
        image_sha256="0" * 64,
        image_sha256s=("0" * 64,),
        prompt_sha256=label,
        request_sha256=label,
        response_sha256=label,
        content=content,
        usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        raven_meta={},
    )


class RoleClient:
    def __init__(self, *, bad_first: bool = False) -> None:
        self.bad_first = bad_first
        self.count = 0
        self.requests = []

    def generate(self, **kwargs) -> ModelCall:
        self.count += 1
        self.requests.append(kwargs)
        label = kwargs["call_label"]
        if self.bad_first and self.count == 1:
            return call("not json", label)
        if label.startswith("planner"):
            content = (
                '{"schema_version":"plan.v1","current_subgoal":'
                '{"subgoal_id":"sg_01","description":"Open the note."},'
                '"open_requirements":["Read the note."],'
                '"required_variables":["note_text"],'
                '"completion_requirements":[{"id":"cr_1",'
                '"description":"The requested note is saved.",'
                '"evidence_memory_ids":[]}],'
                '"plan_summary":"Open, read, then save the note."}'
            )
        else:
            content = (
                '{"schema_version":"critic.v1","verdict":"recover",'
                '"issue":"The same tap had no effect.",'
                '"recommended_constraint":"Re-observe and avoid the same tap.",'
                '"memory_ids":["f_0001"]}'
            )
        return call(content, label)


def orchestrator(client: RoleClient) -> RoleOrchestrator:
    return RoleOrchestrator(
        client=client,  # type: ignore[arg-type]
        planner_prompt="planner",
        critic_prompt="critic",
    )


def test_planner_contract_repairs_once(tmp_path: Path) -> None:
    image = tmp_path / "screen.png"
    image.write_bytes(b"fixture")
    client = RoleClient(bad_first=True)
    result = orchestrator(client).call(
        role="planner",
        image_path=image,
        payload={"task": "Open a note"},
        episode_id="episode-a",
        step=0,
        remaining_model_calls=2,
        allowed_memory_ids=set(),
    )
    assert result.output["schema_version"] == "plan.v1"
    assert len(result.calls) == 2
    repair_prompt = client.requests[1]["user_prompt"]
    assert "INVALID_RESPONSE" not in repair_prompt
    assert "close it with `}]`" in repair_prompt
    assert "Rebuild the object from scratch" in repair_prompt


def test_critic_rejects_unavailable_memory_id(tmp_path: Path) -> None:
    image = tmp_path / "screen.png"
    image.write_bytes(b"fixture")
    result = orchestrator(RoleClient()).call(
        role="critic",
        image_path=image,
        payload={"trigger": "loop"},
        episode_id="episode-a",
        step=2,
        remaining_model_calls=1,
        allowed_memory_ids=set(),
    )
    assert result.output is None
    assert result.error["type"] == "RoleValidationError"
