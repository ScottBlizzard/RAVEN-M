# Top-3 Composite-System Component Selection

Date: 2026-08-15 (Asia/Hong_Kong)

Status: design selection only. No new composite arm is implemented, qualified, or authorized for live generation.

## Decision

The earlier seven-track design space is narrowed to three independent Pro studies:

1. `SYS-TRC-R2`: R2 compact memory plus a sparsely triggered recovery critic.
2. `SYS-HMP-R2`: R2 compact memory plus a bounded hierarchical milestone planner.
3. `SYS-VOV-R2`: R2 compact memory plus a sparse visible-outcome verifier.

They are not combined. Each is a separately attributable composite hypothesis. A later combination requires a new factorial preregistration after component-level positive evidence.

## Why these three

### 1. Triggered Recovery Critic — highest priority

A8/A9 showed that deterministic recurrence detectors can expose repeated routes. A1-R9 then detected the intended cycle and injected three recovery messages, yet the executor continued the wrong route. A10-v2/A11/A12 diagnostics similarly produced reads without productive-divergence signals. The strongest observed gap is therefore between failure evidence and a genuinely different recovery decision.

The critic is tested as the intelligence; recurrence detection is only its scheduler. The critic must be compared with a same-trigger, same-call generic reasoning control and a no-auxiliary base.

### 2. Hierarchical Milestone Planner

A6/A7/A10/A11 represented actions, goals, obligations, routes, and frontiers, but storage did not create a stable task decomposition. Long failed episodes repeatedly navigated locally without preserving phase structure. A bounded planner tests whether explicit milestone computation, rather than more memory fields, converts retained goals into long-horizon execution.

The planner cannot verify outcomes, criticize failures, or select from action candidates. It is compared with a call-matched plan shadow/generic control and the no-auxiliary R2 base.

### 3. Sparse Visible-Outcome Verifier

A1's only paired gain involved maintaining an unconfirmed repeated operation. A2 attempted verified progress but coupled frequent self-authored memory with a guard and scored 0/19. Several later traces showed false completion, proceeding without confirmation, or stale pending claims. A separate sparse verifier tests confirmation without making the executor both actor and judge.

The verifier cannot recommend the next action, plan, criticize, override, or terminate. It is compared with a same-trigger, same-call generic visual reasoning control and a no-auxiliary R2 base.

## Why the other four are deferred

- Candidate Action Arbitration adds two auxiliary roles per opportunity and risks measuring extra sampling compute rather than a targeted component before simpler decision support is tested.
- Budgeted Trajectory Monitoring is cheap and auditable, but R12 already showed a cost-side intervention can activate without capability gain; it is lower priority than a component that can change reasoning.
- Evidence-Preserving History Compression is valuable for cost, but R12's exact duplicate compression already reduced tokens by 4.37% without reward improvement on its gate.
- Frozen Workflow Retrieval has the highest leakage, donor-quality, and direction-mismatch risk; A4's weak donor experiment is insufficient support for near-term implementation.

## Shared positive base

All three use the frozen A1-R2 system as the executable base, not a failed A2–A12 arm. They may reuse one narrowly evidenced primitive from a failed arm—for example A9's recurrence detector or A2's visible-transition audit—but must not inherit the failed arm's full prompt/state stack.

A1-R2 achieved 6/19, reward 6.5, 603 calls, 595 actions, 2,685,730 tokens, and 11,230.18 valid seconds. It preserved all five A1 successes and added `OsmAndMarker` with zero paired losses. This is the preservation floor.

## Shared resource envelope

- Same Qwen3-VL-32B revision for executor and auxiliary role.
- At most two auxiliary calls per episode, no retries or reflection chains.
- Each auxiliary completion at most 256 tokens.
- Each auxiliary call input plus output at most 8,192 tokens and latency at most 60 seconds.
- Native Android action-step budget is unchanged.
- Executor proposals, including proposals later ignored by an allowed component protocol, must still be counted; however these top-three designs should avoid action override.
- Report executor and auxiliary calls/tokens/time separately and combined.
- Unused auxiliary budget is not filled with dummy calls.

Direct cross-track ranking is valid only within this common envelope. Otherwise results are an accuracy-cost Pareto comparison.

## Shared live gates

The fixed R2-success order is:

1. `ExpenseDeleteMultiple2`
2. `RetroSavePlaylist`
3. `SimpleCalendarAddOneEvent`
4. `SportsTrackerTotalDurationForCategoryThisWeek`
5. `RecipeDeleteMultipleRecipesWithConstraint`
6. `OsmAndMarker`

For each track, first compare Full with its generic active control on the first task. Full must pass and exhibit a preregistered productive intervention. Only then continue Full and control through the remaining five tasks. Full must be 6/6 with no paired loss before the other thirteen are released.

A valid scientific failure is never rerun. Infrastructure-invalid attempts are retained and linked to a bounded same-task replacement.

## Shared final verdicts

- System accuracy: at least 7/19, reward greater than 6.5, and no loss on the R2 six.
- Component causality: Full must beat its call-matched generic active control by at least one full success with no R2-six loss and at least two trace-grounded productive interventions. If specialized and generic controls tie, benefit cannot be attributed to the specialized role.
- Cost: report against both R2 and the frozen common auxiliary envelope. A composite may improve accuracy while failing cost; verdicts remain separate.

All 19 tasks and this seed have been observed. Results are matched prospective diagnostics, not pristine held-out generalization.

## Required evidence boundary

Each Pro must audit:

- `evidence/a1/A1_R1_R2_POSITIVE_AND_R3_R12_FAILURE_AUDIT_2026-08-15.md`
- `evidence/a1r2/A1R2_CVP_SCORED_RESULT_2026-08-14.md`
- `evidence/composite/COMPONENT_EVIDENCE_LEDGER_2026-08-13.md`
- formal A2–A12 protocols/results and enriched diagnostic results
- the selected track's new request document

Missing raw traces must be identified and materialized through a zero-generation, hash-bound audit before formula or trigger freeze. A Pro cannot infer unavailable trace facts.
