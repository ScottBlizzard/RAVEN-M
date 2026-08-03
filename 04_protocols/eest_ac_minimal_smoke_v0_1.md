# EEST-AC Minimal Paired Smoke Protocol v0.1

Status: **frozen before implementation and model calls**  
Study ID: `eest_ac_smoke_v0_1_20260803`  
Research namespace: `raven_m.eest_ac`  
Run root: `runs/eest_ac_smoke_v0_1_20260803/`

## 1. Research question

Does a small, typed, evidence-grounded episode state improve cross-page GUI task execution over a strong simple-summary baseline when model, task instance, action budget, call ceiling, and context ceiling are controlled? Does a verifier restricted to consequential actions reduce high-risk mistakes without imposing unacceptable cost?

This study does **not** test or claim a complete memory lifecycle. It does not continue the H17/rXX controller-tuning program.

## 2. Contamination boundary

- The study must not import `protocol_v2_guard.py`, any H17/date-row helper, or any protocol-v2.2 routed-evidence rule.
- `protocol-v1`, frozen B0–B3/M0 results, and prior H17 evidence are read-only historical artifacts.
- H17, every SportsTracker task, identical date-row layouts, and repeatedly debugged row/date patterns are permanently excluded.
- Existing r79 worktree modifications are legacy-route work and remain unstaged and untouched.
- Candidate template names were searched in existing `runs/`, configs, protocols, and reports before selection. Neither selected template occurred.
- Task parameters and initialized screenshots remain blind until all eight cells finish. Only the task-class definitions and public template semantics were used for selection.

## 3. Minimal architecture

### Shared substrate

All arms share the same model revision, screenshot preprocessing, canonical action schema, strict JSON parser, AndroidWorld adapter, evaluator, initialization seed, maximum environment actions, maximum model calls, 8192-token total context ceiling (`prompt_tokens + max_new_tokens`), and raw-artifact logging.

### B3 — simple summary

- Current screenshot has priority.
- Keep the last two executed transitions.
- Every fifth executed action, use one auxiliary call to update an ordinary trajectory summary.
- No typed ledger, authority routing, risk gate, planner, critic, PSI-lite, reliability scalar, or lifecycle state.

### B3-MATCH — call-schedule matched summary

- Same ordinary summary representation as B3.
- No periodic summary call.
- Whenever the shared deterministic risk detector marks an executor candidate eligible for an M-RISK gate, spend one auxiliary call to update a useful ordinary structured summary from the same available evidence.
- The candidate action is not gated by this call.
- No neutral padding is permitted. It receives the same prompt/context ceilings and the same auxiliary-call upper bound as M-RISK.

### M-SLOTS — minimal typed episodic state

- Immutable task literals parsed once from the task goal.
- Append-only EventLog.
- EvidenceLedger records only explicit `entity–field–value–source–scope` bindings with acquisition step and source hash.
- Closed GoalLedger contains only requirements directly parsed from the task or deterministically entailed by it.
- Recovery Registry is populated only after an executed state–action pair has a confirmed semantic no-effect.
- Context Compiler selects only task literals, open requirements, recovery entries relevant to the current state, and evidence relevant to the next action. The current screenshot is always the highest authority for the current page.
- History is authoritative only for cross-page fields and transitions that the controller actually observed.
- No periodic Planner, general per-step Critic, PSI-lite, unified reliability scalar, or full stale/superseded/revoked lifecycle.

### M-RISK — M-SLOTS plus action-conditioned authority

- Identical to M-SLOTS except for a single auxiliary gate on candidate `Save`, `Send`, `Delete`, `Answer`, or terminal `Done` actions.
- Low-risk reversible navigation is never gated merely because it is a navigation action.
- A rejected high-risk candidate is not executed and is recorded as a gate event; the next executor call must choose a safer action or gather missing evidence.

## 4. Falsifiable hypotheses

- **H1 (cross-page state):** On EEST-P1, M-SLOTS must avoid at least one entity/field loss or binding error seen in B3-MATCH, and task success must not be lower.
- **H2 (negative-control restraint):** On EEST-N1, M-SLOTS and M-RISK must not add an unnecessary verification; their wall time and total-token cost should not exceed B3-MATCH by more than 15% absent a correctness gain.
- **H3 (risk selectivity):** M-RISK may gate the final `Send` on EEST-P1 but must not gate ordinary thread navigation. Any extra call must have an auditable high-risk trigger.
- **H4 (closed goals):** No arm using GoalLedger may create a requirement not supported by a task-literal span or deterministic entailment rule. Invented-requirement rate must be zero in local corruption tests and is measured in the live smoke.
- **H5 (recovery causality):** Recovery Registry must remain empty unless a real executed state–action pair has confirmed semantic no-effect. A merely repeated intention or model proposal is insufficient.

The smoke is diagnostic, not statistical confirmation. A single paired win is a signal only; expansion still requires the preregistered threshold below.

## 5. Held-out tasks and selection basis

| ID | AndroidWorld class | Role | Why it tests the claim | Explicit exclusions |
|---|---|---|---|---|
| EEST-P1 | `SimpleSmsSendReceivedAddress` | cross-page positive | The agent must bind the address sent by `name2`, retain it across conversation navigation, bind the destination to `name1`, and perform a consequential Send. | No SportsTracker, no date, no repeated row layout, not in prior runs/configs/reports. |
| EEST-N1 | `OpenAppTaskEval` | short reversible/current-history-unnecessary control | The target app is an immutable task literal; successful execution should require no historical fact or verifier. | No form filling, no cross-page value, not in prior runs/configs/reports. |

One parameter seed (`20260803`) is paired across all four arms. Parameters are generated and machine-frozen without human inspection before the first cell. Every arm receives the identical parameter hash and clean emulator reset.

## 6. Eight-cell frozen schedule

The order is fixed before task generation and interleaves task and arm to reduce time drift:

1. EEST-P1 / M-SLOTS
2. EEST-N1 / B3-MATCH
3. EEST-P1 / B3
4. EEST-N1 / M-RISK
5. EEST-P1 / M-RISK
6. EEST-N1 / B3
7. EEST-P1 / B3-MATCH
8. EEST-N1 / M-SLOTS

There is one valid attempt per cell. Only preregistered infrastructure failures—emulator unavailable, accessibility unavailable before the first decision, model service transport failure with no response, or evaluator crash—may be retried, preserving the same instance hash and recording both attempts.

## 7. Budgets

| Task | Max environment actions | Max model calls | Max new tokens/call | Context rule |
|---|---:|---:|---:|---|
| EEST-P1 | 18 | 36 | 256 | `prompt_tokens + 256 <= 8192` |
| EEST-N1 | 10 | 20 | 256 | `prompt_tokens + 256 <= 8192` |

All arms receive identical per-task ceilings. Auxiliary calls consume the common call budget. No arm receives extra environment actions after a rejected or invalid model decision.

## 8. Required metrics

Report both raw cell values and paired comparisons:

- task success and evaluator reward;
- paired win/loss/tie;
- environment actions, total model calls, auxiliary calls, prompt/completion/total tokens, and wall time;
- entity–field binding accuracy;
- invented-requirement rate;
- completion precision and recall;
- blocked-action recovery (block followed by successful progress/completion);
- unnecessary-verification rate on gate-ineligible actions and negative controls;
- high-risk error count and context-cap violations.

For smoke-only human labels, ambiguous cases must be marked `needs_adjudication`; they must not be silently counted as correct.

## 9. Local gates before model use

No model call is allowed until all are true:

1. unit tests for immutable task literals, ledger typing, goal closure, no-effect recovery activation, authority precedence, and risk triggers pass;
2. replay tests pass on synthetic multi-page evidence transfer;
3. negative-control tests prove no gate on reversible navigation;
4. corruption tests reject wrong entity binding, ungrounded requirements, source-hash mutation, and recovery without no-effect;
5. full local regression passes, with the already documented legacy r79/frozen-manifest incompatibility reported separately rather than hidden;
6. a zero-model-call preflight validates config, task registration, hashes, emulator/model health, output isolation, budget equality, and blind-run lock.

## 10. Preregistered decisions after the batch

- Stop treating reliability as a main AndroidWorld bottleneck if natural memory-specific hazards are below 2%.
- If every arm scores below 4/12 in the later pilot, repair the shared controller rather than tune memory.
- Do not expand M-SLOTS unless it obtains at least three net paired wins over B3-MATCH in a 12-pair gate. This eight-cell smoke cannot by itself satisfy that expansion rule.
- Remove the Risk Gate if cost exceeds 15% and it does not reduce high-risk errors.
- Any code change after this smoke starts requires a new study ID and new held-out instances. No task-specific rule may be added to rescue a failed cell.

After all eight cells finish, stop. Only then unlock trajectories, label failure mechanisms, calculate costs, and issue a GO/PIVOT/STOP analysis.
