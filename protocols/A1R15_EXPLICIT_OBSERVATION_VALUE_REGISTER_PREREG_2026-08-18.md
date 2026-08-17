# A1-R15 Explicit Observation Value Register — Prospective Preregistration

## Status and evidence boundary

A1-R15 is a new prospective pure-memory identity. Its parent evidence commit is
`b62839a38f4ae2fc000b0e4a0562a59032e60c5b`, which sealed A1-R14 as a valid
target failure with one accepted value (`7`) but no mature read. A1-R14 and all
earlier arms remain immutable.

The A1-R14 live trace is development evidence, not held-out confirmation. It
showed that four genuine observations used two narrowly different English
forms: `number N displayed` and `current number displayed is N`. A1-R15 adds
only those syntactic forms to A1-R14's grammar. It does not accept arbitrary
numbers, arithmetic guesses, lists, OCR, screen text, task names, evaluator
state, hidden UI state, or future observations.

## Frozen identity

- Mechanism: `a1r15_explicit_observation_value_register_v1`
- Experiment: `A1R15_EOVR_QWEN3VL32B_AW_HARD_S20260806_G3407_V1`
- Task seed: `20260806`; generation seed: `3407`
- Model/revision/controller/sampling/native budgets: exact A1-R14 boundary
- Runtime intervention: one episode-local deterministic memory path; zero
  extra model calls, action overrides, guards, forced stops, or extra screenshots

## Frozen grammar delta

The response Thought must still contain a collection cue and exactly one value
matched by the union of A1-R14's patterns and these observed shapes:

1. `number <integer> displayed` (optional `is`, optional quote);
2. `current number displayed is <integer>`.

Matching is case-insensitive and bounded to signed 1–6 digit integers. Multiple
different matched values reject the entire response. In particular, the sealed
hallucination `Assuming the numbers were 2, 3, 5, 7, and 11` must remain rejected.
All TTL, capacity, renderer, current-screen-authoritative statement, history,
and controller behavior remain inherited from A1-R14/R13/R2.

## Zero-generation gate

The replay fixture is the sealed SYS-NAG-V4 19-task suite with BrowserMultiply
replaced by the sealed A1-R14 live target trace. Before live generation:

- exactly 19 unique tasks in frozen target-first order;
- only BrowserMultiply may activate;
- all six historical successes must have zero activation and zero render;
- BrowserMultiply must retain exactly `[1, 8, 10, 7, 2]`, with five response
  appends and an exact rendered five-value read;
- audit size must remain at most 128 KiB;
- source freeze, focused tests, config and replay must all pass with zero calls.

## Live gates and interpretation

Run BrowserMultiply first. It must reward `1`, activate once, append five
response values and deliver the exact five-value read. A valid failure stops the
identity and is not rerun. If it passes, run the six frozen R2 successes; all
must reward `1` and the added register must remain silent. Only then release the
remaining twelve tasks, without rerunning the first seven.

If five correct values are read but BrowserMultiply still fails, the result
refutes the sufficiency of passive factual memory for the arithmetic decision;
the next identity must add a separately named reasoning/calculation component,
not broaden the parser post hoc. If the register is incomplete, any future
grammar change requires a new identity. This same-seed experiment is a matched
prospective diagnostic, not a held-out generalization claim.
