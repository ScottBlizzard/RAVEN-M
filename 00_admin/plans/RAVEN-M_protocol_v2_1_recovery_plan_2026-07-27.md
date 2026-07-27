# RAVEN-M protocol-v2.1 recovery plan

Date: 2026-07-27
Trigger: Gate-F v2 batch 1 completed 4/4 valid cells but 0/4 successes and
exposed semantic false-progress loops.

## Decision

Do not run v2 Gate-F batch 2. The v2 checkpoint remains immutable diagnostic
evidence. Repair generic enforcement, requalify without GPU, then restart
every experimental gate under protocol v2.1.

## Work package 1: controller enforcement

- Normalize visible accessibility elements into a stable semantic digest.
- Exclude hidden nodes, system UI, coordinates, clocks, and transient
  validation overlays from progress.
- Retain newly visible validation messages as separate evidence.
- Detect same-action semantic no-progress and semantic A-B-A-B cycles.
- Require a different recovery action after a block.
- Preserve legitimate repeated actions when visible task content changes.

## Work package 2: reliable failure memory

- Convert newly visible validation messages into observed FAILURE records.
- Attach action and screenshot provenance.
- Route them as ALERT and trigger the Critic.
- Expire them after semantic page change or verified recovery.
- Apply the same deterministic action block to B3 and M0.

## Work package 3: startup accounting

- Persist environment-construction failures before any cell.
- Permit one cold recovery with smoke verification.
- Stop after a second same-phase failure.
- Include startup attempts in future Gate-E/F summaries.

## Gate D

No experimental model cells.

Required:

- full local tests pass;
- protocol-v1 seal is 197/197;
- task/action audit is 19/19;
- live answer/reset smoke passes three isolation cycles;
- live semantic UI smoke uses accessibility rather than screenshot fallback;
- all semantic source files are committed and tagged;
- old Gate-F batch 2 remains absent.

## Gate E v2.1

Restart the same eight non-Hard B3/M0 cells with:

- a new suite ID and protocol ID;
- the same task seed and paired instances unless preregistered otherwise;
- startup recovery accounting;
- semantic-progress and visible-failure audit fields;
- no automatic Gate-F transition.

Any semantic failure requires another Gate-D requalification and a complete
Gate-E restart.

## Gate F v2.1

Only after Gate E passes:

- restart all twelve cells from batch 1;
- keep the same six-task subset, seed, blocked order, limits, and acceptance
  thresholds so the repair does not exploit observed task outcomes;
- never mix v2 and v2.1 cells;
- inspect each four-cell checkpoint before authorizing the next.

## Stop conditions

Stop after an atomic cell for:

- invalid output after one repair;
- unresolved semantic-progress block;
- visible failure followed by the same blocked action after repair;
- provenance, memory, evaluator-leakage, context, pairing, or reset error;
- two startup/in-cell infrastructure failures of the same class;
- projected active time above the frozen cap.
