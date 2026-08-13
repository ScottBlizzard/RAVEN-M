# A1-R1 BPR v1 Design Audit

Date: 2026-08-13 (Asia/Hong_Kong)

Audited design SHA-256:
`e248b8dbdeaaf49fd3d49dea6fd7270ea8f57443df8e080203c487942f2cfcbd`

## Decision

Preserve the Bounded Pending Receipt idea, but reject the frozen v1 protocol for
live generation. A new version is required; v1 must not be silently retuned.

The valuable core is genuinely smaller than A10-v2/A11/A12: one active pending
receipt, one short tombstone, duplicate-no-refresh, a short lifetime, at most two
reads per receipt, an episode read cap, same-RGB suppression, and exact removal
of the memory prefix from ordinary history. It directly targets A1's one plausible
gain, stale reinforcement, and duplicated context.

## Materialized A1 evidence

The complete local A1 suite remains available and was read without generation:

- 19 episode directories and 19 `episode.json` files;
- zero episode JSON hash mismatches against the frozen paired ledger;
- 1,199 PNG files;
- 2,440 files and 381,429,354 bytes total;
- aggregate SHA-256 exactly
  `7a4ebaad754802fcf3350e83ca13032a16de609f2904c96c7b5ecd0efc006f51`.

The large raw tree remains local and ignored. The compact audit is committed in
`evidence/a1r1/A1R1_V1_RAW_TRACE_AUDIT_2026-08-13.json`.

## Deterministic v1 failure

Across 514 historical non-`none` A1 pending values, only 365 fit the v1 limit of
48 characters and 72 UTF-8 bytes: 71.011673% coverage. Character lengths were
P50 45, P75 57, P90 100, P95 100, P99 100, maximum 122. UTF-8 byte P95 was 100
and maximum was 122.

V1 gate R3 requires at least P95 to fit 48 characters/72 bytes. It therefore
fails by its own frozen rule and must end as `A1R1_OFFLINE_QUALIFICATION_FAIL`.
This failure does not refute the single-receipt mechanism; it refutes the v1
field cap and its qualification binding.

## Supported part of the hypothesis

In A1's unique paired gain, `RecipeDeleteMultipleRecipesWithConstraint`, step 24
wrote `pending=confirm deletion` and the next ordinary call at step 25 received
the pending state, terminated successfully, and obtained reward 1.0. The key
opportunity is therefore compatible with a short source+1 read window.

This is structural historical support, not proof that a future `op/proof` prompt
will reproduce the gain.

## Gate that cannot be honestly replayed

V1 gate R5 asks whether an episode cap of eight BPR reads would be exhausted
before the key RecipeDelete receipt. Old A1 outputs contain `pending`, but not the
new BPR `op/proof` contract, and mix navigation, page opening, waiting, searching,
and true task-state changes. A deterministic future BPR write schedule cannot be
reconstructed without a counterfactual semantic classifier.

The next design must separate:

1. facts directly measurable from A1 traces;
2. synthetic engineering-only lifecycle tests;
3. prospective behavior that only a new model run can decide.

It must not turn an inherently prospective unknown into a replay PASS by using
hand labels, task-specific rules, a semantic model, or optimistic mapping.

## Required narrow revision

The next GPT Pro response should keep the BPR causal kernel and change only what
the audit forces. It must create new mechanism/experiment/schema identities,
recompute renderer and budget hashes, replace the impossible R3 gate with a
trace-valid rule, and either replace R5 with an honestly testable qualification
or declare read-cap consumption prospective and let the fixed five-task live gate
test it. It must incorporate the completed A11/A12 diagnostic result committed
under `evidence/diag6/A11_A12_DIAGNOSTIC6_RESULTS_2026-08-13.md`.

Do not add frontier, route, branch, failure-signature, action-family recurrence,
maturity scoring, guard, action blocking, or extra model calls.
