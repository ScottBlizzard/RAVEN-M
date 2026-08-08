# Screenshot-only completion verifier diagnostic

Date: 2026-08-08  
Status: complete; verifier line stopped  
Claim class: development-contaminated offline layer diagnostic; not held-out efficacy and not a novelty claim

## Bottom line

A detached Qwen critic rejected 19/21 false-success claims, but accepted only 2/6 evaluator-confirmed successes. Balanced accuracy was 0.6190, below the frozen 0.70 gate. Ordinary accuracy was 21/27 = 77.78%, exactly equal to the trivial reject-all rule on this imbalanced set. The screenshot-only completion verifier therefore does not qualify for online deployment.

The negative result is informative. Completion evidence has different observability types:

- a positive, fully visible record can sometimes be checked from one screenshot;
- deletion is an absence claim and generally requires a scoped query or database inspection;
- copy/export requires evidence of the destination, not a generic toast;
- multi-object and cross-app tasks require evidence accumulated across several states;
- even a visually strong `No recipes found` result is unsafe if the search operator does not cover the task predicate.

## Frozen setup

- run: `completion_verifier_20260808T183051_50c0413f`
- manifest: `05_project/configs/completion_verifier/official_qwen32b_success_claims_27.final.json`
- manifest SHA-256: `8d721aa99ac5f0f9cabf91410d83ebd8361d97265333ac9117754d87e60cfaf5`
- source: all 27 scientifically eligible official-baseline episodes with `model_claimed_status=success`
- labels: six evaluator-confirmed successes and 21 false-success claims
- model: `Qwen/Qwen3-VL-32B-Instruct`
- revision: `0cfaf48183f594c314753d30a4c4974bc75f3ccb`
- runtime: stock vLLM BF16 on one RTX PRO 6000 96GB
- sampling: seed 3407, temperature 0.7, top-p 0.8, top-k 20, presence penalty 1.5
- input: task goal plus exactly one screenshot captured immediately before `terminate(success)`
- hidden from verifier: evaluator label/reward, UI tree, database, original action history and original success prose
- calls: exactly 27, no repair call
- exact JSON outputs: 27/27 valid
- total usage: 75,464 prompt tokens, 2,224 completion tokens, 77,688 total tokens
- summed model latency: 128.135 seconds

The prompt, dataset, code hashes, thresholds and stop rule were frozen before generation in `05_project/docs/OFFLINE_COMPLETION_VERIFIER_PREREG_2026-08-08.md`.

## Result against the frozen gate

| Metric | Result | Frozen requirement | Decision |
|---|---:|---:|---|
| exact output validity | 27/27 | 27/27 | pass |
| false-success rejection | 19/21 = 90.48% | at least 16/21 | pass |
| true-success acceptance | 2/6 = 33.33% | at least 4/6 | **fail** |
| balanced accuracy | 61.90% | at least 70% | **fail** |
| task-level online qualification | no | all gates | **stop** |

Confusion matrix:

| Evaluator / critic | CONFIRMED | INSUFFICIENT |
|---|---:|---:|
| success | 2 | 4 |
| failure | 2 | 19 |

## What the critic did well

The critic correctly rejected several failure types that the acting agent had accepted:

- all three Expense-from-Gallery claims lacked proof that every visible receipt item had been entered;
- the Markor--SMS partial success visibly proved the SMS but not the required Markor note;
- all three merge-note failures showed missing, empty or filename-literal content;
- OsmAnd marker and track screenshots failed to prove the exact coordinate/object/waypoint sequence;
- recipe-add screenshots showed only one recipe or omitted required fields/multiplicity;
- both receipt-copy screenshots showed a generic `File copied successfully` toast but no `Download` destination;
- the failed playlist screenshot was blank.

These decisions support the earlier object-role diagnosis: a detached critic can often recognize that a related visible fact is weaker than the full task predicate.

## Why four true successes were rejected

### Deletion is an absence claim

Both successful ExpenseDeleteMultiple2 episodes were rejected. One screenshot simply did not display the deleted expense names; another showed the launcher. From one terminal screenshot, the critic could not distinguish `the objects were deleted` from `the relevant list is not currently visible`.

This is not merely excessive caution. A sound deletion verifier needs a scoped negative query or external state check. Absence from the current viewport is not absence from the database.

### Export is an off-screen side effect

The successful RetroSavePlaylist episode showed a playlist with three songs, but the title was truncated and export to Downloads was not visible. The evaluator confirmed the task, while the screenshot-only critic correctly noted that the destination side effect could not be observed.

### Final-screen choice can hide a completed state

Two of three successful calendar episodes ended on a detail screen displaying the exact title, date, time and description; the critic accepted both. The third successful calendar episode ended with a menu/other view that did not display the event, so the critic rejected it. The underlying task result was correct in all three. Thus verifier accuracy depends not only on task completion but also on whether the controller deliberately exposes a verifiable final view.

## Why two false successes were accepted

Both false positives were RecipeDeleteMultipleRecipesWithConstraint episodes. Their final screenshots showed `No recipes found` after searching for the target phrase (`lettuce` or `almond milk`). The critic treated this as proof that all recipes whose directions contained the phrase had been deleted.

The inference is invalid because the screenshot does not establish the search operator's scope. A UI search may cover title, indexed fields or current filter state rather than the `directions` predicate required by the task. `query returned zero rows` proves only `zero rows under this query semantics`, not `zero database objects satisfy the evaluator predicate`.

This is another correct-memory/wrong-authority failure: the visible observation is real, but its authority is narrower than the conclusion. A generic strictness instruction did not recover the missing provenance of the search operator.

## Resulting evidence taxonomy

| Task predicate | Minimum credible evidence | One terminal screenshot? |
|---|---|---|
| visible positive fields | exact detail/list row with all values | often yes |
| deletion / non-existence | scoped exhaustive query or database check | usually no |
| copy/export destination | destination listing or filesystem state | usually no |
| multiplicity | count/list covering every required object | only if exhaustive view is visible |
| cross-app transfer | source extraction plus destination state | no |
| typed object creation | object type, parent/container and fields | sometimes, if final detail view is explicit |

This taxonomy is more actionable than a single `critic on/off` flag. It says what evidence channel must be made available for each predicate type.

## Frozen decision and next boundary

Do not insert this screenshot-only critic as an online success gate. It would remove many false-success terminations, but it would also block four of six genuine successes and would not beat reject-all balanced behavior sufficiently.

The next defensible verifier must be requirement-wise and evidence-channel-aware:

1. decompose the task into positive, negative, multiplicity, destination and cross-app predicates;
2. attach each predicate to an evidence source with known scope;
3. deliberately navigate to a verifiable final view when screenshot evidence is possible;
4. use Android/database/filesystem state for predicates that cannot be proved visually;
5. separate `task succeeded` from `current screenshot visibly proves success` in both training labels and evaluation.

Any implementation of that verifier is a new experiment and requires a new closest-prior audit and preregistration. The present result supports the need for typed evidence channels; it does not establish a new method or a performance gain.

## Artifacts

- preregistration: `05_project/docs/OFFLINE_COMPLETION_VERIFIER_PREREG_2026-08-08.md`
- dataset manifest: `05_project/configs/completion_verifier/official_qwen32b_success_claims_27.final.json`
- protocol/parser: `05_project/src/raven_m/official_qwen_mobile/completion_verifier.py`
- runner: `05_project/scripts/run_offline_completion_verifier.py`
- run: `runs/completion_verifier/completion_verifier_20260808T183051_50c0413f`
- machine-readable result: `runs/completion_verifier/completion_verifier_20260808T183051_50c0413f/aggregate.json`
