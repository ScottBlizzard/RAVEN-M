# INFRA-M5 Process-Identity Semantics v1

## Scope and immutable predecessor

M5 is a zero-model, DEV-only infrastructure qualification. M4 remains immutable `RUNTIME_UNSTABLE` with first edge `FRAMEWORK_RUNTIME:EXCLUDED_PID_DRIFT`. M5 neither edits nor reinterprets M4.

No model generation, held-out capture, role-binding experiment, memory/controller efficacy claim, LaTeX edit, old-result edit, or push is permitted. The three legacy r79 WIP files remain unstaged and hash-protected.

## Falsifiable infrastructure question

Can one structural process-identity policy admit only preregistered project core processes and evidenced official descendants/helpers, while rejecting PID reuse, missing/contradictory identity, unrelated new binaries, parent mismatch, port-owner change, 5038 restart, and any 5037 listener throughout one complete M4-equivalent chain?

PASS is necessary but not sufficient for preparing v0.3. It is not hypothesis or a11y efficacy evidence.

## Identity model

PID alone is never an identity. Each observed identity is the tuple:

`identity_key = pid@create_time`; the remaining fields below are mandatory role evidence rather than substitutes for that key.

1. PID and creation time;
2. absolute executable path and SHA-256;
3. full command line;
4. parent PID plus observed parent identity/ancestry;
5. start time relative to the runner, launcher, and qemu;
6. listening ports;
7. assigned role;
8. first/last observation gate.

At each transition the runner saves the full process inventory, relevant structural records, ancestry, raw netstat, evaluation, and hashes. A 250 ms append-only sampler preserves transient relevant processes and their currently visible ancestors. Any failing evaluation atomically writes the complete triggering snapshot before returning.

## Roles and authority

- `preexisting_unrelated_no_authority`: exact prelaunch PID+creation identity. It may coexist or disappear. It is never adopted, killed, or used as a project role. The same PID with a different creation time is a new process and fails.
- `adb_server`: locked official ADB path/hash, exact `tcp:5038 fork-server server` grammar, unique owner of 5038, immutable PID+creation time after registration.
- `emulator_launcher`: locked launcher path/hash and exact frozen AVD/port/gRPC arguments; PID equals the direct frozen runner `Popen` child and parent identity.
- `qemu`: locked qemu path/hash and frozen arguments, direct launcher parent, unique owner of 5554/5555/8554.
- `runner_adb_client`: locked ADB path/hash, direct frozen runner parent, explicit `-P 5038`, and either the frozen serial or start/kill-server operation. It has no server or kill authority.
- `emulator_bootstrap_adb`: locked ADB path/hash, exact emulator overlay or multidisplay command grammar, start within 300 seconds of qemu, and recorded ancestry to launcher/qemu through only an exact locked command wrapper if needed.
- `crashpad`/`netsimd`: exact locked binaries, start within 900 seconds of qemu, and recorded ancestry to launcher/qemu.
- `emulator_shutdown_helper`: only during cleanup, exact launcher hash and `-kill <frozen qemu PID> -sleep 20`, with recorded core ancestry.
- everything else: fail closed.

Missing path, hash, command, creation time, or required parent evidence cannot authorize a new owned/helper role.

## Permanent vetoes

- Any listener on 5037.
- Any change to the 5038 server PID+creation identity or listener owner.
- Any change to qemu PID+creation identity or owner of 5554/5555/8554 before intentional cleanup.
- Launcher/qemu parent mismatch.
- New relevant process without an authorized role.
- PID reuse, including reuse of a preexisting unrelated PID.
- Continuous sampler error, missing failure snapshot, duplicate terminal record, protected-WIP drift, or unsealed external live log.

## Required offline gates

Before freeze and live mutation:

1. focused tests for official short-lived helpers, runner clients, unrelated/new binaries, PID reuse, parent mismatch, missing evidence, port-owner change, 5038 restart, helper time window, non-adoption, trigger persistence, and write-once failure persistence;
2. M4 terminal-accounting tests;
3. full role-binding-timing namespace;
4. complete project regression, accepting only the already frozen r79 manifest conflict;
5. schema corruption and source-isolation tests;
6. exact binary, psutil, protocol/config/source, protected-WIP, tag/lock, empty-output, no-temp-residue, and zero-listener preflight.

Raw stdout/stderr and SHA-256 are preserved. Offline gates make zero device mutations and zero generation calls.

## One frozen live chain

Exactly one fresh output root and one external temporary log root are permitted:

1. baseline snapshot and non-authority registry;
2. locked 5038 server start and identity registration;
3. exact AVD launch with `ANDROID_ADB_SERVER_PORT=5038`, launcher/qemu registration, and zero 5037;
4. boot qualification;
5. framework qualification;
6. 24 sequential burn-in cycles over at least 180 seconds;
7. Settings same-observation screenshot+a11y 3/3;
8. four-app by three-round DEV grid 12/12;
9. qualified cleanup, continuous-history close, external-log seal, and independent terminal finalization.

Process identity is checked before and after every major gate, each burn-in cycle, each Settings observation, and each DEV grid cell. No source/config/protocol changes or retry are permitted after live start.

## Stop and PASS rules

The first failed gate stops all later experimental gates. Cleanup, sealing, and terminal writing still run, but cannot replace the first edge.

Overall PASS requires:

- no identity-policy issue, no 5037, no 5038/core restart, and a valid continuous history;
- boot and framework PASS;
- 24/24 burn-in cycles and elapsed time at least 180 seconds;
- Settings 3/3 and DEV grid 12/12;
- clean reset/isolation, no owned-process/listener/temp residue;
- exactly one schema-valid completion and sealed logs;
- zero generation calls, model tokens, and held-out captures;
- unchanged protected WIP.

Only that full PASS authorizes **preparation, not execution**, of a separately reviewed v0.3 protocol. Any failure returns `RUNTIME_UNSTABLE`, `PROCESS_IDENTITY_FAILED`, `A11Y_QUALIFICATION_FAILED`, or `LOG_SEAL_FAILED` with the exact first layer and stops M5.
