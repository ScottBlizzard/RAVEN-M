# A2 Design Rationale and Zero-Generation A1 Trace Replay

This document explains why A2 contains exactly one memory upgrade and one separately attributed cost guard. It is design evidence, not an A2 result.

## Empirical starting point

On the same 19 AndroidWorld Hard instances and seed 20260806:

| Arm | Full success | Steps | Total tokens | Approx. wall time |
|---|---:|---:|---:|---:|
| A0 official Qwen baseline | 4/19 | 329 | 1,273,361 | 1.82 h |
| A1 Action Working Memory | 5/19 | 603 | 3,464,267 | 4.06 h |

A1 produced one paired gain and no paired losses, but its cost increase is too large for the accuracy gain. The three largest loop increases account for about 194 of A1's 274 extra steps (roughly 71%). A1 also keeps up to six memory records while the same `MEMORY[...]` payload remains in ordinary action history, which duplicates information and increases later prompt length.

The useful A1 gain still matters: in `RecipeDeleteMultipleRecipesWithConstraint`, A0 initiated the final deletion and stopped before the evaluator-confirmed end state, whereas A1 kept the pending confirmation requirement visible and completed it. This supports preserving explicit pending/verified progress, not discarding memory altogether.

## Minimal A2 change

A2 therefore does not add a planner, critic, RAG retriever, extra screenshots, or extra model calls. It:

1. replaces six raw recency records with one compact progress state;
2. requires `observed`, screenshot-attested `verified`, `pending`, and the next action's expected visible effect;
3. records whether the action actually produced an observable screen/activity/UI-tree change;
4. stores the structured state once and commits only the short imperative to ordinary action history.

This directly targets A1's useful behavior (persisting pending confirmation) and its largest cost defect (repeated structured prose).

## Separate cost guard and its attribution boundary

The deterministic guard only asks whether an equivalent action was executed twice on the same visibly equivalent screenshot state without any observable screenshot change. Its state signature is computed from the screenshot already supplied to the model; hidden activity and UI-tree data remain audit-only. The first two attempts are allowed. A third equivalent proposal is blocked and the model is told to inspect or reroute. If it ignores two consecutive block messages, interaction stops and the normal evaluator assigns the final label; the guard receives no success credit.

The guard cannot see evaluator state and cannot earn success credit. Its events are logged separately from memory reads and writes. Therefore the final analysis can distinguish:

- memory-supported changed decisions;
- guard-only avoided execution;
- episodes with both mechanisms;
- ordinary failures with neither mechanism active.

## Zero-generation replay on frozen A1 traces

The frozen guard rule was replayed over already recorded A1 screenshots, UI hashes, activities, canonical actions, and transitions. Replay stopped at each task's first hypothetical trigger because later A1 actions are no longer a valid counterfactual after an intervention.

| A1 task | A1 result | A1 steps | First hypothetical guard trigger (1-based) | Repeated action |
|---|---:|---:|---:|---|
| MarkorMergeNotes | fail | 78 | 14 | top-bar tap |
| MarkorTranscribeVideo | fail | 20 | 13 | repeated central tap |
| OsmAndTrack | fail | 120 | 26 | repeated add/control tap |
| RecipeAddMultipleRecipesFromImage | fail | 60 | 10 | repeated unchanged-state swipe |
| SaveCopyOfReceiptTaskEval | fail | 16 | 7 | repeated unchanged-state swipe |
| SportsTrackerActivitiesOnDate | fail | 20 | 17 | repeated unchanged-state swipe |

No successful A1 episode reached the frozen blocking condition in this replay. This does **not** prove that A2 will be harmless or successful; it only shows that the rule is aimed at observed failed loops rather than being chosen without trace evidence.

## Frozen decision

The actual A2 run remains necessary. Accuracy improvement requires more than A1's 5/19 full successes, while cost improvement requires both fewer total tokens and lower wall time than A1. Any guard-only saving is reported as cost control, not as memory effectiveness.
