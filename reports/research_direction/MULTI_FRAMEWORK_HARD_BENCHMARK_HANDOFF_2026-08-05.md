# Multi-framework Hard benchmark: evidence handoff for GPT Pro

## Executive decision request

The latest `Correct Memory, Wrong Target` and natural-loop analysis should not
end the summer project. The specific proposed loop-binding intervention was
stopped because the closest-prior overlap was too strong, not because the Hard
failures were uninteresting. The next defensible activity is a broad but
controlled reproduction/diagnostic benchmark of representative public mobile
GUI systems on the same 19 AndroidWorld Hard task classes.

No model call or new Android episode has been run for this benchmark. This
handoff asks GPT Pro to freeze the design before generation.

## Local readiness that has direct evidence

- AndroidWorld commit `3e508885...` is present locally.
- The Windows AndroidWorld runtime, official evaluator, emulator lifecycle,
  split-host model service, and Qwen3-VL-32B revision `0cfaf481...` have prior
  smoke evidence in `04_protocols/environment_lock.yaml`.
- The MobileAgent repository is already present at commit `11cea575...` and
  contains both `Mobile-Agent-v3.5/android_world_v3.5/run_guiowl15.sh` and
  `run_ma35.sh`.
- The MobileUse repository is already present at commit `babec07f...` and
  contains `benchmark/android_world/run.py`, MultiAgent configuration, and
  ColorMobileAgent support. Its own README recommends Python 3.12 on Windows,
  so it must not be installed into the pinned Python 3.11 AndroidWorld runtime.
- DroidRun's dedicated AndroidWorld repository was cloned at commit
  `50901303...`; its direct accessibility/tool privileges require a separate
  reporting stratum.
- ScaleCUA officially documents AndroidWorld evaluation, but two shallow clone
  attempts ended in GitHub TLS/RPC truncation. Its remote HEAD is
  `5d92feea...`; local readiness must remain false until the source and model are
  complete.

## Why several strong papers are not automatically runnable arms

- VLAA-GUI has public code but evaluates desktop environments; an AndroidWorld
  implementation would be a mechanism port.
- VeriGUI includes a trained verification/recovery system and evaluates a
  robustness benchmark based on AndroidControl; reimplementing only its prompt
  logic is not an exact reproduction.
- BacktrackAgent includes trained modules/data and is not a quick plug-in
  AndroidWorld controller.
- K2-Agent reports strong AndroidWorld performance but no stable named official
  repository was verified during the 2026-08-05 audit.

These methods remain essential closest priors and reported references, but they
must not be presented as completed reproductions without their exact artifacts.

## Proposed empirical structure

The benchmark deliberately separates two questions:

1. **Common-backbone diagnostic:** when technically faithful, use the same
   pinned Qwen3-VL-32B service to study controller differences.
2. **Native-system benchmark:** use each public system's documented model and
   tools to measure end-to-end capability, while disclosing non-comparable
   privileges and resources.

The full proposed pool is M3A, RAVEN-B0, RAVEN-M0, GUI-Owl-1.5,
Mobile-Agent-v3.5, MobileUse MultiAgent, ColorMobileAgent, DroidRun, ScaleCUA,
and conditionally UI-TARS-1.5. This is intentionally a candidate pool, not a
claim that every arm is already runnable.

## Runtime estimate after protocol approval

- Static/runtime qualification and isolated environments: 1--2 days.
- One excluded two-task smoke per arm: roughly 0.5--1 day total if model access
  is already available.
- S2 breadth: 19 cells per qualified arm. Nine arms imply 171 cells. At the
  observed single-generation latency plus reset/action overhead, expect roughly
  14--24 hours of sequential wall time, excluding adapter failures.
- S3 confirmation: 38 additional cells per arm. For six qualified core arms,
  this adds 228 cells and roughly 1--2 days of stable execution.
- Manual trajectory audit, normalized aggregation, and report update: 1--2 days.

A realistic, credible multi-seed result is therefore 6--9 calendar days after
approval. A one-seed breadth table can be available in roughly 3--5 days. Exact
paper-configuration reproduction can take longer because checkpoints and
training artifacts differ.

## Files GPT Pro must read

1. `2026_08_05_17_36.md` -- latest full no-go/novelty audit.
2. `RAVEN-M_GPTPro_full_plan_2026-08-05.md` -- preceding full-control plan.
3. `04_protocols/multi_framework_hard_benchmark_v0_1.md` -- proposed protocol.
4. `05_project/configs/experiments/multi_framework_hard_benchmark_v0_1.json` -- machine-readable freeze candidate.
5. `03_code/manifests/multi_framework_candidates_v0_1.csv` -- candidate and readiness ledger.
6. `05_project/configs/task_manifests/androidworld_hard_v1.json` -- frozen 19-task source.
7. `04_protocols/environment_lock.yaml` -- available runtime/model resources.
8. `reports/breadth_forensic_analysis_2026-07-26.md` -- prior Hard behavior evidence.

## Required GPT Pro output

Return one Markdown document containing:

- a verdict on whether this benchmark is scientifically worthwhile;
- a corrected, prioritized arm table with exact-reproduction versus adapter
  labels;
- any omitted stronger public AndroidWorld systems with official artifacts;
- a final frozen S0/S1/S2/S3 protocol;
- exact fairness rules for models, observation privileges, budgets, and seeds;
- the minimum useful process metrics when task success remains zero;
- a day-by-day execution order optimized for early informative results;
- explicit GO/NO-GO gates for each arm and for multi-seed expansion;
- exact claim language allowed for each possible result pattern.
