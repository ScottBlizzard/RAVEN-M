# GPT Pro Request — SYS-VOV-R2 Sparse Visible-Outcome Verifier

You are in a fresh research-design conversation with no inherited context. Audit the repository before proposing anything.

Repository: <https://github.com/ScottBlizzard/RAVEN-M>

Branch: `a2-verified-progress-audit-20260810`

Frozen evidence commit: `9f9a611728826ada1daf809dccd7613de39660ac`

Read `evidence/composite/TOP3_COMPONENT_SELECTION_2026-08-15.md`, `evidence/composite/COMPONENT_EVIDENCE_LEDGER_2026-08-13.md`, `evidence/a1/A1_R1_R2_POSITIVE_AND_R3_R12_FAILURE_AUDIT_2026-08-15.md`, frozen A1-R2 evidence/code, A1's unique Recipe gain, A2 verified-progress/guard evidence, A6 transition logs, and later false-completion/confirmation diagnostics. Verify formal versus post-hoc status and identify missing trace evidence.

Design exactly one prospective composite system: frozen A1-R2 compact memory plus a sparse independent visible-outcome verifier using the same model revision. The verifier tests whether a bounded commitment action or completion claim is supported by visible evidence. It does not become a planner, critic, grounder, or evaluator.

The verifier sees only the goal, the executor's explicit expected visible outcome, bounded action provenance, and model-visible before/after RGB. Its output schema is exactly `SUPPORTED`, `UNSUPPORTED`, or `UNCERTAIN` plus one short evidence sentence. The verdict may be injected once into the next normal executor call. It cannot propose the next action, issue tools, block/override/retry the prior action, terminate the episode, access hidden UI/evaluator/reward/activity/package/future frames, use task/app rules, or treat arbitrary pixel change as semantic success.

Common resource envelope: same Qwen3-VL-32B revision; at most two verifier calls per episode; no retry/chain; each completion ≤256 tokens; each input+output ≤8,192 tokens; latency ≤60 seconds; unchanged native action budget. Report executor/verifier resources separately and combined.

First materialize a zero-generation hash-bound audit across all 19 R2 episodes. Quantify false or unconfirmed continuation, false terminal claims, repeated commitment actions, and where visible evidence was actually discriminative, separately for R2 successes and failures. Freeze a sparse task-agnostic trigger before live generation. Do not call the verifier after every action.

Required comparison:

1. `VOV_FULL`: specialized three-value verifier verdict is injected.
2. `VOV_GENERIC_ACTIVE`: identical trigger, model, images/provenance, calls, token ceiling, and injection slot, but generic visual reconsideration without verifier role or verdict semantics.
3. `VOV_NO_AUX`: frozen R2 plus deterministic trigger audit only.

If Full does not beat Generic Active, no gain is attributed to verification. A productive verification requires exact trigger/call/verdict/injection provenance, a verdict-induced next-decision divergence, visible correction within three actions, and no short relapse. Verifier agreement, pixel change, or fewer steps with reward 0 is insufficient.

Live order: compare Full and Generic Active first on `ExpenseDeleteMultiple2`; Full must succeed and show a productive verifier opportunity. Then run both through `RetroSavePlaylist`, `SimpleCalendarAddOneEvent`, `SportsTrackerTotalDurationForCategoryThisWeek`, `RecipeDeleteMultipleRecipesWithConstraint`, and `OsmAndMarker`. Only Full 6/6 releases the remaining thirteen. Valid scientific failure is terminal; infrastructure replacements are bounded and linked.

Final system accuracy requires ≥7/19, reward >6.5, and no R2-six loss. Component causality requires Full versus Generic Active ≥1 paired full-success gain, zero R2-six losses, and ≥2 productive verification events. Report false accept/reject/uncertain rates and cost separately. This is matched prospective evaluation, not held-out generalization.

Only design; do not modify code or run GPU. Return exactly one self-contained Markdown document named:

`GPT_PRO_SYS_VOV_R2_SPARSE_VISIBLE_OUTCOME_VERIFIER_DESIGN_2026-08-15.md`

Include commit-pinned audit; cross-task trigger analysis; one frozen design; exact verifier/generic-control prompts; schemas/constants/caps; uncertainty handling; R2-six preservation table; integration plan; replay/preflight/source freeze/live receipt/checkpoint/result contracts; three-arm attribution; gates/verdicts; and decisive falsification/no-hot-fix rules.
