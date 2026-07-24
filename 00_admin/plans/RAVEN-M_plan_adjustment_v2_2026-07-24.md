# RAVEN-M plan adjustment v2

Date: 2026-07-24

This addendum changes research emphasis and execution order, not the frozen
protocol-v1 method or schedule.

## Refined research thesis

RAVEN-M studies whether a GUI agent should separate the information utility of
memory from its authority to justify an action.  The central mechanism is
**Selective-Trust Memory Routing**:

> Relevant memory may help reasoning, but only sufficiently verified and
> currently valid memory may justify acting.

The system name remains RAVEN-M.  Planner, Executor, Memory, Critic, Working
Memory, Verified Episodic Ledger, Failure and Recovery Memory, and Page-State
Index are the implementation carrier, not separate novelty claims.

## Evidence hierarchy

1. **Mechanism:** M0 versus MREL tests reliability-aware routing against
   relevance-only routing.
2. **System outcome:** M0 versus B3 tests the full method against ordinary
   summary memory; M0 versus B0 is secondary.
3. **Compute fairness:** B3_CTX and B3_CALL test whether gains are explained
   only by more context or model calls.
4. **Mechanism localization:** MNO_WM, MNO_VEL, MNO_FRM, MNO_PSI and
   MNO_CRITIC identify which failure modes each component affects.
5. **Process evidence:** stale or contradictory memory use, memory-induced
   error, loop, recovery and premature completion explain success-rate
   changes.

RQ3 from the master plan becomes the central mechanism question.  RQ1 remains
the primary system-level outcome question; RQ4 remains the fairness gate.

## Additional exploratory analysis

Existing decision-time routes, verification states, memory citations and
screenshots may support a post-freeze exploratory
`decision_authority_violation_rate`: the proportion of memory-citing
decisions in which an unverified, expired, contradicted or non-FACT item is
used as direct action justification without current-screen verification.

This metric is explicitly post hoc.  It cannot replace preregistered primary
metrics or be presented as confirmatory evidence.

## Relationship to prior OrthKD work

The two earlier OrthKD projects provide the research motivation: a source can
contain complementary information without being reliable enough to control
the final decision.  The GUI project transfers that reliability question to
episodic memory.  This connection belongs in motivation and discussion; it is
not evidence that GUI selective-trust routing is automatically novel.

## Execution order

1. Apply and validate protocol-v1 hotfix-001 for aggregation only.
2. Resume and complete the 95-cell breadth phase; do not auto-start later
   phases.
3. Audit breadth completeness, pairing, infrastructure and realized runtime.
4. Continue the remaining frozen phase order only after manual review:
   confirmatory additional (114), strict control (19), ablation and budget
   controls (136).
5. Organize the report as selective trust, overall effect, compute controls,
   component mechanisms, and success/failure cases.

No Hard observation may change prompts, thresholds, task selection, budgets or
the confirmatory claim definitions.
