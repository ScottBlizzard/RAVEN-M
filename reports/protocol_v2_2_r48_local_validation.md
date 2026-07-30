# Protocol-v2.2 r48 local validation

Status: **PASS locally; fresh M0 Contacts smoke pending**

Parent commit:
`1f5fadee94042326c58216eee0a846f40e0044f4`

## Local evidence

- 369 tests collected and 369 passed.
- 133 focused guard, controller, repair-prompt, and reliability-recovery tests
  passed.
- The full-chain regression executes the first no-effect tap, blocks the next
  ordinary repeat, admits the exact bounded repair once, and observes the
  contact form open.
- The live-shaped audit has one visible-control override, one unverified
  progress block, and a structured `Create contact` accessibility record.
- Separate regressions reject Save, unnamed, editable, system, and keyboard
  controls.
- A repeated request for the same allowance is rejected, proving that a third
  identical tap cannot pass.
- `compileall`, `git diff --check`, and the Protocol-v1 197/197 breadth seal
  passed.

## Change and compatibility

The controller computes a fresh accessibility assessment for every candidate
tap. It exposes the allowance only during repair of the exact r47
unverified-progress error shape. The guard consumes it only when the
assessment is permitted, the page/action fingerprint exactly matches the
immediately preceding no-effect fingerprint, and that fingerprint has never
used the allowance.

The special repair prompt explicitly permits one exact retry rather than
issuing the contradictory instruction to choose a different control. All
non-tap loop repairs retain the prior higher-level-navigation contract.

The action schema, Planner/executor base prompts, action executor, memory
subsystem, thresholds, evaluator, readiness logic, and runner are unchanged
from r47. r47's input-activation proof path and all task-grounding behavior
remain covered by the passing suite.

## Evidence boundary

No server/GPU result has been produced with r48 source. r47 remains a valid
failed development smoke whose task scope was correct and whose observed
conflict defines this candidate. The next admissible action is one fresh M0
Contacts smoke after candidate freeze and zero-call preflight. No formal
Gate-E rerun is authorized yet.
