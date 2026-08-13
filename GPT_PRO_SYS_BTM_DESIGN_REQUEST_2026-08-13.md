# SYS-BTM Request: Budgeted Trajectory Progress Monitor

Design one zero-extra-call prospective system testing whether a deterministic,
task-agnostic trajectory monitor helps the executor allocate its native action
budget. This is a monitor, not a planner, verifier, critic, or memory narrator.

Allowed: RGB transition statistics, canonical executed-action recurrence, and
the current native step count; a fixed short monitor string in the next ordinary
executor prompt; bounded episode-local state. Auxiliary generation calls = 0.

Excluded: semantic success probability, next-action recommendation, task
progress percentage, action blocking/override, forced termination, free-text A1
history, hidden UI/evaluator/future frame, task rules, donor, or extra calls.
Shorter reward-zero failures are not a success.

Freeze state/schema, equivalence thresholds, progress/stagnation categories,
render text, caps, reset/expiry, CPU/token budgets, and anti-leak invariants.
Compare Full with an identical-history empty-monitor arm and a monitor-without-
budget-signal ablation. A productive event requires monitor exposure, a next
action divergence, visible progress, and no immediate relapse. Because there
are no extra calls, full-suite calls/tokens/wall must beat A1 for a cost pass.

Use the common 4/4 -> Recipe -> remaining-14 schedule. Accuracy >5/19, no A1-five
loss, cost, and mechanism evidence are independent gates.

Return only
`GPT_PRO_SYS_BTM_BUDGETED_TRAJECTORY_MONITOR_DESIGN_2026-08-13.md`, with a
commit-pinned audit, one frozen monitor, algorithms and exact renderer,
integration map, replay/preflight/tests, ablations, prospective protocol,
verdict schema, and falsification criteria. No code or GPU.
