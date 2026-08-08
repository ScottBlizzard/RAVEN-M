# Object-role evidence mismatch in the frozen official 57-key baseline

Date: 2026-08-08  
Scope: zero-generation retrospective audit  
Inputs: frozen 57-key aggregate, per-step screenshots/events, and the cross-seed mechanism notes

## Operational definition

An episode is counted as a clean object-role evidence mismatch only when all four conditions hold:

1. the relevant action produced a real GUI transition or a visible result;
2. that result proved a weaker or differently typed predicate;
3. the model promoted it to a stronger task-progress predicate in reasoning/history or termination;
4. the unsupported promotion was upstream of evaluator failure.

This definition excludes pure no-change loops, OCR errors without a later progress promotion, protocol errors, and episodes that failed before reaching the ambiguous object or destination.

## Clean cases

| Task class | Qualifying seeds | Observed evidence | Unsupported stronger claim |
|---|---:|---|---|
| `MarkorMergeNotes` | 3/3 | source file selected, clipboard item visible, or target file created | exact source content was pasted into the ordered target position |
| `OsmAndMarker` | 2/3 | Favorite page or map zoom transition | requested map marker was created |
| `OsmAndTrack` | 3/3 | place search / map visit / country-level result | place was added as a route waypoint and the track was saved |
| `RecipeDeleteMultipleRecipesWithConstraint` | 3/3 | title-search result empty, or a candidate detail page opened | directions-field candidate set was empty, or the last recipe was deleted |
| `SaveCopyOfReceiptTaskEval` | 2/3 | copy toast under `Internal/DCIM/Download` | file was copied to root `Internal/Download` |

Total: **13 clean episodes across 5 task classes and 4 application families**. Two additional seeds in these task classes failed at an earlier layer and were not counted: `OsmAndMarker/20260808` never reached object-type selection, and `SaveCopyOfReceiptTaskEval/20260808` never reached destination-path disambiguation.

## Why these are not ordinary no-change failures

The L4 intervention only rejected semantic progress when the activity, UI hash and pixels all remained effectively unchanged. Every clean case above can escape that rule because the interface genuinely changes:

- opening a Favorite editor is a real transition, but it does not create a Marker;
- visiting a place on the map is real, but it does not append a waypoint;
- opening a recipe detail is real, but it does not delete the recipe;
- receiving a copy-success toast is real, but it does not prove the parent directory is correct;
- creating the destination note is real, but it does not prove the required source values reached the body in order.

Therefore `screen_changed=true` is only an execution-level fact. It cannot by itself authorize a task-level predicate update.

## Cross-seed boundary

The count is descriptive, not 13 independent stochastic replications. The model generation seed was fixed and some task seeds share identical initial visible states. The stronger evidence is cross-task and cross-application recurrence with different target parameters and different low-level actions, not the raw episode count alone.

## Gate decision

The prevalence gate frozen in `05_project/docs/OBJECT_ROLE_EVIDENCE_CLOSEST_PRIOR_AUDIT_2026-08-08.md` is satisfied: at least three task classes and two application families contain clean cases.

This authorizes one matched diagnostic, but not a novelty or efficacy claim. The diagnostic must:

- use the same official Qwen model revision, task instance, sampling, native action budget and evaluator as baseline;
- add only a generic evidence-typing instruction, with no task answer, hidden UI tree or evaluator leakage;
- treat all selected task-seed pairs as development-contaminated matched cases;
- freeze the exact prompt, task list, metrics and stop rule before generation;
- report whether unsupported predicate promotions disappear separately from final reward;
- stop after the frozen tasks, regardless of outcome.

## Interpretation

The empirical contribution is not “we invented verification.” Existing work already covers structured task state, transition reflection and logical action checking. The narrower finding is that a visually successful transition can still carry the wrong proof type. In the current baseline, this happens across files, maps, recipes and notes, so it is not only an OsmAnd-specific anecdote. Whether a generic prompt can repair it remains untested.
