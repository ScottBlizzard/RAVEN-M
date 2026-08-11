# GPT Pro Design Request: A Standalone Memory Arm That Beats A0 and A1

## Assignment

Design the next RAVEN-M AndroidWorld Hard memory arm. The research objective is
a **standalone memory mechanism** that preserves every known A0 capability and
exceeds the best existing arm, A1, under the same execution contract.

This is an optimization target, not a result that may be assumed in advance.
Do not claim guaranteed superiority. Produce the most defensible mechanism,
failure theory, implementation specification and prospective test plan that
could plausibly achieve it.

## Read first

1. `HANDOFF_2026-08-11.md` — full project history and A0–A7 ledger.
2. `HANDOFF_2026-08-12.md` — current delta and next campaign.
3. `protocols/A345_FAILURE_FORENSICS_AND_SUCCESSOR_CONSTRAINTS_2026-08-11.md`.
4. `evidence/a678/A7_TRANSPARENT_19_TASK_CONTROL.json`.
5. `evidence/a678/A8_V2_OFFLINE_TRACE_AUDIT_2026-08-11.json` and
   `protocols/A8_EXACT_REVISIT_FAILURE_AWARE_V2_DESIGN_2026-08-11.md`.
6. `evidence/a678/A9_ZERO_GENERATION_DESIGN_EVIDENCE_2026-08-11.json` and
   `protocols/A9_SPARSE_RECURRENCE_CANARY_PREREG_2026-08-11.md`.
7. `evidence/a678/A89_INITIAL_GATE_RESULTS_2026-08-12.json`.
8. The implementations and tests under
   `implementation/src/raven_m/official_qwen_mobile/` and
   `implementation/tests/official_qwen_mobile/`.

## Existing empirical ledger

The primary paired comparison uses AndroidWorld Hard task seed `20260806`:

| Arm | Mechanism | Valid scope | Success |
|---|---|---:|---:|
| A0 | No added memory | 19/19 | 4/19, reward 4.5 |
| A1 | Action working memory | 19/19 | 5/19, reward 5.5 |
| A2 | Verified-progress memory | 19/19 | 0/19 |
| A3 | ConAct-style folded context | first gate task | 0 |
| A4 | Frozen donor workflow memory | first gate task | 0 |
| A5 | Visual-symbolic graph | first gate task | 0 |
| A6 | Short transition episodic buffer | 19/19 | 0/19 |
| A7 | Goal-item ledger, transparently stitched | 19/19 | 4/19, reward 4.0 |
| A8-v2 | Failure-aware exact revisit | initial gate | 0/1 |
| A9 | Sparse recurrence canary | initial gate | 1/2 |

The dominant failure pattern is not lack of memory activation. It is memory
that repeats low-value history, arrives at the wrong time, amplifies an already
bad local policy, or describes failure without inducing a productive strategy
change. A6 roughly doubled actions and tokens relative to A0 while losing all
four A0 successes. In A8-v2 Expense, 14 nonempty reads coincided with a
max-step scrolling loop. A9 preserved Expense while silent, then failed Retro
after sparse recurrence activations.

## Non-negotiable experimental contract

The new arm must be directly comparable to A0–A9:

- Same Qwen3-VL-32B-Instruct revision, vLLM BF16 backend and sampling:
  generation seed `3407`, temperature `0.7`, top-p `0.8`, top-k `20`, presence
  penalty `1.5`, repetition penalty `1.0`, max tokens `32768`.
- Same 19 AndroidWorld Hard instances at task seed `20260806`, same evaluator,
  native step limits, official system prompt and current-screenshot observation.
- Exactly one controller-authored memory mechanism using the existing
  `read(context)` / `observe_step(...)` interface.
- Zero additional model calls. No second planner, critic, verifier, retrieval
  model, tool model or summarization model.
- No hidden accessibility/UI-tree evidence, evaluator reward, task ground truth
  or future information in decisions.
- No action-blocking guard, action override or forced termination.
- Memory may use only model-visible RGB, the task query, executed canonical
  actions and policy-authored action summaries allowed by the controller.
- Bounded state and bounded rendered text with explicit capacities and eviction.

This permits a sophisticated deterministic memory algorithm inside the one
memory component: state abstraction, selective consolidation, novelty or
uncertainty scoring, event-triggered read, counterfactual action bookkeeping,
hierarchical records, decay and retrieval ranking.

## Required performance gates

1. **Capability preservation:** all four A0-success tasks must pass, 4/4, in a
   fresh fail-fast gate before any other task is released.
2. **Full benchmark superiority:** after release, at least 6/19 successes and
   reward sum greater than 5.5 are required to beat A1's primary result.
3. **No hidden crutch:** zero extra calls, guards and overrides in every audit.
4. **Mechanism evidence:** at least one successful episode must contain a
   nonempty memory read with a trace-grounded causal hypothesis. Pure silence
   that only reproduces A0 is insufficient.
5. **Efficiency report:** calls, actions, prompt tokens and wall time versus A0
   and A1. Success is primary, but context inflation must be visible.

## Questions the design must answer

1. What exact information was missing when A0/A1 failed, and why can it be
   derived from allowed observations?
2. Why did A2–A9 fail to convert memory into better actions?
3. What are the formal state, update rule, retrieval score and rendering format?
   Give pseudocode precise enough to implement without interpretation.
4. How does it remain silent on competent trajectories but provide useful
   information before a costly loop?
5. What causes a record to be trusted, revised, decayed or evicted?
6. How does it preserve action diversity without becoming a forbidden guard or
   planner?
7. What are the leakage, boundedness and false-positive risks?
8. Which offline replay and adversarial unit tests must pass before generation?
9. What evidence would falsify the mechanism hypothesis even if score improves?

## Required deliverable

Return one primary mechanism, not a menu of vague alternatives. Include:

- Name and one-sentence causal thesis.
- Evidence-based diagnosis tied to repository traces.
- Formal state schema and deterministic write/update/read algorithms.
- Exact injection text template and maximum rendered length.
- Capacity and eviction table.
- Integration pseudocode for the existing controller interface.
- Unit-test matrix, offline replay plan and leakage audit.
- Four-task gate protocol and full-19 release rule.
- Expected gains, likely failure modes and falsification criteria.
- A comparison explaining why it differs materially from A1, A2, A6, A7,
  A8-v2 and A9.

Do not relax the benchmark, change prompts, add a second agent component,
increase step limits, cherry-pick a seed, or relabel diagnostic results.
