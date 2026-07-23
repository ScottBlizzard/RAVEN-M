# G3 non-Hard development gate

Generated: 2026-07-23  
Status: **passed with executor v1**  
Scope: development only; no Hard task was run or scored.

## Gate definition

The frozen G3 gate required five explicitly non-Hard AndroidWorld task classes,
at least 50 real model decision attempts, at least 90% strict first-pass action
validity, at least 95% validity after one bounded repair, and the already
frozen maximum-shape request to complete without OOM.

The five task classes were `ContactsAddContact`, `ClockTimerEntry`,
`ExpenseAddSingle`, `MarkorCreateNote`, and `FilesMoveFile`, spanning five apps
and easy/medium difficulty. The manifest fixed task order, seeds, budgets, and
top-up order before execution.

## Retained executor v0 failure

The first suite is preserved under
`runs/dev_nonhard_g3/g3_b0_20260723/`. Normalized audit counts are:

| Metric | v0 result | Gate |
|---|---:|---:|
| Distinct tasks | 5 | 5 |
| Decision attempts | 54 | >=50 |
| First-pass valid | 40/54 (74.07%) | >=90% |
| Valid after one repair | 51/54 (94.44%) | >=95% |
| Infrastructure errors | 1 | report separately |
| Evaluator successes | 0/7 | exploratory |

The normalization recovers one parsed decision that the pre-fix controller
failed to persist when ADB execution raised. It also counts the initial and
repair calls from a legacy double-parse failure. The model-host JSONL contains
68 generation-complete records for this suite.

The three unrepaired outputs were one overlong `decision_summary` and two
repeated mixed-coordinate actions with normalized `x` but pixel `y=438`.
Additional first-pass failures used pixel `y` values, malformed wait wrappers,
or non-JSON text. Visual inspection also confirmed policy failures: invented
`TechCorp`, completion before Save, a wrong running timer, a wrong expense
category, and failure to recognize Markor's all-files permission page.

## Executor v1 change

No task, seed, budget, model, schema, or backend was changed. Executor v1:

- includes screenshot dimensions and a pixel-to-normalized example each step;
- requires both explanatory strings to be short;
- teaches repair to normalize coordinates, shorten text, and wrap wait inside
  `status=continue`;
- forbids treating a visible persistence button as proof of completion;
- explicitly treats a visible permission settings page as actionable UI.

The v1 suite is preserved under
`runs/dev_nonhard_g3/g3_b0_executor_v1_20260723/`.

## Passing result

| Task | Decisions | First-pass | Reward | Outcome |
|---|---:|---:|---:|---|
| `ContactsAddContact` | 9 | 9/9 | 1.0 | passed |
| `ClockTimerEntry` | 10 | 10/10 | 0.0 | budget exhausted |
| `ExpenseAddSingle` | 10 | 10/10 | 0.0 | budget exhausted |
| `MarkorCreateNote` | 12 | 9/12 | 1.0 | passed after three repairs |
| `FilesMoveFile` | 14 | 14/14 | 0.0 | budget exhausted |
| **Total** | **55** | **52/55 (94.55%)** | **2/5** | **G3 parse gate passed** |

All 55 decisions were valid after at most one repair (100%). There were 58
model calls and zero infrastructure/controller errors. The authoritative
model-host log reports mean latency 8.791 s, p50 8.774 s, p90 10.206 s, p95
10.321 s, maximum 10.877 s, and maximum peak VRAM 19,554,077,184 bytes. The
service remained healthy and no OOM occurred.

## Interpretation and next work

G3 establishes a reliable action contract and execution path; it does not
claim a strong task-success baseline. Three policy failures remain:

1. Clock repeatedly manipulated an incorrect/running timer state.
2. Expense saved the default `Food` category instead of requested `Education`,
   then started a duplicate entry.
3. Files reached move-related UI but did not finish destination selection.

These are now clean strategy errors rather than serialization failures. The
next planned step is B1/B2/B3 baseline implementation and development-only
policy/error analysis, followed by the frozen 19-task Hard preregistration.
Scored Hard runs remain forbidden until that protocol is frozen.
