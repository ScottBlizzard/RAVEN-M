# A3/A4/A5 public-memory-kernel preregistration (2026-08-11)

## Question and fixed comparison

On the same official Qwen3-VL-32B AndroidWorld Hard controller, do three
meaningfully different memory representations preserve known capability and
then improve the 19-task paired outcome?

All arms freeze the A0 model revision, vLLM BF16 backend, sampling parameters,
seed 3407, AndroidWorld task seed 20260806, APK/runtime/reset identity, current
screenshot input, official `mobile_use` action parser, native action budgets,
evaluator, and layered evidence.  No arm adds a planner model, critic, action
repair, guard, hidden UI input, evaluator input during decisions, or automatic
transport retry.  Memory is the only intended policy-side intervention.

## Arms and honest reproduction labels

- **A3** — `zero-shot ConAct adaptation on A0`.  The same policy response
  updates folded action history, folded UI state, and the recent step record.
  It does not use MemGUI-8B-SFT.  Source: MemGUI-Agent, arXiv:2606.19926,
  official commit `321734eaf9788c6a802f8f11e62651702d14af28`.
- **A4** — `AWM-style frozen donor-only procedural workflow memory on A0`.
  The bank must be induced before scoring from preregistered AndroidWorld
  Easy/Medium donor episodes with evaluator reward 1.  The 19 scored Hard
  tasks, their earlier A0/A1/A2 traces, exact task instances, answers, and
  evaluator feedback are forbidden bank inputs.  The bank is immutable during
  scoring.  Source: Agent Workflow Memory, ICML 2025, official commit
  `8c0ff8cd11d648c8fceb99e4e42f37e3b75381b1`.
- **A5** — `online in-trial visual transition graph memory (HyMEM-inspired)`.
  It couples policy-authored symbolic page/edge fields with a deterministic
  perceptual fingerprint of model-visible pixels.  It is explicitly not full
  HyMEM because there is no Q-Former, learned trajectory embedding, offline
  success bank, digestion model, or cross-task self-evolution.  Source basis:
  HyMEM arXiv:2603.10291, official commit
  `911722c99c8c3fa0052cbb1f596e13d691610ed5`.

These are three different memory categories: proactive in-trial working
context, frozen cross-task procedural memory, and an online visual-symbolic
transition graph.  Their overall-arm outcomes are comparable; differences are
not claimed to be a byte-level component ablation across the three formats.

## Qualification-first schedule

The following known A1-success tasks run first, in their original manifest
relative order:

1. `ExpenseDeleteMultiple2`
2. `RecipeDeleteMultipleRecipesWithConstraint`
3. `RetroSavePlaylist`
4. `SimpleCalendarAddOneEvent`
5. `SportsTrackerTotalDurationForCategoryThisWeek`

This is a post-hoc capability-preservation gate, not held-out accuracy
evidence. The required gate is the four tasks A0 previously solved; all four
must remain successful. The fifth A1-only success is run in the same prefix as
an observational development probe but is not required for expansion. Any
model format, reasoning, action,
termination, max-budget, or reward failure is a scientific failure: stop the
arm immediately, do not rerun it, and do not resume it.  Only an explicitly
logged infrastructure-invalid episode may be rerun from a clean reset.  Five
successes are required before the remaining 14 manifest tasks run in their
original relative order.

The first scored task must prove actual memory exposure.  A3/A5 require a
successful write followed by a later non-empty read in a captured request.  A4
requires a non-empty frozen workflow retrieval in a captured request.  Failure
stops before task 2.

## Frozen evidence and attribution

Every step stores full/reconstructable request text and hashes, current image
hash, response and usage, memory parse/read/write/retrieval with provenance,
history deduplication, proposed/mapped/executed action, physical coordinates,
before/after transition, L0-L5 layers, evaluator result, and transport count.
Every gain/loss receives a first-divergence trace review.  A non-empty read is
exposure, not by itself proof of causal benefit.

Primary outcomes: full success count/rate, paired gains/losses against A0/A1,
and gate result.  Secondary outcomes: calls, actions, tokens, elapsed time,
memory compliance/activation, repetition, termination, and failure layer.
One repeatedly observed seed is diagnostic only.  Any chosen best arm requires
a newly frozen seed before a generalization claim.

## No tuning and stopping

All three mechanisms, source locks, prompts, capacities, retrieval thresholds,
task order, gate, and stopping rules are frozen before the first generation.
Any code/prompt/threshold change creates a new version and restarts its gate
from task 1.  Failed gate observations may diagnose a later version but may not
be relabeled held-out.
