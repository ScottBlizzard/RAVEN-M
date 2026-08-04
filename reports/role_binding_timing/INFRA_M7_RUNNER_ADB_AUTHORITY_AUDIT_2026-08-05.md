# INFRA-M7 Runner-Owned ADB-Client Authority Audit

Date: 2026-08-05

## Verdict

M6 exposed an ownership-policy defect, not an unsafe process: the inherited M5 policy tied `runner_adb_client` authority to a small list of argv shapes. It therefore rejected the frozen runner's own locked, direct-child, explicit-port `adb.exe -P 5038 devices -l` process. M6 remains immutable `PROCESS_IDENTITY_FAILED`; this audit does not relabel it.

The correct M7 boundary is structural ownership. Ordinary short-lived ADB clients may vary in harmless/preregistered subcommand, but must have the locked executable path/hash, exactly one explicit `-P 5038`, the direct frozen runner as parent, bounded creation/active lifetime, and no listening TCP socket. Server lifecycle remains a separate phase-authorized role.

## Frozen M6 invocation audit

The M6 result contains six unique ADB argv shapes:

| Class | Shapes |
|---|---:|
| Generic runner-owned clients | 4: `devices -l`, serial `get-state`, serial `shell getprop`, serial `emu kill` |
| Server lifecycle | 2: `start-server`, `kill-server` |
| Runner server mode | 0 |

All six use the locked project ADB path and exactly one explicit `-P 5038`. The source audit records the hashes and relevant construction sites in the frozen M6/M5/M4/M2/B2.10 chain. Later framework, burn-in, and a11y commands are produced through the same explicit-port builders even though M6 stopped before executing them.

## M7 generic authority predicate

An ordinary runner client must satisfy every condition:

1. exact locked `adb.exe` path and SHA-256;
2. argv begins with that executable and contains exactly one `-P 5038`;
3. direct frozen-runner parent identity, with no `cmd.exe` or PowerShell wrapper;
4. creation after the runner and age no greater than 45 seconds at first authorization;
5. no listening socket on any local TCP port in each observed snapshot/history sample;
6. active lifetime no greater than 45 seconds; and
7. no server lifecycle or server-mode token.

`start-server` is authorized only during launch, `kill-server` only during cleanup, and `nodaemon server`, `fork-server`, or other runner server mode is forbidden. A missing `-P`, any other port, ambiguous duplicate port, missing listener evidence, PID reuse, parent/path/hash mismatch, wrapper ambiguity, listener ownership, or overlong active client fails closed.

Once a client was admitted with listener-bearing evidence and is independently observed absent, its completed identity remains in an auditable ledger. It must not later age into a false cleanup failure merely because continuous history retains it.

## Measurement requirement

M5 snapshots only map a small selected port set, and their continuous history does not attach listener evidence to each transient process. M7 must therefore add a full local TCP listener-port set to every structural process record in both gate snapshots and the 250 ms history sampler. The complete triggering snapshot must be written before a failure returns.

This change does not authorize arbitrary server ownership: the unique 5038 server remains the separately registered core identity, 5037 remains forbidden, and a generic client with any listener is rejected.

## Claim boundary and decision

Direct evidence supports only that M6 falsely rejected its own `devices -l` client. It does not establish that boot, display quorum, burn-in, AndroidEnv a11y, or the grid would pass.

**Decision: continue to M7 offline implementation only.** No live mutation is authorized until the generic predicate, listener-bearing history, lifecycle ledger, corruption tests, source audit, complete regressions, protocol, config, schema, and lock all pass and are frozen in a separate commit/tag.
