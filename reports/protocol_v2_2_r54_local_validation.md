# Protocol-v2.2 r54 local validation

Status: **local PASS; one isolated live B3 Contacts smoke required**

Candidate commit/tag:
`54adaf031abd87dc5c420bd1d8d07acc8c0a4b94` /
`protocol-v2-2-r54-local-candidate`

## Trigger and change

Formal r53 stopped in B3 Contacts at step 6. The first response used the
correct task-literal phone number but an illegal `y=638`. The only repair
changed it to `y=0.638` while retaining immediate `clear_text=true`.
`UNFOCUSED_CLEAR_TEXT_GUARD` correctly blocked that repair because Phone was
visible but inactive.

r54 does not accept or normalize the malformed coordinate. It routes this
narrow response class to a tap-only repair. The tap must hit a visible
editable field whose semantic role matches the verified unchanged task
literal. Text, clear, navigation, wait and commit actions are forbidden in
that repair. A later policy step may type only after observing activation.

## Local evidence

- 395/395 project tests passed.
- 145/145 focused guard, semantic-controller, and full-memory-policy tests
  passed.
- The positive regression activates a role-matched input, observes the next
  state, types without coordinates and without Ctrl+A, and consumes the
  one-step activation proof.
- The exact r53-shaped direct-text repair is rejected before execution.
- All prior focus, role binding, optional-field, loop, Files transfer and
  memory regressions remain passing.
- `compileall`, `git diff --check`, and the unchanged Protocol-v1 197/197
  breadth seal passed.

## Evidence boundary

No live AndroidWorld action has run from r54. The r53 formal directory is
frozen and must not be resumed. The only authorized next action is one fresh,
isolated, non-scored B3 `ContactsAddContact` smoke under an r54 development
namespace after zero-model-call preflight. Gate D, a new formal Gate E, and
Gate F remain unauthorized until that smoke is audited.
