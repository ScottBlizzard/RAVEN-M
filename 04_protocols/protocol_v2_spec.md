# AndroidWorld protocol v2 exploratory specification

Status: implementation candidate; no GPU experiment authorized  
Protocol ID: `androidworld_protocol_v2_exploratory`  
Branch: `protocol-v2-exploratory`

## Scope and separation

Protocol v1 remains a sealed diagnostic pilot. Its raw episodes, scored
results, schedule, amendments, and checksums are immutable. Protocol-v2
artifacts must use `runs/protocol_v2/` and must never be pooled statistically
with v1.

## Semantic corrections

1. The canonical action language includes AndroidWorld's terminal `answer`
   action. An answer is executable only with `status=done` and only for an
   information-return goal. The controller executes it before evaluation so
   that `env.interaction_cache` contains the submitted text.
2. `type_text` and `answer` declare `text_origin` and
   `source_memory_ids`. Permitted origins are task literal, current screen,
   verified memory, and deterministic calculation. Verified-memory text must
   cite routed memory; other origins must not claim memory provenance.
3. A page/action fingerprint that produces no screenshot change twice is
   blocked. A repaired decision must choose a materially different recovery
   action.
4. M0 and MREL no longer require completion evidence to survive a delayed
   memory-routing turn. A completion candidate may use direct current-screen
   evidence or a routed FACT and is adjudicated by the Critic in the same
   turn. Critic failure or rejection fails closed and consumes the ordinary
   model-call budget.

## Completion semantics

- Mutation tasks: execute the persistence action, observe the result, then
  return `done` with direct-screen or verified-memory evidence.
- Information-return tasks: read or deterministically compute the requested
  value, return `done` with an `answer` action, and execute that action before
  the benchmark evaluator runs.
- `fail`: action is null and no completion evidence is allowed.
- The native AndroidWorld evaluator remains hidden until the episode ends and
  is the only source of task success.

## Audit and budget rules

Every selected task must pass the capability audit across task requirement,
schema, prompt, adapter, and controller terminal semantics. All Executor,
repair, Planner, Critic, and summarizer calls count against the frozen episode
model-call budget. Same-turn completion Critic calls are logged as history
calls. No per-task coordinates, macros, evaluator hints, or result-dependent
budget changes are allowed.

## Gates

Gate D (this implementation round) requires:

- v1 checksum seal reproduces;
- 19/19 task capability rows pass;
- schemas accept and reject the intended v2 forms;
- adapter and controller execute answer correctly;
- provenance, loop, and completion-adjudication tests pass;
- the full local test suite passes;
- no GPU suite has been started.

Passing Gate D permits preparation of an eight-cell non-Hard capability gate;
it does not authorize that gate to run.
