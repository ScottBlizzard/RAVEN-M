# PF01 MobileUse × Qwen3-VL-32B scored post-hoc

## 1. Bottom line

The frozen first-seed MobileUse arm produced a **descriptively positive but scientifically incomplete** result.

- Frozen official Qwen baseline: **4/19 full successes**, one partial reward, total reward **4.5**, all 19 tasks valid.
- MobileUse: **5 full successes**, two partial rewards, total reward **6.0**, but only **18 tasks were scientifically valid**; H12 crashed inside the public framework.
- Full-success count therefore moved from 4 to 5, and reward moved from 4.5 to 6.0, but the preregistered label `TASK-QUALIFIED BROAD UPGRADE` is **not awarded**, because its first condition requires all 19 tasks to be scientifically valid.
- The correct primary notation is **5 full successes / 18 valid tasks + 1 invalid task**, not `5/18` as if H12 had never existed and not a clean `5/19` as if H12 had received a valid zero.

If the invalid H12 is retained in the requested 19-task denominator only as a descriptive denominator, the observed full-success count is 5/19 (26.32%) and the observed reward is 6.0/19. These figures are not a qualified benchmark result.

## 2. Frozen boundary and recovery boundary

The behavioral arm was frozen before scored execution:

- arm: `PF01_MOBILEUSE_HR_QWEN3VL32B_AW_HARD_S20260806_V1`;
- model: `Qwen/Qwen3-VL-32B-Instruct`;
- model revision: `0cfaf48183f594c314753d30a4c4974bc75f3ccb`;
- runtime: vLLM multi-image, BF16, one RTX PRO 6000;
- sampling: temperature 0.7, top-p 0.8, top-k 20, presence penalty 1.5, repetition penalty 1.0, seed 3407;
- AndroidWorld task seed: 20260806;
- task order, native budgets, evaluator, role order, prompts, action boundary and stop rules were frozen.

The original suite stopped after H12 because an invalid `long_press` proposal exhausted parser retries, leaving a `None` action. Upstream `TrajectoryReflector` then dereferenced `step.action.name` and raised `AttributeError: 'NoneType' object has no attribute 'name'`.

No old result was overwritten. A separate recovery suite resumed only the remaining task IDs. The only recovery change was a harness boundary that caught a task-level runtime error and allowed the next task to start. It made no controller, prompt, action, sampling, task, evaluator or model change. Frozen file hashes remained identical to the post-smoke freeze record.

## 3. Task-level results

| ID | Task | Reward | Valid | Actions | Decisions | Main observed mechanism |
|---|---|---:|:---:|---:|---:|---|
| H01 | BrowserMultiply | 0 | yes | 16 | 17 | The model read individual numbers, then rewrote the sequence during summary and submitted the wrong product. |
| H02 | ExpenseAddMultipleFromGallery | 0 | yes | 20 | 60 | It bound the task to the wrong/uncertain source image, failed to structure all expense fields, then repeatedly typed without focusing the Amount field. |
| H03 | ExpenseAddMultipleFromMarkor | 0 | yes | 27 | 29 | Wrong/stale source content was carried into the wrong destination state; the controller declared completion without evaluator support. |
| H04 | ExpenseDeleteMultiple2 | 0 | yes | 12 | 13 | Two targets were handled, but `Bike Repairs` was not found; the model converted missing evidence into “may already be deleted” and terminated successfully. |
| H05 | MarkorCreateNoteAndSms | 0.5 | yes | 17 | 18 | The note/content subgoal was completed, but the prepared SMS was not actually sent. |
| H06 | MarkorMergeNotes | 0 | yes | 77 | 78 | Clipboard/layout ambiguity caused a correct remembered operation to bind to the wrong current object; the long recovery loop did not restore exact note identity/order. |
| H07 | MarkorTranscribeVideo | 0 | yes | 20 | 20 | It observed one frame (`KWHC6JSTt2`), switched to Markor, and exhausted the budget creating the file without collecting the complete ordered frame sequence. |
| H08 | OsmAndMarker | 1 | yes | 7 | 8 | Coordinate search produced a direct result and a visible Marker action; the short single-app chain closed correctly. |
| H09 | OsmAndTrack | 0 | yes | 22 | 23 | It searched the three named places, but later clicked approximate map positions instead of binding the exact search-result objects as ordered waypoints. |
| H10 | RecipeAddMultipleRecipesFromImage | 0 | yes | 26 | 60 | The image was treated like selectable text, a generic recipe was hallucinated, and the same long text was repeatedly typed without correct field focus. |
| H11 | RecipeAddMultipleRecipesFromMarkor | 0 | yes | 41 | 43 | Copy/source acquisition failed, stale clipboard content propagated, and progress text hallucinated correct recipe creation. |
| H12 | RecipeAddMultipleRecipesFromMarkor2 | — | **no** | — | — | Public-framework crash after prohibited-action parse failure; excluded from task reward and preserved as implementation-invalid. |
| H13 | RecipeDeleteMultipleRecipesWithConstraint | 1 | yes | 16 | 17 | App search created a reliable candidate set, deletions were executed against visible objects, and `No recipes found` provided a strong closure signal. |
| H14 | RetroSavePlaylist | 0.5 | yes | 49 | 50 | Playlist creation/export partially succeeded, but song-card taps were mistaken for per-song option menus; Progressor recorded songs as added although screenshots showed playback only. |
| H15 | SaveCopyOfReceiptTaskEval | 0 | yes | 8 | 9 | The file was copied to `Internal/DCIM/Download` rather than the required root `Internal/Download`; a success toast verified an operation, not the required destination. |
| H16 | SimpleCalendarAddOneEvent | 1 | yes | 19 | 20 | It initially landed on October 24, used visible date feedback to correct to October 26, and then filled title, exact description, 08:00–09:00 and saved. |
| H17 | SportsTrackerActivitiesOnDate | 0 | yes | 5 | 6 | It browsed records and answered `hiking, running`, but did not establish that the returned set exactly matched October 2. |
| H18 | SportsTrackerTotalDistanceForCategoryOverInterval | 1 | yes | 5 | 6 | A failed app-launch click was detected immediately, retried, and the directly visible interval/category aggregate was read correctly as 3990. |
| H19 | SportsTrackerTotalDurationForCategoryThisWeek | 1 | yes | 3 | 4 | The directly visible weekly/category aggregate was read correctly as 80. |

Totals over the 18 valid tasks: **390 native actions**, **481 operator decisions**, **6.58 hours** of summed episode elapsed time, five full successes, two partial rewards and total reward 6.0. Including the invalid H12 trace, the two suites contain 509 Operator requests and **1,520 total model requests** across all roles.

## 4. Paired change against the official first-seed baseline

The official baseline full successes were H04, H14, H16 and H19. MobileUse full successes were H08, H13, H16, H18 and H19.

| Change type | Tasks | Interpretation |
|---|---|---|
| New full successes | H08, H13, H18 | MobileUse helped when the UI exposed a direct candidate/result set and visible local correction was possible. |
| Retained full successes | H16, H19 | Calendar correction and direct aggregate reading remained reliable. |
| Full-success regression | H04 | Reflection did not prevent unsupported completion after one deletion target was missing. |
| Full-to-partial regression | H14 | The framework created/exported a playlist but failed exact ordered song membership. |
| Retained partial | H05 | Both arms completed the note-side work but failed the final SMS-send closure. |
| Invalid instead of valid zero | H12 | The MobileUse public framework crashed; this cannot be counted as an ordinary task result. |

The net descriptive movement is **+1 full success** and **+1.5 reward**, but it is not broad qualification because H12 is invalid.

## 5. Mechanism findings

### 5.1 It reached destinations more often, but did not transfer payloads more correctly

On the eight cross-app tasks that are valid in both arms, the official baseline reached the destination app after the source in 4/8 cases. MobileUse did so in 6/8 cases. However:

- full cross-app task success remained 0;
- H05 remained the only positive cross-app reward, still 0.5;
- H02, H03, H07, H10, H11 and H15 show that reaching the destination is much weaker than binding the exact source object, retaining the full payload, selecting the correct destination entity/field and verifying the final state.

This is the clearest interpretation of the framework: **navigation/handoff reach improved, semantic handoff did not**.

### 5.2 Reflection is strongest on immediate local errors

H16 corrected October 24 to October 26, and H18 retried an app icon after observing no page change. These errors were visible immediately after one action.

By contrast, H14 discovered much later that its playlist state was wrong and could only move between adjacent screens. H06 and H11 could not recover an earlier wrong source/clipboard binding. Reflection therefore helped with local action correction but did not reliably perform long-horizon causal backtracking.

### 5.3 Natural-language progress is not a trustworthy memory store

H01 is the cleanest example. Intermediate Operator responses reported numbers including 8, 10, 7 and 2. At final aggregation the same controller claimed the sequence was 3, 7, 2, 9 and 4 and submitted 1512. The arithmetic step was internally consistent with the rewritten sequence; the failure was historical observation binding.

H14 shows the related completion problem: tapping a song card started playback, yet Progressor wrote that the song had been added to the playlist. Once this false fact entered progress, later reasoning treated it as history.

### 5.4 Operation success is weaker than task-predicate success

H15 received a visible copy-success outcome, but the destination directory was wrong. H04 deleted some targets, but one required target remained unverified. H05 composed an SMS, but did not send it. These cases support a strict distinction:

1. an action executed;
2. the page changed;
3. the intended local operation succeeded;
4. the exact task predicate is satisfied.

The framework frequently promoted levels 1–3 into level 4 without sufficient evidence.

### 5.5 Exact binding, not generic planning, is the central bottleneck

The recurrent failures are not explained by “the model forgot the whole plan.” The model often knew the correct abstract next step:

- use a song's options menu;
- bind three searched locations as ordered waypoints;
- copy a receipt to Download;
- collect all video-frame strings;
- enter the expense amount in the Amount field.

The breakdown occurred when the abstract step had to bind to an exact current object, field, container, source version or destination. This is a more specific and testable target than adding another generic planner or longer free-form memory.

## 6. Completion integrity and audit

The official first-seed baseline contained eight false-success claims. MobileUse contained seven valid false-success claims: H01, H03, H04, H09, H11, H15 and H17. This is a small non-regression/improvement, but not enough to compensate for H12 invalidity.

The recovery suite passed the standard hash-chain/schema audit with no errors:

- 9 episodes, all valid;
- L0: 987 events;
- L1: 454;
- L2: 600;
- L3: 327;
- L4: 163;
- L5: 25;
- role calls: Operator 154, Reflector 146, Progressor 146, TrajectoryReflector 27, GlobalReflector 8, AnswerAgent 8.

The original crashed suite lacked a final aggregate because execution stopped at H12. A read-only episode audit validated all ten event hash chains with no log errors, yielding nine valid tasks, one invalid task, one full success, reward 1.5 and four false-success claims. No synthetic aggregate was written into the frozen original directory.

## 7. Scientific judgment

This result is **not** evidence that MobileUse is generally better than the official Qwen baseline. It is one frozen seed, one benchmark slice and one invalid task. It also consumed substantially more inference: 481 valid operator decisions versus 329 in the official first-seed baseline, plus separate reflection/progress calls.

It is nevertheless useful positive evidence in a narrower sense:

- public multi-role reflection can recover some immediate UI errors;
- direct candidate/result-set tasks gained three full successes;
- destination reach improved on shared cross-app tasks;
- the layered logs identify why those gains did not extend to payload-heavy long tasks.

The most important negative evidence is equally concrete:

- free-form progress can overwrite correct observations;
- reflection does not reliably rewind to the earliest wrong binding;
- visual action grounding can be wrong while textual intent is right;
- local success signals are repeatedly mistaken for complete task proof;
- the upstream public framework is not robust to a parser-invalid action.

The appropriate label is therefore:

```text
DESCRIPTIVE TASK IMPROVEMENT, NOT PREREGISTERED QUALIFICATION
5 full successes / 18 valid tasks + 1 implementation-invalid task
```

## 8. Next legal step

Do not tune prompts on failed scored episodes and call the same tasks held-out. The next step should be separated explicitly:

1. preserve PF01 exactly as reported here;
2. preregister a generic mechanical repair for the `None`-action crash and decide in advance whether H12 is a repair-only completion or whether the entire corrected arm must be rerun;
3. use the PF01 trajectories only as development evidence to define the next intervention;
4. target exact object/field/container binding and structured observation retention, not another generic free-form planner;
5. evaluate the next arm on a declared comparison set with the same Qwen revision, evaluator and task budgets;
6. report full reward, false success, source coverage, exact object retention, destination-entity reach and complete payload transfer together.

Raw local suites:

- original: `runs/public_framework/mobileuse/pf01_scored_20260809T112613_044b0afa`;
- recovery: `runs/public_framework/mobileuse/pf01_scored_recovery_20260809T155503_aa8b36ab`.

