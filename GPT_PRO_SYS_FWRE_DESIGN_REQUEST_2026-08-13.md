# SYS-FWRE Request: Frozen Workflow Retrieval Executor

Design one prospective system testing whether independently sourced successful
workflows provide transferable action priors when retrieval and adaptation are
frozen before scoring. This must directly avoid A4's weak, direction-mismatched
donor injection.

Allowed: a hash-frozen donor bank built from a genuinely independent
Easy/Medium or training split; deterministic task-agnostic retrieval from goal
text and visible state; null retrieval; bounded executor adaptation. Retrieval
itself uses zero model calls. At most one same-model adapter call per episode may
be proposed only if strictly justified and compute-matched.

Excluded donor sources: the 19 scored Hard instances, their same-seed A0-A12
traces, target future data, or human selection using target outcomes. Also
excluded: exact target scripts, coordinate copying, task/app whitelist, online
bank updates, evaluator/hidden UI, future frame, and unlogged editing.

Freeze lawful acquisition/split, provenance and leakage hashes, abstraction,
query, relevance/conflict thresholds, null behavior, exact injection/adaptation,
caps, and invalidation. Include retrieval-withheld, relevance-matched wrong-
donor/random, and donor-source ablations. A donor success proves only its source;
mechanism attribution requires actual retrieval, traceable adapted actions, and
a Full-over-control paired gain without blind text/coordinate copying.

Use the common staged gates and separate accuracy, cost, leakage, and mechanism
verdicts. Do not claim held-out generalization on the observed Hard seed.

Return only
`GPT_PRO_SYS_FWRE_FROZEN_WORKFLOW_RETRIEVAL_EXECUTOR_DESIGN_2026-08-13.md`, with
one frozen design, donor governance, exact schemas/algorithm/prompt, leakage
tests, integration, replay/preflight, controls, prospective protocol, verdicts,
and falsification rules. No repository modification or GPU work.
