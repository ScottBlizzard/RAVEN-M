# EEST-AC v0.2.1 Action Contract Qualification — Final Analysis

Date: 2026-08-04

Study: `eest_ac_v0_2_1_action_qualification_20260804`

Verdict: **FAIL — remain at the controller floor**

## 1. Conclusion boundary

The frozen real-model qualification stopped after the first probe, exactly as preregistered. Q-SWIPE remained invalid after its one allowed repair, so Q-OPEN-APP and Q-PRESS-BACK were not started. No efficacy task, arm comparison, 48-cell batch, or online M-RISK cell was started.

This is not evidence for or against M-SLOTS. It is evidence that the shared prompt → complete-decision schema → adapter contract is still not qualified. The failure is narrower than v0.2: both live outputs contained a semantically appropriate, field-complete, in-bounds canonical `swipe` action object. The enclosing decision was nevertheless invalid because its `intent` exceeded the schema's 24-character maximum, including after repair. Because qualification is conjunctive, the adapter correctly received no task action and AndroidEnv executed no task action.

## 2. Frozen runtime and preflight

- Candidate source: `1722430f7674247fb41a4f297ccc2792f1c1863a`, tag `eest-ac-v0.2.1-qualification-candidate-3-20260804`.
- Qualification lock commit: `564426f`, tag `eest-ac-v0.2.1-qualification-lock-20260804`.
- Lock check: 22/22 frozen paths matched; 0 mismatches.
- Model: `Qwen/Qwen3-VL-32B-Instruct`.
- Revision: `0cfaf48183f594c314753d30a4c4974bc75f3ccb`.
- Backend: `qwen3_vl_32b_transformers_bf16_4x4090_v1`.
- Runtime: loaded; 2400×1080 RGB observation; accessibility tree available.
- Adapter preflight: all 10 canonical action types present.
- Run root before start: absent/empty.
- Model generation calls before qualification: 0.

The first runtime-preflight invocation outlived its five-minute shell wrapper while AndroidWorld was installing a temporary dependency and then exited without a report. It made no generation calls and created no qualification run root. With no preflight process remaining and the emulator ready, the exact frozen preflight was rerun without implementation changes and passed. This operational event is not counted as a model or qualification retry.

## 3. Per-probe results

| Cell | Probe | Intended category | Initial | One repair | Adapter | Environment task action | Reset | Result |
|---:|---|---|---|---|---|---|---|---|
| 1 | Q-SWIPE | swipe | schema invalid | schema invalid | not reached | not executed | pass | hard FAIL |
| 2 | Q-OPEN-APP | app navigation | not run | not run | not run | not run | not run | stopped |
| 3 | Q-PRESS-BACK | navigation press | not run | not run | not run | not run | not run | stopped |

### Q-SWIPE raw evidence

Initial output:

```json
{"status":"continue","action":{"type":"swipe","x":0.5,"y":0.75,"x2":0.5,"y2":0.25,"duration_ms":500},"intent":"swipe up to open app drawer","evidence":[],"citations":[]}
```

- The action object is already a direct canonical `swipe`; no alias normalization is needed.
- Coordinates and duration are within the frozen contract.
- The complete decision fails: intent length 27 > 24.
- Error: `DECISION_SCHEMA_INVALID:intent: 'swipe up to open app drawer' is too long`.

Repair output:

```json
{"status":"continue","action":{"duration_ms":500,"type":"swipe","x":0.5,"x2":0.5,"y":0.8,"y2":0.2},"intent":"swipe up to reveal app drawer","evidence":[],"citations":[]}
```

- The repaired action object is also a direct canonical `swipe` and is not identical to the initial action object.
- The complete repaired decision still fails: intent length 29 > 24.
- Error: `DECISION_SCHEMA_INVALID:intent: 'swipe up to reveal app drawer' is too long`.
- Canonicalization provenance is therefore `direct_shape_but_full_decision_rejected_before_acceptance` for both attempts. There is no accepted decision-level canonicalization record.

The repair trace was bounded to one call and remained transparent. It named the schema error and included the rejected output, but it did not make the numerical 24-character envelope constraint actionable to the model. This exposes a live decision-envelope contract gap that the action-only 10/10 conformance matrix did not test.

## 4. Pass rates and coverage

- Initial complete-decision pass rate among executed probes: 0/1 = 0%.
- Pass within at most one repair among executed probes: 0/1 = 0%.
- Preregistered qualification count: 0/3 canonical decisions within one repair.
- Full schema + adapter + execution + reset chain: 0/1.
- Reset alone: 1/1.
- Required categories: swipe, app navigation, navigation press.
- Attempted categories: swipe.
- Achieved categories: none. A merely emitted but schema-rejected action object does not count as coverage.
- Schema truncations: 0. Neither response hit the 256-token cap.

## 5. Calls, tokens, and time

| Quantity | Planned/frozen maximum | Realized |
|---|---:|---:|
| Qualification cells | 3 | 1 |
| Initial calls | 3 if all cells run | 1 |
| Repair calls | up to 3 if needed | 1 |
| Raw call records | up to 6 | 2 |
| Attempt records | up to 6 | 2 |
| Reported calls | up to 6 | 2 |

Raw calls = recorded calls = attempts = reported calls = 2. The planned/actual difference is fully explained by the preregistered hard stop after Q-SWIPE; it is not missing accounting.

- Initial usage: 3,352 prompt + 66 completion = 3,418 tokens; 8.447 s model latency.
- Repair usage: 3,713 prompt + 64 completion = 3,777 tokens; 8.499 s model latency.
- Total: 7,065 prompt + 130 completion = 7,195 tokens.
- Combined model latency: 16.946 s.
- Executed-probe wall time: 72.813 s.
- Whole runner wall time, including home reference/setup and final reset: 182.110 s.

## 6. Offline replay and conformance evidence

The frozen replay of all 18 v0.2 raw outputs remains:

| Class | Count |
|---|---:|
| original invalid | 18 |
| safely normalizable | 8 |
| must repair | 10 |
| canonical direct | 0 |
| repair repeated initial invalid action | 9 |

Offline action conformance remains 10/10 for prompt syntax/example presence, schema example acceptance, and adapter mapping:

| Action | Schema | Adapter operation | Offline verdict |
|---|---|---|---|
| tap | pass | click | conformant |
| long_press | pass | adb_long_press | conformant |
| swipe | pass | adb_swipe | conformant |
| type_text | pass | input_text | conformant |
| press_back | pass | navigate_back | conformant |
| press_home | pass | navigate_home | conformant |
| press_enter | pass | keyboard_enter | conformant |
| open_app | pass | open_app | conformant |
| answer | pass | interaction_cache_answer | conformant |
| wait | pass | sleep | conformant |

The maximal high-entropy serialized decision was 200 Qwen tokens, below the frozen 256 completion-token cap. Focused tests passed 59/59. Full regression remained 1,059 passed and one expected failure: the transparently preserved legacy r79/r78 frozen-manifest conflict.

## 7. Failure classification

Primary class: `decision_envelope_schema_contract_not_closed`.

Specific mechanism: `intent_max_length_not_satisfied_after_one_repair`.

It is not:

- schema truncation;
- an unsupported canonical action;
- an adapter mapping failure;
- an AndroidEnv execution failure;
- a reset failure;
- a missed model call; or
- an infrastructure retry disguised as controller failure.

The frozen implementation did the correct safety-preserving thing by refusing to execute a decision that failed its complete schema. The research-relevant defect is that offline conformance validated action forms but did not close the prompt/schema contract for decision-envelope constraints such as `intent.maxLength`.

## 8. Claim–evidence verdict and next boundary

Q-C4 fails: the real model did not produce a complete accepted canonical decision within one repair, 3/3 coverage was not obtained, and no task action reached adapter/execution. Q-C5 and Q-C6 pass: accounting is exact, early stop worked, isolation was preserved, and no efficacy run started. The detailed Q-C1–Q-C6 verdict is in `claim_evidence_v0_2_1_verdict.md`.

The project remains at the controller floor. The next allowed round is a separately frozen controller-contract repair qualification. This run may not be modified, rerun as if blind, rescored as efficacy, or used to start 48 cells. M-RISK remains offline.

## 9. Raw evidence anchors

- Runtime preflight: `runs/eest_ac_v0_2_1_offline_gates_20260804/preflight_runtime_final.json` (`a6c0a82b...c39da`).
- Start record: `runs/eest_ac_v0_2_1_action_qualification_20260804/qualification_start.json` (`298ac902...3d57`).
- Raw calls: `runs/eest_ac_v0_2_1_action_qualification_20260804/probes/01_Q-SWIPE/model_calls.jsonl` (`63b08898...238`).
- Attempts: `runs/eest_ac_v0_2_1_action_qualification_20260804/probes/01_Q-SWIPE/attempts.json` (`7dcb4b9b...45f3`).
- Probe result: `runs/eest_ac_v0_2_1_action_qualification_20260804/probes/01_Q-SWIPE/probe_result.json` (`eafa7d4b...053`).
- Completion/early-stop record: `runs/eest_ac_v0_2_1_action_qualification_20260804/qualification_complete.json` (`d14fbbf6...c89`).

All full hashes are preserved in `eest_ac_v0_2_1_qualification_metrics.json`.
