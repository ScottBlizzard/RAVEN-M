# A7 gated-continuation protocol amendment

This amendment is frozen before any post-shutdown A7 generation. It changes
only campaign scheduling and continuation policy. The A7 memory class, model,
revision, official system prompt, action protocol, sampling, task instances,
native budgets, evaluator, and zero-extra-call property remain unchanged.

## Parent evidence

The parent suite is
`runs/a678_memory/official_qwen_20260811T094144_c61c8a37`. Its seven valid
episodes are immutable scientific records and must not be rerun. It contains
one A0-preservation task, `ExpenseDeleteMultiple2`, with evaluator reward 1.
The interrupted `OsmAndMarker` attempt is infrastructure-invalid and is not a
valid result.

## Blocking capability gate

The next valid episodes must be, in order:

1. `RetroSavePlaylist`
2. `SimpleCalendarAddOneEvent`
3. `SportsTrackerTotalDurationForCategoryThisWeek`

Each must receive AndroidWorld evaluator reward 1. A model error, wrong action,
format error, max-budget exit, premature terminal claim, or reward below 1 is
a scientific gate failure: freeze the continuation immediately and do not run
another task. An explicit infrastructure-invalid attempt remains logged and
may retry only the same task.

Together with the retained `ExpenseDeleteMultiple2` success, three new gate
successes establish 4/4 preservation. Only then may the remaining nine unique
untested tasks run. No already valid parent episode may be repeated.

## Evidence and claim boundary

The parent signature, checkpoint, and every imported `episode.json` are bound
by SHA-256 in a zero-generation continuation plan. New episodes are stored in
a separate suite; the parent directory is never modified. The final ledger
must contain exactly 19 unique canonical task/seed pairs and must retain all
parent infrastructure-invalid audit records until resolved or explicitly
excluded.

This is a transparent post-seven-episode protocol amendment. It may support a
complete A7 mechanism comparison if the gate passes, but it is not described
as one pristine, originally preregistered 19-task campaign.

## GPU-start boundary

No-card preparation ends with a passing local/remote zero-generation preflight.
After a GPU is attached, start vLLM only through
`implementation/scripts/start_a7_gated_server.sh`. Once `/v1/models` is live,
run `qualify_a678_live_server.py` against the newly written
`A7_GATED_SERVER_LAUNCH_INTENT.json`, copy the new live receipt to the local
runner, validate its SHA-bound preflight, and only then execute the continuation.
The historical PID 1334 and historical A678 receipt are invalid.
