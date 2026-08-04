# INFRA-M8 Full-Snapshot Ancestry Qualification v1

Status before execution: frozen zero-model, DEV-only infrastructure protocol. M7 remains immutable.

## Question and non-claims

The only question is whether a complete OS process observation can prove PID existence/currentness/ancestry while a separate filtered view alone governs project-role authority. PASS requires the entire chain through Settings 3/3 and the four-app by three-round DEV grid 12/12. PASS authorizes preparation, not execution, of v0.3. It does not test held-out data, model behavior, memory or role binding. Generation calls and held-out captures are exactly zero.

## Two-view contract

One OS enumeration produces:

- `observation_universe`: all observed PID, PPID, creation-time and identity records. It alone governs existence, current identity, PID reuse and parent-chain traversal.
- `authorization_candidates`: the hash/listener-enriched project-relevant projection. Only this view may receive a project role.

Every current candidate must map to exactly one equal PID+creation identity in the universe. The frozen runner must exist with its exact identity. A duplicate PID, truncated universe, missing runner, creation mismatch or candidate/universe mismatch fails closed. An unrelated or universe-only parent proves only existence; it receives no role.

Runner ADB clients retain all M7 requirements: exact official path/hash; argv beginning `-P 5038`; direct frozen-runner parent; creation after runner; active lifetime at most 45 seconds; complete evidence of zero listening ports; no PID/argv drift. `start-server` is launch-only, `kill-server` cleanup-only, and server mode is forbidden. Parent traversal uses only the current complete universe; stale history cannot replace a missing or reused parent.

Each gate persists `process_snapshot.json` with the full universe and `derived_authorization_view.json` with candidate links/hashes. A failure embeds both. The 250 ms history retains a complete compact PID/PPID/creation identity universe for every sample plus rich listener-bearing candidates.

## Preserved chain and gates

M8 reuses read-only M3 external logs, M4 journal/terminal accounting, M5 structural roles, M6 display quorum, and M7 generic ADB-client authority. Before live: compile, M8 property/fault tests, M7/M6/M5/M4 focused regressions, namespace regression, full regression with only the known frozen-r79 manifest conflict, schema corruption, source isolation, protected/binary hashes, exact base hashes, and zero-mutation runtime preflight.

After the freeze commit/tag, exactly one chain may run: exclusive 5038; emulator launch; boot; display/framework quorum; at least 24 cycles and 180 seconds burn-in; Settings a11y 3/3; four DEV apps by three rounds 12/12; cleanup and log sealing. First failure stops. No code/rule edit or retry occurs inside M8.

All scenes are DEV-contaminated. Protected r79 WIP, frozen predecessors, LaTeX and prior verdicts remain untouched. No push.
