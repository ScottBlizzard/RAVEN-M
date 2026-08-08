# Source-document coverage: Markor development pilot preregistration

## Status and question

This file must be frozen before the first intervention generation call.  The pilot asks whether an explicit, auditable forward-browsing contract can repair the first currently measured edge: all eight official-baseline trajectories that opened a Markor document performed zero forward vertical scrolls, and the frozen screenshot extractor recovered only 11/21 expected identifiers.

This is a contaminated development mechanism pilot.  It is not held out, not a new-framework benchmark, and not evidence that a general memory method improves AndroidWorld.

## Frozen cohort and comparator

The intervention contains three exact previously observed task instances, one per Markor multi-record task class:

- `ExpenseAddMultipleFromMarkor`, seed 20260806;
- `RecipeAddMultipleRecipesFromMarkor`, seed 20260806;
- `RecipeAddMultipleRecipesFromMarkor2`, seed 20260807.

The comparator is the already frozen official Qwen baseline for the exact same task--seed instances.  It will not be regenerated.  Comparator source-object recovery is 3/8 identifiers in aggregate (37.5%), full recall 1/3 episodes, forward document scroll 0/3, and task success 0/3.

## Frozen intervention

Only the opt-in `SOURCE_DOCUMENT_COVERAGE_SUFFIX` is appended to the byte-identical official Qwen Mobile Agent system prompt.  It requires an Action-led ledger containing the last visible bottom anchor and exact accumulated identifiers, at least one forward vertical swipe, continued forward scanning until a repeated anchor/no-new-record condition, and exact identifier carry into the destination.  The screenshot policy, action schema, action adapter, history transport, native task budget, evaluator, model revision, and sampling stay unchanged.

Model: `Qwen/Qwen3-VL-32B-Instruct` at revision `0cfaf48183f594c314753d30a4c4974bc75f3ccb`.  Sampling: temperature 0.7, top-p 0.8, top-k 20, presence penalty 1.5, repetition penalty 1.0, generation seed 3407.  Maximum tokens 32,768 and native step limit 60.  Current screenshot only; hidden UI tree, task parameters, `row_objects`, evaluator, and reward are never exposed to the model.

## Frozen measurements

After all three online episodes finish, the same frozen screenshot-only object extractor is applied once to every unique Markor `DocumentActivity` screenshot.  Hidden `row_objects` are used only after generation for scoring.  Report:

1. forward vertical scroll count before leaving the source document;
2. number of unique document screenshots;
3. exact-output rate, micro precision, micro recall, and full-recall episodes;
4. destination reach, correct identifier text writes, evaluator reward, calls, tokens, and wall time.

## Qualification gate and stopping rule

The source-coverage pilot qualifies only if all conditions hold:

1. all 3/3 episodes open the Markor document and perform at least one forward vertical swipe before leaving or terminating;
2. the offline extractor returns valid JSON for every selected frame and micro precision remains 1.00;
3. aggregate identifier recall is at least 6/8 (75%), an absolute gain of at least 37.5 points over the frozen 3/8 comparator;
4. at least 2/3 episodes achieve full identifier recall;
5. no evaluator or hidden task state is used online.

Task success is secondary and is not required to qualify source capture.  If any gate fails, stop this prompt intervention: do not edit the prompt on these same three instances and call the rerun held out.  If all gates pass, it authorizes only a separately preregistered destination-write pilot on new instances; it does not authorize a method-superiority claim.

## Contamination and immutability boundary

The cohort and failure mechanism were selected after observing the official 57-cell baseline, so every result is development evidence.  Prior official runs, L4 runs, evidence-qualified runs, completion-verifier outputs, extractor outputs, and all frozen reports remain immutable.  No failed episode is retried for model error.  Infrastructure-invalid attempts must be preserved and excluded explicitly rather than silently replaced.

## Pre-call implementation lock

Local validation completed before any intervention generation call: all 43 tests under `05_project/tests/official_qwen_mobile` passed, both modified Python modules passed `py_compile`, and `git diff --check` passed for the pilot files.

- full source-coverage system prompt SHA-256: `ef6a2125c5b36e55bab5bfe2e06b30fc2987423d1b11a2c394e3e510a773ae85`
- `protocol.py` SHA-256: `e96fd394b20f21d389fd3859c2403138df51b40426603a75e2b89a14ec8b4da7`
- `run_official_qwen_mobile.py` SHA-256: `d9ea962b0d6c8aa4003451183692024e0e809236ae23cde2b05d542bad12f262`
- frozen three-instance manifest SHA-256: `170510c468ead303bb588f776b7808efbcfa0c9b7378215277383c83f40f5a37`
