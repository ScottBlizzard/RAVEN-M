# Protocol-v2.2 r52 local validation

Status: **local PASS; one isolated live Files smoke required**

Candidate commit/tag:
`92d7be90e9627346d717ad68163f52de4948a8a2` /
`protocol-v2-2-r52-local-candidate`

## Trigger and change

r51's clean 20-step failure occurred before MOVE. After a Search activation
tap, accessibility showed the keyboard but no focused editable. The existing
repair removed type coordinates while retaining `clear_text=true`; Ctrl+A
then selected all 14 storage-root items instead of clearing Search.

r52 prevents only this post-activation clear race. With a pending activation
proof, clear mode requires an actually focused editable. Keyboard-only
evidence is insufficient. The bounded repair must keep identical task text
and provenance, omit x/y, and set `clear_text=false`.

## Local evidence

- 392/392 project tests passed on the exact candidate commit.
- 142/142 focused guard, controller, and full-memory-policy tests passed.
- The r51-shaped full-chain regression executes the activation tap, blocks
  the keyboard-only clear action, executes safe non-clearing text exactly
  once, and consumes the one-step activation proof.
- The repair contract rejects retained clear mode, changed authority,
  coordinates, or a non-text repair before execution.
- A positive actual-focused-editable case preserves legitimate clear mode.
- r51 destination-navigation and r50 source-exit full-chain tests still pass.
- `compileall`, `git diff --check`, and the Protocol-v1 197/197 breadth seal
  passed.

## Evidence boundary

No live AndroidWorld action has run from r52. r51 is frozen and cannot be
resumed. The only authorized next action is one fresh, isolated, non-scored
M0 `FilesMoveFile` smoke under an r52 namespace after a zero-model-call
preflight. Gate D, formal Gate E, and Gate F remain unauthorized until that
smoke provides the required live evidence.

