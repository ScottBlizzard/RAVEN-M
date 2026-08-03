# EEST-AC Minimal Paired Smoke v0.1.1 — Post-batch Analysis

## Executive decision

**STOP this batch; do not expand to 48 cells.** The minimal structured ledger showed a real mechanism signal—it captured the exact cross-page source binding correctly—but it did not produce a task-level paired win. The batch instead exposed three shared-controller/measurement defects that must be repaired generically before a new held-out study:

1. delayed UI/accessibility transitions can be misclassified as no-effect;
2. the executor can preserve the right value while acting on the wrong destination entity or wrong coordinate;
3. verbose duplicate evidence can hit the frozen 256-token output limit, and a failed repair currently skips the evaluator and undercounts calls in the online summary.

No task-specific SMS, contact, coordinate, date, row, or H17 rule should be added. This task and seed are now development-contaminated and must not re-enter confirmatory evaluation.

## Frozen batch and validity

- Study: `eest_ac_smoke_v0_1_1_20260803`
- Scale: 2 templates × 1 paired seed × 4 arms = 8 cells.
- Runtime: all eight cells completed in the frozen order in about 24.4 minutes; the runner stopped automatically.
- Context: every raw call satisfied `prompt_tokens + 256 <= 8192`; maximum prompt length was 4,549 tokens.
- Two positive-task method cells ended with `EestDecisionValidationError` after both the initial and one permitted repair were truncated at exactly 256 completion tokens. They are model/controller-invalid cells, not infrastructure retries, and have no evaluator reward.
- The raw call log is authoritative. Those two cells used 5 and 6 calls, whereas the online counters reported 3 and 4 because the exception occurred before the counter update. The metrics JSON corrects this without rerunning anything.

## Main results

| Task | B3 | B3-MATCH | M-SLOTS | M-RISK |
|---|---:|---:|---:|---:|
| EEST-P1 cross-page SMS | 0 (reward 0) | 0 (reward 0) | invalid/no evaluator | invalid/no evaluator |
| EEST-N1 open-app negative control | 1 | 1 | 1 | 1 |
| Intent-to-treat success | 1/2 | 1/2 | 1/2 | 1/2 |
| Evaluator-valid cells | 2/2 | 2/2 | 1/2 | 1/2 |

Paired win/loss/tie against B3-MATCH:

- intent-to-treat: B3 = 0/0/2, M-SLOTS = 0/0/2, M-RISK = 0/0/2;
- evaluator-valid only: B3 = 0/0/2; M-SLOTS and M-RISK each have 0/0/1 plus one invalid pair.

Therefore M-SLOTS has **0 net paired wins**, far below the preregistered requirement of at least 3 net wins over 12 pairs. Expansion is not allowed.

## Cost

| Arm | Actions | Raw calls | Auxiliary | Tokens | Wall time | Successes |
|---|---:|---:|---:|---:|---:|---:|
| B3 | 9 | 13 | 1 | 46,602 | 235.3 s | 1/2 |
| B3-MATCH | 28 | 32 | 4 | 116,114 | 554.2 s | 1/2 |
| M-SLOTS | 13 | 15 | 0 | 59,687 | 318.3 s | 1/2 |
| M-RISK | 14 | 16 | 0 | 64,480 | 331.8 s | 1/2 |

On the negative control, relative to B3-MATCH:

- M-SLOTS: equal calls/actions, +8.1% tokens, −5.2% wall time;
- M-RISK: equal calls/actions, +9.3% tokens, −11.0% wall time;
- B3: −30% calls, −32.3% tokens, −42.0% wall time, and half the actions.

M-SLOTS/M-RISK therefore stayed within the 15% negative-control cost ceiling versus B3-MATCH, but both used the full 10-action budget after the Clock app was already visibly open after action 1. B3 also waited unnecessarily, but terminated after action 5. Completion control, not memory cost, is the dominant negative-control defect.

## Entity–field binding and goal closure

The initialized positive instance was:

- source entity: `Petar Muller`;
- field: `event_address`;
- exact value: `968 Spruce St, Hartford, CT, 06103`;
- destination entity: `Gabriel Fernandez`.

Both M-SLOTS and M-RISK admitted two records. All 4/4 admitted records correctly bound `Petar Muller → event_address → 968 Spruce…`, used current-screen source hashes, and marked cross-page scope. Record-level accuracy was therefore 100%, and Context Compiler routed the `ev:` record on the next page/decision.

That did **not** become correct task-level binding: neither method reached the Gabriel conversation. The GoalLedger contained only the exact root task requirement, so invented-requirement rate was 0/8 = 0%, but source and destination roles were not separately exposed as closed structured obligations. The result is a clean distinction:

- evidence capture/retention signal: positive;
- destination-role coverage and execution: failed;
- task success gain: absent.

## Failure mechanisms

### 1. B3 false completion after wrong-entity send

B3 correctly read and retained the address, typed it in a conversation whose header was the source number rather than Gabriel, pressed Send, observed a checkmark, and declared completion. The evaluator returned 0. This is a natural entity/destination binding error, not a stale-date or H17 pattern.

Evidence: `cells/03_EEST-P1_B3/attempt_01/screenshots/d003_before.png` and its step record.

### 2. B3-MATCH wrong-entity send plus no-effect loop

B3-MATCH also typed the correct address into the source conversation. Its first Send cleared the input field, but the immediate semantic observation was classified as unchanged. It then repeated Send until the 18-action limit. Four useful ordinary summary calls were spent at the matched Send triggers; there was no neutral padding. The later candidate paths diverged from M-RISK, so actual auxiliary counts were 4 versus 0 even though ceilings and per-candidate trigger policy were matched.

### 3. M-SLOTS/M-RISK correct evidence, wrong execution plan

Both typed ledgers captured the source address before leaving the list. The model nevertheless tried to long-press near the message-input area rather than navigate Back and select Gabriel. This is visible grounding/controller planning failure. It cannot be repaired honestly by adding a SimpleSMS coordinate or contact-name rule.

### 4. Output truncation

On the next decision the model duplicated the same evidence object several times. Both the initial output and repair stopped mid-JSON at exactly 256 completion tokens. Input context was well below 8192, so this is an output-contract/compaction failure, not context overflow. The next implementation should deterministically deduplicate evidence and make the response contract shorter while retaining the same 256-token ceiling.

### 5. “True no-effect” was not true enough

At least one tap was logged as no-effect even though the next screenshot had transitioned from the conversation list to the Petar detail page. Runtime warnings also reported temporary a11y-tree unavailability. Recovery Registry therefore satisfied the syntactic admission rule—an executed same-hash transition—but not the intended real-world semantic rule. Across M arms it accumulated 17 records, including repeated waits on an already-correct Clock screen. H5 is not supported.

## Completion, Risk Gate, and recovery metrics

- Across six evaluator-valid cells: TP=1, FP=1, FN=3; completion precision=0.50 and recall=0.25.
- M-RISK produced zero eligible high-risk candidates, zero gate calls, and zero blocks. It never reached Send or Done.
- Unnecessary-verification rate was 0/14 detector-ineligible M-RISK candidates = 0%, but this is vacuous because the gate was never exercised.
- Blocked-action recovery is N/A (0 blocks).
- Risk Gate retention/removal is undecidable: there is neither gate cost nor high-risk error reduction to compare.

## Preregistered stopping decisions

| Rule | Observation | Decision |
|---|---|---|
| Natural memory-specific hazards <2% | One clear wrong-destination hazard exists, but only one positive baseline instance was run. | Frequency rule not estimable; make no 2% claim. |
| All arms below 4/12 → repair controller | Not formally applicable at 2 tasks, but all four arms were 0/1 on the only positive task. | Treat as an early controller-floor warning; repair shared controller first. |
| M-SLOTS needs ≥3 net wins/12 | 0 net wins in this smoke. | Do not expand. |
| Risk cost >15% without error reduction | No gate calls; negative-control total cost stayed within 15% of B3-MATCH. | Risk efficacy/cost rule undecidable; do not promote M-RISK. |

## Next study gate

Before any new model calls:

1. make observation readiness cross-modal and delayed-transition aware; a no-effect must survive a bounded re-observation before entering Recovery Registry;
2. store the canonical failed action—not only an opaque hash—in recovery context and test that the next decision does not repeat it;
3. keep GoalLedger closed but expose generic, exact-span roles such as source entity, requested field, and destination entity; do not add task-class rules;
4. compact and deduplicate evidence before/within the response contract, and fix raw-call counting plus evaluator execution after non-infrastructure controller/model failure;
5. add a generic completion principle: do not wait for hypothetical pop-ups or changes absent from the stabilized current screen;
6. use this completed SMS/Clock seed only as development replay. Select new templates/seeds for the next blind paired smoke.

The next real run should again be small. It should start only after replay, corruption, delayed-transition, output-truncation, completion, and zero-call runtime gates pass. M-RISK should remain secondary until M-SLOTS produces a non-floor positive-task signal.

## Artifacts

- Raw batch: `runs/eest_ac_smoke_v0_1_1_20260803/`
- Recomputed metrics: `reports/eest_ac/eest_ac_smoke_v0_1_1_metrics.json`
- Protocol: `04_protocols/eest_ac_minimal_smoke_v0_1.md`
- Amendment: `04_protocols/eest_ac_minimal_smoke_v0_1_1_amendment.md`
- Claim–evidence table: `reports/eest_ac/claim_evidence_v0_1.md`
- Local validation: `reports/eest_ac/local_validation_and_regression_v0_1_1.md`
