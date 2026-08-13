# A10-v2/A11/A12 enriched six-task diagnostic protocol

Status: prospective diagnostic binding, not a formal-arm repair.

Protocol ID: `ENRICHED_MEMORY_DIAGNOSTIC6_V1`

Infrastructure binding: the live server must set
`VLLM_USE_FLASHINFER_SAMPLER=0` and record it in both launch intent and live
receipt. This is a fail-closed Blackwell compatibility fallback for vLLM's
top-k/top-p sampler; it does not change the model, prompt, seeds, sampling
parameters, memory mechanism, action schema, or model-call count.

This protocol asks a narrower question than the frozen A10-v2, A11, and A12
preregistrations: when a task is enriched for a historically observed memory
opportunity, does a nonempty memory read change the next action and produce
arm-native bounded short-horizon escape or visible progress? It does not authorize any claim about the
nineteen-task AndroidWorld Hard distribution and cannot change the formal
failure or protocol-invalid status of the parent arms.

## Frozen identities

The source mechanisms are unchanged and are instantiated independently, one
fresh instance per episode. The diagnostic experiment identities are:

- `A10V2_DIAG6_EMOBF_QWEN3VL32B_AW_HARD_T20260806_G3407_V1`
- `A11_DIAG6_CRC_ECOBF_QWEN3VL32B_AW_HARD_T20260806_G3407_V1`
- `A12_DIAG6_MADM_QWEN3VL32B_AW_HARD_T20260806_G3407_V1`

Model, revision, system prompt, task seed 20260806, generation seed 3407,
sampling parameters, native task budgets, screenshot-only model-visible input,
and single-transport policy remain identical to A0/A1.

## Frozen enriched panel

The order is exact:

1. `OsmAndTrack`
2. `RecipeAddMultipleRecipesFromImage`
3. `RecipeAddMultipleRecipesFromMarkor`
4. `RecipeDeleteMultipleRecipesWithConstraint`
5. `RetroSavePlaylist`
6. `SaveCopyOfReceiptTaskEval`

The panel was selected before live generation because all three mechanisms had
an offline memory opportunity on these task identities. This is deliberate
post-hoc enrichment and must be reported as such.

## Execution and closure

Arm order is A10-v2, A11, then A12. Every arm runs all six tasks even after a
scientific failure. Valid completed episodes are never rerun. Infrastructure-
invalid episodes may be replaced at most twice for the same task, with explicit
bidirectional links. The three memories are never composed.

No mechanism may add model calls, block or replace actions, force termination,
or use hidden UI, evaluator state, reward, task name, future frames, or another
arm's state for a decision. The original failed preflights remain immutable;
this diagnostic uses a separate preflight and live receipt.

## Evidence and interpretation

For every nonempty read, record exact injected text/hash, rendered size/tokens,
support/maturity evidence, next executed action, next-action divergence,
arm-native visible progress or frontier escape within at most three actions,
same-failed-action or frontier relapse within four
actions, final reward, actions, model calls, and tokens.

An arm is `diagnostically_active` only if at least three of six episodes contain
a real nonempty read. It has a `productive_divergence_signal` only if at least
two trace-grounded reads are followed by action divergence and short-horizon
escape/progress without a four-action relapse. These labels are exploratory;
reward comparisons against A0/A1 are descriptive paired comparisons, not a
generalization claim.

Zero activation, activation without divergence, divergence without progress,
and reward regression are all valid scientific outcomes and do not permit
threshold changes or task replacement.
