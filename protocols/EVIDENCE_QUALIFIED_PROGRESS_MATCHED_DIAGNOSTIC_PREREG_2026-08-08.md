# Evidence-qualified progress: matched diagnostic preregistration

Freeze date: 2026-08-08  
Status: frozen before any generation call for this diagnostic  
Claim class: development-contaminated, same-instance causal diagnostic; not held-out efficacy

## 1. Motivation and prior-work boundary

The complete official Qwen baseline contains 7/57 successes. The L4 transition-attested intervention failed: it could reject semantic claims after an observably unchanged action, but it could not reject a wrong action that caused a genuine page transition.

A zero-generation retrospective audit identified 13 clean object-role evidence mismatches across 5 task classes and 4 application families. In each, a real transition proved one predicate while the agent promoted it to a stronger, differently typed task predicate.

Generic structured task state, progress tracking and transition verification are already covered by TSR; action-effect expectation and recovery are covered by VeriGUI and StepReflect; pre-action logical intent checking is covered by VeriSafe Agent. This experiment therefore does not claim a new framework. It tests only whether a generic evidence-typing instruction changes the earliest failure on frozen Qwen cases.

## 2. Single intervention

Append the following exact text to the official Qwen Mobile Agent system prompt, separated by two newlines:

> Evidence-qualified progress rule: Treat every action as ATTEMPTED until the current screenshot directly verifies the exact task predicate. A real screen transition is insufficient if the object type, parent hierarchy, field, container, or operation differs from the requirement. Before acting, state the intended object role and exact postcondition. After acting, compare visible evidence against those exact slots. Never promote a related weaker fact to completed progress. If exact proof is absent, keep the subgoal pending and inspect the current page or recover. Apply the same standard before terminate(success).

No task name, answer, target value, button location, hidden UI tree, database state or evaluator result is included. The official tool schema, parser, text action history, current-screenshot-only input and Android execution remain unchanged. L4 transition attestation is disabled so that only this prompt intervention differs from the frozen official baseline.

## 3. Frozen tasks and order

Manifest: `androidworld_hard_v2_evidence_qualified_progress_matched_diagnostic.final.json`

1. Pilot: `RecipeDeleteMultipleRecipesWithConstraint/20260806`, native budget 40.
2. Confirmation A: `SaveCopyOfReceiptTaskEval/20260806`, native budget 16.
3. Confirmation B: `OsmAndMarker/20260806`, native budget 20.

All three baseline instances were previously inspected. The order is frozen and none can be described as pristine held-out. The prompt and implementation may not be changed after the pilot while retaining the confirmation label.

## 4. Matched runtime

- model: `Qwen/Qwen3-VL-32B-Instruct`
- revision: `0cfaf48183f594c314753d30a4c4974bc75f3ccb`
- runtime: stock vLLM, BF16, one RTX PRO 6000 96GB
- generation seed: 3407
- temperature: 0.7
- top_p: 0.8
- top_k: 20
- presence penalty: 1.5
- repetition penalty: 1.0
- max generation tokens: 32768
- request timeout: 120 seconds
- screenshots: current frame only
- task initialization, native action budget and evaluator: unchanged
- transport recovery: same-idempotency-key response recovery only; no Android action replay

## 5. Frozen judgments

For each task report reward, model calls, Android actions, elapsed time, termination reason, false-success status and earliest task-related failure.

The manual mechanism label is `unsupported_progress_promotion` when a step meets all of:

1. a genuine visible transition/result exists;
2. that evidence proves a weaker or differently typed predicate;
3. the model writes or uses the stronger task predicate as completed;
4. the promotion is upstream of failure or premature termination.

Mechanism qualification requires both:

- no unsupported progress promotion before the baseline's corresponding earliest mismatch in at least 2/3 tasks;
- no new protocol, execution or infrastructure error.

Task qualification requires reward improvement on at least 1/3 tasks without a new earlier false-success termination. Expansion beyond these three tasks is allowed only if both mechanism and task qualification pass. Otherwise record a negative or mixed diagnostic and stop this prompt line.

## 6. Stop and contamination rules

- No prompt tuning after the pilot.
- No selective rerun for reward.
- Infrastructure-invalid episodes may be replaced once with the exact frozen implementation; old artifacts remain.
- No merging of these results into the 57-key baseline denominator.
- No method or novelty claim from success on these development-contaminated cases.
- Stop after all three valid task outcomes or on a reproducible controller defect.

## 7. Pre-implementation hashes

- `controller.py`: `e198fed3ff44dc25c11ddedbf3734dca90e4cf97bf08f7afc2e9abf898ee0245`
- `protocol.py`: `88a6a7c17f2d3e1d54c5318b6ac14cdf1f88ad1086317032fc7fedcb3391bd93`
- `run_official_qwen_mobile.py`: `bd92fe26087b3ad4f5a8a1ff69ec7d6d6bc208226303ac87f1fa298618faa48b`
- `run_official_qwen_h01.ps1`: `ff42d8c86e92a078cfb2d3a0f1555fcb3cb7adee43f43fed261b9e39af38dd58`
- backend config: `b8204fbf1288666854eb508663e1792223f50c4824178c33fe827e153a36294c`

Implementation hashes and tests must be appended before generation begins.

## 8. Frozen implementation record (before generation)

- preregistration SHA-256 before this implementation record was appended: `79cedfb52f33b07fc7245342517013a126b3225698d4809142d3afe472ba605f`
- manifest SHA-256: `45e319f6c744501f39484aefa8ac54a4b7a8e84a4882ea139dd76c8607c8d66d`
- full diagnostic system prompt SHA-256: `970af7af61d5c0e79e97c3a3be0d2fde04c401f29b1b3a4c3c7c6213fd7ae81f`
- `controller.py`: `e198fed3ff44dc25c11ddedbf3734dca90e4cf97bf08f7afc2e9abf898ee0245`
- `protocol.py`: `e9951b757ae577e66e2031675d5159dc3894c419b2fb9ba78094eec0584c482d`
- `run_official_qwen_mobile.py`: `8392e142ba672468aca5c09cfc707d2b4ab9d65c44ca12445081424e06f618c2`
- `run_official_qwen_h01.ps1`: `ea1b5727f10690ea25ada140a9c82a328a758bb59f20d8e942696d482bcf590a`
- `vllm_client.py`: `b3c613db89cf690ed4c8b56158d7d341fb948c4ce553d4ef269d7fb854f5c3d2`
- test command: `python -m pytest 05_project/tests/official_qwen_mobile -q`
- test result: `26 passed` on 2026-08-08 before the first diagnostic generation call.
- PowerShell launcher parsed successfully as a script block before generation.

The implementation adds only an opt-in prompt-selection flag and metadata. It leaves the official system prompt, parser, controller, action executor, observation stream and task evaluator unchanged. The three diagnostic modes are mutually exclusive.
