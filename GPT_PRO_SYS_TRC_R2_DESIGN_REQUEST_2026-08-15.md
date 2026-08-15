# GPT Pro Request — SYS-TRC-R2 Triggered Recovery Critic

You are in a fresh research-design conversation with no inherited context. Audit the repository before proposing anything.

Repository: <https://github.com/ScottBlizzard/RAVEN-M>

Branch: `a2-verified-progress-audit-20260810`

Frozen evidence commit: `9f9a611728826ada1daf809dccd7613de39660ac`

Read `evidence/composite/TOP3_COMPONENT_SELECTION_2026-08-15.md`, `evidence/composite/COMPONENT_EVIDENCE_LEDGER_2026-08-13.md`, `evidence/a1/A1_R1_R2_POSITIVE_AND_R3_R12_FAILURE_AUDIT_2026-08-15.md`, the frozen A1-R2 implementation/result, A8/A9 recurrence evidence, A1-R7–R9 results, and A10-v2/A11/A12 diagnostic causal records. Verify claims against repository paths and distinguish formal results, post-hoc diagnostics, inference, and missing raw evidence.

Design exactly one prospective composite system: frozen A1-R2 compact memory plus a sparsely triggered same-model recovery critic. Do not inherit the full A8/A9/R9 prompt stack. A deterministic recurrence/no-progress detector is only a scheduler; the critic is the component under test.

The critic may see only the goal, current model-visible RGB screenshot, and bounded executed action/visible-transition provenance available to the executor. It must output exactly one bounded failure hypothesis and one recovery principle. Its output is injected once into the next normal executor request and then destroyed. It cannot issue a tool call, plan the full task, verify completion, override/block/retry an action, terminate the episode, access hidden UI/evaluator/reward/activity/package/future frames, use task/app rules, or persist as free-text memory.

Common resource envelope: same Qwen3-VL-32B revision; at most two critic calls per episode; no retry/reflection chain; each completion ≤256 tokens; each auxiliary input+output ≤8,192 tokens; each latency ≤60 seconds; unchanged native action budget. Report executor and critic resources separately and combined.

Freeze one trigger supported across multiple A1-R2 failed tasks, not only `ExpenseDeleteMultiple2`. First materialize a zero-generation hash-bound cross-task trace audit. Define exact visual/action equivalence, maturity, cooldown, expiry, suppression, capacity, transport failure behavior, and why the trigger is silent or safe on the six R2 successes.

Required comparison:

1. `TRC_FULL`: specialized critic prompt and injected result.
2. `TRC_GENERIC_ACTIVE`: identical trigger, model, screenshot/history visibility, calls, token ceiling, and injection slot, but generic extra reasoning without the critic role/schema.
3. `TRC_NO_AUX`: frozen R2 plus trigger audit only, no auxiliary generation.

If Full does not beat Generic Active, no benefit may be attributed to recovery criticism. Triggering, emitting text, changing one action, or shortening a failed episode is insufficient. A productive intervention requires exact call/injection provenance, first post-injection divergence, visible escape/progress within four actions, and no relapse for four actions.

Live order is fixed: first compare Full and Generic Active on `ExpenseDeleteMultiple2`; Full must succeed and show a productive opportunity before continuing. Then run both through `RetroSavePlaylist`, `SimpleCalendarAddOneEvent`, `SportsTrackerTotalDurationForCategoryThisWeek`, `RecipeDeleteMultipleRecipesWithConstraint`, and `OsmAndMarker`. Only Full 6/6 with no paired loss releases the remaining thirteen. Scientific failures are terminal; only bounded linked infrastructure replacement is allowed.

Final system accuracy requires ≥7/19, reward >6.5, and no R2-six loss. Component causality requires Full versus Generic Active ≥1 paired full-success gain, zero R2-six losses, and ≥2 productive interventions. Cost is separate. Results are matched prospective diagnostics, not held-out generalization.

Only design; do not modify code or run GPU experiments. Return exactly one self-contained Markdown document named:

`GPT_PRO_SYS_TRC_R2_TRIGGERED_RECOVERY_CRITIC_DESIGN_2026-08-15.md`

It must include commit-pinned evidence audit; cross-task trigger prevalence; one frozen algorithm; exact critic and generic-control prompts; schemas/constants/caps; R2 preservation table; implementation map; offline replay/preflight/source freeze/live receipt/checkpoint/result contracts; three-arm attribution; gates/verdicts; and decisive falsification/no-hot-fix rules. If evidence is unavailable, specify a zero-generation materialization step rather than inventing facts.
