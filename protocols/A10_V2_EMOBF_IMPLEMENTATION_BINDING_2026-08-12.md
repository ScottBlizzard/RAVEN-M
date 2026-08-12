# A10-v2 EM-OBF implementation binding

This file binds the deterministic implementation of the first, EM-OBF half of
`GPT_PRO_A10_V2_STANDALONE_MEMORY_DESIGN_2026-08-12.md`. It does not bind the
separately registered A11 CRC-ECOBF design.

## Identity

- Design parent: `4548b932bc3b189507e1442e312c73c8f35dbdb8`
- Mechanism: `a10_v2_evidence_matured_obligation_branch_frontier_v2`
- Experiment: `A10_V2_EMOBF_QWEN3VL32B_AW_HARD_S20260806_G3407_V1`
- CLI arm: `a10_v2_emobf`

## Deterministic clarifications

These close underspecified representation details without changing any Pro
trigger count, threshold, score coefficient, replay gate, or experimental
success condition.

1. Extraction priority is also specificity weight: quoted 6, colon/marker 5,
   constraint bundle 4, numeric/time 3, temporal 2. Group weight equals its
   extraction unit weight. Weighted Jaccard uses these group weights.
2. `operation_class` uses the frozen ordered lexicon in the implementation:
   DELETE, TRANSFER, TRANSFORM, CREATE_OR_ADD, QUERY_OR_CALCULATE, NAVIGATE,
   otherwise OTHER. It is audit-only.
3. `route_head_gain` is the maximum non-negative confidence delta, measured
   from the departure receipt baseline through route resolution, over HEADs of
   groups open at departure. `target_context_changed` is true iff a subsequent
   route action has a different exact target-group mask.
4. Only HEAD anchors receive confidence evidence. An action explicitly touches
   a HEAD iff its exact token-subsequence bit is present in `target_anchor_mask`.
   Failure/reopen terms must be within 48 normalized characters of that HEAD.
   A strong negative means weight at most -0.30 occurring after prior hard
   support.
5. A legal clear is canonical `type_text(clear_text=true)` or an action summary
   matching `clear|erase` within 32 characters of `input|text|field|query|search`.
   T4 requires same normalized text, phase, open-group mask, source frontier
   route-match and target-group mask. A clear suppresses re-entry unless the
   policy returns to the same previously bad frontier.
6. A post-return watch consumes observations only from `returned_step + 1`.
   The return action that creates the watch cannot be its second witness.
7. One bounded `NoGroupPhaseWatch` records a no-group COMMIT local change and
   switches phase only after four route actions without a source return.
8. A negative constraint is rendered with the literal prefix `exclude`; its
   polarity is never dropped.
9. Frontier merge chooses exact first, otherwise minimum distance, then newest
   visit, then lexical frontier ID. Exemplars are exact-deduplicated and keep
   the three most recent deterministic representatives. Eviction uses the
   utilities and lexical tie-breakers frozen in the design.
10. The generated zero-generation preflight, review, live receipt and result
    artifacts are not inputs to their own source-freeze digest. The live
    receipt binds the completed preflight hash separately.
11. The sole pre-live replay failure verdict is
    `A10_V2_ZERO_GENERATION_PREFLIGHT_FAIL`; the non-schema phrase
    `A10_V2_PROTOCOL_INVALID_FOR_LIVE` is treated as explanatory prose only.

## Public interface

`EvidenceMaturedObligationBranchFrontierMemory` exposes:

```text
read(context) -> (text, audit)
observe_step(**kwargs) -> audit
audit_record() -> audit
```

The module also exports `describe_visual_state`, `visual_distance`,
`visual_match`, `changed_pixel_fraction`, `canonical_action_family`,
`target_masks`, and `parse_goal`.

It has no model client, evaluator input, action filtering, action override,
guard, planner, verifier, critic, or termination API.

## Evidence status

This binding is an implementation artifact only. It does not constitute a
formal replay report or preflight pass. Live generation remains forbidden until
the separately generated real-trace replay, two independent reviews, source
freeze, tests, tokenizer/capacity checks, preflight, and fresh server receipt all
pass.
