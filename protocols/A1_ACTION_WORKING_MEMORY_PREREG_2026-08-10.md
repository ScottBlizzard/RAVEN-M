# A1 Action Working Memory - frozen preregistration

Frozen before the first A1 model-generation call on 2026-08-10.

## Question

Does a minimal explicit within-episode working memory improve the official
Qwen3-VL-32B AndroidWorld Hard baseline when the model, task instances, action
protocol, observation, sampling, and action budgets are unchanged?

## A0 control

- Official Qwen3-VL mobile-agent controller and prompt port.
- Qwen3-VL-32B-Instruct revision
  `0cfaf48183f594c314753d30a4c4974bc75f3ccb`.
- Current screenshot only.
- The model's ordinary Action prose is retained as task-progress history.
- Frozen AndroidWorld Hard instances at task seed `20260806`.

## A1 intervention

A1 keeps every A0 component above. It adds one bounded, deterministic memory
path:

1. The system suffix asks the Executor to begin the Action sentence with a
   compact `MEMORY[observed=...; verified=...; pending=...]` payload.
2. After a successfully executed action, the controller stores that payload
   with step, model-call, response, and screenshot provenance.
3. Before the next model call, the six most recent unique payloads, capped at
   3000 characters, are injected as an explicit working-memory block.
4. The current screenshot is declared authoritative over stale memory.

The memory manager makes no model call. It cannot access the hidden UI tree,
AndroidWorld evaluator, database, or another episode. A1 therefore measures a
basic raw working-memory mechanism, not a planner, critic, repair policy,
structured verification method, or cross-task experience store.

## Fixed comparison

- 19 Hard task classes, exactly one seed: `20260806`.
- Same frozen task parameters, goal hashes, order, and native action budgets as
  the A0 first-seed records.
- Generation seed `3407`; temperature `0.7`; top-p `0.8`; top-k `20`;
  presence penalty `1.5`; repetition penalty `1.0`; max output tokens `32768`.
- No step-cap increase and no extra model calls.
- Primary endpoint: AndroidWorld task success rate, paired against A0 on the
  same 19 task/seed instances.
- Secondary endpoints: total reward, model calls, prompt/completion tokens,
  wall time, false-success claims, repeated-state/stagnation behavior, memory
  write compliance, memory read activation, and case-level benefit/harm.

## Qualification and stopping

- No GPU run is allowed until the zero-generation preflight passes.
- The first scored task is H01, preserving A0 manifest order. Before H02, its
  evidence must contain at least one successful memory write followed by a
  non-empty memory read. Failure of this implementation gate stops the suite;
  it is not a task-performance stopping rule.
- Controller, transport, action-execution, evaluator, reset, or teardown
  infrastructure errors stop the suite. The affected task may be rerun from
  its clean frozen state and the invalid attempt remains logged.
- Model parse errors, wrong actions, premature termination, max-step exits, and
  reward zero are scientific outcomes and are not rerun.
- A1 will not be changed after its first valid generation call. Any later
  modification receives a new method/version label and cannot be pooled with
  A1-v1.

## Interpretation boundary

A1 can show whether explicitly carrying raw task state helps. It cannot prove
that multi-agent summarization or reliable structured memory is effective.
Those are separate later arms. A negative A1 result remains useful because it
tests whether adding more remembered text alone is sufficient or instead
creates distraction/staleness.
