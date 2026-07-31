# Protocol v2.2 r61 Local Validation

## Decision

**PASS locally; online preflight pending.** The generic delayed-transition
candidate is frozen at commit
`baa398babf9707f32eb94d1287e5bc2d728a84bb` and tag
`protocol-v2-2-r61-local-candidate`. This report does not authorize a live
smoke or a formal Gate-F run.

## What r61 changes

r60's valid scored H17 failure showed that a UI transition can complete after
the immediate post-action audit. A sub-one-percent visual change was accepted
with the previous accessibility tree, so a false no-progress critic constraint
survived onto the Search screen and routed the policy into Markers.

r61 gives protocol v2.2 a bounded three-observation post-action settle window.
If the transition still lands only between steps, the controller reconciles it
before the next prompt: it corrects the previous outcome, invalidates only
same-page memory, clears only a critic constraint created from the
just-contradicted step, and corrects the provisional no-effect count. An
already-blocked loop fingerprint remains blocked.

The mechanism contains no H17 task name, OpenTracks package, answer, target
date, evaluator parameter, label, or coordinate special case.

## Validation result

- Complete project tests: **467/467**
- Protocol-v1 breadth seal: **197/197**, zero failures, not rewritten
- Python compilation: passed
- `git diff --check`: passed
- Historical r60 execution package and formal stop: reproduced from their
  immutable tags
- Real model calls during local validation: **0**
- GPU experiment cells during local validation: **0**

Replay-shaped tests cover a sub-threshold transition inside the settle window,
a transition that completes after that window, stale critic expiration,
same-page memory invalidation, and preservation of an already-blocked loop
fingerprint.

## Current online boundary

The Android emulator remains connected as `device`. The server route was not
healthy at the end of local validation: an independent SSH probe to
`10.10.217.244:22` timed out after ten seconds, so model identity could not be
verified. One tunnel watchdog is running and may recover automatically.

The next safe work is static preparation of a fresh H17/M0-only r61 wrapper and
namespace. A zero-model-call online preflight must pass after server recovery;
only then may one isolated, non-scored H17/M0 smoke run. The r60 formal suite is
immutable and no r61 formal batch is authorized.

Machine-readable evidence:
`reports/protocol_v2_2_r61_local_validation.json`.
