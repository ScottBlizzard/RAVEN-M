# RAVEN-M: Public Framework Decision Packet

This branch is a deliberately curated decision repository for the next stage of
the Zhejiang University summer-camp project on memory management for
Qwen3-VL-32B mobile GUI agents.

The previous repository mixed early RAVEN-M prototypes, dozens of protocol
revisions, infrastructure failures, obsolete hypotheses, and the later valid
official-style baseline. Those materials remain recoverable in Git history, but
they are removed from the current tree so that an external reviewer is not asked
to infer the present research question from superseded work.

## The only decision requested now

Select **one existing public, broadly capable mobile/computer-use agent
framework** to reproduce faithfully with the same Qwen3-VL-32B foundation and
AndroidWorld interface. It should cover as much of the observed long-horizon
failure chain as possible. Do not design a second framework combination and do
not design our own method yet.

Start with:

1. [`GPT_DECISION_REQUEST.md`](GPT_DECISION_REQUEST.md)
2. [`FRAMEWORK_SELECTION_RUBRIC.md`](FRAMEWORK_SELECTION_RUBRIC.md)
3. [`ARTIFACT_MANIFEST.md`](ARTIFACT_MANIFEST.md)
4. [`assessment/夏令营考核题目_提取文本.txt`](assessment/夏令营考核题目_提取文本.txt)
5. [`evidence/baseline/official_qwen32b_full_hard_combined_corrected_final.md`](evidence/baseline/official_qwen32b_full_hard_combined_corrected_final.md)
6. [`evidence/baseline/official_qwen32b_full_hard_failure_taxonomy_2026-08-08.md`](evidence/baseline/official_qwen32b_full_hard_failure_taxonomy_2026-08-08.md)
7. every Markdown report under [`evidence/layer_audits/`](evidence/layer_audits/)
8. every Markdown report under [`evidence/interventions/`](evidence/interventions/)

## Current empirical anchor

- Model: `Qwen/Qwen3-VL-32B-Instruct`
- Revision: `0cfaf48183f594c314753d30a4c4974bc75f3ccb`
- Runtime: stock vLLM, BF16, one RTX PRO 6000 96 GB
- Benchmark: 19 AndroidWorld Hard task classes x 3 task seeds
- Scientifically eligible instances: 57/57
- Full successes: 7/57
- First seed, retained for the future 19-task main comparison: 4/19
- Valid model calls / recorded steps: 1,175
- Steps missing any L0-L5 record: 0
- False success claims: 21
- Episodes with repeated page states: 39
- Episodes with consecutive stagnation: 14

The 7/57 baseline is not a pure measure of model weights. It measures the fixed
Qwen model together with Qwen's public mobile-agent prompt/history/tool protocol,
our faithful AndroidWorld adapter, the native task budgets, and the AndroidWorld
evaluator. Infrastructure-invalid and implementation-invalid attempts were
retained separately and never counted as model failures.

## Repository map

```text
assessment/          original summer-camp assignment and extracted text
evidence/baseline/   final 57-instance result and whole-suite analyses
evidence/layer_audits/
                     deterministic audits of the failure chain
evidence/interventions/
                     preregistered or frozen rescue results, including failures
evidence/prior_reviews/
                     earlier independent GPT Pro reviews, preserved as context
protocols/           current preregistrations, corrections, and runbook
implementation/      compact inspectable slice of the official baseline code
final_report/        current formal Chinese report in TeX and PDF
```

## Raw-data boundary

The full local run tree contains screenshots, UI records, requests, responses,
actions, transitions, and evaluator output for all 1,175 steps. It is not pushed
because of size. The repository includes mechanical JSON summaries, event-file
hashes, audit scripts, task manifests, and representative aggregate evidence.
Any claim that cannot be supported from these materials must be listed as an
information gap rather than guessed.
