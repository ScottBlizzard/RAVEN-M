# C0 Native MobileUse — frozen protocol before GPU

## Question

How well does the released MobileUse MultiAgent controller work on the required
Qwen3-VL-32B and the same 19 AndroidWorld Hard instances, before adding any new
RAVEN-M memory mechanism?

## Scientific boundary

- C0 restores MobileUse's released six-role schedule, prompts, coordinate
  conversion, action space, transient trajectory/progress, and optional native
  `take_note` action.
- C0 adds **no new RAVEN-M retrieval, persistent memory, structured memory, or
  task-specific rule**. C1 is the first arm allowed to add one.
- PF01 and B2 remain frozen historical adaptations. C0 does not overwrite them.
- Model, model revision, decoding, task instances, evaluator, seed, and logging
  backend are locked. MobileUse's documented 1.2 step multiplier is applied to
  every arm from C0 onward and is reported explicitly.

## Fixed task order

`H08, H12, H05, H14, H04, H16, H19, H13, H18, H06, H03, H11, H02, H10, H15, H09, H17, H01, H07`

The order is diagnostic, not a changed sample: all 19 frozen instances are
still run. H08 checks end-to-end health; H12 checks long-press and prior parser
crash containment; H05 checks Markor reset/clear-text; H14 checks a long trace;
H04/H16/H19 are known Qwen baseline successes. C1 must reuse this order.

## State isolation

The task/evaluator source remains AndroidWorld commit
`3e50888527ef9f29b9157ecd537e408008bb1c85`. The documented MobileUse reset for
Audio Recorder, Camera, Tasks, Markor, Simple Calendar Pro, and Chrome is
inserted at the same lifecycle location as the MadeAgents fork: after snapshot
restore and before task-specific seeded state is created. Every episode writes
`reset_audit.json`.

## Qualification and stopping

- Reward 0, wrong clicks, early model termination, or ordinary model mistakes
  are scientifically valid outcomes: record them and continue.
- Missing resets, action-mapping failures, parser/program crashes, model-server
  faults, evaluator lifecycle faults, or broken log hash chains invalidate the
  suite. Stop immediately, fix only the generic problem offline, and restart
  the full order from H08. The invalid prefix is not a held-out result.
- No task-specific prompt/rule may be added after seeing a C0 outcome.
- One seed only (`20260806`). Additional seeds are optional later validation,
  never a replacement for this paired seed.

## Evidence

Each episode preserves every model request/response by role, parsed action,
physical action, screenshots, audit-only UI tree, package transition, progress
and reflection outputs, evaluator reward, reset audit, mechanism metrics, and a
hash-chained event log. The aggregate is rewritten after every task so an
interruption cannot erase completed evidence.

