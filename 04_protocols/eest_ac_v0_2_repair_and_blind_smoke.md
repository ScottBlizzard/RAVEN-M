# EEST-AC v0.2 Repair and Blind-Smoke Protocol

Status: frozen before implementation and before any v0.2 model generation call  
Research namespace: `raven_m.eest_ac` only  
Legacy boundary: protocol-v1, B0–B3/M0, H17/rXX, and the three preserved r79 WIP files are read-only and out of scope.

## 1. Corrected interpretation of v0.1.1

The four accepted records in v0.1.1 were two records in each of two method episodes. They are an implementation-level existence signal, not four independent task successes and not evidence that M-SLOTS outperforms ordinary summary. B3 and B3-MATCH also retained the correct address. The observed end-to-end failure was destination-role/action binding: the correct value was not applied to the requested destination.

The SMS and Clock instances from v0.1.1 are development-contaminated. They may be used only for deterministic replay and regression tests. They may not produce new held-out claims, online tuning evidence, or v0.2 live cells.

## 2. Shared controller defects that must be repaired first

1. Immediate post-action observation can precede a delayed UI or accessibility transition, producing false no-effect recovery entries.
2. Recovery records omit the canonical action and do not enforce a different action class in an unchanged state.
3. Source, requested field, and destination are not explicit shared task roles, allowing value capture to be confused with destination/action correctness.
4. The v0.1 decision contract can be truncated at the fixed 256-token completion cap.
5. The online counter misses calls when parsing or repair fails, and the evaluator is skipped after controller/model-invalid termination.
6. A task already satisfied on a stable current screen can continue through speculative waits because completion is left entirely to the next model decision.
7. B3-MATCH matches trigger policy and call ceilings, but post-treatment trajectory divergence prevents a guarantee of equal realized calls.

No repair may add an SMS branch, app/task-class branch, contact name, screen coordinate, row/date rule, or H17/rXX guard.

## 3. Frozen v0.2 method boundary

### 3.1 Shared across all online arms

All arms use the same immutable task, deterministic exact-span role parser, GoalLedger, action adapter, observation stabilizer, completion policy, executor prompt/schema, model/revision/temperature, parameter seed, task instance, action budget, model-call budget, and context cap.

The parser emits one immutable `TaskRoleFrame` with exact task spans for:

- source entity: the entity from which a requested value must be obtained;
- requested field: the literal semantic field requested by the task;
- destination entity: the entity to which the value or operation must be applied.

It uses only task text and generic linguistic relations. Unsupported or ambiguous text fails closed before live execution. All three arms receive the same frozen frame; parser output is not an experimental treatment.

### 3.2 Online arms

- `B3`: ordinary-summary baseline using the shared controller.
- `B3_MATCH`: B3 plus one useful ordinary-summary call at each shared eligible opportunity, subject to the same per-candidate and total-call ceilings. No neutral padding is allowed.
- `M_SLOTS`: typed EvidenceLedger, closed GoalLedger, Recovery Registry, and action-relevant Context Compiler. No auxiliary summary or critic calls.

`M_RISK` is excluded from every v0.2 live cell. Risk detection/gating remains offline-test-only, and v0.2 makes no online Risk Gate efficacy claim.

### 3.3 Observation stabilization and Recovery

After every executed action, the controller obtains an initial post-action observation, waits a frozen bounded delay, and obtains a second post-action observation. It may take at most one additional bounded observation when the first two post-action observations disagree.

Each observation has separate pixel and accessibility hashes plus availability metadata. `no_effect_confirmed` is allowed only if:

1. accessibility data is available in the before observation and every post-action observation;
2. the pixel hash equals the before pixel hash in every post-action observation;
3. the accessibility hash equals the before accessibility hash in every post-action observation; and
4. all post-action observations agree with one another inside the frozen window.

Any disagreement, missing accessibility tree, or late transition yields `changed_or_uncertain`, never a Recovery entry.

A Recovery record contains the canonical action, its deterministic signature, action class, and stable combined state signature. In the same stable state, the controller blocks both an exact repeat and any proposal from the same action class and returns a deterministic instruction to choose a different action class. The block consumes no environment action and no auxiliary model call.

Evidence and Recovery output is deterministically sorted and deduplicated.

### 3.4 Compact decision and call/evaluator audit

The v0.2 decision schema removes redundant prose, caps evidence count and string lengths, and remains at `max_new_tokens=256`. A deterministic maximum-shape serialization test and recorded-token replay must fit below the cap. No increase to the cap is permitted.

Raw model calls are derived from append-only call records in every success and failure path. `model_calls == len(model_call_records)` is an invariant. Eligible opportunities, planned auxiliary calls, realized auxiliary calls, and non-realization reasons are recorded separately.

After any non-infrastructure controller/model-invalid termination, the benchmark evaluator is run once read-only before teardown. The result is marked `ran_after_controller_error`; the error is never relabelled as an infrastructure retry. If the evaluator itself fails, that separate failure is recorded transparently.

### 3.5 Generic completion

The completion policy may close only a requirement deterministically derived from exact task spans and a stable transition. In particular, a generic “open target app” requirement is satisfied when an executed `open_app` action exactly matches the parsed target span and the stabilized post-state is changed and available. The rule is lexical/action-semantic, not app-name- or task-class-specific. Once all closed requirements are satisfied, the episode terminates without another model call or speculative wait.

Other tasks remain open until a schema-valid terminal decision or terminal answer. The policy must not infer popups, confirmations, or extra requirements absent from the task literal.

## 4. Falsifiable hypotheses and three-layer binding metrics

### H1 — source→field→value capture

For each positive episode, score whether the value read from the source page is attached to the preregistered source entity and requested field. Report TP/FP/FN and episode accuracy. Multiple records in one episode are not independent task successes.

### H2 — destination-role retention

After leaving the source page and immediately before the value-carrying action, score whether the controller context/decision retains the preregistered destination as destination rather than source. Report correct destination, source-as-destination, other destination, and missing destination counts plus accuracy.

### H3 — final value→destination action correctness

Score whether the correct value is applied to the requested destination in the executed action sequence. This requires both value correctness and destination correctness and is audited from action/UI/evaluator artifacts. Report correct, wrong value, wrong destination, both wrong, and not attempted plus accuracy.

H1 alone is only a capture/mechanism signal. A v0.2 method benefit requires H3 and task success, not record-level accuracy.

### H4 — shared-controller repair

The development replay suite must reject delayed false no-effect, block repeated same-class recovery actions, avoid v0.1 output truncation, count calls on failure, evaluate controller-invalid episodes, and terminate a satisfied open-app negative control without an extra model decision.

### H5 — M-SLOTS task signal

Across the two held-out positives, M-SLOTS must achieve at least one real task success, perform no worse than B3-MATCH in total task success, and obtain at least one end-to-end destination-action paired win over B3-MATCH.

## 5. B3-MATCH fairness language

The only permitted claim is: “B3-MATCH matches the auxiliary trigger policy and per-opportunity/total budget ceiling.” It is forbidden to claim equal actual calls unless the realized records are equal.

For every arm and task report:

- eligible opportunities;
- planned auxiliary calls under the shared trigger policy;
- realized auxiliary calls;
- missed/blocked auxiliary calls and reason;
- the first trajectory divergence explaining different downstream opportunity counts.

## 6. Pre-live gates

No v0.2 model generation call is allowed until all are true:

1. delayed-transition, wrong-destination, repeated-action, output-truncation, early-completion, and negative-example replay tests pass;
2. all focused EEST-AC tests pass;
3. the full repository regression completes, with the preserved r79 frozen-manifest mismatch reported rather than hidden;
4. source isolation finds no legacy controller/guard import and no task/app/name/coordinate branch;
5. static and real-environment preflights make zero generation calls;
6. every selected task instance is deterministic and absent by class and instance hash from prior runs/configs/reports;
7. protocol, config, task hashes, implementation hashes, prompts, schema, schedule, and empty run root are locked before launch.

## 7. Blind nine-cell study

After the gates pass, select and freeze:

- two previously unused positive templates that genuinely require cross-page source→field→destination retention;
- one previously unused current-screen-sufficient or short reversible-navigation negative control;
- arms `B3`, `B3_MATCH`, and `M_SLOTS` only;
- exactly nine cells, each task paired across all three arms.

The order is frozen before launch. From the first generation call until all nine cells either complete or hit a preregistered batch-fatal condition, no single-cell trajectory may be inspected and no code, prompt, schema, config, task, or rule may be modified. Infrastructure retries are allowed only for transport/emulator faults and retain identical task hashes.

The batch stops immediately after nine final cell results. It never auto-expands.

## 8. Preregistered continuation and stopping rules

Continue to another small study only if all are true:

1. all nine cells have no schema truncation, no missing raw calls, and one evaluator result;
2. M-SLOTS succeeds on at least one of the two positives and its positive-task success is not below B3-MATCH;
3. M-SLOTS has at least one end-to-end destination-action paired win over B3-MATCH;
4. the negative control stops without obvious extra operations after completion, and M-SLOTS total negative-control cost is at most 15% above B3-MATCH for calls, tokens, and wall time separately.

Mandatory stops:

- if all arms fail both positives, declare controller floor and stop memory-efficacy experiments;
- if M-SLOTS has zero net task-success paired wins over B3-MATCH, do not start a 48-cell study;
- regardless of result, M-RISK remains excluded until M-SLOTS first shows a non-floor task signal in a valid held-out batch.

## 9. Required final outputs

The post-batch report must include per-cell result and validity; three-layer binding confusion/counts/accuracy; paired win/loss/tie; completion precision/recall; repeated-action recovery; calls/tokens/wall time; planned-versus-realized B3-MATCH accounting and trajectory divergence; claim–evidence verdict; and an explicit pass/fail for every continuation rule.

