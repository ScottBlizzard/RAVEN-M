# INFRA-M9 authorization-view separation audit

## Verdict

M8's first edge is a verified generic view-semantics defect, so the next step is **eligible for M9 offline implementation only**. M8 remains immutable `FAIL_AUTHORIZATION_VIEW_DERIVATION`; this audit is not a runtime qualification and contains zero model calls or device mutations.

## Direct evidence

The frozen M8 trigger contains 362 full process rows and 11 `structural_processes` rows. Four of the 11 were selected only because their broad name was `crashpad_handler.exe`; the other seven were ancestors added by `enrich_structural_records`. The AccessDenied row that triggered M8's failure was an ancestry-only external process with no project authority. All controlled ports were empty.

M8 then used the same overloaded set in nine distinct places: snapshot declaration, candidate derivation, role-loop input, policy history, baseline, discovery, continuous history, core registration, and failure provenance. The failure provenance is complete, but the persisted candidate semantics are wrong. Broad process-name membership is not sufficient project identity evidence.

## Frozen M9 boundary

M9 must derive four disjoint views from the complete OS snapshot:

1. `trusted_runner_root`: exact PID, creation time, path and command frozen at runner start; it proves ancestry but receives no project role.
2. `project_authorization_candidates`: exact locked project binaries, controlled-port owners, or descendants admitted under a frozen role. Only this view is evaluated for role completeness and role assignment.
3. `support_only_ancestry_nodes`: nodes used only to prove direct parent existence, creation ordering and PID reuse. AccessDenied support is permitted as observation evidence but never gains authority.
4. `unrelated_observed_processes`: all remaining rows; observation only.

Global vetoes remain independent of view membership: 5037 presence, a controlled port owned by a support/unrelated row, runner identity drift, an incomplete or ambiguous required ancestry chain, candidate PID reuse, or incomplete candidate role evidence all fail closed.

M9 must assert that support/unrelated rows cannot be adopted as core, assigned a role, selected for cleanup, or own a controlled port. The failure artifact must preserve the complete trigger plus all derived views exactly. No PID-specific or AccessDenied-specific exception is justified.

## Claim–evidence boundary

- M8 overloaded-view defect: directly verified.
- M9 view implementation and tests: not yet evaluated.
- Exclusive 5038, emulator, framework, burn-in, accessibility and DEV grid: not evaluated in this audit.
- Held-out collection, model behavior and role-binding hypothesis: not evaluated.

The machine-readable ledger is stored under `05_project/artifacts/role_binding_timing/infra_m9_authorization_view_audit/`.
