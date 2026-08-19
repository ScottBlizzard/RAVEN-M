# A4-v2 donor acquisition terminal report

Date: 2026-08-19

Experiment: `A4V2_FAITHFUL_OFFLINE_AWM_QWEN3VL32B_AW_HARD_S20260806_V1`

Evidence class: post-observed donor-acquisition diagnostic (not held-out)

Terminal status: `DONOR_COVERAGE_BLOCKED`

## Outcome

The frozen required panel, every selected optional slot, and every single ordered
final fallback were run. All valid scientific failures were retained. The panel
contains 24 valid scored donor episodes: 6 evaluator-confirmed successes and 18
valid scientific failures. Two additional infrastructure-invalid attempts are
retained and hash-bound: one Retro media-scan initialization failure and one
OsmAnd episode interrupted by loss of the first GPU service. Each was replaced
once under the frozen infrastructure rule; the successful replacement evidence
links back to the invalid artifact.

| Route | Confirmed successes | Required | Frozen attempts exhausted | Status |
|---|---:|---:|---:|---|
| browser/open-local-task | 0 | 2 | 4/4 | blocked |
| expense/delete | 2 | 2 | required panel sufficient | qualified |
| retro/create-playlist | 0 | 2 | 4/4 | blocked |
| calendar/add-event | 0 | 2 | 4/4 | blocked |
| OpenTracks/retrieve-duration | 2 | 2 | 4/4 executed | qualified |
| Broccoli/delete-recipe | 2 | 2 | required panel sufficient | qualified |
| OsmAnd/open-location-result prefix | 0 | 2 | 4/4 | blocked |

The six admitted donors are Expense seeds 20260833 and 20260834, OpenTracks
ActivityDuration seeds 20260843 and 20260844, and Broccoli seeds 20260845 and
20260846. Portable successful-donor snapshots are stored under
`evidence/a4v2/donor_snapshots/` and remain evidence even though the seven-route
bank cannot be constructed.

## Resource closure

- Completed model calls: 454
- Executed actions: 442
- Prompt tokens: 1,661,953
- Completion tokens: 54,544
- Total tokens: 1,716,497
- Sum of episode elapsed time: 16,905.421589 seconds
- Missing usage records: 0
- Transport attempts: 454; every completed call used exactly one transport attempt

The first GPU service was replaced only after an in-flight OsmAnd call became an
infrastructure-invalid episode. The replacement episode and final seed bind the
fresh receipt `d290489b2b4b59314a90d5fef2c5a34f2f1f2fd5128b3e57c35d03b8d02a1d0e`;
the suite checkpoint retains both initial and replacement receipt hashes while
the original run signature remains immutable.

## Protocol consequence

The preregistration requires at least two evaluator-confirmed donors for every
route before source lock and offline induction. Four routes exhausted all four
frozen attempts with zero successes. Therefore no complete source lock is
authorized, and offline induction, workflow-bank freezing, the fixed seven-task
scored run, shuffled-content ablation, and 19-task expansion are all
`NOT_RUN_BY_PROTOCOL` under this identity. No additional seed or task class may
be added under this identity.

This is not evidence that AWM is generally ineffective. It establishes only
that the frozen A0 screenshot-only controller, plan-v2 donor tasks, seeds,
native budgets, and finite fallback schedule could not supply the preregistered
seven-route donor coverage needed to test A4-v2 transfer.

## Machine-readable authority

The authoritative result is `A4V2_DONOR_ACQUISITION_RESULT.json` in this
directory. Its canonical content SHA-256 is
`a000d2fb4ec99736b66997358028c9ed94347af1bbad3473df72e8b98c48be68` and
its file SHA-256 is
`e5eba57bb9c1a6d2bc37f553ff9f59f9098f3b437210105d21568d4f0fbd07aa`.
