# A4-v2 faithful offline Agent Workflow Memory preregistration

Date: 2026-08-18  
Experiment identity: `A4V2_FAITHFUL_OFFLINE_AWM_QWEN3VL32B_AW_HARD_S20260806_V1`  
Parent controller: A0 official Qwen3-VL-32B screenshot-only controller

## Question

Does an AWM-faithful *offline* workflow bank, induced from independently
successful non-Hard AndroidWorld examples and retrieved by a matched task route,
improve or preserve the fixed seven-task diagnostic relative to A0?

This is a new arm. It does not repair, resume or overwrite A4-v1. A4-v1 remains
a valid negative result for a single-donor deterministic workflow port, but is
not evidence against faithful offline AWM.

## Fidelity commitments

The official AWM code induces common, reusable subroutines from multiple
successful examples before evaluation and injects workflows during policy
execution. A4-v2 therefore requires:

1. Only evaluator-confirmed successful Easy/Medium donor episodes.
2. At least two independent donor episodes for every released route, with
   different seeds; a third is a non-blocking robustness target when time permits.
3. Donor task classes absent from the scored 19-Hard manifest. Exact scored
   instances, answers, earlier Hard trajectories and evaluator feedback are
   forbidden induction inputs.
4. A model-induced summary of common subroutines across the donor traces. A
   deterministic per-action paraphrase is forbidden.
5. Donor literals and coordinates replaced by descriptive variables. A
   workflow must contain at least two reusable steps.
6. The bank is frozen and hashed before scored generation. It never updates
   during the seven or nineteen scored tasks.
7. Scoring adds no planner, critic, action repair, guard, hidden UI input,
   evaluator input or extra model call. Workflow text is memory context only.
8. Retrieval requires exact App + operation-family compatibility. A same-App
   but different-operation donor is never injected as a fallback.

## Frozen route map and donor acquisition targets

| Scored task | Required route | Eligible non-Hard donor classes | Minimum |
|---|---|---|---:|
| BrowserMultiply | Browser / open-local-task | BrowserDraw, BrowserMaze | 2 successes; route workflow only, no arithmetic claim |
| ExpenseDeleteMultiple2 | Pro Expense / delete | ExpenseDeleteMultiple, ExpenseDeleteSingle, ExpenseDeleteDuplicates | 2 successes; third targeted |
| RetroSavePlaylist | Retro Music / create-playlist | RetroCreatePlaylist | 2 seeds; only the create-playlist subroutine transfers |
| SimpleCalendarAddOneEvent | Simple Calendar Pro / add-event | SimpleCalendarAddOneEventTomorrow, SimpleCalendarAddOneEventRelativeDay, SimpleCalendarAddOneEventInTwoWeeks | 2 successes; third targeted |
| SportsTrackerTotalDurationForCategoryThisWeek | OpenTracks / retrieve-duration | SportsTrackerActivityDuration, SportsTrackerActivitiesCountForWeek, SportsTrackerLongestDistanceActivity | 2 successes; common navigation/read subroutines only |
| RecipeDeleteMultipleRecipesWithConstraint | Broccoli / delete-recipe | RecipeDeleteMultipleRecipes, RecipeDeleteMultipleRecipesWithNoise, RecipeDeleteSingleRecipe | 2 successes; third targeted |
| OsmAndMarker | OsmAnd / add-location-marker | OsmAndFavorite | 2 seeds; third targeted |

The task-list difficulty labels are frozen from the repository's archived
official AndroidWorld task list. A donor is not admissible merely because its
class appears in this table; its success and provenance still must validate.

## Induction contract

Donor packets are grouped by route, template-deduplicated, and include the
natural-language query plus the raw successful Thought/Action trace with task
literals masked. The induction instruction follows the official AWM contract:
extract non-overlapping commonly reused subroutines, preserve invariant UI
semantics, replace variable inputs with descriptive placeholders, and emit at
least two steps per workflow.

The induction response is rejected if it contains donor literals, coordinates,
Hard task values, fewer than two donor IDs, a one-step workflow, generic text
such as “perform the visible done operation”, or a route mismatch.

## Scored retrieval and causal boundary

The goal is deterministically classified into App, operation, object and
constraint families. Retrieval first filters by exact App and operation. Object
or constraint fields may be `*` only when the induced workflow is a genuine
common subroutine. Within the compatible set, specificity then workflow ID
provides deterministic ordering. At most three workflows and 1800 characters
are injected.

The model is told that workflows are optional prior examples, current pixels
override them, donor values must never be copied, and unsupported steps must be
ignored. The memory cannot block or replace an action.

## Schedule and stopping

Run all seven tasks without scientific fail-fast, in this exact order:

1. `BrowserMultiply`
2. `ExpenseDeleteMultiple2`
3. `RetroSavePlaylist`
4. `SimpleCalendarAddOneEvent`
5. `SportsTrackerTotalDurationForCategoryThisWeek`
6. `RecipeDeleteMultipleRecipesWithConstraint`
7. `OsmAndMarker`

Every valid task is retained, including reward zero. Only infrastructure-invalid
attempts may be replaced. If the arm reaches at least 7/7, run the remaining 12
in original manifest order. A weaker result remains a complete seven-task
diagnostic and receives route-level failure analysis; it is not rerun or tuned
under the same identity.

## Required analysis

For every task, report workflow match, injected workflow IDs, read count, first
post-read divergence, reward, cost and L0--L6 information-lineage break. A
success without a read is not credited to AWM. A read followed by failure is
reported as exposure without benefit.

If any task is a paired gain over A0, run a matched-content ablation on that
task under a new identity: same retrieval shell and prompt length, but shuffled
incompatible workflow content. This separates useful workflow content from
generic extra-context effects.

## Claim boundary

Success supports offline workflow transfer in this Qwen/AndroidWorld setting.
Failure supports only: “this faithful offline-AWM adaptation did not transfer
under the frozen donor coverage and controller.” It does not establish that AWM
is universally ineffective.
