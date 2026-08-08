# Evidence-qualified progress matched diagnostic

Date: 2026-08-08  
Status: complete; frozen prompt line stopped  
Claim class: development-contaminated, same-instance causal diagnostic; not held-out efficacy

## Bottom line

The intervention failed both preregistered qualification gates. All three tasks remained at reward 0. The prompt did not prevent unsupported progress promotion on the recipe task, produced no reward improvement, and one confirmation episode ended with an official-protocol error. The line must not be expanded or tuned and relabeled as confirmation.

This is nevertheless a useful causal result: a natural-language instruction to verify the exact object role is not enough when the dominant upstream failures are app-icon grounding, repeated ineffective navigation, menu/control grounding, and protocol compliance. Typed evidence is a real diagnostic distinction, but it is not yet an effective controller mechanism.

## Frozen setup

- suite: `official_qwen_20260808T174900_cd353e24`
- manifest: `androidworld_hard_v2_evidence_qualified_progress_matched_diagnostic.final.json`
- model: `Qwen/Qwen3-VL-32B-Instruct`
- revision: `0cfaf48183f594c314753d30a4c4974bc75f3ccb`
- runtime: stock vLLM, BF16, one RTX PRO 6000 96GB
- generation seed: 3407
- temperature/top-p/top-k: 0.7/0.8/20
- observation: current screenshot only
- history: official text action summaries only
- task budgets and evaluators: unchanged
- diagnostic prompt SHA-256: `970af7af61d5c0e79e97c3a3be0d2fde04c401f29b1b3a4c3c7c6213fd7ae81f`
- held-out eligibility: false

The prompt, manifest, judgments, contamination boundary, stop rule, implementation hashes and 26 passing tests were frozen before the first generation call in `05_project/docs/EVIDENCE_QUALIFIED_PROGRESS_MATCHED_DIAGNOSTIC_PREREG_2026-08-08.md`.

## Matched results

| Task / seed | Arm | Reward | Calls | Executed actions | Elapsed (s) | Termination | False success |
|---|---:|---:|---:|---:|---:|---|---:|
| RecipeDeleteMultipleRecipesWithConstraint / 20260806 | official baseline | 0 | 15 | 14 | 281.1 | model success | yes |
| RecipeDeleteMultipleRecipesWithConstraint / 20260806 | evidence-qualified | 0 | 25 | 24 | 765.2 | model success | yes |
| SaveCopyOfReceiptTaskEval / 20260806 | official baseline | 0 | 10 | 9 | 187.4 | model success | yes |
| SaveCopyOfReceiptTaskEval / 20260806 | evidence-qualified | 0 | 16 | 16 | 482.4 | native max steps | no |
| OsmAndMarker / 20260806 | official baseline | 0 | 11 | 10 | 250.2 | model success | yes |
| OsmAndMarker / 20260806 | evidence-qualified | 0 | 8 | 7 | 306.7 | official output invalid | no |
| **Total** | **official baseline** | **0/3** | **36** | **33** | **718.7** | 3 false-success endings | **3** |
| **Total** | **evidence-qualified** | **0/3** | **49** | **47** | **1554.3** | 1 false success, 1 max-steps, 1 protocol invalid | **1** |

The intervention used 13 more model calls, 14 more Android actions and 835.6 more seconds without improving any evaluator reward. It reduced false-success terminations only by replacing two of them with other failures; this is not task improvement.

## Task-level causal audit

### 1. Recipe deletion: target mechanism reached and failed

The official baseline navigated efficiently but, after deleting two matching recipes, opened the remaining matching recipe and then treated a click within its detail page as deletion before terminating success. The post-action screen still showed the matching recipe.

The intervention initially opened Chrome instead of Broccoli, recovered, later found the correct app and searched for `zucchini`. Near the end it opened Android's share sheet rather than a delete confirmation. The visible sheet offered `Copy`, `Nearby`, OsmAnd, Tasks, VLC and Markor. Despite this contradictory object and operation type, the next call claimed that the recipe had been deleted and terminated success. Reward was 0.

Earliest relevant failures:

- step 1: L1 perception/grounding, Chrome icon mistaken for Broccoli;
- repeated desktop/app-drawer and detail/list cycles: L4 control progress/stagnation;
- step 23: L1/L2 menu grounding, share operation mistaken for delete;
- step 24: L4/L5 unsupported progress promotion and false success.

Mechanism judgment: **fail**. The exact failure targeted by the intervention still occurred, with stronger visible counterevidence than in the baseline.

### 2. Receipt copy: target mechanism not reached

The official baseline entered Simple Gallery Pro, reached the receipt, invoked copy, and saw a generic `File copied successfully` toast. It promoted that weak evidence to the stronger claim that the copy existed in the required `Download` destination, but the hidden evaluator returned 0.

The intervention first opened Maps instead of the gallery, recognized the mismatch and returned home. It then spent the remaining budget repeatedly swiping within the application drawer and never re-entered Simple Gallery Pro. It reached the native 16-step limit with reward 0.

Earliest relevant failures:

- step 1: L1 perception/grounding, Maps mistaken for Simple Gallery Pro;
- steps 7--15: L4 control progress/stagnation, repeated app-drawer swipes;
- required destination-binding event: not reached.

Mechanism judgment: **not qualified / fail for the preregistered gate**. Avoiding a false-success claim by failing earlier is not evidence that exact destination binding improved.

### 3. OsmAnd marker: target mechanism not reached and protocol regressed

The official baseline searched the coordinates, long-pressed the map, created and named an item, and saved it. The resulting screen explicitly categorized the object under `Favorites` and still offered a separate `Marker` action. The model nevertheless promoted `Favorite saved` to `location marker created` and terminated success; reward was 0.

The intervention opened Retro Music instead of OsmAnd, later recognized the wrong app and returned home. It then emitted `system_button: Recent`, whereas the frozen official schema accepts `Back`, `Home`, `Menu`, or `Enter`. The parser correctly failed closed before action execution, and the evaluator returned 0.

Earliest relevant failures:

- step 2: L1 perception/grounding, Retro Music mistaken for OsmAnd;
- step 7: L2 protocol compliance, invalid button enum `Recent`;
- required favorite-versus-marker distinction: not reached.

Mechanism judgment: **fail**. The preregistration explicitly required no new protocol/execution/infrastructure error.

## Qualification decision

### Mechanism gate

Required: no unsupported progress promotion before the corresponding baseline mismatch in at least 2/3 tasks, with no new protocol, execution or infrastructure error.

Result: **failed**.

- Recipe: unsupported promotion persisted.
- Receipt copy: target mechanism was never reached.
- OsmAnd: target mechanism was never reached and an official-protocol error occurred.

### Task gate

Required: reward improvement on at least 1/3 tasks without a new earlier false-success termination.

Result: **failed (0/3 reward improvements)**.

### Frozen decision

Do not expand, tune or implement a destination-first binding gate under this prompt line. Any later variant is a new exploratory experiment and cannot inherit the confirmation label.

## What the negative result changes

The retrospective idea remains conceptually correct: a transition proves only the predicate that is visibly supported. But this run shows that asking the same model to enforce that distinction in prose is too weak. The instruction competes with earlier failures and with the model's own self-authored history.

The next defensible direction is therefore not a longer prompt. It is to separate capabilities and measure them:

1. **App/control grounding:** can the model select the correct application and control from the current screenshot?
2. **Transition detection:** did the action cause any observable change?
3. **Typed postcondition binding:** what exact object, container, field and operation did the new screen verify?
4. **Task-state update:** which required slots, if any, may be marked complete?
5. **External completion:** does the AndroidWorld evaluator confirm the final state?

The present diagnostic isolates why a single semantic rule cannot replace those layers. It also explains why future work should compare component interventions on the same frozen episodes instead of adding more unverified controller prose.

## Artifacts

- preregistration: `05_project/docs/EVIDENCE_QUALIFIED_PROGRESS_MATCHED_DIAGNOSTIC_PREREG_2026-08-08.md`
- closest-prior audit: `05_project/docs/OBJECT_ROLE_EVIDENCE_CLOSEST_PRIOR_AUDIT_2026-08-08.md`
- retrospective prevalence audit: `reports/object_role_evidence_prevalence_audit_2026-08-08.md`
- frozen manifest: `05_project/configs/task_manifests/androidworld_hard_v2_evidence_qualified_progress_matched_diagnostic.final.json`
- intervention suite: `runs/official_qwen_mobile/official_qwen_20260808T174900_cd353e24`
- matched official baseline suite: `runs/official_qwen_mobile/official_qwen_20260808T012646_c8281b8f`
