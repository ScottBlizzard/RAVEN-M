# SYS-HMP Request: Hierarchical Milestone Planning

Design one prospective system that tests whether a visible-evidence-constrained
short milestone plan reduces long-horizon drift. Use the common component
ledger and do not absorb the other six SYS interventions.

Allowed: an initial planner call and event-triggered replanning using the same
frozen Qwen model; the official executor; a compact plan with source evidence.
Default hard ceiling: one initial plan plus at most three replans per episode.
The plan may use only the goal, model-visible RGB history, and executed actions.

Excluded: post-action verification, failure criticism, donor retrieval,
candidate voting, termination judgment, evaluator/hidden UI/future information,
task templates, and increased action-step budget. A planner must not silently
act as verifier or critic.

Freeze milestone schema, exact prompts, replan conditions, plan invalidation,
executor authority, context/call/token/latency caps, and transport policy.
Compare Full against `PLAN-SHADOW`, which makes identical planner calls but does
not inject their output, plus a no-replan ablation. Attribute a mechanism event
only when an injected milestone changes the next action and yields visible
progress within four steps without short relapse.

Use the fixed 4/4 A0-preservation gate, then the A1 Recipe gain, then the other
14. Accuracy pass is >5/19, reward >5.5, and no loss on A1's five successes.
Budget and mechanism verdicts remain separate. Report all auxiliary calls and
tokens by role.

Return only
`GPT_PRO_SYS_HMP_HIERARCHICAL_MILESTONE_PLANNER_DESIGN_2026-08-13.md`: a
commit-pinned audit, one frozen design, exact role contracts/prompts, algorithms,
integration blueprint, offline/preflight tests, shadow/ablation, prospective
protocol, verdict schema, and falsification rules. Do not modify code or run GPU.
