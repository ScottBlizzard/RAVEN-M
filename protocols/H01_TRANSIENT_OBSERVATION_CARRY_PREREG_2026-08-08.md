# H01 transient-observation carry: frozen diagnostic preregistration

Status: frozen before implementation and before any rescue-model call.

## Evidence that motivates this test

In the frozen official Qwen3-VL-32B H01 run
`official_qwen_20260808T004327_dcaa8b3a`, the visual agent correctly exposed the
five transient values `1, 8, 10, 7, 2` on screen.  L0--L4 records show valid
model calls, parsing, coordinate mapping, action execution, and page changes.
The official action-only history retained only variants of "clicked Click Me",
not the values.  The model later invented `3, 4, 5, 6, 7`, entered `2520`, and
declared success; the hidden AndroidWorld evaluator returned 0.  The correct
product was `1120`.

## Causal hypothesis

For H01, the earliest task-relevant failure is loss of transient visual values
at the history-compression boundary, rather than perception of the current
screen, coordinate conversion, or action execution.  Requiring the model to
carry exact transient observations in its existing one-line `Action` summary
should preserve those values without adding a model call, hidden UI input,
external OCR, or controller-written task memory.

## Single intervention

Append the following two rules to the otherwise unchanged official system
prompt:

1. If the current screenshot contains a task-relevant value or label that will
   disappear after the next action, copy it exactly into the `Action` sentence.
2. Use `Remember: <exact observation>; <imperative action>` for such a step, so
   the official action-history mechanism carries the observation forward.

The controller continues to store only the model's own `Action` summaries.
The model still sees only the current screenshot plus text history.  No audit UI
tree, evaluator state, prior screenshot, extra model call, retry, parser repair,
or task-specific correct answer is exposed.

## Frozen comparison

- Task instance: H01, seed 20260806, unchanged frozen manifest.
- Model/revision/runtime: unchanged Qwen3-VL-32B-Instruct revision
  `0cfaf48183f594c314753d30a4c4974bc75f3ccb`, vLLM BF16.
- Sampling: temperature 0.7, top-p 0.8, top-k 20, presence penalty 1.5,
  repetition penalty 1.0, generation seed 3407.
- Call budget and native action limit: unchanged.
- Baseline comparator: `official_qwen_20260808T004327_dcaa8b3a`.
- Scientific status: post-hoc causal diagnostic, never pristine held-out.

## Frozen outcomes and decision rule

Primary mechanistic outcomes:

1. Each of the five observed values appears correctly in subsequent textual
   history before multiplication.
2. The entered product is `1120`.
3. The AndroidWorld evaluator returns success.

Interpretation:

- All three pass: evidence that the history-compression boundary caused the H01
  failure and that observation-carry is a sufficient minimal rescue on this
  instance.
- Values are preserved but product/evaluator fails: memory boundary repaired,
  later planning, arithmetic, grounding, or completion remains causal.
- Values are not preserved: this prompt-level mechanism is insufficient; do not
  tune it on H01 and relabel a later run held-out.

## Stopping and contamination rules

Run one frozen rescue episode.  Do not edit the prompt after observing its
output and rerun it as confirmatory.  Any subsequent variant is exploratory and
must use a separately frozen document and a distinct run-stage label.
