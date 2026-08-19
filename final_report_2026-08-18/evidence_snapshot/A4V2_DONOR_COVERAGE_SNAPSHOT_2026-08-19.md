# A4-v2 donor-coverage snapshot

Date: 2026-08-19

Source repository: `D:/ZJU/Summer_Camp/RAVEN-M-AWM-Audit`

Source commit: `22a9b9a62b7f4e51b0b25ef70d64218f13dc0f0b`

Authoritative source files:

- `evidence/a4v2/A4V2_DONOR_ACQUISITION_RESULT.json`
- `evidence/a4v2/A4V2_DONOR_COVERAGE_BLOCKER_2026-08-19.md`
- `HANDOFF_A4V2_2026-08-19.md`

## Terminal result

Status: `DONOR_COVERAGE_BLOCKED`

- 24 / 24 frozen donor slots produced valid scientific outcomes.
- 6 evaluator-confirmed successes and 18 valid scientific failures.
- 2 additional infrastructure-invalid attempts were retained with legal replacement linkage.
- Qualified routes: Expense/delete, OpenTracks/retrieve-duration, Broccoli/delete-recipe.
- Blocked routes: Browser/open-local-task, Retro/create-playlist, Calendar/add-event, OsmAnd/open-location-result.
- Each blocked route exhausted 4 / 4 frozen attempts and still had 0 / 2 required donors.
- 454 model calls, 442 executed actions, and 1,716,497 total tokens were recorded with no missing usage.
- Focused tests: 17 / 17 PASS.

Because the preregistered requirement was at least two successful donors per route,
no complete source lock or workflow bank could be constructed. Offline induction,
seven-task scoring, content ablation, and 19-task expansion were therefore
`NOT_RUN_BY_PROTOCOL`.

## Claim boundary

This does not show that AWM is generally ineffective. It shows that the frozen
A0 screenshot-only controller, donor panel, seeds, native budgets, and finite
fallback schedule could not provide the seven-route donor coverage required to
test A4-v2 transfer.

## Use in the final report

The result upgrades the earlier one-task A4 mismatch into a measured upstream
prerequisite failure. In this setting, reusable successful donors were scarce
enough that workflow induction could not legally begin. This supports extending
the information-opportunity audit with a precondition stage (`P0`) before online
fact tracing (`L0-L6`): first establish that a memory method has a valid source,
write/read opportunity, and budget; only then evaluate its behavioral effect.
