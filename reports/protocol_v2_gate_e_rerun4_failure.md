# Protocol-v2 Gate E rerun 4 failure

Date: 2026-07-27  
Suite: `nonhard_capability_seed20260729_rerun4`  
Frozen tag: `protocol-v2-gate-e-rerun4-freeze`  
Completed experimental cells: 2 of 8  
Successful tasks: 0 of 2  
Decision: stopped; diagnostic only; do not enter Gate F

The first B3 `ContactsAddContact` cell was a valid ordinary capability failure
at the 12-step budget. The second M0 `SimpleCalendarEventsOnDate` cell then
correctly navigated to October 25, read `Board meeting`, and proposed a
terminal answer, but the JSON omitted two required top-level fields:
`expected_outcome` and `memory_citations`.

The one permitted repair added `memory_citations=[]` but still omitted
`expected_outcome`. The output remained invalid and no answer action was
executed. The runner stopped on the preregistered 100% output-validity gate;
the six remaining cells were not started.

Both v2 system prompts name their required fields, but the bounded repair
prompt did not provide a full top-level response skeleton or explicitly
require every missing property to be fixed together. The correction is
schema-generic:

- give B3 and M0 complete top-level skeletons;
- require all validator-listed missing fields to be repaired in one pass;
- retain the exact status/action, provenance, state, and completion-evidence
  rules already frozen.

No task-specific date, event title, coordinate, answer, or evaluator
information is added. This run is preserved and must not be continued or
combined with a later attempt.
