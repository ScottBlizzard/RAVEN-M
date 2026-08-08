# Screenshot-only completion verifier diagnostic: preregistration

Freeze date: 2026-08-08  
Status: frozen before any verifier generation call  
Claim class: development-contaminated offline layer diagnostic; not held-out task efficacy and not a novelty claim

## 1. Question

The official 57-key Qwen baseline produced 27 explicit success claims: six were confirmed by the native AndroidWorld evaluator and 21 were false-success claims. The preceding L4 and evidence-qualified prompt interventions did not improve task reward.

This diagnostic asks a narrower question: when Qwen is removed from action selection and corrupt self-authored history, can the same model use only the task and the screenshot immediately before the success claim to distinguish evaluator-confirmed completion from false completion?

The experiment evaluates a possible layer boundary, not a new method. Completion verification, action-effect checking and process-aware evaluation have close prior work. Passing would authorize only a later online held-out verifier test; failing would stop the screenshot-only critic line.

## 2. Frozen dataset

Manifest: `05_project/configs/completion_verifier/official_qwen32b_success_claims_27.final.json`  
Manifest SHA-256: `8d721aa99ac5f0f9cabf91410d83ebd8361d97265333ac9117754d87e60cfaf5`

Selection is mechanical: every scientifically eligible episode in the frozen official 57-key report with `model_claimed_status=success`. No task or screenshot was selected after viewing verifier output.

- 27 total records;
- six evaluator-confirmed success claims;
- 21 false-success claims;
- one screenshot per record, captured immediately before `terminate(success)`;
- order sorted by task class and seed;
- every screenshot and source `episode.json` is hash-verified;
- evaluator label, reward, prior actions, UI tree, database and model's original success prose are not provided to the verifier.

All records were previously generated and many were previously inspected. This is therefore a development-contaminated diagnostic, not held-out evidence.

## 3. Frozen verifier

Model: `Qwen/Qwen3-VL-32B-Instruct`  
Revision: `0cfaf48183f594c314753d30a4c4974bc75f3ccb`  
Runtime: stock vLLM, BF16, one RTX PRO 6000 96GB  
Generation seed: 3407  
Temperature/top-p/top-k: 0.7/0.8/20  
Presence/repetition penalty: 1.5/1.0  
Maximum output tokens: 512  
Input image policy: exactly one final current screenshot  
Calls: exactly one per record; no repair call

System prompt SHA-256: `30021734fcb6cef65adfe19b2fff538d06fdd8565ad0ede629b5f6663b6e494d`

The frozen system prompt is:

> You are a strict mobile-task completion evidence auditor. You receive a task and one current screenshot captured immediately before another agent claimed success. Judge only whether this screenshot is sufficient to allow that success claim.
>
> Rules:
> - CONFIRMED requires visible evidence that every task requirement, including the exact object, value, field, container, operation, multiplicity, and destination, is satisfied.
> - A page transition, generic success toast, opened detail page, related object, or the other agent's claim is insufficient when it does not prove the exact task predicate.
> - Do not assume that an unseen earlier action succeeded.
> - If any required fact is hidden, ambiguous, contradicted, or only indirectly suggested, choose INSUFFICIENT.
>
> Output exactly one JSON object and nothing else:
> `{"verdict":"CONFIRMED or INSUFFICIENT","reason":"one concise sentence","visible_evidence":["short visible fact"]}`

The user prompt contains only the task goal and asks whether the attached screenshot provides sufficient visible evidence to allow success.

## 4. Frozen metrics and gate

Prediction is positive only for a valid exact-JSON `CONFIRMED`. Invalid output fails closed as `INSUFFICIENT` but is also counted separately.

Report:

- true positives: evaluator success accepted;
- true negatives: false success rejected;
- false positives: false success accepted;
- false negatives: evaluator success rejected;
- exact-output validity;
- true-success acceptance (TPR);
- false-success rejection (TNR);
- balanced accuracy, `(TPR + TNR) / 2`;
- total calls, tokens and latency.

The diagnostic passes only if all conditions hold:

1. 27/27 exact outputs are protocol-valid;
2. false-success rejection is at least 16/21 (76.19%);
3. true-success acceptance is at least 4/6 (66.67%);
4. balanced accuracy is at least 0.70.

These conditions prevent the trivial reject-all policy from passing: reject-all has 77.78% ordinary accuracy but zero true-success acceptance and balanced accuracy 0.50.

## 5. Stop and interpretation rules

- No prompt, parser, threshold, sampling or record change after the first call.
- No selective rerun for a preferred verdict.
- A transport-invalid call may be recovered only through the existing same-idempotency-key retry; no second scientific call is allowed.
- Stop after 27 records or on a reproducible runner defect.
- Do not merge these calls or labels into the 57-key task-success denominator.
- Passing authorizes only a separately preregistered online gate on fresh tasks.
- Failing stops the screenshot-only completion-verifier line; it does not show that completion verification is useless when supplied structured state, action history or external database evidence.

## 6. Frozen implementation and qualification

- `completion_verifier.py`: `85d28d7e83f2fa7e3dfe356f5696f9981f77b1caa5fcee6a47d9159b37fdd8cf`
- `build_completion_verifier_manifest.py`: `d298e9020bfe21930e42e82e006fd2d2171c923a213fbf6ab467544dbc69f4ab`
- `run_offline_completion_verifier.py`: `457673d550fb1d5cb0db36e568f7615854e4fe982de8863737673de794f6ebb1`
- `run_offline_completion_verifier.ps1`: `2e13b732a394670ffc4301754f53eda9f91bdfc602b5630c857ab555f47633ea`
- `vllm_client.py`: `b3c613db89cf690ed4c8b56158d7d341fb948c4ce553d4ef269d7fb854f5c3d2`
- Python source compilation: pass;
- PowerShell syntax parse: pass;
- official mobile-agent test suite: 34 passed before the first verifier call.
