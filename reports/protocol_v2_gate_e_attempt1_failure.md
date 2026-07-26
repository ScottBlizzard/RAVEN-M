# Protocol-v2 Gate E attempt 1 failure

Date: 2026-07-26  
Suite: `nonhard_capability_seed20260729`  
Frozen tag: `protocol-v2-gate-e-freeze`  
Completed experimental cells: 1 of 8  
Decision: stopped; diagnostic only; do not enter Gate F

The first B3 `ContactsAddContact` cell failed the preregistered
`100% valid output after one bounded repair` condition.

The initial model output represented `open_app` as a string plus
`action_details`. The one permitted repair then represented `swipe` using
`direction` and `distance` rather than the canonical `x/y/x2/y2/duration_ms`
form. No GUI action was executed and the native reward was 0.

The runner subsequently hit a reporting-only `NoneType` error while trying to
aggregate the invalid decision. This happened after the atomic cell had
finished and before any second cell began.

Root causes:

1. The v2 system prompts named supported actions but did not enumerate every
   exact JSON object form as the v1 prompts did.
2. The bounded repair prompt did not explicitly show the canonical
   `open_app` and `swipe` forms or forbid `direction`/`distance`.
3. The Gate-E aggregator assumed every logged step had a decision object.

Corrective policy:

- preserve the failed run directory unchanged as diagnostic evidence;
- strengthen only the generic protocol-v2 action contract, with no task
  coordinates or task-specific instructions;
- make the aggregator null-safe and stop immediately on invalid-after-repair;
- rerun Gate D because prompts are protocol-semantic;
- create a new development tag and Gate-E freeze;
- rerun all eight cells from scratch in a new suite directory.
