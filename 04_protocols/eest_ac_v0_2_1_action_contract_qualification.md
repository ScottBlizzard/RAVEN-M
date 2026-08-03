# EEST-AC v0.2.1 Action Contract Qualification Protocol

Status: preregistered before implementation and before any v0.2.1 model generation.

## 1. Evidential boundary inherited from v0.2

The v0.2 blind smoke ended with 9/9 controller-invalid cells, 18 recorded model calls, and 0 environment actions. Its shared failure was a prompt→schema→adapter contract mismatch. The resulting P2A, P2B, and N2 traces are development-contamination evidence for the action interface; they are not M-SLOTS efficacy evidence and cannot be reused as held-out tasks.

This protocol is not a memory experiment. It contains no arms, no M-RISK online path, no paired success claim, and no permission to start a 48-cell study.

## 2. Single falsifiable question

Can the frozen real model produce, either initially or after exactly one syntax-repair call, a task-agnostic canonical action that:

1. validates against the action contract-derived JSON schema;
2. maps through the contract-audited AndroidWorld adapter;
3. executes in AndroidEnv; and
4. permits the probe to reset cleanly?

A PASS qualifies only the shared action contract for a later, separately preregistered held-out design. It does not support any claim that structured memory is effective. A FAIL leaves the work at the controller floor.

## 3. Implementation scope

All new production logic lives under `raven_m.eest_ac` and new v0.2.1 artifacts. The three legacy H17/r79 WIP files and all frozen v0.2 files remain untouched.

One machine-readable action contract is authoritative for tap, long_press, swipe, type_text, press_back, press_home, press_enter, open_app, answer, and wait. The following must be generated from it or machine-checked against it:

- the action definitions embedded in the v0.2.1 decision schema;
- the complete required-field syntax and compact examples in the executor prompt;
- adapter coverage and mapping conformance.

The prompt retains `max_new_tokens=256`. The repair prompt must name the rejected action, validation errors including missing or extra fields, and legal canonical forms, and demand only corrected JSON. Repeating the same invalid action after repair must terminate transparently as `REPAIR_IDENTICAL_INVALID_ACTION`.

## 4. Deterministic normalization boundary

Normalization is permitted only for syntactically recognizable, semantically unique aliases:

- `press{key=back|home|enter}` may become the corresponding canonical press type;
- a complete `swipe{x,y,direction,distance[,duration_ms]}` may become endpoints using the frozen screen-coordinate convention: right increases x, left decreases x, down increases y, and up decreases y;
- a complete `swipe{x,y,dx,dy[,duration_ms]}` may become `x2=x+dx`, `y2=y+dy`, treating deltas as signed endpoint displacement.

The contract supplies the sole shorthand duration default. Every input and derived coordinate must remain in `[0,1]`; out-of-range results are rejected and never clamped. Mixed shorthand dialects, partial fields, unknown keys, and ambiguous actions are rejected. `recent_app` is unsupported and must never be mapped to back or home.

No SMS, Markor, Clock, task-class, contact, phone-number, fixed-coordinate, template, H17, date-row, rXX, or guard-specific branch is allowed.

## 5. Offline gates before real generation

All gates must pass:

1. Replay all 18 frozen v0.2 raw outputs and report original-invalid, safe-normalization, must-repair, and identical-invalid-repair classifications.
2. Pass the generated-artifact check and prompt/schema/adapter conformance matrix for every canonical action.
3. Pass maximum serialized-decision/256-token checks; no contract example may depend on truncation tolerance.
4. Pass normalization property, direction, boundary, no-clamp, ambiguous-input, unsupported-recent-app, and identical-repair tests.
5. Pass the EEST focused suite and full repository regression. The known r79 frozen-manifest conflict remains visible if it is the only failure.
6. Pass source/legacy isolation and a real environment preflight with `zero_model_generation_calls=0`.

Failure of any gate forbids real qualification probes.

## 6. Frozen real-model qualification probes

Maximum: three non-scoring, reversible, single-model-decision cells. They do not use P2A/P2B/N2 semantics and are not efficacy tasks. Each cell permits at most an initial executor call plus one repair call.

The frozen coverage categories are:

1. one canonical swipe;
2. one canonical open_app or contract-equivalent app-navigation action;
3. one distinct tap or canonical navigation-press action.

The probe configuration fixes model ID/revision/backend, temperature, seed, prompt/schema/contract/adapter hashes, setup/reset policy, intended category, and order before generation. The runner records raw initial and repair outputs, normalization provenance, schema validation, adapter audit, execution result, stabilized before/after states, calls/tokens/time, and reset evidence.

If a probe emits the wrong category, it is a coverage failure; no extra cell may be appended. Any schema truncation, missed call, unsupported adapter action, unrecoverable identical-invalid repair, non-execution, or reset failure immediately stops the remaining probes. No code or configuration may change between the first generation and the final/early-stop record.

## 7. Qualification PASS rule

All conditions are conjunctive:

- 3/3 probes obtain a canonical action within at most one repair;
- 3/3 pass schema, adapter mapping, environment execution, and reset;
- all three preregistered action categories are covered;
- schema truncations = 0;
- raw calls = recorded calls = attempted calls in every probe.

Initial-pass rate and after-one-repair pass rate are reported separately. Regardless of PASS or FAIL, the runner stops after three probes or the first hard failure and performs no efficacy-task selection.

## 8. Required final evidence

The final record must include per-probe evidence; the 18-output replay confusion; the prompt/schema/adapter conformance matrix; initial and repaired pass rates; calls, tokens, and time; failure classes; a claim–evidence verdict; the start/end legacy hashes; and the explicit next-step boundary.
