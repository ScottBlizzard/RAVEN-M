# Protocol-v2.2 r47 local validation

Status: **PASS locally; fresh M0 Contacts smoke pending**

Parent commit:
`412d07d`

## Local evidence

- 360 tests collected and 360 passed.
- 120 focused controller, guard, and repair-prompt tests passed.
- The new full-chain regression executes two identical activation taps only
  because the second is the bounded repair of
  `UNFOCUSED_CLEAR_TEXT_GUARD`.
- The next no-coordinate, `clear_text=false` task-bound input executes; the
  activation proof count and consumption count are both one, and no proof
  remains pending.
- The override audit count is exactly one while the ordinary
  unverified-progress block count remains zero for that bounded chain.
- Existing ordinary repeat/loop tests continue to pass.
- `compileall`, `git diff --check`, and the Protocol-v1 197/197 breadth seal
  passed.

## Change and compatibility

The controller passes an allowance only during validation of the specific
unfocused-clear-text repair and only for a tap. The guard consumes the
allowance only when the candidate is also the exact immediately preceding
unverified-progress fingerprint. All other decisions take the old branch.

The action schema, Planner/executor prompts, action executor, memory subsystem,
thresholds, evaluator, readiness logic, and runner are unchanged from r46.
The new audit counter makes any live use explicit rather than silently
relaxing the loop guard.

## Evidence boundary

No server/GPU result has been produced with r47 source. r46 remains a failed
development smoke whose task-scope behavior was live-qualified but whose
activation repair did not execute. The next admissible action is one fresh
M0 Contacts smoke after candidate freeze and zero-call preflight. No formal
Gate-E rerun is authorized yet.
