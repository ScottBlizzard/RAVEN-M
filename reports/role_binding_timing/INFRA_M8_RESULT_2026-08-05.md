# INFRA-M8 full-snapshot ancestry — final result

## Verdict

**FAIL_AUTHORIZATION_VIEW_DERIVATION.** The one frozen chain stopped at `prelaunch_baseline` with immutable first edge:

`PROCESS_IDENTITY:prelaunch_baseline:AUTHORIZATION_CANDIDATE_IDENTITY_MISSING`

No retry or code change occurred. No 5038 server, emulator, boot, display check, burn-in, a11y stage or DEV grid was started. Generation calls and held-out captures remained zero.

## Exact failure mechanism

M8 correctly persisted the complete full snapshot and a separately hashed derived view, but derived the authorization view from all of M5's `structural_processes`. That source is not candidate-only: it contains each relevant process **and its selected ancestors**.

The baseline structural view contained 11 rows: four names were project-relevant process classes and seven were ancestry support. PID 5848 was an external `LenovoPcManagerService.exe` ancestor. Windows returned `AccessDenied`, leaving its name, creation time and identity key unavailable. It was included only to connect an unrelated Lenovo crashpad ancestry chain; it had no project role and no authority. M8 nevertheless required it to satisfy authorization-candidate identity completeness and failed closed.

Therefore the new root cause is **STRUCTURAL_VIEW_CONFLATES_ROLE_CANDIDATES_WITH_ANCESTRY_SUPPORT**. This is distinct from M7's full-vs-filtered currentness bug. It means the two-view idea remains plausible, but M8 did not implement the authorization projection correctly. The result cannot be reinterpreted as a qualification pass.

## Accounting

| Item | Result |
|---|---:|
| Frozen chains | 1 |
| Process snapshots | 4 |
| Terminal completions | exactly 1 |
| Journal entries | 8 |
| Terminal schema errors | 0 |
| Generation calls / tokens | 0 / 0 |
| Held-out captures | 0 |
| Burn-in | 0/24 |
| Settings / DEV grid | 0/3, 0/12 |
| External live logs | not created; seal passed |

Post-run ports 5037, 5038, 5554, 5555 and 8554 were all empty; no project runtime process or M8 temporary residue remained. The artifact manifest validated. Protected r79 WIP hashes remained unchanged.

## Claim–evidence boundary

- Full-snapshot ancestry qualified: **no**.
- Authorization-view derivation qualified: **no**.
- Exclusive 5038, emulator, boot, display, burn-in, accessibility and 12-cell grid: **untested**.
- v0.3 preparation: **not authorized**.
- Held-out role binding, memory or model hypothesis: **not tested**.

M8 stops here. A future separately authorized version would have to derive role candidates by the explicit relevant-role predicate, keep ancestry-support rows in the observation universe only, and test missing/access-denied ancestors without allowing them to gain or veto unrelated role authority. This is a prospective requirement, not an M8 modification.
