# A11 CRC-ECOBF Implementation Binding — 2026-08-12

This binding resolves only omissions and contradictions that made the split
Pro design non-executable. It does not alter any Pro threshold.

## Frozen identity

- Mechanism: `a11_confirmed_route_contraction_ecobf_v1`
- Experiment: `A11_CRC_ECOBF_QWEN3VL32B_AW_HARD_T20260806_G3407_V1`
- Parent evidence: `4548b932bc3b189507e1442e312c73c8f35dbdb8`

## Deterministic resolutions

1. Only `APP_SCOPE_RE` is used. The conflicting greedy `BARE_APP_RE` is not
   used. This is necessary for `that use zucchini from Broccoli app` to retain
   `zucchini` while excluding the explicit app span.
2. Attribute predicates `is` and `are` normalize to `EQUAL`.
3. `operation_class` uses the ordered DELETE, TRANSFER, TRANSFORM,
   CREATE_OR_ADD, QUERY_OR_CALCULATE, NAVIGATE lexicon in the A11 core.
4. Specificity equals the parser priority: constraint 5, quoted 4, list 3,
   numeric/temporal 2.
5. Reversal/failure prose uses the fixed core regex and the same 48-character
   proximity rule as commit prose.
6. T0 evidence strength is `clip(0.65 + min(0.20, gained-anchor confidence)
   + 0.10*max(0, offscreen_count-2), 0, 1)`. T4 evidence strength is the
   greater of 0.65 and the first bad occurrence's branch confidence.
7. Target progression means a route mentions an item bit that was open but had
   not occurred in `phase_targeted_mask` before the route began. Pending routes
   retain that baseline.
8. T3 workflow credit is the maximum residual-work credit among the adverse
   receipts supporting the candidate.
9. Cooldown is episode-global. A phase switch resets only the per-phase read
   counter, never `last_nonempty_read_step`.
10. A bounded four-entry `LateRouteWatch` retains a fully embedded pending
    route through action 8. A late return revises, rather than duplicates, its
    durable receipt and raw count.
11. A decision visit is registered only by `read()`. `observe_step()` may
    match or create source/destination frontiers but never increments visits.
12. Branch confidence is recomputed from the retained 32 receipts. Evicted
    receipts no longer contribute decayed evidence.
13. Pending routes embed source descriptor, entry branch key/label/intent,
    entry attempt/bad baselines, masks, confidences, and targeted-mask baseline.
    Route evidence therefore remains valid if a frontier or branch is evicted.
14. Post-return confirmation requires `source_match AND (same entry branch OR
    current branch bad confidence >= 0.55)`.
15. The replay metrics in `a11_contract.py` are the normative evaluator-side
    algorithms. A post-return T2 has one route plus a distinct adverse branch
    receipt and therefore is not a prohibited single-support delivery.

## Runtime boundary

The core exposes the working-memory interface:

```text
read(context) -> (text, audit)
observe_step(**kwargs) -> dict
audit_record() -> dict
```

It imports no network, model, evaluator, OCR, UI-tree, accessibility, or task
database component. Formal offline replay and preflight evidence are not
created by this implementation commit.
