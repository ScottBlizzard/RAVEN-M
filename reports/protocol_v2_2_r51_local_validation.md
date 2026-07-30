# Protocol-v2.2 r51 local validation

Status: **local PASS; one isolated live Files smoke required**

Candidate commit/tag:
`ee6f04a4624e964266836354e1e35a289f52aef9` /
`protocol-v2-2-r51-local-candidate`

## Trigger and change

r50 completed `FilesMoveFile` with native reward 1.0, one MOVE, no second
mutation, and a live source-exit repair. Its root-level step-18 tap hit the
exact `Ringtones` text and entered that folder, but r49/r50 required a
separate clickable accessibility container that real Android Files did not
expose.

r51 replaces only that requirement with an exact destination content-label
binding. The tap must hit the exact task destination in Android Files, below
the top 20% title/breadcrumb region, on a visible, enabled, noneditable,
bounded and non-commit text node. Clickable-container evidence is retained
for audit but made optional.

## Local evidence

- 389/389 project tests passed on the exact candidate commit.
- 139/139 focused guard, controller, and full-memory-policy tests passed.
- The real-shape full-chain regression uses no clickable parent, executes one
  MOVE followed by the exact `Ringtones` tap, classifies it as
  observe-navigation, and records one live-equivalent navigation event.
- Unit tests preserve a separately clickable Files row while proving that a
  lone exact nonclickable content label also qualifies.
- Negative tests deny a top-region breadcrumb/title, editable exact label,
  compound commit-like label, wrong label, non-Files package, absent
  accessibility, non-tap action, and pre-commit counting.
- r50's source-exit full-chain and negative repair regressions still pass.
- `compileall`, `git diff --check`, and the Protocol-v1 197/197 breadth seal
  passed.

## Evidence boundary

No live AndroidWorld action has run from r51. r50 is frozen and cannot be
resumed. The only authorized next action is one fresh, isolated, non-scored
M0 `FilesMoveFile` smoke under an r51 namespace after a zero-model-call
preflight. Gate D, formal Gate E, and Gate F remain unauthorized until the
smoke provides both source-exit and destination-navigation live evidence.

