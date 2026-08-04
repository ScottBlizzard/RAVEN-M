# Role-Binding Timing Phase B2 fresh snapshot/oracle collection qualification

## Verdict

**`NOT_ELIGIBLE_FOR_PHASE_C_PREREGISTRATION`**. The one frozen B2 v0.2 pool attempted 8 structurally distinct base families in 8 apps and 8 destination widget/layout families, but qualified **0/8 families**. All 16 high/low variants failed before a stable paired PNG + raw UI tree was produced. There were **0 model-generation calls**, no pilot, no oracle-efficacy evaluation, and no memory/controller-efficacy result.

The stop rule therefore applies: B2 v0.2 is closed. No failed family was replaced, no same-version recapture occurred, and Phase C was not started.

## What was frozen before capture

- Protocol-freeze commit: `76473dfb238e5e5d9a601e52c8f4e8eaf2e95f00`.
- Tag: `role-binding-timing-phase-b2-v0.2-protocol-freeze-20260804`.
- Protocol SHA-256: `67e797309f778338e557c3d6a668b4485cccca276c3378b427b28ec3f4ba4122`.
- Config SHA-256: `1a89460d3679f58884c29426489aba94f4ee894b308078540db31141b49b95af`.
- Source/config lock SHA-256: `593a3fcb76caa796ace4ec4234bb7170be34807386c357d6e0d941deb5ab60db` (9 entries, no mismatch at freeze).
- A base family was defined by distinct task semantics plus destination app/layout/widget family. Different entity names in one Contacts list were explicitly forbidden from counting as separate families.

The frozen inventory met the corrected diversity requirement:

| Family | App | Task semantics | Destination widget/layout family |
|---|---|---|---|
| B2F-001 | Contacts | update destination contact phone | person row |
| B2F-002 | Markor | append code to destination note | document row |
| B2F-003 | Files | move retrieved value to destination document | DocumentsUI file row |
| B2F-004 | Tasks | update destination task note | task row |
| B2F-005 | Simple Calendar | update destination event location | event block |
| B2F-006 | Pro Expense | update destination expense amount | expense row |
| B2F-007 | Broccoli | add ingredient to destination recipe | recipe card |
| B2F-008 | Simple SMS | send code to destination conversation | conversation row |

Thus, diversity passed independently: 8 apps, 8 widget families, and at most 1 family per app. This does **not** imply that any snapshot qualified.

## One-shot collection and exclusions

Collection ran from `2026-08-04T13:02:12.691873Z` to `2026-08-04T13:21:08.868896Z` (1,136.187 s). It made exactly 16 capture attempts, with zero candidate replacements and zero same-version recaptures.

| Family | Low ambiguity | High ambiguity | Point of failure |
|---|---|---|---|
| B2F-001 Contacts | target text `SAVE` absent | target text `SAVE` absent | setup/onboarding selector, before capture |
| B2F-002 Markor | reset-before failed | ADB shell reset failed | reset/setup, before capture |
| B2F-003 Files | ADB shell reset failed | reset-before failed | reset/setup, before capture |
| B2F-004 Tasks | foreground package unavailable | foreground package unavailable | app launch/foreground observation |
| B2F-005 Calendar | foreground package unavailable | foreground package unavailable | app launch/foreground observation |
| B2F-006 Expense | foreground package unavailable | foreground package unavailable | app launch/foreground observation |
| B2F-007 Broccoli | foreground package unavailable | foreground package unavailable | app launch/foreground observation |
| B2F-008 SMS | target text `SAVE` absent | target text `SAVE` absent | setup/onboarding selector, before capture |

Failure counts across variants were: 8 `FOREGROUND_PACKAGE_UNAVAILABLE`, 4 `TARGET_TEXT_NOT_FOUND`, 2 `ADB_SHELL_FAILED`, and 2 `RESET_BEFORE_FAILED`. The first preregistered broken edge was B2F-001 low/high capture failure. The final cleanup/reset audit also failed for B2F-002 and B2F-003; the latter produced a nonsensical observable count (`1,100,756`) rather than a valid empty-state proof.

Consequently, the frozen output contains 16 setup traces but **0 PNGs and 0 raw UI-tree XML files**. There was nothing eligible for oracle uniqueness, pairing, or stability qualification. The one-shot qualifier correctly returned 0/8 (0%) and wrote exactly one qualification record.

## Infrastructure evidence and deviation

Before the pool, the connected emulator lacked Android `package`, `window`, and `activity` services. The one preregistered cold restart of `AndroidWorldAvd` on explicit ADB port 5038 restored all three services and passed the immediate isolation check. Client and server used the official locked ADB SHA-256 `957e46b8615f7af5b7292a2ddabe98d2e61940c3fb2b0545756507f080613e71`, serial `emulator-5554`, with no fallback to 5037.

There is one transparent protocol/infrastructure deviation. During collection, an operator progress check addressed explicit port 5038 after that daemon had disappeared; the same official locked ADB binary implicitly restarted the 5038 daemon. This observation was external to the collector, so it is marked as operator evidence rather than silently inserted into the frozen trace. No 5037 server was used. The restart prevents a claim of uninterrupted ADB-server continuity and is a plausible contributor to the shared setup failures, but it cannot turn the failed pool into usable data or weaken the stop decision.

## Integrity and regression checks

- Candidate manifest: `candidate_pool_frozen.v0_2.json`, SHA-256 `9b85e166db3bee15b9eb2e4a28ad5137bc1cc741cea08e66c44aa0e866e81e7f`.
- Candidate pool lock: `candidate_pool_frozen.v0_2.lock.json`, SHA-256 `c37d1604d4173d43867607482e75390612d78c5c3c4837a7f2def9f9565b5d00`.
- The pool lock contains 19 files; independent rehashing found 0 mismatches.
- A narrow parent `.gitattributes` rule disables text/diff transforms only for this frozen artifact root; all 21 worktree files were byte-identical to their staged Git blobs, so CRLF normalization cannot invalidate the committed hashes.
- Candidate manifest validation found 0 JSON-schema errors.
- The artifact root has 21 files / 184,420 bytes: 19 JSON and 2 emulator logs.
- B2 focused tests: 10/10 passed. Entire `role_binding_timing` namespace: 27/27 passed.
- The previously accepted Phase-B full regression remains exactly `1150 passed / 1 failed`, with the one known frozen-r79-manifest conflict. It was not rewritten as a B2 result.
- Protected legacy WIP SHA-256 values remained `fc0e82…fe33`, `ff89d6…9d10`, and `5bb1f1…d0a`; none was staged or committed.

## Claim–evidence verdict

| Claim | Verdict | Evidence boundary |
|---|---|---|
| The corrected pool avoids eight-Contacts pseudoreplication | Supported | Eight distinct apps/task semantics/widget families; max one family per app |
| The B2 collector produced a qualified fresh corpus | Rejected | 0/8 families, 0 PNG, 0 UI tree |
| Snapshot/oracle qualification is at least 95% | Rejected | Observed family rate 0%; oracle stage was never reached |
| Phase C generation may begin | Rejected | `generation_eligible=false`; frozen stop rule applies |
| The timing × ambiguity hypothesis is true or false | Untested | No model calls or qualified critical states |
| Memory or controller efficacy changed | Untested | B2 was infrastructure/data qualification only |

The narrow diagnosis is a **collection/setup and ADB lifecycle floor**. A future attempt, if separately authorized, must use a new B2 version and a newly frozen candidate pool after a task-agnostic infrastructure correction. The failed v0.2 pool cannot be repaired and relabeled held-out.
