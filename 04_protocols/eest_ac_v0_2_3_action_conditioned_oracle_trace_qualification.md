# EEST-AC v0.2.3 Action-Conditioned Outcome Oracle Trace Qualification

Status: preregistered before implementation, held-out trace collection, oracle evaluation, or any v0.2.3 model generation call.

## 1. Scope and immutable prior verdict

EEST-AC v0.2.2 remains permanently `FAIL`: 3/3 initial decisions were legal canonical commands and 3/3 mapped, executed, and reset, but only 2/3 met its exact terminal-pixel stability rule. DEQ-BACK-03 produced a real Camera-to-launcher transition while the final exact pixel pair differed. v0.2.3 does not rewrite, relabel, or replace that verdict.

This stage asks one falsifiable question only: can a task-agnostic observation oracle allocate evidence authority by action class so that real semantic transitions are accepted while no-op, wrong-target, dynamic-pixel-only, unstable, contradictory, and missing-critical-evidence traces are not accepted?

Passing supports only eligibility for a separately preregistered live oracle qualification. It supports no M-SLOTS, M-RISK, memory, task-success, or efficacy claim.

## 2. Zero-generation and stopping boundary

- v0.2.3 generation calls must remain exactly zero.
- No model generation endpoint, live model probe, task selection, 9-cell, 48-cell, or M-RISK run is authorized.
- The oracle implementation and machine contract may be frozen once before held-out evaluation.
- Held-out trace collection, labels, order, seeds, and raw hashes must be frozen before the oracle reads the held-out inputs.
- Exactly one held-out oracle evaluation is permitted. Any wrong prediction, false accept, false reject, missing provenance, incomplete hash/accounting record, or coverage failure produces overall `FAIL` and ends the stage. No second threshold, window, witness set, or held-out repair is allowed.

## 3. Single machine-readable evidence-authority contract

The authoritative contract generates or machine-validates the input schema, parser constraints, action-class policies, oracle decision vocabulary, witness/veto vocabulary, and conformance matrix. Production oracle code must contain no App, task, coordinate, H17, or rXX branch.

Every trace contains an action class, canonical action summary, optional resolver evidence, a pre-action observation, a bounded ordered post-action sample sequence, and provenance hashes. Observations expose only generic fields: pixel hash, a11y availability/hash/content/page identity, package/activity/route identity, scroll semantics, and state hash. Labels are stored separately and are not passed to the oracle.

The oracle returns `accept`, `reject`, or `uncertain`, a bounded confidence value, the required witnesses it observed, optional witnesses, vetoes, missing evidence, and deterministic rule provenance. `accept` is the sole positive classification; `reject` and `uncertain` fail closed.

### 3.1 Swipe/scroll authority

Required witnesses for `accept`:

1. pre and terminal a11y evidence is available;
2. the terminal evidence window has stable package, activity, route/page context, a11y page identity, and a11y content/scroll semantics;
3. pre and terminal remain in an allowed same-page context;
4. stable a11y content identity or explicit scroll semantics changes from pre to terminal.

Optional witnesses: exact or changed pixels. Pixel evidence cannot authorize success.

Vetoes/non-accept outcomes: page-context transition, terminal semantic instability, contradictory scroll direction when direction evidence exists, unchanged stable a11y/scroll semantics, or missing critical a11y/context evidence. Dynamic overlay or pixel change alone must be rejected; critical evidence absence is `uncertain`.

### 3.2 `open_app` authority

Required witnesses for `accept`:

1. a generic resolver supplies the allowed target package/activity identity with provenance;
2. terminal target package/activity and a11y evidence are available and stable;
3. the terminal identity matches the resolver target;
4. the transition is not a stable no-op from an already matching state.

Optional witnesses: page/a11y change and pixel evidence. Exact pixels are never required.

Vetoes/non-accept outcomes: stable wrong target is `reject`; stable already-target no-op is `reject`; missing resolver target, package/activity, or terminal a11y stability is `uncertain`. Pixels alone cannot override a target mismatch or missing target evidence.

### 3.3 Navigation-press authority

Required witnesses for `accept`:

1. terminal package/activity/route and a11y page evidence are available and stable;
2. either stable package/activity/route identity differs from pre, or, within the same package/activity, stable page identity/a11y content shows an explainable page transition.

Optional witnesses: pixel change or equality. Exact pixels are never required.

Vetoes/non-accept outcomes: stable no-op, terminal semantic instability, contradictory route evidence, or pure pixel change without semantic identity change are `reject`. If a11y is unavailable and package/activity/route does not independently prove a transition, the result is `uncertain`.

## 4. Development-contaminated replay

The following are development diagnostics only and must be frozen by hash: all three v0.2.2 live transitions; v0.2.2 measurement-contract v1/v2 Settings, Camera, and notification/a11y-missing traces; and any already executed v0.2.1 qualification trace used for compatibility. Every replay row must declare `development_contaminated=true` and `held_out_eligible=false`.

The replay may check directional sanity: v0.2.2 BACK should be described as a semantic cross-context transition under navigation authority, while Camera dynamic-pixel-only and missing-a11y cases must not be accepted merely because pixels changed. Replay accuracy cannot contribute to PASS.

## 5. Held-out trace matrix

The matrix contains at least twelve newly collected real emulator transitions, ordered and seeded before collection: three action classes, each with at least two positives and two negative/control cases. It may not reuse any v0.2.2 live or measurement screenshot/state combination or the executed v0.2.1 Q-SWIPE state.

Harness setup and ground truth may name concrete applications or screens, but production contract/parser/oracle code may not. Ground truth follows the harness-known setup/action/control and is frozen separately from oracle inputs. Each trace stores raw pre/post screenshot hashes, a11y hashes, package/activity/route/page/scroll identities, canonical action, timing/order, and file hashes.

Negative/control coverage across the matrix must include no-op or wrong target/action, dynamic pixels without semantic authorization, and missing or unstable critical evidence. If collection qualification cannot demonstrate two reliable positives and two reliable controls for every action class, the stage stops before evaluation rather than substituting easier traces.

After trace and label freeze, the oracle is executed once over the entire matrix without per-row inspection. Results are unblinded only after all predictions are written.

## 6. Offline gates

Before held-out evaluation:

1. contract/schema/parser/oracle outputs conform to the single machine source;
2. property and negative tests cover missing, contradictory, dynamically changing pixel, same-package page transition, cross-package transition, no-op, and source isolation;
3. DEV replay is hashed and marked ineligible;
4. EEST focused tests pass;
5. the full repository regression has no new failure beyond the transparent protected r79 frozen-manifest conflict;
6. generation-call count is zero and legacy hashes match.

## 7. PASS and reporting

Strict PASS requires all of the following:

- 12/12 or more held-out rows exactly match their frozen `accept`/`reject`/`uncertain` labels;
- false accepts = 0 and false rejects = 0;
- each action class has precision = recall = 1.0 for `accept` and contains at least two positives and two controls;
- every row reports the witnesses, vetoes/missing evidence, confidence, rule ID, input hash, output hash, label hash, and accounting record;
- legacy/process/generation-call audits pass.

The final report includes the row-level confusion matrix, per-class precision/recall, witness provenance, DEV/held-out boundary, hashes, tests, commits/tags, and one Boolean: `eligible_for_separately_preregistered_live_oracle_qualification`. Regardless of PASS or FAIL, the stage then stops.
