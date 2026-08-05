# GPT Pro Full-Control Research Handoff

Date: 2026-08-05  
Repository branch: `protocol-v2-exploratory`  
Purpose: give GPT Pro the complete research context and transfer scientific decision-making to it

## 1. Role boundary from this point forward

GPT Pro is the research planner. It is responsible for:

- auditing the complete evidence and closest prior work;
- deciding whether the current direction should stop, continue, or pivot;
- choosing the research question and the single recommended hypothesis;
- defining constructs, causal variables, task families, experimental arms and controls;
- freezing prompts, model revision, budgets, metrics, exclusions, contamination boundaries and stopping rules;
- specifying what follows under every important result branch;
- determining what can and cannot be claimed.

The local Codex agent is the execution engineer. It is responsible for:

- implementing the frozen plan faithfully;
- making only engineering repairs that do not change experimental semantics;
- running tests and model/server experiments;
- preserving raw artifacts, hashes, logs and frozen results;
- mechanically comparing results with GPT Pro's predeclared gates;
- continuing to the next predeclared stage when the gate clearly authorizes it;
- stopping and returning the evidence to GPT Pro whenever a scientific choice is required.

The executor must not independently change task wording, sample definitions, arms, thresholds, metrics, hypotheses or claims. Any such change must be decided by GPT Pro after seeing the relevant evidence.

## 2. Current empirical state

The most recent hypothesis was `Correct Memory, Wrong Target`: a correct source fact exposed before destination grounding might increase wrong-target first actions under high source/destination role ambiguity.

Three development pilots were completed with frozen `Qwen/Qwen3-VL-32B-Instruct`, revision `0cfaf48183f594c314753d30a4c4974bc75f3ccb`, backend `qwen3_vl_32b_transformers_bf16_4x4090_v1`.

Across the three pilots:

- 96 experimental cells;
- 192 model calls;
- 0% parser failure;
- 100% exact-value recall;
- exact Early/Late text-token equality for every matched pair under the real Qwen tokenizer;
- no selective retry;
- all material is development-contaminated and cannot support confirmatory claims.

### v0.1

Candidate interface: target ID, visible label, human-written visual cue and bounds.

- low-ambiguity target accuracy: 100%;
- Early-Low, Late-Low, Early-High and Late-High wrong-target rates: all 0%;
- Timing × Ambiguity interaction: 0;
- interpretation: ceiling.

### v0.2

Candidate interface: anonymous target ID and bounds only. The model had to read the screenshot and construct the text-to-region mapping.

- low-ambiguity target accuracy: 25%;
- Early-Low and Late-Low wrong-target rates: both 75%;
- Early-High and Late-High wrong-target rates: both 87.5%;
- Timing × Ambiguity interaction: 0;
- Call 2 usually preserved the incorrect Call 1 grounding commitment;
- interpretation: grounding floor, not an identifiable memory-timing effect.

### v0.3

Candidate interface: target ID, screenshot-visible label and bounds, without the human-written visual cue.

- low-ambiguity target accuracy: 100%;
- all four wrong-target rates: 0%;
- no source-as-target errors;
- no post-grounding drift;
- Timing × Ambiguity interaction: 0;
- qualification passed, but the mechanism gate failed.

The predeclared decision was therefore followed: Stage 1 was not expanded and `Destination-First Binding Gate` was not implemented.

## 3. Primary source-of-truth files

Current verdict:

- `reports/role_binding_timing/CORRECT_MEMORY_WRONG_TARGET_DEV_PILOT_VERDICT_2026-08-05.md`

Pilot protocol, code and tests:

- `04_protocols/role_binding_timing/stage1_dev_pilot_v0_1.md`
- `05_project/src/raven_m/role_binding_timing/dev_pilot_v0_1.py`
- `05_project/scripts/run_role_binding_timing_dev_pilot_v0_1.py`
- `05_project/tests/role_binding_timing/test_dev_pilot_v0_1.py`

Frozen configurations:

- `05_project/configs/role_binding_timing/stage1_dev_pilot_v0_1.json`
- `05_project/configs/role_binding_timing/stage1_dev_pilot_v0_2.json`
- `05_project/configs/role_binding_timing/stage1_dev_pilot_v0_3.json`

Raw results:

- `05_project/artifacts/role_binding_timing/stage1_dev_pilot_v0_1/`
- `05_project/artifacts/role_binding_timing/stage1_dev_pilot_v0_2/`
- `05_project/artifacts/role_binding_timing/stage1_dev_pilot_v0_3/`

Earlier project evidence and audits:

- `README.md`
- `reports/research_direction/`
- `reports/eest_ac/`
- `04_protocols/role_binding_timing/stage1_diagnostic_v0_1.md`
- `05_project/contracts/role_binding_timing_stage1.v0_1.json`
- `05_project/configs/role_binding_timing/stage1_v0_1.json`
- `reports/androidworld_hard/` and other AndroidWorld Hard reports present in the repository
- historical infrastructure protocols and artifacts under `04_protocols/role_binding_timing/` and `05_project/artifacts/role_binding_timing/`

GPT Pro should inspect the repository tree rather than relying only on this index. Raw per-cell outputs include the exact prompts, responses, usage, hashes, latency and parsed decisions.

## 4. Important historical boundary

The repository contains a long infrastructure-diagnosis history. Much of it was produced while attempting to obtain fresh Android snapshots and includes repeated M1–M14 contracts, freezes, failures and audit artifacts. It is relevant as evidence of engineering cost and failure modes, but it must not automatically dictate the next scientific direction.

Some protected local worktree files are intentionally not in the latest commit because they are incomplete WIP owned by an earlier task. They are not frozen positive results and must not be treated as missing evidence that the executor may silently complete.

The successful v0.1–v0.3 pilots deliberately used already-inspected real AndroidWorld frames as development material and bypassed the failed fresh-snapshot collector. They did not execute live Android actions. This boundary must remain explicit.

## 5. What GPT Pro must now decide

GPT Pro should independently determine, after reading the complete repository and current literature:

1. whether any scientifically worthwhile question remains in the current evidence;
2. whether the observed v0.2–v0.3 discontinuity is a genuine research signal or merely an expected consequence of supplying structured UI text;
3. whether another direction has stronger evidence, novelty and feasibility;
4. whether the correct recommendation is to stop rather than manufacture a new novelty claim;
5. if continuing, the complete executable study plan and every decision branch needed by the executor.

No candidate direction is privileged by this handoff. The latest null result is evidence, not a request to rescue the rejected hypothesis.

## 6. Required completeness of the next plan

The next GPT Pro output should leave no scientific design work to the executor. It should specify, where applicable:

- closest-prior novelty audit with primary-source links and publication status;
- one final recommended question and hypothesis;
- exact causal estimand and alternative explanations;
- fresh task/state selection procedure and contamination boundary;
- qualification corpus and held-out corpus;
- experimental arms, controls, counterbalancing and randomization;
- exact prompt templates or a deterministic prompt-generation specification;
- model revision, decoding settings, calls, token/action budgets and retry policy;
- oracle construction and annotation protocol;
- primary, diagnostic and cost metrics;
- exclusion rules and invalid-cell handling;
- numeric qualification, continue, stop and pivot gates;
- minimum sample sizes and the logic behind them;
- the exact next action under positive, null, ceiling, floor, mixed and infrastructure-limited outcomes;
- files and artifacts the executor must produce;
- claims allowed and forbidden at each evidence level;
- a rapid first screening stage that prioritizes actual model calls over infrastructure expansion.

If the available evidence is insufficient to select a defensible direction, GPT Pro should say so explicitly and specify the smallest information-gathering audit required before another experiment. It should not fill the gap with generic framework design.
