# INFRA-M7 Runner-Owned ADB-Client Authority Qualification v1

Status before execution: frozen DEV-only infrastructure protocol. This protocol neither edits nor reinterprets INFRA-M6.

## Question and claim boundary

The only question is whether process identity can admit harmless, short-lived ADB clients structurally owned by the frozen runner without enumerating their subcommands, while continuing to reject unrelated clients, listener/server ownership, PID reuse, wrappers, wrong ports and phase-invalid lifecycle commands.

PASS requires the complete maintenance chain through Settings 3/3 and the four-app by three-round DEV grid 12/12. PASS authorizes preparation, but not execution, of a fresh v0.3 collection protocol. It does not test held-out data, model behavior, memory, role binding or the research hypothesis. Generation calls and held-out captures are exactly zero.

## Frozen authority predicate

An ordinary runner ADB client is authorized only when all conditions hold:

1. the executable path and SHA-256 equal the locked official `adb.exe`;
2. argv begins with that executable followed by the global prefix `-P 5038`; later subcommand flags, including `screencap -p`, are not reinterpreted as global port selectors;
3. the direct parent is the current frozen runner PID+creation-time identity, with no `cmd.exe` or PowerShell wrapper ambiguity;
4. client creation is no earlier than runner creation and its observed active lifetime is at most 45 seconds;
5. complete TCP-listener evidence shows no listening port in any sampled state;
6. the PID+creation-time identity and argv hash do not drift or exhibit PID reuse.

The ordinary subcommand has no allowlist. `devices -l`, `get-state`, `shell`, `getprop`, `dumpsys`, input commands and screenshot commands therefore share the same ownership predicate. This grants no server authority.

`start-server` is authorized only in `launch`; `kill-server` only in `cleanup`. `nodaemon server`, `fork-server`, or another server-mode token is forbidden. Missing evidence fails closed. Preexisting unrelated processes are never adopted or killed. Port 5037 is forbidden throughout; the registered 5038 server identity may not restart.

Every gate stores a full process and TCP-listener snapshot. A 250 ms append-only history preserves transient clients, first/last observation, exit state and any listener ever observed. The first triggering snapshot is written once before failure returns. A completed authorized client remains an audited completed identity; an active client is rechecked for age, listeners and argv drift.

## Immutable predecessor and runtime chain

M7 reuses, read-only: M3 external live-log lifecycle, M4 journal/terminal accounting, M5 structural core identities and helper ancestry, and M6 multi-plane display quorum plus cleanup-only official emulator-kill ancestry. The M7 overlay deterministically resolves the frozen M6 config whose SHA-256 is recorded; the derived runtime JSON lives outside the repository and is deleted on exit.

The one live chain is: exclusive 5038 launch; emulator registration and boot; display/framework quorum; at least 24 burn-in cycles and 180 seconds; Settings same-observation accessibility 3/3; four DEV apps by three rounds (12/12); cleanup and external-log sealing. Stop on the first failure, but preserve the M4 journal, first edge, trigger snapshot, terminal completion and cleanup evidence.

## Offline gates and stop rule

Before the freeze tag: compile; focused M7 tests; M6 display tests; M5 identity tests; M4 terminal tests; all role-binding-timing tests; full regression with only the pre-existing frozen-r79 manifest conflict accepted; completion-schema corruptions; source-boundary checks; exact M6-invocation audit; binary/protected-WIP hashes; and a zero-mutation runtime preflight requiring no controlled listeners, no project runtime process, a fresh output root and no M7 temp residue.

If an offline gate fails, live is forbidden. After freezing, exactly one M7 chain may run. Any live failure stops M7. Even after 12/12 PASS, no held-out collection or model call follows automatically.

## Contamination and protected files

All Settings/grid apps and entities are DEV-contaminated. The three r79 WIP files are hash-audited before/after and are never modified, staged or committed. Frozen predecessor artifacts, LaTeX and prior verdicts are read-only.
