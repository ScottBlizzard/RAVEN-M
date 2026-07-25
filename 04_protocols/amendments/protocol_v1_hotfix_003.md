# Protocol v1 amendment 003: post-outage emulator recovery

Status: `active`

Date: 2026-07-25

Scope: `single_cell_post_outage_emulator_recovery`

## Trigger

The model endpoint passed the hotfix-002 three-check stability gate.  The
authorized attempt 4 then received a valid response from the exact frozen model
in 7.93 seconds, but the local emulator timed out while launching OsmAnd and
again while tearing it down.  The event ledger records the successful model
call followed by `AdbControllerError`; no evaluator or scored result exists.
The unresponsive cleanup process was stopped only after these events were
persisted.

## Authorized correction

Only breadth cell 013 may receive attempt 5.  It may start only after:

1. the named AndroidWorld AVD is cold-restarted;
2. the fixed no-LLM smoke reports 116 registered tasks and a
   `2400×1080×3` screen;
3. the exact model endpoint again passes three consecutive health checks.

Attempts 1–4 remain archived and unscored.  Attempt 5 uses the same frozen
task instance, variant, model, prompts, budgets, evaluator and success rules.
If it suffers another infrastructure failure, execution stops.

After this cell produces a scored result, the remaining schedule continues
under hotfix-002; no other cell receives an additional attempt exception.

The original protocol and hotfix-001/002 files remain byte-identical.
Resumption requires tests, an exact hash manifest and Git tag
`protocol-v1-hotfix-003`.
