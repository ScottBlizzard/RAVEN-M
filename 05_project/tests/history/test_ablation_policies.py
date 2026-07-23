from raven_m.history.policies import (
    CallMatchedSummaryPolicy,
    ContextMatchedSummaryPolicy,
    FullRavenMemoryPolicy,
    make_history_policy,
)


class UnusedClient:
    pass


def make(variant: str):
    return make_history_policy(
        variant,
        client=UnusedClient(),  # type: ignore[arg-type]
        summary_system_prompt="summary",
        planner_system_prompt="planner",
        critic_system_prompt="critic",
    )


def test_budget_control_policy_types_are_explicit() -> None:
    assert isinstance(make("B3_CTX"), ContextMatchedSummaryPolicy)
    assert isinstance(make("B3_CALL"), CallMatchedSummaryPolicy)


def test_memory_ablation_configs_remove_only_predeclared_component() -> None:
    rel = make("MREL")
    no_wm = make("MNO_WM")
    no_vel = make("MNO_VEL")
    no_frm = make("MNO_FRM")
    no_psi = make("MNO_PSI")
    no_critic = make("MNO_CRITIC")
    assert isinstance(rel, FullRavenMemoryPolicy)
    assert not rel.manager.config.reliability_aware
    assert no_wm.manager.config.working_quota == 0
    assert no_vel.manager.config.episodic_quota == 0
    assert no_frm.manager.config.failure_quota == 0
    assert no_psi.manager.config.page_hint_quota == 0
    assert isinstance(no_critic, FullRavenMemoryPolicy)
    assert not no_critic.critic_enabled
