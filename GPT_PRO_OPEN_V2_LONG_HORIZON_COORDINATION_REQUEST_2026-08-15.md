# Open V2 Pro Request — Long-Horizon Decomposition and Coordination

You are in a fresh research-design conversation. First audit <https://github.com/ScottBlizzard/RAVEN-M>, branch `a2-verified-progress-audit-20260810`, at frozen evidence commit `b5635939acd628156f8c8e36aa8219834a3e6ad8`.

Read `evidence/composite/TOP3_OPEN_DESIGN_CHARTER_2026-08-15.md`, `evidence/composite/TOP3_COMPONENT_SELECTION_2026-08-15.md`, `evidence/a1/A1_R1_R2_POSITIVE_AND_R3_R12_FAILURE_AUDIT_2026-08-15.md`, the A1-R2 implementation/result, and A6/A7/A10/A11 formal and diagnostic evidence. Verify all claims independently and identify unavailable raw evidence.

Research problem: what additional computation or state organization helps the mobile agent decompose a long goal, maintain phase and requirement coherence, and avoid local navigation drift while preserving its successful reactive behavior?

A hierarchical milestone planner is only an initial hypothesis. You may retain, redesign, rename, or reject it. Alternatives may include subgoal scheduling, phase control, adaptive replanning, workflow state, plan-execute interleaving, option-like skills, or another evidence-supported architecture. Do not assume that a planner is required merely because the track name originally used “planner.”

A1-R2 is the default positive reference, not an immutable implementation mandate. You may choose a different parent or reuse a narrowly supported primitive from A6/A7/A10/A11 if the evidence justifies it, but cannot inherit a failed stack wholesale. Explain exactly how the six R2 successes remain protected.

You decide whether planning happens initially, reactively, repeatedly, or not at all; the role schema; state representation; evidence grounding; call count; token budget; replanning/invalidation; and comparison controls. Derive limits from cross-task traces. If extra model computation is proposed, compare it with an appropriate resource-matched generic reasoning control and a no-component base so that gains are not automatically attributed to “planning.”

Hard boundaries: no evaluator/reward, hidden UI/accessibility, activity/package, future frames, task/app templates, cross-episode leakage, unreported compute, or increased native action budget. Do not rewrite historical results. Freeze the prospective design before generation and do not rerun scientific failures.

First perform or specify a zero-generation, hash-bound audit across all 19 R2 episodes. Quantify requirement loss, phase loss, repeated local navigation, premature termination, and long-horizon drift in both successes and failures. Consider counterexamples where a planner would harm simple reactive tasks. The final design must be based on cross-task evidence, not one known trajectory.

The prospective protocol must first preserve all six R2 successes, then release the remaining thirteen. Final accuracy improvement requires at least 7/19, reward >6.5, and zero R2-six loss. Accuracy, cost, and component causality remain independent. Choose controls and causal criteria that fit your final architecture.

You may conclude that explicit planning is unsupported or that another coordination mechanism is superior. If so, justify the replacement while keeping the response centered on long-horizon decomposition/coordination and distinct from the recovery and verification tracks.

Only design; do not modify the repository or run GPU. Return exactly one self-contained Markdown document named `GPT_PRO_OPEN_V2_LONG_HORIZON_COORDINATION_DESIGN_2026-08-15.md`, with commit-pinned evidence, alternatives, one recommendation, exact architecture/prompts/state/budgets, integration, preservation table, offline/preflight/live protocol, controls, verdicts, and falsification rules.
