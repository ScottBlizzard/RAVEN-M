# Protocol-v2.2 r57 local validation

Date: 2026-07-31  
Decision: **passed locally; only zero-call preflight authorized**

## Candidate

- Source:
  `4667166b60710f32348ace47243e41bcc041cd13`
- Tag: `protocol-v2-2-r57-local-candidate`
- Parent formal evidence:
  `reports/protocol_v2_2_r56_gate_f_batch1_stopped.json`
- Parent checkpoint SHA-256:
  `c095b69e550c66c01fa5e75c5cc1aa29cce1d26868001716590868611297cda6`

r57 does not alter the r56 result. It adds a protocol-v2.2-only contract for
finite repeated taps that TASK explicitly requires.

## Contract

The fourth or later exact-coordinate tap can cross the generic ceiling only
when TASK supplies a finite count from two to twenty, the proposed ordinal
does not exceed it, the coordinate binds to exactly one labelled and safe
visible control, and every earlier exact-coordinate tap changed the semantic
screen.

The override is unavailable for a long-press, swipe, unlabelled or ambiguous
target, editable target, System UI, keyboard, commit-like control, no-effect
streak, A-B cycle, blocked fingerprint, visible failure, or count overflow.
The guard independently checks that the assessment's streak counters match
its own state.

## Results

- Full local suite: **423/423 passed**.
- Python `compileall`: passed.
- `git diff --check`: passed.
- Protocol-v1 breadth seal: **197/197**, zero failures.
- The exact r56 H01 fourth-tap controller shape passed without a repair.
- Fourth and fifth taps were accepted; a sixth tap was rejected.
- No-count, no-effect, commit-target, ambiguous-target, count-exceeded, and
  A-B-cycle denials passed.
- A generic semantic-changing fourth tap without the task assessment remains
  blocked.
- The candidate manifest preserves r56's six Hard families, twelve-cell
  schedule, seeds, budgets, prompts, schemas, acceptance thresholds, and stop
  policy.
- The stopped r56 checkpoint remained byte-identical.

## Boundary

This is code-level evidence, not a live H01 result. It authorizes a fresh
zero-model-call preflight only. The preflight must verify exact candidate
hashes, source tag, parent Gate-E evidence, all frozen Hard instances, model
identity, emulator health, protocol-v1 seal, and an absent candidate
namespace.

The preflight cannot start a model call. If it passes, one separately isolated
H01 B3 development smoke may be considered. That smoke is explicitly
non-scored and cannot resume r56 or authorize formal Gate F.
