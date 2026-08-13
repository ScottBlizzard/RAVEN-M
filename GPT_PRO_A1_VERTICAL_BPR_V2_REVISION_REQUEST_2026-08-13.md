# Request: Narrow Revision of A1-R1 BPR v1

This request is for the same GPT Pro conversation that produced
`GPT_PRO_A1_VERTICAL_MINIMAL_MEMORY_DESIGN_2026-08-13.md`.

Audit the GitHub commit supplied with this request, especially:

- `HANDOFF_2026-08-13.md`;
- `evidence/a1r1/A1R1_V1_RAW_TRACE_AUDIT_2026-08-13.json`;
- `evidence/a1r1/A1R1_V1_DESIGN_AUDIT_2026-08-13.md`;
- `evidence/diag6/A11_A12_DIAGNOSTIC6_RESULTS_2026-08-13.md`.

## Required decision boundary

Preserve the BPR causal kernel. Do not restart ideation and do not import A10,
A11, or A12 machinery. The retained kernel is:

- one active pending receipt and at most one short refractory tombstone;
- model-authored operation plus visible confirmation condition;
- duplicate writes do not refresh lifetime or read budget;
- short expiry, sparse bounded reads, same-RGB reinjection suppression;
- exact removal of valid memory prefixes from ordinary history;
- prompt-only influence, zero added model calls, no action control.

The frozen v1 cannot pass unchanged. Its R3 requires historical pending P95 to
fit 48 characters/72 bytes, but the materialized trace gives P95=100 and only
71.011673% coverage. V1 must remain a failed version. Produce a new v2 identity;
never edit the v1 threshold while retaining its mechanism/experiment/schema IDs.

V1 R5 is also not directly decidable: historical A1 `pending` prose is not a
future BPR `op/proof` write schedule. Do not use hand labels, task-specific rules,
LLM/VLM classification, or synthetic placeholders to claim effectiveness or a
real read-budget PASS.

## Required revision work

1. Re-audit field caps and renderer budgets from the committed raw-trace summary.
   Freeze one evidence-defensible choice. A larger single-receipt cap is allowed
   if bounded and justified; a deterministic eligibility denominator is allowed
   only if it is computable without semantic guessing or task/app branching.
2. Replace R3 with a gate whose denominator and pass condition are reproducible.
3. Replace R5 with an honestly zero-generation-testable gate, or classify future
   cap consumption as prospective and make the fixed five-task live sequence the
   falsification test. Unknown must not be mislabeled PASS.
4. Preserve the supported source+1 RecipeDelete timing fact, while labeling it
   structural historical support rather than counterfactual effectiveness.
5. Incorporate the completed diagnostics: A11 was 2/6 with four real reads and
   A12 was 1/6 with three real reads; both had zero productive-divergence signals,
   all read-active episodes failed, and every success was memory-silent.
6. Keep accuracy, cost, and mechanism verdicts independent. Keep the fixed order
   `A0 four-task 4/4 -> RecipeDelete retention -> remaining 14`.
7. Recompute every affected exact prompt, renderer, config, schema, source-freeze,
   replay, preflight, receipt, result, checkpoint, and experiment identifier.
8. Provide an exact delta table from v1 to v2. Every change must be forced by the
   new evidence; unrelated redesign is prohibited.

## Output constraint

Do not modify the repository and do not run GPU experiments. Return exactly one
self-contained Markdown document and no other output. Suggested filename:

`GPT_PRO_A1_VERTICAL_BPR_V2_DESIGN_2026-08-13.md`

The document may still conclude `NO-GO`, but only after applying the committed
evidence and producing a coherent new-version qualification contract.
