# GPT Pro Request — SYS-HMP-R2 Hierarchical Milestone Planner

You are in a fresh research-design conversation with no inherited context. Audit the repository before proposing anything.

Repository: <https://github.com/ScottBlizzard/RAVEN-M>

Branch: `a2-verified-progress-audit-20260810`

Frozen evidence commit: `9f9a611728826ada1daf809dccd7613de39660ac`

Read `evidence/composite/TOP3_COMPONENT_SELECTION_2026-08-15.md`, `evidence/composite/COMPONENT_EVIDENCE_LEDGER_2026-08-13.md`, `evidence/a1/A1_R1_R2_POSITIVE_AND_R3_R12_FAILURE_AUDIT_2026-08-15.md`, frozen A1-R2 evidence/code, A6/A7 state/goal evidence, and A10/A11 obligation/frontier designs and formal replay failures. Verify every claim and mark missing raw evidence.

Design exactly one prospective composite system: frozen A1-R2 compact memory plus a bounded same-model hierarchical milestone planner. The executable base is R2, not a failed A6/A7/A10/A11 arm. You may reuse one minimal representation primitive only if cross-task evidence requires it; do not inherit their state machines.

The planner may use only the goal, current model-visible RGB, bounded earlier model-visible screenshots if already part of normal provenance, and executed action history. It produces a short ordered milestone plan with visible evidence conditions. The executor remains the only action-generating role. The planner may not verify an action, criticize failure, select candidates, retrieve donors, judge terminal success, issue tools, override/block/retry actions, access hidden UI/evaluator/reward/activity/package/future frames, use task/app templates, or increase native step budgets.

Common resource envelope: same Qwen3-VL-32B revision; exactly one initial planner opportunity and at most one event-triggered replan per episode; total auxiliary calls ≤2; no retry/chain; each completion ≤256 tokens; each input+output ≤8,192 tokens; latency ≤60 seconds. Unused budget is not filled. Report resources by role and combined.

Before freezing the system, materialize a zero-generation hash-bound audit of all 19 R2 episodes and quantify cross-task phase loss, requirement loss, repeated local navigation, and long-horizon drift in successes versus failures. A planner cannot be justified only from the Expense trace. Freeze exact milestone schema, evidence grounding, number/length, invalidation, replan trigger, plan expiry, injection slot, executor authority, capacity, and failure behavior.

Required comparison:

1. `HMP_FULL`: milestone plan is injected into the executor.
2. `HMP_GENERIC_ACTIVE`: identical calls, model, inputs, token ceiling, and injection slot, but generic extra task reasoning without frozen milestone structure.
3. `HMP_NO_AUX`: frozen R2 without auxiliary generation.
4. Within Full, report a no-replan diagnostic; it cannot replace the generic active control.

Planning benefit requires an injected milestone to change the next executor decision and produce visible milestone progress within four actions without short relapse. More coherent prose, plan completion claims, or success while the plan is silent is not component evidence. If Full does not beat Generic Active, any benefit is attributed to extra inference rather than milestone planning.

Live order: compare Full and Generic Active first on `ExpenseDeleteMultiple2`; Full must succeed and expose a productive plan intervention. Then run both through the remaining R2 successes: `RetroSavePlaylist`, `SimpleCalendarAddOneEvent`, `SportsTrackerTotalDurationForCategoryThisWeek`, `RecipeDeleteMultipleRecipesWithConstraint`, `OsmAndMarker`. Only Full 6/6 releases the remaining thirteen. Scientific failures are terminal; infrastructure replacement is bounded and linked.

Final system accuracy requires ≥7/19, reward >6.5, and no R2-six loss. Component causality requires Full versus Generic Active ≥1 paired full-success gain, zero R2-six losses, and ≥2 productive milestone interventions. Cost is independently adjudicated. The study is matched prospective, not held-out.

Only design; do not edit code or run GPU. Return exactly one self-contained Markdown document named:

`GPT_PRO_SYS_HMP_R2_HIERARCHICAL_MILESTONE_PLANNER_DESIGN_2026-08-15.md`

Include commit-pinned evidence; cross-task planning-defect audit; one frozen design; exact planner/generic-control/executor prompts; state/schema/constants/caps; R2-six preservation analysis; minimal integration; zero-generation replay/preflight/source closure; live receipt/checkpoint/result contracts; controls/gates/verdicts; and falsification/no-hot-fix rules.
