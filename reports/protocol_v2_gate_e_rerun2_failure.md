# Protocol-v2 Gate E rerun 2 failure

Date: 2026-07-26  
Suite: `nonhard_capability_seed20260729_rerun2`  
Frozen tag: `protocol-v2-gate-e-rerun2-freeze`  
Completed experimental cells: 2 of 8  
Successful cells: 1 of 2  
Decision: stopped; diagnostic only; do not enter Gate F

The first B3 `ContactsAddContact` cell passed the native evaluator. The second
M0 `SimpleCalendarEventsOnDate` cell then triggered the preregistered
`100% valid output after one bounded repair` stop condition.

The M0 model correctly opened the calendar, recognized that October 25, 2023
was visible, and proposed a normalized tap on that date. The action itself was
valid and was never executed because the accompanying `state_delta` failed
schema validation:

1. the initial response used a free-form object;
2. the one permitted repair changed it to an array of free-form objects;
3. neither response used the required structured fact fields
   (`kind`, `subject`, `predicate`, `object`, `natural_language`, `evidence`).

This is a generic protocol-contract defect. The v2 M0 system prompt described
`state_delta` as structured but, unlike the v1 prompt, did not give its exact
object form. The repair prompt referred to a system-prompt example that did
not exist. No task-specific coordinate, answer, or evaluator information is
needed to correct it.

Corrective policy:

- preserve this complete two-cell run as diagnostic evidence;
- add the exact generic `state_delta` object form to the M0 system prompt;
- add the same form to the protocol-v2 bounded repair prompt while retaining
  the B3 rule that its `state_delta` is empty;
- add a regression test for the repair contract;
- rerun the full Gate D qualification;
- freeze a new development tag and restart all eight Gate E cells in a new
  immutable suite directory.
