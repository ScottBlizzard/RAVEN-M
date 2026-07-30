# Protocol-v2.2 Gate-E r39 final report

Date: 2026-07-30  
Suite: `nonhard_capability_v2_2_seed20260729_r39`  
Source: `02f1028b5bcef12fa2cad3c35799a8588affbf66`  
Tag: `protocol-v2-2-gate-e-r39-dev`  
Decision: **PASS as a protocol requalification gate**

## Bottom line

The frozen r39 run completed all eight paired non-Hard cells in 4,438.094
seconds (73 minutes 58.094 seconds). All eight are valid scored cells, seven
pass the native AndroidWorld evaluator, and every one of the 19 preregistered
Gate-E checks is true.

This result establishes that protocol-v2.2 can run a complete paired gate
without invalid output, evaluator leakage, cross-episode memory contamination,
unresolved loop repair, or semantic-audit failure. It does **not** establish a
method advantage. B3 is the simple-summary baseline and M0 is the full
RAVEN-M method; on this one-seed four-task gate, B3 scores 4/4 and M0 scores
3/4. The gate is an engineering qualification, not a Hard benchmark result or
a statistical method comparison.

## Frozen outcome

| Seq. | Variant | Task | Native | Steps | Calls | Termination | Manual visible review |
|---:|---|---|---:|---:|---:|---|---|
| 1 | B3 | `ContactsAddContact` | 1 | 9 | 12 | model done | partial: correct fields; save transition not captured |
| 2 | M0 | `SimpleCalendarEventsOnDate` | 1 | 3 | 6 | answer | pass: `Board meeting` visible and cache-matched |
| 3 | B3 | `ExpenseAddSingle` | 1 | 12 | 16 | max steps | partial: all fields/category correct; native row confirmed |
| 4 | M0 | `FilesMoveFile` | 1 | 20 | 32 | max steps | partial: native move confirmed; no positive final Ringtones view |
| 5 | M0 | `ContactsAddContact` | 1 | 12 | 23 | max steps | pass: saved contact detail visible |
| 6 | B3 | `SimpleCalendarEventsOnDate` | 1 | 3 | 3 | answer | pass: date and exact title visible |
| 7 | M0 | `ExpenseAddSingle` | 0 | 12 | 19 | max steps | fail: Housing selected, not Donation; not saved |
| 8 | B3 | `FilesMoveFile` | 1 | 17 | 25 | model done | pass: target visibly present in Ringtones |

The three `partial` labels are deliberately conservative. Native AndroidWorld
state is authoritative for task success, but the final screenshot does not
show an equally strong positive completion state. This distinction prevents
task score, protocol validity, and visual trajectory quality from being
collapsed into one claim.

## Acceptance audit

The suite passes all frozen checks:

- 8/8 valid scored cells and correct paired task/seed/goal/parameter hashes;
- 7/8 native successes, above the required four, with successes from both B3
  and M0;
- 100% valid executor output after at most one bounded repair;
- correct information-retrieval answer and populated interaction cache;
- zero evaluator-prompt leakage and zero cross-episode memory errors;
- zero unsupported task/action combinations and zero executed blocked actions;
- semantic-progress, visible-failure, readiness, startup-environment, and
  consequential-action accounting all pass;
- no unresolved guard repair or unhandled third identical no-effect action;
- exact frozen model identity:
  `Qwen/Qwen3-VL-32B-Instruct` at revision
  `0cfaf48183f594c314753d30a4c4974bc75f3ccb`, served by
  `qwen3_vl_32b_transformers_bf16_4x4090_v1`.

One pre-action Calendar attempt failed because Android returned no
accessibility tree. The runner archived it under
`invalid_infrastructure_attempts`, reset the environment, and reran the same
frozen cell. It is counted as one infrastructure attempt and not as a scored
agent failure. The retry completes in three valid actions with native reward
1.0.

## B3/M0 descriptive comparison

| Variant | Role | Success | Mean steps | Mean calls | Mean prompt tokens | Mean completion tokens |
|---|---|---:|---:|---:|---:|---:|
| B3 | simple-summary baseline | 4/4 | 10.25 | 14.00 | 67,920.25 | 1,225.00 |
| M0 | full RAVEN-M | 3/4 | 11.75 | 20.00 | 120,122.50 | 2,415.50 |

Relative to B3, M0 is -0.25 in absolute task success rate and uses 42.86%
more model calls, 76.86% more prompt tokens, and 97.18% more completion
tokens in this gate. These are descriptive diagnostics only: four paired tasks
at one seed are far too small for a general method-effect claim.

The clearest negative case is `ExpenseAddSingle`. B3 steps 7-9 perform three
horizontal swipes across the category strip, step 10 selects Donation, and
step 11 presses Save. M0 steps 7-8 repeat a tap on the strip, step 9
long-presses it, and steps 10-11 swipe vertically. It exhausts the budget with
Housing still selected. The evaluator, screenshot, and action trace agree.
This is a genuine M0 method/controller failure and remains in the result.

The remaining pairs also favor B3 on efficiency. Both Contacts variants
succeed, but B3 uses 12 calls versus M0's 23. Both Calendar variants return
the exact title, but B3 uses three calls versus M0's six. Both Files variants
move the file, but B3 reaches a visible Ringtones confirmation in 17 steps
whereas M0 uses all 20 steps and finishes by searching Music.

## What r38/r39 repaired

r38 added cross-modal observation freshness: when the screenshot changes
materially but the accessibility digest remains unchanged, the controller
waits for a fresh tree instead of treating the stale semantic state as the new
screen. This is exercised during Files startup and prevents the drawer/root
transition from being misread.

r39 closes the post-commit completion gap exposed by r38. After a destination
`MOVE`, if completion review requests another observation, the sole bounded
repair is an exact `press_back`. It cannot rewrite coordinates, repeat the
commit, or inspect evaluator state. Both Files cells execute this path, remain
protocol-valid, and receive native reward 1.0; B3 additionally reaches
positive visual confirmation in Ringtones.

## Evidence and reproducibility boundary

The raw suite is local under
`runs/protocol_v2_2/nonhard_capability_v2_2_seed20260729_r39/`. Its immutable
top-level hashes are:

- `suite_summary.json`:
  `fcb3e9880448f0423ce8459a5d8e91e78b453c802e682d82ea1af317f5ff68b9`;
- `manifest.snapshot.json`:
  `0ae96dd85e0eb9aa059ccb4627f1ee42ec843b99d91bf04dcb47b6ce9a7e86e0`;
- `instances.snapshot.json`:
  `13d6ab543008b94d38e789105210d7fc56eb2eec7f66ed498f7113c910ae79b5`.

The machine-readable result, per-cell screenshot hashes, manual review labels,
paired diagnostics, and next-gate boundary are recorded in
`reports/protocol_v2_2_r39_gate_e_final.json`.

## Decision

Gate E is closed as **passed**. Automatic Gate-F transition remains disabled.
The correct next step is not to claim M0 superiority or immediately spend
another long run. First preserve this artifact, review the Expense-M0 failure
as a possible generic method limitation, and decide whether a scientifically
justified change is needed. Any source change requires a new frozen protocol
version; r39 results must not be mixed with revised-code evidence.
