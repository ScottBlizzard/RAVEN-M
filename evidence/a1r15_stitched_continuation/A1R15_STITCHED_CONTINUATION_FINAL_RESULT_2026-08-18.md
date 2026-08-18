# A1-R15 stitched continuation final result

Status: **SEALED_SIX_TASK_DIAGNOSTIC_NO_RELEASE**  
Evidence class: `TRANSPARENT_POST_TERMINAL_STITCHED_BEHAVIORAL_DIAGNOSTIC`

The six newly executed tasks scored **3/6**. Together with the immutable, previously sealed BrowserMultiply success, the descriptive stitched panel is **4/7**. The 7/7 release gate failed, so the remaining twelve tasks were not run.

This does not revise the original A1-R15 terminal result. Browser was not rerun, the seven tasks are not held out, and neither Browser nor the three new successes is attributed to EVR.

| Task | Reward | Calls | Actions | Tokens | EVR activation/append/read | Classification |
|---|---:|---:|---:|---:|---:|---|
| ExpenseDeleteMultiple2 | 1 | 22 | 21 | 87,490 | 0/0/0 | SUCCESS_COMPONENT_SILENT_OR_UNUSED_UNATTRIBUTED |
| RetroSavePlaylist | 1 | 29 | 28 | 118,263 | 0/0/0 | SUCCESS_COMPONENT_SILENT_OR_UNUSED_UNATTRIBUTED |
| SimpleCalendarAddOneEvent | 0 | 34 | 34 | 140,889 | 0/0/0 | REGRESSION_COMPONENT_SILENT_ZERO_OPPORTUNITY |
| SportsTrackerTotalDurationForCategoryThisWeek | 1 | 11 | 11 | 42,615 | 0/0/0 | SUCCESS_COMPONENT_SILENT_OR_UNUSED_UNATTRIBUTED |
| RecipeDeleteMultipleRecipesWithConstraint | 0 | 34 | 33 | 141,735 | 0/0/0 | REGRESSION_COMPONENT_SILENT_ZERO_OPPORTUNITY |
| OsmAndMarker | 0 | 14 | 13 | 55,186 | 0/0/0 | REGRESSION_COMPONENT_SILENT_ZERO_OPPORTUNITY |

## Mechanism result

All six live continuation tasks were outside the collection-arithmetic goal grammar. Across all six, EVR had zero opportunity, zero activation, zero append, zero retained values, zero render/read, and zero use. Expense, Retro, and Sports are therefore component-silent successes. Calendar, Recipe, and Osm are regressions relative to frozen R2 successes, but the losses cannot be assigned to EVR content because it never entered a prompt.

Against the historical R2 six-task panel, the descriptive comparison is 0 wins, 3 ties, and 3 regressions. The continuation used 42 more calls, 43 more actions, and 180,350 more tokens. This is not a matched contemporaneous ablation: visible starting state and route differed, and generation used temperature 0.7, so these deltas do not establish an EVR causal effect.

Failure chains:

- **Calendar:** first physical warning `L4@step0`, first meaningful route divergence `L1/L2@step1`; repeated day-by-day navigation exhausted the budget before save.
- **Recipe:** first meaningful divergence `L1/L2@step1`, no-progress visible by `L4@step3`; the model never opened Broccoli and terminated failure.
- **Osm:** launch transition failed at `L4@step2`, route diverged at `L2@step3`; the model selected Add/favorite rather than Marker and then claimed completion from the orange favorite pin, while evaluator reward was zero.

## Cost and closure

The six live episodes used **144 calls**, **140 executed actions**, and **586,178 tokens** (568,732 prompt + 17,446 completion), with **144/144 single-transport calls** and no invalid or lifecycle-invalid attempt. Their summed episode elapsed time was **7767.378235 seconds**. Imported Browser token/time totals are unavailable from the frozen parent bundle, so no stitched token/time total is reported.

Checkpoint content SHA-256: `c4295225271cbc161d0218664433431f519d1c262855d89f04e514b34a78049d`  
Runner result content SHA-256: `73eb81540c7033cb432a13806d72a24e3713342ad683f66010327d4f69c36bce`  
Final evidence content SHA-256: `53b78fd02ad18153a2e8a465def27c44a9303d2d915db6be01a17930b5c71404`
