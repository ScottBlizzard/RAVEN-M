# Protocol-v2.2 Gate-E r56 final report

Date: 2026-07-31  
Suite: `nonhard_capability_v2_2_seed20260729_r56`  
Source: `24ddb7a34c0e873218cbac6b081d7d24ecd7d61e`  
Tag: `protocol-v2-2-gate-e-r56`  
Decision: **PASS as a protocol requalification gate; Gate F not started**

## Bottom line

The frozen r56 run completed all eight paired non-Hard cells in 3,490.938
seconds (58 minutes 10.938 seconds). Eight of eight are valid scored cells,
seven receive AndroidWorld native reward `1.0`, and every one of the 19
frozen Gate-E checks is true.

This is a protocol-engineering result, not a method-win result. B3 scores 4/4
and M0 scores 3/4 on four paired tasks at one seed. The sample is too small
and too narrow to establish a B3/M0 effect, and none of these cells belongs to
the frozen 364-episode Hard evaluation.

## Formal cell results

| Seq. | Variant | Task | Native | Actions | Calls | Termination | Visible review |
|---:|---|---|---:|---:|---:|---|---|
| 1 | B3 | `ContactsAddContact` | 1 | 9 | 16 | `model_done` | partial: exact form values; native persistence |
| 2 | M0 | `SimpleCalendarEventsOnDate` | 1 | 3 | 5 | `model_answer` | pass: exact date/title and cache match |
| 3 | B3 | `ExpenseAddSingle` | 1 | 10 | 15 | `model_done` | pass: new row visible after Save |
| 4 | M0 | `FilesMoveFile` | 1 | 20 | 32 | `max_steps` | pass: Ringtones and target tile visible |
| 5 | M0 | `ContactsAddContact` | 0 | 12 | 21 | `max_steps` | fail: correct form values, Save never executed |
| 6 | B3 | `SimpleCalendarEventsOnDate` | 1 | 3 | 3 | `model_answer` | pass: exact date/title |
| 7 | M0 | `ExpenseAddSingle` | 1 | 12 | 21 | `max_steps` | pass: new row visible after Save |
| 8 | B3 | `FilesMoveFile` | 1 | 15 | 23 | `model_done` | partial: source absence plus native success |

All eight semantic audits pass. Across the suite there are 21 validation
blocks, zero visible-failure violations, zero executed blocked actions, and
zero unresolved guard repairs. Model identity, paired goal/parameter hashes,
memory isolation, evaluator leakage, readiness accounting, startup
accounting, task/action compatibility, valid output, interaction-cache
population and IR correctness all pass.

## Retained M0 Contacts failure

The failed cell is a genuine method/planning failure, not an infrastructure
failure. Its final screenshot shows the exact `Sofija Martin` name and
`+1 763-432-2348` phone, but the Save button is still present and was never
pressed.

The causal trace is unusually informative:

1. Steps 0-7 correctly open Contacts and fill the required name and phone.
2. The M0 planner invents a current subgoal, “Enter the company name for the
   contact,” plus a completion requirement that Company contain the correct
   company name.
3. That requirement has no evidence memory IDs, and Company is absent from
   both the task and the planner's own required-variable list.
4. Step 8 follows the unsupported plan and focuses the optional Company
   field.
5. Task-scope and text-provenance guards correctly prevent the model from
   inventing a company value, but the policy then spends steps 9-11 on Back
   and Wait rather than rejecting the bad plan and saving the valid form.
6. The twelve-step budget expires; the screenshot and native evaluator agree
   that the contact was not saved.

This sharpens the research hypothesis. Separating retrieved memories into
FACT, HYPOTHESIS and failure records is necessary but not sufficient: planner
requirements also need provenance, contradiction checks and expiration.
Otherwise an unsupported plan obligation can become a frozen anchor even
when no false value is allowed to enter the GUI. This is retained evidence
for a future method revision; r56 is not changed or rerun after seeing it.

## Files safety and r56 evidence boundary

Both Files cells encounter an initial exact-target guard at step 5 while the
target is not yet safely selectable. Each then searches the exact filename
and executes one exact long press, one destination MOVE commit, and no second
transfer mutation.

M0 reaches a positive Ringtones view with the target audio tile visible at
step 16, then spends the remaining reversible steps checking source absence.
B3 presses Back after the commit and stops from the Music view where the
target is absent. Both receive native reward `1.0`.

Neither formal Files cell needs the r56 view-mode repair: after exact-name
search, the model selects the exact target correctly. The r55 rationale
normalizer also does not fire in the formal run. Therefore this suite
qualifies the exact r56 source as a whole but does not turn the deterministic
r56 branch tests and real-AVD zero-model-call control probe into live
model-trigger evidence. The earlier development smoke remains separate and
is not pooled into formal scoring.

## Infrastructure accounting

Sequence 5 attempt `a1` encountered a real connection refusal on the local
forwarded endpoint `127.0.0.1:18000` (`WinError 10061`). The frozen runner:

1. archived the attempt under
   `invalid_infrastructure_attempts/05_M0_ContactsAddContact_seed20260729_attempt_01`;
2. confirmed the exact model revision and backend healthy after 0.125
   seconds;
3. reset the task and ran attempt `a2`.

Attempt `a1` is counted as one infrastructure attempt and excluded from task
scoring. Attempt `a2` is the valid scored M0 Contacts failure described
above. This separation prevents transport instability from being mislabeled
as an agent failure while preserving the real algorithmic outcome.

## B3/M0 descriptive diagnostics

| Variant | Role | Success | Mean actions | Mean calls | Mean prompt tokens | Mean completion tokens |
|---|---|---:|---:|---:|---:|---:|
| B3 | simple-summary baseline | 4/4 | 9.25 | 14.25 | 72,817.50 | 1,264.25 |
| M0 | full RAVEN-M | 3/4 | 11.75 | 19.75 | 123,449.00 | 2,331.25 |

Relative to B3, M0 uses 27.03% more executed actions, 38.60% more model
calls, 69.53% more prompt tokens and 84.40% more completion tokens in this
gate, while its observed success rate is 0.25 lower. These are descriptive
engineering diagnostics only. Four paired non-Hard instances cannot support
a paper-level method comparison.

## Immutable evidence

The raw formal suite remains local under
`runs/protocol_v2_2/nonhard_capability_v2_2_seed20260729_r56/`. Key hashes:

- `suite_summary.json` and final `suite_progress.json`:
  `98173b320ad4e10125cc05d92e17e4eb83b65e489cbaf1369fe083e95e684e2c`;
- `manifest.snapshot.json`:
  `8f367830e7b9dbd769c95f84893a54adcadff2341724f7d1c63e47c60cf315a8`;
- `instances.snapshot.json`:
  `13d6ab543008b94d38e789105210d7fc56eb2eec7f66ed498f7113c910ae79b5`;
- startup audit:
  `018436e344dd1b9f567fe66e5973ce3612f4f993d5b25c9ba822bd4678dbcaf0`;
- scored M0 Contacts `episode.json`:
  `88c95d676861546959bec789f3748d32725319c17de72f5080df71e4acd5ea52`;
- scored M0 Contacts `events.jsonl`:
  `9d3ec5a04d8fea74a4776a47bf1ffe3925b565cc0a8322ac3f4740d42c34a456`.

The machine-readable report records every cell, evidence screenshot hash,
paired diagnostic, Files guard count, infrastructure archive and claim
boundary.

## Decision

Gate E is closed as **passed**. Automatic Gate-F transition was disabled and
Gate F has not started. The next valid action is to seal this artifact, then
run a fresh zero-model-call Gate-F preflight and make a separate manual launch
decision for the twelve-cell paired Hard micro-gate. The M0 Contacts failure
must remain in the record, and no development smoke may be pooled into this
formal score.
