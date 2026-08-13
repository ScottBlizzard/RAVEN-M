# Request: A1 Vertical Minimal-Memory Design

This request is intended for a fresh GPT Pro conversation. Supply the exact Git
commit to audit in the accompanying conversation.

## Objective

Audit the pinned repository before proposing one new prospective memory arm
that vertically improves A1. Preserve A1's smallest plausible causal benefit --
explicit bookkeeping for still-unconfirmed operations -- while removing stale
reinforcement, duplicated context, and unnecessary cost. Do not modify or
rename frozen A1.

## Empirical starting point

On the same 19 AndroidWorld Hard instances and task seed `20260806`:

- A0: 4/19, reward 4.5, 329 calls, 1,273,361 tokens, 6,541.82 s.
- A1: 5/19, reward 5.5, 603 calls, 3,464,267 tokens, 14,595.49 s.
- A1 versus A0: one gain, zero losses, 18 ties; calls +83.3%, tokens
  +172.1%, elapsed time +123.1%.
- A1's unique gain is `RecipeDeleteMultipleRecipesWithConstraint`.
- A1 wrote memory 515 times and made 580 non-empty reads across 19 episodes.
- Its `MEMORY[...]` payload remained in ordinary history and was reinjected,
  duplicating context. Stale pending records stabilized several wrong loops.

A10-v2 and A11 failed formal offline replay. A12 is formally
`A12_PROTOCOL_INVALID`. The enriched six-task study is post-hoc and non-held-out.
The completed A10-v2 diagnostic had six reads across three episodes but zero
productive-divergence signals; both successful episodes were memory-silent.
These are design warnings, not successful priors.

## Runtime boundary

The only intervention may be one deterministic, episode-local memory path
embedded in the existing official Qwen mobile controller. Keep the same model,
revision, controller semantics, screenshot input, action schema, task instances,
seeds, sampling configuration, and native step budgets.

Forbidden: planner, critic, verifier, RAG, retriever, additional agent, extra
model call, extra screenshot, OCR, hidden UI tree, activity/package metadata,
evaluator access, future information, database, cross-episode donor, task/app
whitelist, training, action override, action blocking, guard, forced termination,
or increased step budget.

Allowed inputs are the goal, the model's own past text and actions, model-visible
RGB screenshots, and deterministic statistics derived from visible transitions.
Current RGB always overrides memory. Memory may affect behavior only through
context in the next ordinary model request.

Ordinary action history must preserve its non-memory semantics, but the same
structured memory must not exist both in history and in the memory block. Freeze
an exact deduplication rule.

## Design discipline

Return one final mechanism, not a menu. Every state field, threshold, trigger,
and cache must answer a documented A1 failure and be rejected if a simpler rule
suffices. More state is not evidence of rigor.

Freeze upper bounds for per-read characters, UTF-8 bytes and model tokens;
episode injection budget; maximum non-empty reads; cooldown; expiry; resident
storage; CPU latency; and zero additional model calls. Derive the numbers from
trace distributions before live generation.

Separate three evidence layers:

1. implementation: write provenance -> exact later read -> exact injected text;
2. behavior: next action divergence -> visible escape/progress within three or
   four steps -> short-term relapse check;
3. outcome: final AndroidWorld evaluator reward.

Activation alone is not effectiveness. A successful episode with no read is
unattributed. Include a minimal no-read/empty-read ablation or matched-trace
counterfactual that adds no runtime component and uses no future information.

## Prospective gates

The first live gate is fixed and ordered:

1. `ExpenseDeleteMultiple2`
2. `RetroSavePlaylist`
3. `SimpleCalendarAddOneEvent`
4. `SportsTrackerTotalDurationForCategoryThisWeek`

It must score 4/4. A scientific failure stops the arm; only a recorded
infrastructure-invalid attempt may be replaced on the same task.

Next run `RecipeDeleteMultipleRecipesWithConstraint` as an A1-gain retention
gate. Only after retaining that fifth success may the remaining 14 tasks run.

Report independent conclusions:

- accuracy pass: more than 5/19 full successes, reward greater than 5.5, and no
  paired loss on A1's five successful tasks;
- cost pass: full-suite calls, tokens, and elapsed time all below A1;
- mechanism pass: a preregistered number of trace-grounded productive reads.

Matching 5/19 at lower cost is a Pareto/cost improvement, not an accuracy gain.
All 19 tasks at this seed have been observed; call the result a matched
prospective paired diagnostic, never pristine held-out generalization.

## Required audit sources

Start with `HANDOFF_2026-08-13.md`, then inspect A0/A1 summaries, A1 protocol and
implementation, A2 replay analysis, A10-v2/A11/A12 design and formal replay
artifacts, and `protocols/ENRICHED_MEMORY_DIAGNOSTIC6_PROTOCOL_2026-08-13.md`.
Cite exact paths and distinguish committed evidence, local provisional status,
inference, and unknowns.

## Required output

Do not modify the repository or run GPU experiments. Your response must be only
one self-contained Markdown document named:

`GPT_PRO_A1_VERTICAL_MINIMAL_MEMORY_DESIGN_2026-08-13.md`

It must contain the commit-pinned evidence audit; retained/deleted A1 causal
kernel; one chosen mechanism; exact schema and lifecycle; write/update/read/
merge/forget/expiry rules; all constants; fixed renderer and injected prompt;
pseudocode; cost bounds; minimal integration blueprint; invariants and
fail-closed rules; source/evidence freeze; tests; zero-generation replay and
preflight; fixed run order and resume policy; failure taxonomy; accuracy/cost/
mechanism verdicts; ablation and attribution table; and explicit falsification
conditions. It may conclude `NO-GO` if evidence cannot support a valid arm.
