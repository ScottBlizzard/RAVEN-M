# Role-Binding Timing B2.5 infrastructure/collector root-cause audit

## Verdict and boundary

This is a zero-generation, evidence-only audit of the frozen B2 v0.2 failure. It uses the immutable v0.2 manifest, lock, 16 setup traces, emulator log, the pinned AndroidWorld source/configuration, and the installed AndroidEnv ADB-controller source. It performs no new capture and does not change the v0.2 verdict.

**Root-cause verdict:** B2 v0.2 failed through at least three independent edges: a definitive collector shell-command bug, a launch/foreground observability contract that cannot distinguish launch failure from parser failure, and an app-setup/seeding mismatch inherited from text-only AndroidWorld helpers. A 5038 daemon replacement occurred during the pool and violates continuous-server isolation, but its timing rules it out as the common cause of all failures.

Every v0.2 app, entity value, setup trace, and state combination is now `DEV-contaminated=true` and `held_out_eligible=false`. None may be repaired, recaptured, or relabelled as v0.3 evidence.

## Evidence basis

- Frozen candidate manifest SHA-256: `9b85e166db3bee15b9eb2e4a28ad5137bc1cc741cea08e66c44aa0e866e81e7f`.
- Frozen candidate pool lock SHA-256: `c37d1604d4173d43867607482e75390612d78c5c3c4837a7f2def9f9565b5d00`; 19/19 locked entries rehashed without mismatch in the B2 completion audit.
- One-shot qualification: 0/8 families, 0/16 captured variants, 0 PNG, 0 raw UI tree, 0 generation calls.
- Collector source SHA-256: `f336591a7ff61cf2a31e110afe5777555a88832ffdc67ca1d781c9409d11ffcc`.
- Deterministic parser/qualifier SHA-256: `41dbe104fad423030b5e7c9952ce2a42629dda85eb5cbf78c362bcb8a47ff19c`.
- AndroidWorld sources: `adb_utils.py` `f5bb97…ff25`, `actuation.py` `2246cb…c744`, `contacts_utils.py` `58a9be…90d4`, `file_utils.py` `39d0fe…e301`, and `setup_device/apps.py` `35ecd4…9f20`.
- Installed AndroidEnv `adb_controller.py` SHA-256: `c7ee0f96579cfd87d560a089232f3da9ce7eef826cb39aee1157b1021f952986`.

Direct evidence below means a frozen artifact or exact source path establishes the fact. Inference means the evidence is compatible with the explanation but v0.2 did not log the discriminating observation.

## Failure timeline

| UTC interval | Family/variant | Frozen primary failure |
|---|---|---|
| 13:10:24–13:11:19 | B2F-001 Contacts low/high | AndroidWorld `Target text "SAVE" not found` |
| 13:11:19–13:13:15 | B2F-002 Markor high/low | ADB shell timeout or nonzero reset count |
| 13:13:15–13:15:04 | B2F-003 Files low/high | ADB shell timeout or nonzero reset count |
| 13:15:04–13:16:07 | B2F-004 Tasks high/low | `FOREGROUND_PACKAGE:None:org.tasks` |
| 13:16:07–13:17:04 | B2F-005 Calendar low/high | foreground package `None` |
| 13:17:04–13:17:47 | B2F-006 Expense high/low | foreground package `None` |
| 13:17:47–13:18:44 | B2F-007 Broccoli low/high | foreground package `None` |
| 13:18:44–13:19:37 | B2F-008 SMS high/low | AndroidWorld `Target text "SAVE" not found` |

The replacement 5038 daemon process has host creation time 13:18:28Z, inside B2F-007 high. The pre- and post-cold-restart isolation records instead name PID 3208. Therefore all Markor/Files failures and seven of eight foreground-`None` episodes began before the replacement; SMS `SAVE` failures occurred after it. The replacement cannot be the shared root cause.

## 1. 5038 daemon loss and implicit restart

### Direct evidence

1. The frozen runtime recorded one 5038 listener, PID 3208, immediately before and after the preregistered cold emulator restart. It recorded the official client/server hash `957e46…3e71`, serial `emulator-5554`, and no 5037 fallback.
2. The post-run 5038 server is the same locked binary but a different process, PID 29964, created at 13:18:28Z. The accepted B2 completion report already records the operator-observed disappearance/restart as a protocol deviation.
3. AndroidEnv's pinned `AdbController.command_prefix()` always supplies `-P <configured port>`, so this path did not fall back to 5037. However, `execute_command()` automatically calls `_restart_server()` after a device-specific timeout/error; `_restart_server()` issues `kill-server` and `start-server` without notifying the B2 collector.
4. The B2 collector checks server identity only before collection and after the cold emulator restart. It does not record PID/server-start continuity per operation or at the end. Its setup traces omit raw ADB launch results.

### Causal verdict

`ENVIRONMENT_LIFECYCLE_FAILURE` is supported for continuous 5038 identity: the server was replaced. `COLLECTOR_OBSERVABILITY_BUG` is also supported because implicit restart was neither prohibited nor logged. But **5038 loss did not cause the earlier reset and foreground failures**, because they precede the replacement. It may have caused or followed one B2F-007 command failure; the exact direction is unresolved because daemon lifecycle events and raw ADB stderr were not atomically recorded. Any effect on the a11y forwarder is also inference, not direct evidence.

## 2. Launch and foreground-package failures

### Direct collector defects

1. `_launch_app()` calls AndroidWorld `adb_utils.launch_app()` and discards its response, then sleeps three seconds. It logs `launch_app` even if the response is non-OK.
2. AndroidWorld `launch_app()` uses `start_activity(..., timeout_sec=5)`. `start_activity()` returns a non-OK response rather than raising. Thus the B2 trace cannot prove that an activity was successfully started.
3. `_foreground()` parses only a line containing `mResumedActivity` and then takes the first slash-containing token. It does not recognize `topResumedActivity`, `ResumedActivity`, `mCurrentFocus`, or the AndroidEnv current-activity API. The repository's independent EEST trace harness already uses a task-agnostic regex accepting both `topResumedActivity` and `mResumedActivity`, showing that the narrower B2 parser was not the only available contract.
4. No raw `am start`, AndroidWorld response, `dumpsys activity`, `dumpsys window`, or UI-tree output was retained for the eight foreground failures. Framework-service checks at the beginning/end do not prove individual launch success.

### Classification

The observed value `foreground_package=None` is real, but the v0.2 evidence cannot distinguish:

- `LAUNCH_FAILED_OR_TIMED_OUT`: activity never reached foreground;
- `FOREGROUND_PARSER_FALSE_NEGATIVE`: activity was foreground but the one-format parser missed it;
- a transient ADB/controller failure between launch and provenance.

This is a **definitive collector contract bug** even though the underlying branch remains unresolved: a qualification collector must retain the raw launch result and use multiple concordant foreground witnesses before assigning a failure class. The repeated `None` across four apps is not evidence that four app packages were wrong.

## 3. Literal `SAVE` and real locator authority

### Direct evidence

1. The literal did not originate in the frozen family config. `contacts_utils.add_contact()` in AndroidWorld hard-codes `actuation.find_and_click_element("SAVE", env)` after an INSERT intent.
2. `find_and_click_element()` searches only AndroidWorld a11y elements' `text` and `content_description`, accepts Levenshtein distance ≤1, and does not use resource ID, class, package, or node relations.
3. Both Contacts variants fail while seeding contacts. Both SMS variants fail for the same reason because the SMS seed first calls the same `contacts_utils.add_contact()` helper before inserting inbound SMS. The error is therefore not evidence about the Contacts-list or SMS-conversation destination UI.
4. The collector's generic onboarding pass tries the same five labels (`Skip`, `Don't allow`, `Continue`, `OK`, `Got it`) for every app and swallows failures. AndroidWorld's own app setup specifies materially different flows: Markor needs four `NEXT` actions plus `DONE`, `OK`, and file-access permission; Expense needs `NEXT`/`CONTINUE`; SMS needs default-app selection; Contacts needs its own `Skip`/notification flow.
5. No failing UI tree or screenshot was stored before the exception.

### Locator verdict

The real stable locator for the contact-editor save control is **unknown from v0.2**. It cannot honestly be declared text, content-desc, resource-id, or a node relation after the fact. A new DEV-only inspection must retain raw trees and evaluate a preregisterable, task-agnostic hierarchy: unique package-scoped resource ID; unique normalized content description; unique normalized text; then a unique semantic node relation to the editor/form action container. Each resolution must require visibility/enabled/clickable ancestry and log all rejected candidates. Coordinates and app/task-name branches are forbidden.

This class is `APP_SPECIFIC_SETUP_MISMATCH` plus `COLLECTOR_LOCATOR_DEFECT`, not a role-binding failure.

## 4. Files/Markor nonsensical reset count

### Direct evidence and mechanism

The collector calls explicit ADB with separate arguments equivalent to:

`adb -P 5038 -s emulator-5554 shell sh -c "find <directory> -maxdepth 1 -type f | wc -l"`

ADB serializes remote shell arguments into a command string. Without preserving quoting around the `sh -c` payload, the remote outer shell interprets the pipe and invokes `sh -c find ...`; the inner shell executes only `find`, whose default path is `.`. The frozen stderr repeatedly reports `find: ./proc/...`, which is impossible for the intended `/storage/emulated/0/Download -maxdepth 1` query and directly confirms this parse. Completed calls return huge line counts such as 1,153,714 or 1,523,564; timed-out calls report return code `None` with the same recursive `/proc` errors.

This is a **definitive collector bug**, not device residue. The generic correction is to execute `find <fixed directory> -maxdepth 1 -type f -print` without `sh -c` or a remote pipe and count nonempty output lines locally, while retaining raw stdout/stderr/return code. It must reject output outside the requested directory.

## Claim–evidence matrix

| Candidate claim | Evidence | Classification | Verdict |
|---|---|---|---|
| 5038 remained one continuously managed server | PID changed 3208→29964; controller can restart silently | environment lifecycle + collector observability | Rejected |
| 5038 loss explains all 16 failures | Most reset/foreground failures predate 13:18:28; `SAVE` failures straddle restart | causal timing | Rejected |
| Framework services being healthy proves launches worked | Service checks do not capture launch response or resumed component | collector contract | Rejected |
| The four apps were not foreground | Parser returned `None`, but raw dumpsys and launch status were discarded | unresolved launch vs parser | Not identifiable |
| B2 foreground parser is sufficient | Only `mResumedActivity` accepted; no fallback witnesses | collector bug | Rejected |
| `SAVE` is the correct stable control locator | Hard-coded helper assumption; no failure-state tree retained | app setup + locator bug | Unsupported |
| SMS failure occurred in SMS destination UI | It failed in shared contact seeding before SMS destination capture | failure-chain evidence | Rejected |
| Files/Markor had over one million files after reset | stderr proves recursive `find .`; values are malformed command output | collector bug | Rejected |
| v0.2 provides evidence about timing × ambiguity | No qualified snapshot and no generation call | claim boundary | Rejected |

## Generic correction and DEV certificate gate

A new collector version may make only task-agnostic changes:

1. Own one locked 5038 daemon process, prohibit AndroidEnv implicit restart, record PID/path/hash/start time before and after every check, and fail immediately on identity change.
2. Launch with an explicit resolved component, record raw `am start -W`, and require concordance among package/activity, UI-tree package, and at least one resumed/focused activity witness.
3. Replace remote `sh -c` pipelines with direct commands and local parsing; retain raw results.
4. Replace text-only setup clicks with the frozen locator hierarchy above; store the pre-click tree, candidate set, chosen witness, and post-click state. App-specific onboarding must be completed as a declared DEV setup prerequisite, not hidden inside a generic selector loop.
5. Add corruption tests for daemon PID drift, silent restart attempts, `topResumedActivity`/`mResumedActivity`/window formats, non-OK launch responses, ambiguous/missing locator witnesses, and shell-output path escape.

Before any v0.3 freeze, a model-free DEV certificate must show repeated reset → seed → launch → foreground → UI dump → screenshot → cleanup checks across multiple apps, with continuous framework services and the same explicitly managed 5038 PID. If that certificate fails, the result remains `NOT_ELIGIBLE` and no v0.3 pool may be frozen. If it passes, v0.3 still requires new entity values, new setup seeds, a new protocol/lock, and one new one-shot candidate pool; no v0.2 item can be reused.

## Stop/continue decision

The root-cause audit supports continuing only to a separate DEV infrastructure qualification. It does not authorize Phase C, model generation, a held-out capture, or hypothesis interpretation. Generation-call count for this audit is exactly zero.
