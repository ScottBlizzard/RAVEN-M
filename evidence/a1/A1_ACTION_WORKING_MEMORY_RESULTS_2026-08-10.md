# A1 Action Working Memory — Frozen Paired Result

Date: 2026-08-10

Benchmark: 19 AndroidWorld Hard tasks, task seed `20260806`

Model: `Qwen/Qwen3-VL-32B-Instruct`, revision `0cfaf48183f594c314753d30a4c4974bc75f3ccb`

Frozen A1 result/code commit: `fbc25dc`. The current A2 branch intentionally changes shared controller files; exact A1 reruns must check out the frozen A1 commit rather than relabel the current tree as A1.

## Intervention

A1 keeps the official Qwen mobile controller, screenshot-only input, action protocol, model, decoding, task instances, and native step budgets. The only intended intervention is an episode-local Action memory. At every step the model writes:

`MEMORY[observed=...; verified=...; pending=...] | <UI action>`

The controller stores at most six unique recent payloads and injects them into later ordinary requests. It adds no model call and cannot access hidden evaluator state or cross-episode data.

## Main paired result

| Metric | A0 official baseline | A1 Action memory | Difference |
|---|---:|---:|---:|
| Full successes | 4/19 (21.1%) | 5/19 (26.3%) | +1 task |
| Partial-reward tasks | 1 | 1 | 0 |
| Total reward | 4.5 | 5.5 | +1.0 |
| Steps / model calls | 329 | 603 | +274 (+83.3%) |
| Total tokens | 1,273,361 | 3,464,267 | +2,190,906 (+172.1%) |
| Approximate wall time | 1.82 h | 4.06 h | +123% |
| Infrastructure-invalid scored tasks | 0 | 0 | 0 |

A1 memory was operational in all 19 episodes, with 515 successful writes and 580 nonempty reads. Strict pairing gives one gain, zero losses, and eighteen ties. This is a positive signal on one frozen seed, not a generalization result.

## Per-task pairing

| Task | A0 reward | A1 reward | A0 steps | A1 steps |
|---|---:|---:|---:|---:|
| BrowserMultiply | 0 | 0 | 13 | 22 |
| ExpenseAddMultipleFromGallery | 0 | 0 | 16 | 20 |
| ExpenseAddMultipleFromMarkor | 0 | 0 | 13 | 18 |
| ExpenseDeleteMultiple2 | 1 | 1 | 18 | 19 |
| MarkorCreateNoteAndSms | 0.5 | 0.5 | 17 | 18 |
| MarkorMergeNotes | 0 | 0 | 32 | 78 |
| MarkorTranscribeVideo | 0 | 0 | 20 | 20 |
| OsmAndMarker | 0 | 0 | 11 | 17 |
| OsmAndTrack | 0 | 0 | 19 | 120 |
| RecipeAddMultipleRecipesFromImage | 0 | 0 | 60 | 60 |
| RecipeAddMultipleRecipesFromMarkor | 0 | 0 | 13 | 60 |
| RecipeAddMultipleRecipesFromMarkor2 | 0 | 0 | 14 | 10 |
| RecipeDeleteMultipleRecipesWithConstraint | 0 | **1** | 15 | 26 |
| RetroSavePlaylist | 1 | 1 | 32 | 28 |
| SaveCopyOfReceiptTaskEval | 0 | 0 | 10 | 16 |
| SimpleCalendarAddOneEvent | 1 | 1 | 17 | 34 |
| SportsTrackerActivitiesOnDate | 0 | 0 | 3 | 20 |
| SportsTrackerTotalDistanceForCategoryOverInterval | 0 | 0 | 3 | 9 |
| SportsTrackerTotalDurationForCategoryThisWeek | 1 | 1 | 3 | 8 |

## What appears useful

The paired gain is `RecipeDeleteMultipleRecipesWithConstraint`. A0 initiated the final deletion and stopped before the evaluator-confirmed end state. A1 kept the pending confirmation visible and completed it. The most defensible mechanism hypothesis is therefore not better visual recognition; it is persistent accounting of completed versus still-unconfirmed repeated operations.

## What failed

A1 remembers pending work but does not know whether the last action produced the expected effect. `OsmAndTrack` reached 120 steps while repeatedly remembering the same waypoint objective and tapping the same control. `MarkorMergeNotes` increased from 32 to 78 steps while repeatedly carrying the same pending state through failed navigation. Memory can stabilize an error loop as easily as it can stabilize useful progress.

Cost also grows twice: A1 makes 83% more calls and each call is longer because recent structured memory is injected while the same structured Action prose accumulates in ordinary history. The top three loop increases account for roughly 71% of A1's 274 extra steps.

## Conclusion that motivates A2

A1 establishes that a simple memory can be genuinely active and can change one paired outcome, but it is not cost-effective. The next arm should preserve explicit pending/verified progress, attach observable outcome evidence to the preceding action, avoid duplicating structured state in history, and stop repeated no-progress execution. It should not merely increase memory capacity or add unrelated modules.
