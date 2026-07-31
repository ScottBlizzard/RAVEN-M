# Protocol v2.2 r64 Local Validation

## Decision

**PASS locally; exact-package online preflight pending.** The visual
target-row geometry fallback is frozen at commit
`223b54f72961bc59d4e84ea2ec26fe4124138cf3` and tag
`protocol-v2-2-r64-local-candidate`. This report authorizes neither a live
smoke nor a formal Gate-F run.

## What r64 changes

r63 correctly stopped a blind swipe once the target date was visible, but it
rejected the model's geometrically valid row tap because OpenTracks did not
expose a matching accessibility node marked clickable and enabled.

r64 keeps explicit clickable a11y metadata as the strongest tap authority and
adds a bounded visual-structure fallback. The task date must already be
matched to a chronological list; the selected target-date row must contain
visible non-date content; and both that content and the proposed tap must be
on the content side of an unambiguous left or right date column. Taps on the
date column, non-target rows, rows without content, and layouts whose date
column is centered and ambiguous remain rejected.

The mechanism contains no H17 identifier, OpenTracks package, target date,
row title, activity answer, hidden task parameter, or evaluator special case.

## Validation result

- Complete project tests: **562/562** in 147.8 seconds
- Focused and historical tests: **199/199**
- Protocol-v1 breadth seal: **197/197**, zero failures, not rewritten
- Python compilation: passed
- `git diff --check`: passed
- Real model calls during local validation: **0**
- GPU experiment cells during local validation: **0**

The exact r63 repair `(x=0.5, y=0.775)` is now accepted with authority
`visible_content_row_geometry`: it is `0.027708` vertically from the nearest
target-date row center, lies on the content side, and has same-row non-date
content even though no clickable a11y node is present. The controller replay
uses only two mocked calls and no visual critic. Positive and negative tests
also cover explicit clickability, left/right date columns, a centered
ambiguous column, date-column taps, non-target taps, and empty target rows.

## Current boundary

The emulator and frozen four-4090 Qwen3-VL endpoint are healthy, but this
local report made no generation request. A separate r64 wrapper, namespace,
exact freeze manifest, and zero-model-call preflight are required before at
most one non-scored H17/M0 development smoke. The r63 suite remains
immutable.

Machine-readable evidence:
`reports/protocol_v2_2_r64_local_validation.json`.
