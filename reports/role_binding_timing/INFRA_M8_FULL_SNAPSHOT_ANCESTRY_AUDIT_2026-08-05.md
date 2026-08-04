# INFRA-M8 full-snapshot ancestry audit

This is a zero-model, read-only audit of frozen M7. M7's verdict, artifacts and tags remain immutable.

## Direct finding

At M7's trigger, runner PID 1912 with the exact frozen creation identity existed in `all_processes` but not in `structural_processes`. The rejected `start-server` client had already exited, so the server's current filtered ancestry no longer selected the runner. The inherited policy used the filtered map both for project-role authorization and general process existence. This is the verified domain mismatch behind `RUNNER_PARENT_IDENTITY_NOT_CURRENT`.

## Filter/join ledger

Ten M7 joins were audited. Four need M8 correction:

- current PID existence and runner identity were checked in the authorization subset;
- helper ancestry traversal received the same filtered map;
- runner PID reuse lacked an explicit full-universe comparison;
- already-ledgered clients used a synthetic runner-only map rather than current OS evidence.

Two provenance gaps were also found: continuous history retained filtered candidates rather than a compact complete PID/PPID/creation-time universe, and the failure record did not persist a separately named/hash-linked authorization view. Candidate union, core-role validation and role-candidate baseline reuse correctly belong to the filtered authorization view and should not be broadened.

## M8 boundary

M8 must expose two machine-audited views from one process observation:

1. `observation_universe`: every observed OS PID with PID, PPID, creation time and identity, used for existence, currentness, PID reuse and parent-chain traversal;
2. `authorization_candidates`: hash/listener-enriched project-relevant processes, used for roles and action-specific authority.

A non-project parent may prove existence but gains no project role. A runner-owned ADB child still requires the frozen executable path/hash, leading `-P 5038`, direct frozen-runner identity, creation window, bounded lifetime and zero listener ownership. Missing/truncated/ambiguous universe evidence fails closed.

Every gate must persist the full snapshot and a separately hashed derived authorization view. Continuous history must retain a complete compact identity universe and the richer candidate records. No PID-specific exception is permitted.

Decision: `ELIGIBLE_FOR_M8_OFFLINE_IMPLEMENTATION_ONLY`. This audit supplies no runtime, accessibility, held-out, memory or role-binding evidence.
