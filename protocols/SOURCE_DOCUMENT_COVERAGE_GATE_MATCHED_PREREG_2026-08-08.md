# Executable source-document coverage gate: matched source-stage preregistration

## Scientific question and claim boundary

The prompt-only coverage pilot failed because the first episode left Markor without a forward scroll.  This preregistration asks a narrower causal question: on the same new task instances, does an executable controller gate increase the amount of task-relevant source information recoverable from screenshots before the Agent leaves the document?

The result is a development mechanism experiment.  The Markor task classes and the zero-scroll failure were observed previously, so seed 20260809 is a new task instance but not a pristine held-out research test.  The experiment does not run tasks to completion, does not rank frameworks, and cannot establish final AndroidWorld efficacy.

## Frozen matched design

Three task classes are instantiated independently with seed 20260809:

- `ExpenseAddMultipleFromMarkor`;
- `RecipeAddMultipleRecipesFromMarkor`;
- `RecipeAddMultipleRecipesFromMarkor2`.

The exact three-instance manifest is shared by both conditions.  A pre-call repository scan found no prior Markor Hard artifact using seed 20260809; the same seed exists only in unrelated non-Hard S1b smoke manifests.  Both conditions stop at the first transition out of Markor `DocumentActivity`, skip the native task evaluator, and therefore measure source-stage behavior only.

Conditions:

1. **Baseline:** byte-identical official Qwen Mobile Agent prompt and controller, no coverage gate.
2. **Coverage gate:** the frozen source-document coverage prompt plus `SourceDocumentCoverageGate`.  While a Markor document is open and its bottom is not attested, any proposed non-forward-scan action, Home, Back, answer, or terminate is replaced by the fixed normalized swipe `(0.50,0.82)->(0.50,0.24)`.  A forward swipe closes coverage only when pixel change is below 0.001, activity is unchanged, and UI-tree hash is unchanged.  The next model action is then allowed.

The run order is fixed as baseline followed by coverage gate.  This is an acknowledged order confound, but model revision, sampling, task parameters, screenshot policy, action adapter, native 60-step cap, device image, and source-stage stopping condition are matched.

## Frozen model and accounting

- model: `Qwen/Qwen3-VL-32B-Instruct`;
- revision: `0cfaf48183f594c314753d30a4c4974bc75f3ccb`;
- temperature 0.7, top-p 0.8, top-k 20, presence penalty 1.5, repetition penalty 1.0;
- generation seed 3407, max tokens 32,768, request timeout 180 seconds;
- current screenshot only; UI tree, foreground activity, task parameters, reward, and evaluator are hidden from the model;
- report model calls, prompt/output tokens, forward scans, overrides, unique document frames, and wall time for each condition.

## Frozen source-object scoring

After both source-stage suites are complete, a mechanical builder selects every unique `before` screenshot observed in Markor `DocumentActivity`.  The already frozen screenshot-only extractor is called exactly once per selected frame.  It receives only the task text, current screenshot, and fixed task-class extraction rule.  `row_objects` remain hidden until scoring.  Episodes that never open the document remain in the denominator with zero predictions and full false-negative count.

Primary measurements are micro precision, micro recall, full-recall episodes, and absolute recall gain.  This favors neither arm by matching the number of extractor calls: the gate is allowed to spend more calls because producing additional observed frames is the mechanism under test; all added cost is reported explicitly.

## Qualification and stopping rules

The executable coverage gate qualifies only if every condition holds:

1. coverage-gate condition opens the Markor document in 3/3 episodes;
2. coverage-gate condition executes at least one forward vertical scroll in 3/3 episodes;
3. bottom-of-document attestation is reached in 3/3 episodes;
4. every gate-condition extractor output is valid JSON;
5. gate-condition micro precision is exactly 1.00;
6. gate-condition micro recall is at least 0.75;
7. gate-condition recall exceeds matched baseline by at least 0.20 absolute;
8. at least 2/3 gate episodes achieve full identifier recall.

If the first gate episode reveals an implementation-contract failure (for example, the controller logs an attempted prohibited exit without overriding it), terminate the gate suite immediately and preserve it as controller-invalid.  Ordinary model behavior is not retried.  If the final qualification fails, do not tune coordinates, thresholds, prompt text, or extractor on these six cells.  Passing authorizes only a separately preregistered destination-write experiment; it is not a task-success or method-superiority result.

## Frozen implementation lock before generation

All 48 official-mobile tests passed; modified modules passed `py_compile`; `git diff --check` passed.  No baseline or gate generation call for this matched pilot had been made when these hashes were recorded.

- source-coverage system prompt SHA-256: `ef6a2125c5b36e55bab5bfe2e06b30fc2987423d1b11a2c394e3e510a773ae85`
- external gate module SHA-256: `a9785349431c9fba80d76f127d2742aab66ed2b8b8da5b7df83484b954812f97`
- controller SHA-256: `7782db9c09bf99a03594dfd713d0d80f2aed036082c654a8238011c7f48a3b8b`
- online runner SHA-256: `d0391f0e6b516494659b497188b60ee0371b4513893805c508eb44c3e7c89b91`
- extractor runner SHA-256: `fdabda371fa8fc331a9e2aa83b6386ce644ad09d184bcff877a4c5a528522bfd`
- source-frame builder SHA-256: `41602ccc105a58614aae3f684c711ac958d999138e3e7b446904bbeaf1b706f3`
- comparative analyzer SHA-256: `d12a9d4d411677419aef6c0c6089229a583e01fabbd37c9f04df6befebb597a0`
- matched instance manifest SHA-256: `3ebc1376247d73670d1a11c7e5bae6cf79cf13bec43ea8333e8b767f82e15b78`

