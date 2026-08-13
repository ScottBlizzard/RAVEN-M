# SYS-CAA Request: Candidate Action Arbitration

Design one prospective system testing whether limited candidate generation and
independent arbitration improves frozen high-uncertainty decisions over the
official controller's single action. This is not planning, memory, or criticism.

Allowed: the executor's primary proposal; a deterministic uncertainty trigger;
one same-model call generating at most three valid candidates; one separate
same-model arbiter choosing exactly one existing candidate. Default maximum is
three triggered decisions per episode, six auxiliary calls total.

Excluded: future transitions, rewriting or inventing a fourth action, plan or
trajectory summary, post-outcome critique, donor retrieval, hidden UI/evaluator,
task whitelist, free retry, or increased native decision/action budget. Every
proposal and arbitration event counts; rejected primary proposals do not earn a
free decision slot.

Freeze uncertainty evidence, candidate prompt/schema, legality filtering,
arbiter prompt, tie/invalid handling, caps, and transport policy. Compare Full
with `ARBITER-SHADOW`, executing the primary despite identical auxiliary calls,
and an `always-primary` mechanism ablation. Attribute only non-primary choices
that lead to visible progress within three steps and a Full-over-control paired
outcome. Separate any engineering legality-filter benefit from arbitration.

Use the common staged gates and independent accuracy/cost/mechanism verdicts.
All calls, tokens, actions, latency, candidate sets, choices, and outcomes must
be auditable.

Return only
`GPT_PRO_SYS_CAA_CANDIDATE_ACTION_ARBITRATION_DESIGN_2026-08-13.md`, containing
one frozen design, exact contracts/prompts/budgets, implementation blueprint,
offline tests, compute-matched controls, prospective protocol, verdicts, and
falsification rules. No implementation or GPU run.
