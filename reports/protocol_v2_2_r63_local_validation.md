# Protocol v2.2 r63 Local Validation

## Decision

**PASS locally; exact-package online preflight pending.** The dated-list row
and requested-field grounding candidate is frozen at commit
`fe16e7dac9c383b400ca7ab7e4e760e29166ed5a` and tag
`protocol-v2-2-r63-local-candidate`. This report authorizes neither a live
smoke nor a formal Gate-F run.

## What r63 changes

r62 reached the correct date without the earlier Markers/Search detour, but
its terminal answer combined a title from a `2 Oct` row with a title from one
`24 Sep` row. It also returned row titles even though the task requested the
activity type. Both visual critics incorrectly accepted that completion.

r63 introduces a generic dated-list contract. An explicit date binds only to
content on the same horizontal row. Once the target date is visible, another
swipe is rejected. If the requested field is different from the visible row
title and is not explicitly labeled in the list, the controller requires a
pure tap on an enabled target-date row and inspection of its detail view. It
records distinct target rows, rejects repeated inspection of one row as full
enumeration, and requires one answer item per observed target-date row. A
bounded `press_back` repair returns from an incomplete detail answer to the
list. Deterministic date/row/field rejection now runs before visual-source and
completion critics, avoiding the two calls r62 spent adjudicating an answer
that could already be proven invalid.

The mechanism contains no H17 identifier, OpenTracks package, target date,
activity title, activity type answer, hidden task parameter, or evaluator
answer special case.

## Validation result

- Complete project tests: **535/535** in 141.5 seconds
- Focused guard, controller, and prompt tests: **172/172**
- Historical r62 package/preflight/stop tests: **22/22**
- Protocol-v1 breadth seal: **197/197**, zero failures, not rewritten
- Python compilation: passed
- `git diff --check`: passed
- Real model calls during local validation: **0**
- GPU experiment cells during local validation: **0**

The controller replay uses r62's complete rejected answer,
`Bicycle Adventure, Recovery day`. The frozen screenshot places the wrong-date
item at row center `0.608958` and the two target-date rows at `0.747292` and
`0.834375`. r63 rejects the answer before execution and before any visual
critic call, then accepts only a target-row detail tap. Negative tests cover
plural field roles, unrelated dates, requested-name answers, repeated taps on
one row, incomplete enumeration, and a fully enumerated answer path.

## Current boundary

The online route has not been exercised by this local report. A separate r63
wrapper, namespace, exact freeze manifest, and zero-model-call preflight are
required before at most one non-scored H17/M0 development smoke. The r62 suite
remains immutable.

Machine-readable evidence:
`reports/protocol_v2_2_r63_local_validation.json`.
