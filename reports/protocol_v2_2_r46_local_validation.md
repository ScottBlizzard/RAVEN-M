# Protocol-v2.2 r46 local validation

Status: **PASS locally; live smoke failed, candidate rejected**

Parent commit:
`8bb7ed7`

## Change

r46 adds a task-grounding constraint to the Planner and the shared
Protocol-v2.2 turn prompt. Its declared-source repair now performs only a
reversible activation tap when the correct remaining task value belongs to a
different visible input; the value may be typed only after a later
observation confirms input readiness.

The change is task-agnostic. It names common optional-field examples only to
define a negative scope boundary, not to choose an app, coordinate, value, or
action.

## Local evidence

- 359 tests collected and 359 passed.
- 45 directly related prompt, repair, and semantic-controller tests passed.
- The exact failure shape is covered: invented task-literal text is rejected,
  the bounded repair activates Phone with a tap, and no clear/type command is
  issued in that repair.
- The shared Protocol-v2.2 prompt test requires the optional-field omission
  contract.
- A dedicated Planner-prompt test requires explicit task grounding and removal
  of previously invented optional variables.
- `compileall` and `git diff --check` passed.
- The Protocol-v1 breadth seal verified 197 files with zero failures.

## Compatibility boundary

The action schema, parser, guard implementation, thresholds, executor adapter,
memory store, evaluator path, and both executor system prompts are unchanged.
Consequently, retained trajectories remain parseable under the same action
contract; r46 changes only future Planner/executor instructions and the
content of the existing one-repair prompt.

The r45 sequence-5 initial and repair responses remain invalid under r46:
`TechCorp` still fails declared-source validation, and coordinate-bearing
phone entry with `clear_text=true` still fails unfocused-input validation.
r46 does not admit either unsafe action; it steers the single repair toward a
separate activation step.

## Evidence boundary

The fresh server-backed smoke is recorded in
`reports/protocol_v2_2_r46_m0_contacts_smoke.md`. It live-qualified task-scope
grounding but failed the independent activation/loop repair contract. r45
remains a stopped Gate-E artifact with four successes, one formal protocol
failure, and three unexecuted cells. r46 is rejected and Gate D remains
unauthorized.
