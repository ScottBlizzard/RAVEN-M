# Visible Object Extractor on Observed Markor Frames — Frozen Preregistration

Date frozen: 2026-08-08, before any extractor generation call.

## Question

In the frozen official Qwen3-VL-32B Hard trajectories, the Agent often failed to type the expected objects into the destination app. For the subset that actually opened the specified Markor document, can the same base model recover the task-relevant object identifiers when it is used only as a strict screenshot extractor?

This is an offline development diagnostic. It is not held-out efficacy evidence, does not modify an Android state, and does not establish a novel method.

## Frozen cohort

- Source: `reports/official_qwen32b_full_hard_combined_corrected_final.json`.
- Included task classes: `ExpenseAddMultipleFromMarkor`, `RecipeAddMultipleRecipesFromMarkor`, and `RecipeAddMultipleRecipesFromMarkor2`.
- Eligibility: the trajectory contains at least one `before` screenshot whose foreground activity is exactly `net.gsantner.markor/net.gsantner.markor.activity.DocumentActivity`.
- Frame rule: include every unique screenshot hash observed under that activity. Do not select frames using ground truth.
- Frozen size: 8 episodes, 13 unique frames, 21 expected object identifiers.
- Hidden AndroidWorld `row_objects` are retained only for scoring. They are not included in the system prompt, user prompt, image, or model history.
- Manifest: `05_project/configs/visible_object_extractor/markor_observed_frames_v1.final.json`.
- Manifest SHA-256: `7D0B4A75C6956AE32C33CDF80B364BFF8197391348C6EC192B83BD517E0B7F07`.

The two `RecipeAddMultipleRecipesFromImage` episodes that never opened Gallery and the Gallery episodes that never entered a photo viewer are not eligible. This prevents the extractor from being scored on source content that the original Agent never observed.

## Frozen model and calls

- Model: `Qwen/Qwen3-VL-32B-Instruct`.
- Exact revision: `0cfaf48183f594c314753d30a4c4974bc75f3ccb`.
- Runtime: stock vLLM OpenAI endpoint, BF16, one RTX PRO 6000.
- Sampling: temperature 0.7, top-p 0.8, top-k 20, presence penalty 1.5, repetition penalty 1.0, seed 3407.
- Maximum completion length: 512 tokens.
- One logical call per frozen frame; 13 total calls. No self-repair, majority vote, or post-result retry.
- A transport retry inside the frozen client is allowed only for connection/timeout failure and is recorded. If the full run cannot complete, it is infrastructure-invalid rather than partially scored.

System prompt SHA-256: `e9b31d2f418e1c46f0582aa69ecdc803f874e5b4659c58dd09d741afd88dd08e`.

The prompt permits only exact screenshot-visible identifiers. Expense identifiers require the same visible record to state `Reimbursable`; the filtered recipe task requires the task-specified preparation time to be visible for the same record. Outputs must use exactly:

```json
{"objects":[{"identifier":"exact visible object name or title"}]}
```

## Frozen scoring

Predictions are unioned across an episode's frozen frames after Unicode NFKC normalization, case folding, and punctuation-insensitive token normalization. Matching is episode-local, so an identifier from another seed is a false positive.

Primary metrics:

1. exact-schema valid outputs out of 13;
2. micro precision over the unioned identifiers;
3. micro recall over the 21 hidden expected identifiers;
4. number of episodes with full expected-identifier recall out of 8.

The diagnostic passes only if all four gates pass:

- exact-schema output: 13/13;
- micro precision: at least 0.80;
- micro recall: at least 0.60;
- full-recall episodes: at least 4/8.

These thresholds were fixed before generation. A pass authorizes only a new, separately preregistered small online test of structured source capture. It does not authorize a full Hard expansion or a claim that memory improves task success. A failure stops this extractor prompt unchanged and is interpreted by error type: false positives indicate unsupported source inference; false negatives can arise from visual extraction limits or inadequate source-page exploration.

## Frozen implementation and tests

- Extractor and parser SHA-256: `07CDF9423FAB158ACE454773040C6F4A8227242EC10D89252870A09C5CB64019`.
- Manifest builder SHA-256: `797E3631EED013B723A44F904201EBDACB9BF5803715880D35CF6B3F2C46CD87`.
- Runner SHA-256: `05CA1C3DED2642EAD6521E840DEE94EFAC06759B4339E9E6F332440D502FB33B`.
- Before generation, the complete `05_project/tests/official_qwen_mobile` suite passed 42/42 tests.

No prompt, parser, cohort, normalization, threshold, or scoring rule may be changed after the first generation call. Any revised extractor must receive a new version and cannot reuse this run as held-out evidence.
