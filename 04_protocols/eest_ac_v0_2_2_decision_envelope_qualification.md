# EEST-AC v0.2.2 Decision Envelope Qualification Protocol

Frozen: 2026-08-04, before any v0.2.2 model generation call.

## 1. Scope and inherited evidence boundary

This is a non-scoring controller qualification, not a memory-efficacy experiment. It has no arms, no paired comparison, no online M-RISK path, no task-success claim, and no permission to start a 9-cell or 48-cell batch.

EEST-AC v0.2.1 stopped after 1/3 probes. Its two Q-SWIPE outputs contained semantically appropriate canonical swipe payloads, but the complete decisions were rejected because their 27- and 29-character intent strings exceeded a manually imposed 24-character schema limit. The adapter received no task action. That screenshot, instruction, and both outputs are development-contaminated and may be used only for offline replay; they cannot count as v0.2.2 live evidence.

The protected H17/r79 legacy WIP remains outside this namespace and must not be modified, deleted, staged, or committed.

## 2. Single falsifiable question

Can one machine-readable full-decision-envelope contract allow the frozen real model to produce an executable canonical command, initially or after at most one control-plane repair, without allowing an arbitrary short limit on purely descriptive metadata to create a false rejection?

A PASS qualifies only the shared controller contract for a separately preregistered next phase. It does not support M-SLOTS, M-RISK, memory, or task-efficacy claims. A FAIL leaves the work at the controller floor.

## 3. One authoritative full-envelope source

One machine-readable v0.2.2 contract must define and drive or be exhaustively machine-checked against all of the following:

1. top-level required fields and additional-property policy;
2. field authority class and validation policy;
3. status/action phase relations;
4. every canonical action variant, its fields, bounds, phase, example, and adapter operation;
5. evidence item fields, bounds, scope values, and authorization role;
6. citation syntax, uniqueness, and authorization role;
7. intent type, non-empty semantics, deterministic normalization, storage, display, and repair policy;
8. executor prompt, JSON schema, parser behavior, repair diagnostics, and adapter conformance.

Generated prompt and schema artifacts must match their source exactly. A full-envelope conformance matrix must cover each rule above rather than only action variants.

## 4. Field authority and failure permissions

### 4.1 Action-authoritative control plane

`status`, `action`, `evidence`, and `citations` can change what the controller executes, what value it carries across pages, or whether it declares completion. Missing fields, wrong JSON types, unknown fields, ambiguous action aliases, invalid status/action phase combinations, invalid or out-of-bounds action fields, malformed evidence, and unknown or malformed citations fail closed. A control-plane error may consume exactly one syntax-repair call; an invalid repair terminates the probe.

### 4.2 Descriptive observability plane

`intent` is required only for human-readable observability. It cannot authorize an action, evidence use, citation use, or completion, and it never participates in adapter mapping. It must be a JSON string and must remain non-empty after whitespace normalization. A missing, non-string, or whitespace-only intent is schema-critical and may require repair.

Length alone is not a command-validity condition. A non-empty string of any length accepted under the frozen 256-token generation cap is handled deterministically without another model call:

- preserve `sha256(UTF-8(raw_intent))`;
- record raw Unicode-code-point length;
- normalize whitespace by stripping leading/trailing whitespace and collapsing every run recognized by the runtime's Unicode whitespace semantics to one ASCII space;
- record normalized Unicode-code-point length;
- keep at most 256 Unicode code points in the decision-log display value and record whether display truncation occurred;
- record `metadata_normalized` and ordered provenance (`canonical_metadata`, `whitespace_normalized`, and/or `display_truncated_256_codepoints`).

The 256-code-point display limit is an observability-storage bound aligned with the total 256-token completion budget and conservative for CJK-like one-code-point-per-token text. It is not tuned to the v0.2.1 values 27 or 29, and exceeding it never invalidates or changes `status`, `action`, `evidence`, or `citations`. The raw model-call record remains the authoritative full-output archive.

Metadata-only whitespace normalization or display truncation must not trigger a repair call.

## 5. Deterministic action normalization boundary

The v0.2.1 safety boundary is retained: only complete, semantically unique aliases may normalize. Supported swipe aliases are frozen direction-plus-distance and signed-delta forms with explicit direction and bounds checks. No silent clamp is allowed. `recent_app` remains unsupported and cannot map to back or home. Action normalization may never modify envelope authority fields.

## 6. Offline gates

All gates are conjunctive and must pass before live generation:

1. Replay both contaminated v0.2.1 Q-SWIPE outputs. Each must recover a valid canonical swipe decision with identical semantic action category and complete intent provenance. The replay is development evidence only.
2. Generate and verify the full-envelope prompt/schema/parser/repair/adapter conformance matrix.
3. Test intent at empty/non-string/whitespace-only, whitespace, Unicode, boundary, high-entropy, and very-long display cases. Metadata-only normalization must use zero repairs; schema-critical intent errors must repair or reject.
4. Test every status/action phase relation, top-level required/additional field rule, action form, evidence/citation authority rule, and control-plane repair path.
5. Recompute an exact Qwen-tokenizer maximal-shape certificate under `max_new_tokens=256`; no example or accepted maximal decision may rely on truncation tolerance.
6. Pass the EEST focused suite and full repository regression. The known protected r79/r78 frozen-manifest conflict remains visible if it is the only failure.
7. Pass old-protocol isolation, protected-legacy hash checks, the v0.2.2 lock, source scans for forbidden production branches, and a real-environment preflight with zero generation calls.

Failure of any gate forbids live v0.2.2 probes.

## 7. Frozen live qualification boundary

Maximum: three new, non-scoring, reversible, single-command probes. They must not reuse the executed v0.2.1 Q-SWIPE home-to-app-drawer instruction, screenshot, or output. Before generation, a separate lock freezes exact order, model ID/revision/backend, seeds, prompt/schema/parser/adapter hashes, setup/reset policy, intended action category, and probe configuration.

Required categories:

1. one canonical swipe from a harness-prepared non-contaminated state;
2. one canonical `open_app` action;
3. one canonical `press_back` or tap-class navigation action.

Each probe permits one initial call plus at most one repair call, and repair is allowed only for a control-plane or schema-critical error. The runner records raw output; intent raw hash and length; normalized/display value and provenance; control-plane validation; accepted canonical action; adapter audit; environment execution; stabilized before/after state; calls, tokens, and time; and reset evidence.

After the first generation call, no implementation, prompt, schema, adapter, configuration, or task order may change. Intermediate single-cell evidence must not be used for tuning. Any hard failure stops the remaining probes; unexecuted probes are explicitly marked `not_run_due_pre_registered_hard_stop`, and no replacement cell may be appended.

Hard failures include: no valid command within one allowed control-plane repair; metadata-only repair use; wrong category; schema truncation; missed call accounting; unsupported adapter mapping; no environment execution; missing required state change; or reset failure.

## 8. PASS rule

All conditions are conjunctive:

- 3/3 probes obtain a valid canonical command initially or within one control-plane repair;
- 3/3 pass adapter mapping, environment execution, required stabilized state change, and reset;
- all three preregistered categories are covered;
- schema truncations = 0;
- raw calls = attempt records = counters in every probe;
- metadata-only normalization triggers zero repair calls.

Initial direct-command rate, pass-after-control-repair rate, and metadata-normalization rate are reported separately.

## 9. Stop and final evidence

After three probes or the first hard failure, stop immediately and perform offline analysis only. Do not select efficacy tasks, start 9/48 cells, or enable M-RISK.

The final record must include per-probe evidence; initial/repair/metadata-normalization rates; category coverage; calls, tokens, and time; full-envelope conformance; claim-evidence verdict; v0.2.1 contaminated replay; start/end legacy hashes; lock verification; remaining-process audit; commit/tag; and the explicit next-step boundary.
