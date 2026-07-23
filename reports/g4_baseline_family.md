# G4 baseline-family development gate

Status: **passed**
Suite: `baseline_dev_g4_20260723`
Protocol: non-Hard development only; no scored Hard task was run

## Result

| Variant | Episodes | Official successes | Decisions | First-pass parse | Valid after one repair | History calls | Max prompt tokens | Infra errors |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| B0 | 5 | 2 | 55 | 52/55 (94.55%) | 55/55 (100%) | 0 | prior G3 lock | 0 |
| B1 | 2 | 2 | 20 | 19/20 (95.00%) | 20/20 (100%) | 0 | 4327 | 0 |
| B2 | 2 | 2 | 17 | 17/17 (100%) | 17/17 (100%) | 0 | 5567 | 0 |
| B3 | 5 | 3 | 52 | 51/52 (98.08%) | 52/52 (100%) | 6 | 4410 | 0 |

B3's two unsuccessful tasks are retained as agent failures:
`ClockTimerEntry` ended with a model-declared infeasible result and
`FilesMoveFile` exhausted its frozen action budget. Neither was retried.

## Reproducibility and reset evidence

Three task classes were initialized, torn down, and reset three times each.
For every task, fixed-seed goal and generated-parameter hashes were identical,
and foreground activities after initialization and reset were stable. All nine
lifecycle runs completed without exception.

Exact screenshot hashes and asynchronously sampled accessibility-tree hashes
varied because Android rendering frames, cursors, animations, and accessibility
sampling are not benchmark instance keys. Those diagnostic failures remain in
`reset_determinism_g4.json` and `reset_determinism_g4_v2.json`. The final
adjudication uses the preregistered pairing fields `task + seed + goal hash +
params hash`, plus lifecycle and foreground-state stability.

## Budget and leakage audit

The machine-readable G4 audit checks every episode and call:

- `prompt_tokens + max_new_tokens` never exceeds 8192;
- executor and summary decisions use at most one repair;
- B1/B2 make no history-model calls;
- B3 summary calls occur only after steps 5, 10, and so on;
- no evaluator result/reward field appears in a prompt;
- no other episode ID appears in a prompt;
- every referenced historical image exists inside the current episode.

The audit passed with no violations.

## Gate decision

G4 is passed. B0/B1/B2/B3 are executable under one action contract, frozen
context cap, identical model revision/backend, official evaluator, and
episode-local logging. This permits protocol preparation to continue but does
not yet permit scored Hard runs: G7 method smoke and the protocol-v1 hash/tag
remain required.
