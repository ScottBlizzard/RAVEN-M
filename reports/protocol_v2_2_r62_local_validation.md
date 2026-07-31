# Protocol v2.2 r62 Local Validation

## Decision

**PASS locally; exact-package online preflight pending.** The generic
chronological-toolbar grounding candidate is frozen at commit
`4c194d0fd8edbf93447f27f7b663dc802622e563` and tag
`protocol-v2-2-r62-local-candidate`. This report does not authorize a live
smoke or any formal Gate-F run.

## What r62 changes

r61 fixed delayed UI convergence in the live H17 path, but the policy then
misread a visible `Markers` control as a date picker and later treated text
Search as date navigation. r62 binds a top-toolbar claim to the named control
under the proposed coordinate. It rejects an action only when both roles are
known and conflict; matching Calendar, Search, and Markers actions remain
valid, while unknown controls are not blocked.

When the task contains an explicit date, the screen exposes at least three
aligned date headings as a vertical history, the target is absent, and the
bottom visible absolute date proves that the target is older, the bounded
repair is exactly one upward swipe inside the content list. It cannot tap a
toolbar icon, type a date into text Search, wait, answer, or claim progress.
An empty text-search result is explicitly not accepted as proof that no record
exists on the requested date.

The mechanism contains no H17 identifier, OpenTracks package, target date,
activity type, answer, evaluator field, or frozen hidden parameter.

## Validation result

- Complete project tests: **499/499**
- Focused role, chronology, prompt, and controller tests: **158/158**
- Protocol-v1 breadth seal: **197/197**, zero failures, not rewritten
- Python compilation: passed
- `git diff --check`: passed
- Real model calls during local validation: **0**
- GPU experiment cells during local validation: **0**

The controller replay uses r61's exact first bad action coordinates
(`x=0.84`, `y=0.085`), date-picker outcome claim, and decision rationale. With
a visible `Markers` role and chronological history evidence, r62 rejects the
tap before execution and accepts only a vertical content swipe toward older
rows. Negative tests show that a visible target, a newer target, a
non-chronological layout, or an unknown toolbar role does not trigger that
forced swipe.

## Current online boundary

The emulator is connected and the model health endpoint currently reports the
frozen Qwen3-VL revision and four-4090 backend. This check made no generation
request. A separate r62 wrapper, namespace, exact freeze manifest, and
zero-model-call preflight are still required before one non-scored H17/M0
development smoke may run. The r61 suite remains immutable.

Machine-readable evidence:
`reports/protocol_v2_2_r62_local_validation.json`.
