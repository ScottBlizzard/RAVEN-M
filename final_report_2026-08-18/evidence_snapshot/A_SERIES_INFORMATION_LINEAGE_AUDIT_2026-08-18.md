# A-series information-lineage audit after the R15 Browser finding

Date: 2026-08-18
Scope: frozen A0--A12 evidence plus the later R15 Browser forensic. This is an
offline audit; it makes no new generation call and does not relabel any prior
arm.

## Executive finding

The earlier A-series did perform error analysis, but most of its common audit
schema started too late. It asked whether memory was written, retrieved and
followed. The R15 Browser case shows an earlier failure mode: a useful value can
be visible and even articulated in raw Thought/Action, then be removed or
collapsed by the history/parser transform before any memory writer sees it.

The corrected lineage is:

`L0 visible pixels -> L1 raw model articulation -> L2 parser/history transform
-> L3 memory write -> L4 retrieval/injection -> L5 changed decision/execution
-> L6 evaluator outcome`.

Therefore, “memory was active but did not help” and “memory never contained the
needed fact” are different negative results. R15 supplies a naturally occurring
positive trace that exposes this distinction, but the distinction can and must
also be audited from failures without requiring a positive example.

## Evidence-status vocabulary

- **Observed**: directly present in frozen episode/events/request artifacts.
- **Derived**: deterministic computation from observed artifacts.
- **Inferred**: mechanism explanation consistent with evidence but not a
  counterfactual proof.
- **Unobservable**: the old artifact schema did not retain the needed stage.

## Per-arm lineage matrix

| Arm | Frozen outcome | What the original audit established | Earliest evidenced break | Status under the expanded lineage | Consequence |
|---|---:|---|---|---|---|
| A0 | 4/19 | Screenshot-only baseline and full action/evaluator trace | No explicit L3--L4; failures can occur at L1, L2 or L5 | L0/L1/L5/L6 mostly observed; L2 not uniformly compared | Use as behavioral reference, not as a memory-mechanism failure |
| A1 | 5/19 | 515 writes, 580 nonempty reads; one paired gain, no losses | Often L5: persistent pending state can stabilize both useful work and wrong loops | L3/L4 strong; L0->L1->L2 lineage was not the primary audit | Positive evidence for pending-operation memory, with major cost/loop risk |
| A2 | 0/19 | Complete compound negative; deduplicated structured state plus verified-progress/guard | L3 content and L5 policy use; frequent self-authored state did not yield useful execution | Strong post-write audit, weak systematic L1->L2 attribution | Valid negative compound control, not proof that visible evidence was preserved |
| A3 | 0/1 gate | 12/34 compliant writes and 33/34 nonempty reads | L3 protocol compliance and L5 use | Well diagnosed after L2; zero-shot ConAct port, not MemGUI-SFT | Do not expand; retain as a limited-port negative |
| A4 | 0/1 gate | Same workflow injected on all 34 steps | Before L4 relevance: one `ExpenseAddSingle` donor was deterministically flattened and reused for delete | Directly observed in donor bank/audit; not a faithful offline-AWM test | Old A4 cannot support “AWM is ineffective”; run a new identity with matched successful donors |
| A5 | 0/1 gate | 0/34 compliant graph writes | L3: graph never activated | Directly observed; also explicitly not full HyMEM | Valid port failure, no inference about full HyMEM |
| A6 | 0/19 | 625 actions; many low-change transitions and repeated actions after reads | L3/L4 overproduction, then L5 repetition | Strong post-write negative; source-fact preservation not generally tested | Always-on transition replay is harmful in this setting |
| A7 | 4/19 | 19/19 valid; several successes occurred while ledger inactive | Often L3 silence; active delivery not linked to gains | Strong activation/attribution audit | Transparent control preserves baseline-level success but offers no gain evidence |
| A8-v2 | 0/1 gate | 14 reads in the failed Expense episode | L5: exposure without loop escape | Strong L4/L5 negative | Exact revisit statistics alone did not change the decision |
| A9 | 1/2 gate | Expense success was silent; Retro had 3 activations and failed | L5 on Retro; no mechanism credit on silent Expense | Strong activation attribution | Sparse recurrence detection is insufficient without productive recovery |
| A10-v2 | 2/6 diagnostic | 6 reads, all in failed episodes; both successes silent; 0 productive divergences | L5 | Strong L4/L5 negative, post-hoc diagnostic only | Obligation/frontier exposure did not create useful divergence |
| A11 | 2/6 diagnostic | 4 recovered reads in failed episodes; successes silent; 0 productive divergences | L5 | Strong L4/L5 negative; top-level counter had a schema bug | Corrected counting does not change the negative causal result |
| A12 | 1/6 diagnostic | 3 reads in failed episodes; success silent; 0 productive divergences | L5; formal protocol also invalid | Diagnostic evidence only | Useful causal-audit tooling, not a successful memory policy |

## What R15 changes

For `BrowserMultiply`, the successful A1-R15 trajectory retained the displayed
values `1, 8, 10, 7, 2` in ordinary raw history because a malformed structured
prefix bypassed the R2 history deduplicator. R2/R13/R14 retained memory state
but did not preserve that same raw value stream. This is not evidence that a
malformed prefix is a generally good mechanism. It is evidence that the
information lost at L1->L2 was causally upstream of the later memory stages and
was previously under-measured.

This is a methodological change from **component audit** to **information
lineage audit**:

1. Identify the minimal task-relevant fact available in pixels.
2. Test whether it appeared in raw model output.
3. Test whether parser/history transforms retained, normalized or deleted it.
4. Only then judge memory write, retrieval, utilization and outcome.

The positive R15 trace makes the hypothesis unusually legible, but a positive
trace is not required. Across failures, the same audit can distinguish:
`never perceived`, `articulated then lost`, `stored but not retrieved`,
`retrieved but ignored`, and `used but still wrong`.

## Re-analysis priorities

1. Apply L0--L6 lineage first to tasks where the answer or intermediate values
   visibly accumulate: Browser, Sports duration/distance, source-document
   transfer, and repeated constrained deletion.
2. Do not build another memory field until the earliest loss stage is known.
3. Require every new arm to emit per-step hashes/anchors for raw response,
   transformed history, written memory, rendered memory and executed action.
4. Credit a mechanism only when a relevant read precedes a useful divergence;
   silent successes remain preservation evidence only.
5. Keep old A3--A12 verdicts frozen. This audit narrows their interpretation;
   it does not rewrite their outcomes.

## Frozen source basis

- `evidence/a1/A1_ACTION_WORKING_MEMORY_RESULTS_2026-08-10.md`
- `evidence/a2/A2_SCORED_RESULT_20260811.md`
- `protocols/A345_PUBLIC_MEMORY_KERNELS_PREREG_2026-08-11.md`
- `protocols/A345_FAILURE_FORENSICS_AND_SUCCESSOR_CONSTRAINTS_2026-08-11.md`
- `evidence/a345/A4_DONOR_SOURCE_AUDIT.json`
- `evidence/a678/A7_TRANSPARENT_19_TASK_CONTROL.json`
- `evidence/a678/A89_INITIAL_GATE_RESULTS_2026-08-12.json`
- `evidence/diag6/A10V2_DIAGNOSTIC6_RESULT_2026-08-13.md`
- `evidence/diag6/A11_A12_DIAGNOSTIC6_RESULTS_2026-08-13.md`
- `evidence/r15_browser_forensics/R15_BROWSER_FORENSIC_2026-08-18.md`
