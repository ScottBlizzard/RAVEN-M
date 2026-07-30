# Protocol-v2.2 r50 local validation

Status: **local PASS; one isolated live Files smoke required**

Candidate commit/tag:
`ac8d6ece831a18a55d86d82f940faf152669694a` /
`protocol-v2-2-r50-local-candidate`

## Trigger and change

r49 moved the exact file successfully with native reward 1.0 and no repeated
mutation, but reached the 20-step limit after browsing and reopening Search
inside the exact `Music` source folder. Its destination-verification branch
was never proposed live.

r50 adds only an accessibility-bound post-commit source-exit rule. The task's
exact `source_folder` must appear in the top Android Files navigation region;
ordinary root-level folder cards are deliberately excluded. In that state,
the only continuing GUI action is Back, and the sole repair contract enforces
the exact canonical Back action.

## Local evidence

- 385/385 project tests passed on the exact candidate commit.
- 135/135 focused guard, controller, and full-memory-policy tests passed.
- The positive full-chain regression executes MOVE once, blocks a post-commit
  swipe in the exact `Music` current directory, repairs to Back, and records
  one source-exit block.
- The negative repair regression proves that Search/tap cannot evade the
  exact Back contract.
- Unit negatives preserve pre-commit actions, active-picker behavior,
  non-Files screens, wrong labels, absent accessibility, and root-level
  `Music` tiles.
- The existing r49 full-chain tests still prove that the exact post-commit
  `Ringtones` folder tap bypasses only the false-positive consequential critic
  while non-Files equivalents remain blocked.
- `compileall`, `git diff --check`, and the Protocol-v1 197/197 breadth seal
  passed.

## Evidence boundary

No live AndroidWorld action has run from r50. r49 is frozen and cannot be
resumed. The only authorized next action is one fresh, isolated, non-scored
M0 `FilesMoveFile` smoke under an r50 namespace after a zero-model-call
preflight. Gate D, formal Gate E, and Gate F remain unauthorized until that
smoke provides both source-exit and destination-navigation live evidence.
