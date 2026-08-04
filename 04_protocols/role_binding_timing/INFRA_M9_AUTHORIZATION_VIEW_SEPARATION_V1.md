# INFRA-M9 Authorization-View Separation V1

## Scope and immutable predecessor

M8 remains immutable `FAIL_AUTHORIZATION_VIEW_DERIVATION` with first edge `PROCESS_IDENTITY:prelaunch_baseline:AUTHORIZATION_CANDIDATE_IDENTITY_MISSING`. M9 asks only whether explicit, disjoint authorization views remove that generic false rejection while retaining all M4–M8 safety controls. It is zero-model, DEV-only infrastructure qualification: generation calls and held-out captures are fixed at zero, and no role-binding or memory claim is permitted.

## Machine authority model

Every gate takes one complete process snapshot and derives four disjoint views:

1. `trusted_runner_root`: PID, creation time, path and command are frozen at runner start. It can prove ancestry but is not a project role candidate.
2. `project_authorization_candidates`: a process enters only through a locked direct project binary path, ownership of a controlled port, or a separately admitted descendant role. Only this view is evaluated for project-role completeness and role assignment.
3. `support_only_ancestry_nodes`: current parent-chain nodes used for existence, ordering and PID-reuse evidence only.
4. `unrelated_observed_processes`: all remaining observed rows.

Support-only and unrelated rows cannot be adopted as core, assigned a project role, selected as a cleanup target, or own a controlled port. A controlled-port owner is routed to the candidate view and must satisfy its role policy. 5037 remains an unconditional veto. Missing or ambiguous required direct ancestry fails closed. The complete trigger snapshot and all four derived views are persisted and hashed.

## Offline gates before mutation

The focused suite must cover AccessDenied support, unrelated ancestry, controlled-port support corruption, candidate/support mislabeling, a missing direct chain, runner PID reuse/path/command drift, forbidden core adoption, and exact trigger/view persistence. M4–M8 regressions, namespace tests, completion-schema corruptions, protected-WIP hashes, locked binaries, empty controlled ports, empty M9 output root and the accepted single legacy r79 manifest conflict must all pass their frozen criteria. No live execution is permitted before the lock is committed and tagged.

## One frozen chain

Run exactly one M9 chain: exclusive official ADB 5038 with 5037 forbidden; emulator launch and boot; M6 display/framework quorum; at least 24 burn-in cycles over at least 180 seconds; Settings a11y 3/3; and four-app by three-round DEV grid 12/12. Preserve M3 external logs, M4 journal/first-edge accounting, M5 structural identities, M6 display quorum, M7 runner-owned ADB-client authority and M8 full-snapshot ancestry.

Stop at the first failed gate. The independent M9 finalizer must still emit exactly one schema-valid terminal completion and sealed logs. No patch/retry is allowed inside M9.

## PASS boundary

Only a full 12/12 DEV pass authorizes preparation—but not execution—of a future v0.3 collection protocol. A PASS qualifies infrastructure and authorization-view separation only. Any failure keeps v0.3 unauthorized. Regardless of outcome, M9 does not test held-out collection, model behavior, memory efficacy or the role-binding hypothesis.
