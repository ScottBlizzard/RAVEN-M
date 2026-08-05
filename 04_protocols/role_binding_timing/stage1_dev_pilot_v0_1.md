# Correct Memory, Wrong Target — Stage-1 DEV pilot v0.1

## Status and purpose

This is a development screening experiment, not a held-out or confirmatory study.
It reuses AndroidWorld screenshots that were inspected during Phase A. Its only
purpose is to determine whether the Timing × Role-Ambiguity mechanism is worth
testing on a newly collected corpus.

## Frozen question

With the same correct source fact, screenshot, model, decoding, call count and
action budget, does exposing the fact before destination grounding increase the
first wrong-target rate more under high than low source/destination ambiguity?

## Design

- Eight base templates built from three existing AndroidWorld screenshots.
- Four cells per template: early-low, late-low, early-high, late-high.
- Two model calls per cell: destination grounding, then first target-bearing
  action. No live Android action is executed.
- The same screenshot is used for all four cells of a base template.
- High/low variants keep the destination fixed and change only which visible
  item supplies the correct fact: a role-similar source versus a visibly
  dissimilar source.
- The fact occurs exactly once in the logical two-phase transcript. The other
  phase receives a token-matched neutral block.
- Model: Qwen/Qwen3-VL-32B-Instruct, revision
  `0cfaf48183f594c314753d30a4c4974bc75f3ccb`, temperature 0, 128-token cap.
- No output repair, semantic retry, prompt tuning, or selective rerun.
  Idempotent transport retry is allowed only for connection timeout/failure.

## Outcomes

Primary: `WrongTarget@FirstTargetingAction`.

Diagnostics: destination grounding, source-as-target, other wrong target,
post-grounding drift, exact value recall, strict JSON/schema failure, calls,
tokens and wall time.

## DEV qualification and continuation rule

The pilot is usable only if exact-value recall is at least 95%, strict parser
failure is below 5%, and low-ambiguity target accuracy exceeds 80%.

A signal worth expanding requires:

- high-ambiguity early-minus-late wrong-target difference at least 15 points;
- absolute low-ambiguity early-minus-late difference at most 5 points;
- positive Timing × Ambiguity difference-in-differences;
- at least one mechanism diagnostic (source-as-target or grounding drift) moves
  in the predicted direction.

Because the screenshots and task constructions are DEV-contaminated and only
eight templates are used, passing this screen is not evidence for a paper claim.
It only authorizes position/recency/role-swap controls followed by a fresh
held-out Stage 1. Failure stops method development and redirects the project to
grounding/controller diagnosis.

