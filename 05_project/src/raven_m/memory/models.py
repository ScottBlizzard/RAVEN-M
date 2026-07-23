"""Typed records and invariants for episode-local RAVEN-M memory."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from math import exp
from typing import Any


ACTIVE_STATUSES = {"candidate", "observed", "verified"}
INACTIVE_STATUSES = {
    "stale",
    "contradicted",
    "revoked",
    "superseded",
    "archived",
}
ALL_STATUSES = ACTIVE_STATUSES | INACTIVE_STATUSES
MEMORY_TYPES = {"working", "episodic_fact", "failure", "page_hint"}
ROUTES = {"FACT", "HYPOTHESIS", "ALERT", "SUPPRESS"}


@dataclass(frozen=True)
class MemorySource:
    observation_ids: tuple[str, ...] = ()
    action_ids: tuple[str, ...] = ()
    screenshot_paths: tuple[str, ...] = ()
    screenshot_sha256: tuple[str, ...] = ()
    model_call_id: str | None = None
    extractor: str = "deterministic_memory_manager_v1"

    def validate(self) -> None:
        if not self.observation_ids and not self.action_ids:
            raise ValueError(
                "Memory provenance requires an observation or action ID."
            )
        if len(self.screenshot_paths) != len(self.screenshot_sha256):
            raise ValueError(
                "Screenshot paths and hashes must have identical lengths."
            )
        for digest in self.screenshot_sha256:
            if len(digest) != 64 or any(
                character not in "0123456789abcdef" for character in digest
            ):
                raise ValueError(f"Invalid screenshot SHA-256: {digest}")


@dataclass
class MemoryItem:
    memory_id: str
    episode_id: str
    memory_type: str
    content: dict[str, Any]
    task_id: str
    created_step: int
    last_confirmed_step: int
    source: MemorySource
    evidence: dict[str, Any]
    verification_status: str = "candidate"
    subgoal_id: str | None = None
    app_id_observed: str | None = None
    page_signature: str | None = None
    confidence_model: float = 0.5
    reliability_score: float = 0.0
    relevance_cache: dict[str, float] = field(default_factory=dict)
    validity: dict[str, Any] = field(
        default_factory=lambda: {
            "scope": "episode",
            "preconditions": ["same_task"],
            "expires_on": [],
        }
    )
    relations: dict[str, Any] = field(
        default_factory=lambda: {
            "supersedes": None,
            "superseded_by": None,
            "contradicts": [],
            "supports_completion_requirements": [],
        }
    )
    routing_history: list[dict[str, Any]] = field(default_factory=list)
    schema_version: str = "memory_item.v1"

    def validate(self, expected_episode_id: str | None = None) -> None:
        if self.schema_version != "memory_item.v1":
            raise ValueError("Unsupported memory schema version.")
        if expected_episode_id and self.episode_id != expected_episode_id:
            raise ValueError("Cross-episode memory access is forbidden.")
        if self.memory_type not in MEMORY_TYPES:
            raise ValueError(f"Unknown memory type: {self.memory_type}")
        if self.verification_status not in ALL_STATUSES:
            raise ValueError(
                f"Unknown verification status: {self.verification_status}"
            )
        if self.created_step < 0 or self.last_confirmed_step < self.created_step:
            raise ValueError("Memory step indices are inconsistent.")
        if not 0.0 <= self.confidence_model <= 1.0:
            raise ValueError("Model confidence must be in [0,1].")
        if not 0.0 <= self.reliability_score <= 1.0:
            raise ValueError("Reliability must be in [0,1].")
        required_content = {"subject", "predicate", "object", "natural_language"}
        if not required_content.issubset(self.content):
            missing = sorted(required_content - set(self.content))
            raise ValueError(f"Missing memory content fields: {missing}")
        self.source.validate()
        if (
            self.evidence.get("origin") == "model_inference"
            and self.verification_status in {"observed", "verified"}
        ):
            raise ValueError(
                "A model-only inference cannot begin observed or verified."
            )
        if self.validity.get("scope") != "episode":
            raise ValueError("Core RAVEN-M memory must be episode-local.")

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["source"] = asdict(self.source)
        for key, item in value["source"].items():
            if isinstance(item, tuple):
                value["source"][key] = list(item)
        return value

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "MemoryItem":
        copied = dict(value)
        source = dict(copied.pop("source"))
        for key in (
            "observation_ids",
            "action_ids",
            "screenshot_paths",
            "screenshot_sha256",
        ):
            source[key] = tuple(source.get(key, ()))
        return cls(source=MemorySource(**source), **copied)


@dataclass(frozen=True)
class RetrievalQuery:
    step_id: int
    task_terms: tuple[str, ...] = ()
    current_subgoal_id: str | None = None
    required_variables: tuple[str, ...] = ()
    page_signature: str | None = None
    app_label_observed: str | None = None
    last_action_signature: dict[str, Any] | None = None
    event_flags: tuple[str, ...] = ("normal_step",)
    open_completion_requirements: tuple[str, ...] = ()


@dataclass(frozen=True)
class MemoryConfig:
    verification_weight: float = 0.25
    outcome_weight: float = 0.20
    provenance_weight: float = 0.15
    context_weight: float = 0.20
    recency_weight: float = 0.10
    contradiction_penalty: float = 0.45
    stale_penalty: float = 0.20
    failure_transfer_penalty: float = 0.15
    relevance_weight: float = 0.20
    subgoal_weight: float = 0.15
    page_weight: float = 0.15
    retrieval_recency_weight: float = 0.10
    retrieval_reliability_weight: float = 0.40
    retrieval_contradiction_penalty: float = 0.40
    retrieval_stale_penalty: float = 0.20
    fact_threshold: float = 0.75
    hypothesis_threshold: float = 0.45
    retrieve_min: float = 0.30
    alert_min: float = 0.20
    memory_prompt_tokens: int = 3000
    routed_item_cap: int = 2
    working_quota: int = 3
    episodic_quota: int = 8
    failure_quota: int = 2
    page_hint_quota: int = 2
    reliability_aware: bool = True
    recency_tau: dict[str, float] = field(
        default_factory=lambda: {
            "working": 3.0,
            "episodic_fact": 20.0,
            "failure": 12.0,
            "page_hint": 25.0,
        }
    )

    def recency(self, item: MemoryItem, step: int) -> float:
        tau = self.recency_tau[item.memory_type]
        age = max(0, step - item.last_confirmed_step)
        return exp(-age / tau)


@dataclass(frozen=True)
class RetrievalFeatures:
    relevance: float
    subgoal_match: float
    page_match: float
    verification: float
    outcome: float
    provenance: float
    context: float
    recency: float
    contradiction: float
    stale: float
    failure_transfer: float
    scope_compatible: bool


@dataclass(frozen=True)
class RoutedMemory:
    item: MemoryItem
    route: str
    score: float
    reliability: float
    features: RetrievalFeatures

    def __post_init__(self) -> None:
        if self.route not in ROUTES:
            raise ValueError(f"Unknown route: {self.route}")
