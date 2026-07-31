# Protocol v2.2 r60 Local Validation

## Decision

**PASS locally.** r60 may advance to exact-source wrapper preparation and a
zero-model-call H01 preflight. This report does not authorize a live smoke or
any formal Gate-F cell.

Candidate source:

- commit: `5ef66de358423f9940191d8dfde0e74002ccdcec`
- tag: `protocol-v2-2-r60-local-candidate`
- tag resolves exactly to the candidate commit

## What r60 changes

r59 proved that simply adding an authoritative ledger was insufficient. The
ledger initialized on Chrome's `Accept & continue` setup button, then treated
the task page's load-time `6` as a post-action result. The AndroidWorld source
shows the exact task state machine: one number is generated on load, clicks
1–4 generate the next four numbers, and click 5 only reveals the answer form.

r60 binds initialization to a target control and unique numeric value that
coexist on the task UI. Each target click that actually executes samples the
number visible immediately before it. For the frozen H01 instance, the five
click ordinals therefore record `6, 2, 3, 9, 10`; click 5 reveals the form and
the verified product is `3240`.

Action completion and operand completion are independent. Only their joint
completion authorizes post-repeat deterministic input. Missing or ambiguous
ordinals remain missing, equal values remain separate, and a sixth exact action
is denied even if the completed button has disappeared.

## Validation result

- Complete project tests: **446/446**
- Focused guard/controller tests: **128/128**
- Protocol-v1 breadth seal: **197/197**, zero failures, not rewritten
- Python compilation: passed
- `git diff --check`: passed
- Historical r56–r59 execution checkpoints: byte-frozen
- Real model health: `ok`, exact Qwen3-VL revision/backend matched
- Emulator: `device`
- Real model calls during r60 validation: 0
- GPU experiment cells during r60 validation: 0

The replay matrix explicitly covers the false Chrome setup binding, the exact
H01 load/click/form sequence, ambiguous values, equal repeated values, stale
summary precedence, and the disappeared-control sixth-click repair.

## Boundary

The next safe action is to prepare an r60-specific wrapper and manifest, freeze
the exact source hashes, and run a zero-call preflight. A single non-scored
H01/B3 smoke may be considered only after that preflight passes. r59 remains an
immutable failed non-scored result; no formal Gate-F run is authorized.

Machine-readable evidence:
`reports/protocol_v2_2_r60_local_validation.json`.

