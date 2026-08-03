# EEST-AC v0.2 Nine-cell Blind Smoke — Post-batch Analysis

## Executive decision

**STOP the memory-efficacy study and do not start the 48-cell experiment.** The batch hit a shared action-interface controller floor before any environment action was executed. This result does not show that M-SLOTS is worse than, equal to, or better than an ordinary summary. It shows that the frozen executor/schema boundary was not live-compatible and therefore prevented all three arms from reaching the memory mechanism.

The integrity/accounting gate passed: all 9 cells finished, the blind lock remained closed until the batch completed, schema truncation was 0/18 calls, all 18 raw calls were counted, and a read-only evaluator result exists for 9/9 cells. The efficacy gates failed: all six positive cells and all three negative-control cells had reward 0; M-SLOTS had no positive success and no end-to-end destination-action paired win.

## Frozen batch and root cause

- Study: `eest_ac_v0_2_blind_smoke_20260803`
- Design: 2 cross-page positives + 1 negative control × B3/B3-MATCH/M-SLOTS = 9 cells.
- Runner stop: `preregistered_nine_cell_batch_complete_no_auto_expand`.
- Cell wall-time sum: 423.0 s; observed runner elapsed time was about 449 s including inter-cell setup/reset.
- All online M-RISK cells remained removed as preregistered.

Every cell failed on the first decision before an Android action was accepted. The model emitted one of three Android-style action forms:

- `{"type":"press","key":"recent_app"}`;
- `{"type":"swipe",...,"dx":0,"dy":...}`;
- `{"type":"swipe",...,"direction":"up","distance":...}`.

The frozen decision schema instead accepts canonical `press_back`/`press_home`/`press_enter`, or `swipe` with `x2`, `y2`, and `duration_ms`. The single bounded repair call reproduced the same invalid action in every cell. Thus all 18 outputs were recorded, but none crossed the schema-to-adapter boundary. This is a shared action-interface defect, not an infrastructure retry and not a memory-specific failure.

## Per-cell results

| Cell | Task | Arm | Success / reward | Termination | Env actions | Raw calls | Tokens | Time (s) | Eligible / planned / realized aux |
|---:|---|---|---|---|---:|---:|---:|---:|---:|
| 1 | EEST-P2A | B3-MATCH | 0 / 0 | model/controller invalid | 0 | 2 | 6,500 | 102.0 | 0 / 0 / 0 |
| 2 | EEST-P2B | B3 | 0 / 0 | model/controller invalid | 0 | 2 | 6,636 | 40.9 | 0 / 0 / 0 |
| 3 | EEST-P2A | B3 | 0 / 0 | model/controller invalid | 0 | 2 | 6,614 | 52.9 | 0 / 0 / 0 |
| 4 | EEST-N2 | B3 | 0 / 0 | model/controller invalid | 0 | 2 | 6,448 | 32.0 | 0 / 0 / 0 |
| 5 | EEST-P2B | M-SLOTS | 0 / 0 | model/controller invalid | 0 | 2 | 6,650 | 47.0 | 0 / 0 / 0 |
| 6 | EEST-N2 | B3-MATCH | 0 / 0 | model/controller invalid | 0 | 2 | 6,450 | 35.1 | 0 / 0 / 0 |
| 7 | EEST-P2B | B3-MATCH | 0 / 0 | model/controller invalid | 0 | 2 | 6,638 | 41.3 | 0 / 0 / 0 |
| 8 | EEST-N2 | M-SLOTS | 0 / 0 | model/controller invalid | 0 | 2 | 6,462 | 31.0 | 0 / 0 / 0 |
| 9 | EEST-P2A | M-SLOTS | 0 / 0 | model/controller invalid | 0 | 2 | 6,512 | 40.8 | 0 / 0 / 0 |

Every evaluator status is `ran_after_controller_error`; every failure is explicitly classified `model_or_controller_invalid`.

## Three-layer binding

The task-literal parser itself produced the frozen exact spans in 6/6 positive arm-episodes (18/18 source/field/destination roles). This only establishes shared parser initialization. It is not evidence capture, destination retention, or correct acting.

| Arm | H1 source→field→value capture | H2 destination-role retention | H3 value→destination action |
|---|---|---|---|
| B3 | correct 0, missing 2 (0/2) | correct 0, missing 2 (0/2) | correct 0, not attempted 2 (0/2) |
| B3-MATCH | correct 0, missing 2 (0/2) | correct 0, missing 2 (0/2) | correct 0, not attempted 2 (0/2) |
| M-SLOTS | correct 0, missing 2 (0/2) | correct 0, missing 2 (0/2) | correct 0, not attempted 2 (0/2) |
| Overall | correct 0, missing 6 (0/6) | correct 0, missing 6 (0/6) | correct 0, not attempted 6 (0/6) |

The numerical episode accuracy is 0 for all three layers, but the valid interpretation is **unobserved behind a controller floor**, not evidence that structured slots failed to bind a value. No episode admitted an evidence record, reached a value-carrying decision, or attempted a destination action.

## Paired task and H3 outcomes

Against B3-MATCH:

- B3, all three tasks: win/loss/tie = 0/0/3; positives only = 0/0/2.
- M-SLOTS, all three tasks: win/loss/tie = 0/0/3; positives only = 0/0/2.
- M-SLOTS H3 on the two positives: win/loss/tie = 0/0/2.

These are all-failure ties, not equivalence evidence. M-SLOTS has 0 net paired wins and no real positive success.

## Completion, requirements, recovery, and verification

- Completion TP/FP/FN = 0/0/0. Precision and recall are undefined because no episode predicted completion and no task succeeded.
- GoalLedger contains 9 exact root records and 0 invented requirements: invented-requirement rate = 0/9 = 0%.
- Recovery records = 0; repeated-action blocks = 0; different-class recoveries = 0.
- Blocked-action recovery is N/A (0 eligible blocks).
- Unnecessary-verification rate is N/A (0/0): no action executed and M-RISK had no online cells.
- The negative control was 0/3. Therefore the held-out completion-floor repair was not demonstrated; its policy was never reached on a satisfied stable screen.

## Calls, tokens, time, and B3-MATCH fairness

| Arm | Success | Env actions | Raw calls | Executor / repair calls | Auxiliary calls | Tokens | Wall time (s) |
|---|---:|---:|---:|---:|---:|---:|---:|
| B3 | 0/3 | 0 | 6 | 6 | 0 | 19,698 | 125.8 |
| B3-MATCH | 0/3 | 0 | 6 | 6 | 0 | 19,588 | 178.4 |
| M-SLOTS | 0/3 | 0 | 6 | 6 | 0 | 19,624 | 118.7 |

Eligible/planned/realized auxiliary opportunities were 0/0/0 in every cell. The actual total was two raw calls per cell because each used an initial executor call plus one schema-repair call. That incidental equality cannot support a claim that actual matched-memory calls are generally equal; the useful auxiliary trigger policy was never exercised.

First raw proposal branching was disclosed after the batch:

- EEST-P2A: B3 proposed an invalid directional swipe; B3-MATCH and M-SLOTS proposed an invalid recent-app press.
- EEST-P2B: B3 and M-SLOTS proposed an invalid `dx/dy` swipe; B3-MATCH proposed an invalid directional swipe.
- EEST-N2: all three proposed the same invalid `dx/dy` swipe.

No executed trajectory existed, so these are model-output branches before execution, not causal memory-path divergences.

On the negative control, M-SLOTS versus B3-MATCH used equal calls (2 vs 2), 6,462 vs 6,450 tokens (+0.19%), and 31.0 vs 35.1 s (−11.8%). The numeric token overhead is under 15%, but the preregistered conjunction fails because neither arm completed the task. Environment-action overhead is undefined at a 0-action baseline.

## Preregistered continuation decision

| Condition | Observation | Verdict |
|---|---|---|
| No truncation, no missed calls, evaluator in every cell | 0 truncations; 18/18 calls counted; 9/9 evaluator results | Pass |
| M-SLOTS ≥1 positive success and not below B3-MATCH | 0/2 vs 0/2 | Fail |
| At least one M-SLOTS H3 paired win | 0/0/2 | Fail |
| Negative completes cleanly; M-SLOTS cost increase ≤15% | Negative success 0; tokens +0.19% | Fail |
| All methods fail both positives → controller floor | 0/6 positive cells | Triggered |
| M-SLOTS 0 net win → no 48-cell batch | 0 net wins | Triggered |
| M-RISK stays excluded without a non-floor M-SLOTS signal | No signal; no M-RISK live cell | Enforced |

Final decision: `STOP_MEMORY_EFFICACY_REPAIR_SHARED_ACTION_INTERFACE`. No v0.2 rerun and no 48-cell expansion are authorized by these data. The two positive templates and the negative template are now development-contaminated and cannot be presented as fresh held-out confirmation after the interface is repaired.

## Claim boundary

The only held-out positives supported by this batch are operational: the shared parser retained exact role spans, raw-call accounting remained correct on the failure path, evaluator coverage was complete, and the blind runner obeyed its stop rule. The batch supports no online claim about M-SLOTS capture, retention, destination-action correctness, recovery, completion improvement, B3-MATCH auxiliary-call effectiveness, or Risk Gate efficacy.

## Artifacts

- Raw batch: `runs/eest_ac_v0_2_blind_smoke_20260803/`
- Recomputed metrics: `reports/eest_ac/eest_ac_v0_2_blind_smoke_metrics.json`
- Claim verdict: `reports/eest_ac/claim_evidence_v0_2_verdict.md`
- Frozen protocol: `04_protocols/eest_ac_v0_2_repair_and_blind_smoke.md`
- Frozen lock: `05_project/configs/eest_ac/protocol_lock_v0_2.json`
