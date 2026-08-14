# A1-R4 Writer-Resilient Pending Ledger Preregistration

Date: 2026-08-15 (Asia/Hong_Kong)

Status: prospective successor to terminal A1-R3. Live generation is forbidden
until real-trace replay, tests, source freeze, preflight, and fresh receipt pass.

## Frozen evidence and hypothesis

Parent evidence commit: `4a28f757d7312f9ee87c84f4d750a3c43740de28`.

A1-R3 failed `ExpenseDeleteMultiple2` at reward 0 after 34 valid calls. Its new
lifecycle was not exercised: 34/34 Action summaries violated the inherited A1
`MEMORY[...]` writer format, so it had zero valid writes and reads. R4 changes
only this interface failure. It does not tune the stale/failure-memory rules.

- mechanism: `a1r4_writer_resilient_pending_v1`
- experiment: `A1R4_WRPL_QWEN3VL32B_AW_HARD_T20260806_G3407_V1`
- task seed `20260806`; generation seed `3407`.

## Exact intervention

R4 inherits A1-R3's parser, one `verified + pending` ledger, non-refreshing
eight-request TTL, one-state tombstone, and two-same-family no-RGB-progress
failed-attempt fact.

When no semantic ledger exists, and only then, the normal working-memory slot
contains this exact bootstrap text:

`OUTPUT FORMAT REMINDER: Begin the Action sentence exactly with MEMORY[observed=<visible facts or none>; verified=<visibly confirmed requirements or none>; pending=<most important unmet requirement>] | before the UI imperative.`

After any valid non-none state is accepted, the reminder disappears and R4's
renderer is byte-identical to R3. It returns only after clear or expiry leaves
no active ledger. The reminder supplies no task fact, action, plan, completion
claim, hidden input, or evaluator signal. It is separately counted from
semantic-memory reads.

Decision boundary remains: zero extra model calls, no guard, override, repair,
retry, forced termination, extra screenshot, OCR, UI tree, task/app whitelist,
cross-episode state, training, or step-budget change.

## Qualification and prospective stopping

Zero-generation replay uses the exact 19 valid A1-R2 traces and hashed episode
artifacts. It must retain all six historical success sentinels, produce no
failed-attempt fact in them, preserve at least 100 non-refreshing stale writes,
and expose failure evidence in at least two failed episodes. The replay must
report bootstrap-reminder and semantic-read counts separately. It is not a
writer-compliance or reward prediction.

Live order is unchanged and blocking: the four A0 successes, then
`RecipeDeleteMultipleRecipesWithConstraint`, then `OsmAndMarker`. All six must
score reward 1.0 before the other thirteen are released. A valid scientific
failure is terminal and is never rerun; only hash-linked infrastructure-invalid
attempts may be replaced.

Independent full-suite verdicts remain: accuracy PASS requires at least 7/19,
reward >6.5, and no loss on the six sentinels; cost PASS requires calls <603,
tokens <2,685,730, and elapsed <11,230.182856 seconds. Mechanism evidence must
distinguish bootstrap-format exposure, semantic ledger reads, and productive
failed-attempt divergences. Same-seed results are matched prospective evidence,
not held-out generalization.

Any prompt text, parser, reminder schedule, lifecycle, threshold, or renderer
change after the first valid live call creates a new arm/version.

