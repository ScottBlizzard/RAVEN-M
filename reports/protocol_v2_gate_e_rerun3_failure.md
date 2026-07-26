# Protocol-v2 Gate E rerun 3 failure

Date: 2026-07-27  
Suite: `nonhard_capability_seed20260729_rerun3`  
Frozen tag: `protocol-v2-gate-e-rerun3-freeze`  
Completed experimental cells: 5 of 8  
Successful tasks: 3 of 5  
Decision: stopped; diagnostic only; do not enter Gate F

The first five scheduled cells produced the following native outcomes:

1. B3 `ContactsAddContact`: success;
2. M0 `SimpleCalendarEventsOnDate`: success, one answer action, exact
   interaction-cache match, same-turn Critic accepted;
3. B3 `ExpenseAddSingle`: unsuccessful at the 12-step budget;
4. M0 `FilesMoveFile`: unsuccessful at the 20-step budget;
5. M0 `ContactsAddContact`: native evaluator success, but protocol-invalid
   terminal output.

The fifth task was already complete according to the native evaluator. On the
post-save contact screen, however, the M0 Executor used an `answer` action to
return the displayed phone number. `answer` is permitted only for
information-return tasks; creating a contact is an ordinary GUI task and must
finish with `status=done, action=null`. The bounded validator reported this
exact rule, but the one permitted repair repeated the same forbidden answer
unchanged. The runner therefore stopped on the preregistered 100% output
validity gate even though the native task reward was 1.0.

This is a generic repair-contract defect, not a contact-specific action
failure. The corrective change must encode the full status/action matrix for
all v2 tasks and schemas, including ordinary completion, information-return
completion, continuation, and failure. No task coordinate, literal, answer,
or evaluator state may be added.

The three remaining cells were not started. This run is preserved in full and
must not be continued or combined with a later attempt.
