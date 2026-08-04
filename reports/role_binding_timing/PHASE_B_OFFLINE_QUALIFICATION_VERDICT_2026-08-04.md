# Phase B — Offline Qualification Verdict

Date: 2026-08-04
Study: `role_binding_timing_stage1_v0_1`
Phase-A parent commit: `9641177544929bf6613e2f1bdbbfc82b0f497608`

## Outcome

**OFFLINE TOOLING PASS; NOT ELIGIBLE FOR GENERATION.**

The independent preregistration, schema, parser, prompt builder, token audit, blinding, oracle qualification, metrics, and zero-generation preflight are implemented and frozen. The model and emulator are reachable through the locked runtime. However, the frozen fresh snapshot manifest contains zero base families, so the required `>=95%` snapshot/oracle qualification over at least eight fresh paired base families is not met. No qualification pilot or Stage-1 cell was launched.

Novelty remains **UNRESOLVED**. This phase supports no timing-effect, memory-efficacy, controller-efficacy, M-SLOTS, M-RISK, or end-to-end task claim.

## Repository hygiene and protected boundary

- The Phase-A `tmp/` residue was confirmed to contain only the two directories created during the Phase-A literature audit: `pdfs/role_binding_phase_a` and `literature_sources/role_binding_phase_a`.
- It was not committed. It was relocated outside the repository to `D:/ZJU/Summer_Camp/_phase_a_audit_sources/role_binding_timing_2026-08-04` for audit retention.
- The formal LaTeX report and all old frozen protocols/results/tags/verdicts were not modified.
- The three legacy WIP SHA-256 values before and after Phase B are unchanged:
  - `episode_controller.py`: `fc0e82e0fde90119365d4f685f080eb4519bf2f602e4bda58de5d4809a40fe33`
  - `protocol_v2_guard.py`: `ff89d6b70be4b4738646d262beb67d7b7e932e9eb95956d940b1c5000a999d10`
  - `test_protocol_v2_2_r79_r78_trace_replay.py`: `5bb1f1e3de673a1072cfee62938b761a62fd69c187d5eadf54bc46b115a3fd0a`

## Frozen design

- Base-family design: matched high/low role-ambiguity state variants; early/late timing is paired within each identical screenshot/UI-tree variant.
- Four cells per family: early-low, late-low, early-high, late-high.
- Two calls per cell: destination grounding, then first target-bearing action.
- One action proposal per cell; no environment execution in Stage 1.
- The logical transcript contains the exact fact once. The other phase contains a deterministic, task-content-free neutral block.
- Call-1 prose is parsed and canonically serialized before Call 2; raw prose cannot change Call-2 context length.
- Fixed model revision `0cfaf48183f594c314753d30a4c4974bc75f3ccb`, backend `qwen3_vl_32b_transformers_bf16_4x4090_v1`, temperature 0, no sampling, 128 completion-token cap per call, no repair/retry.
- Old AndroidWorld, H17/rXX, EEST-P1/P2/N2, and the eight Phase-A screenshots remain DEV-contaminated and are rejected by the held-out snapshot schema.

Primary and diagnostic metrics are frozen separately: `WrongTarget@FirstTargetingAction`, destination-ID grounding, action target ID, post-grounding drift, exact value recall, source-as-target, other-wrong-entity, correct-target-wrong-widget, source/destination role accuracy, confidence, parser failure, and all call/token/time costs.

## Offline evidence

### Focused tests

- Command: project Python, `pytest tests/role_binding_timing -q`
- Result after the token-counter correction: **17/17 passed**.
- Coverage includes schema drift, budget drift, one-fact transcript invariant, exact neutral matching, forbidden-content corruption, BatchEncoding/input-ID regression, strict JSON/parser corruptions, unknown target IDs, three wrong-target subclasses, fresh snapshot hashes, contamination rejection, and blinded-cell uniqueness.

### Token-certificate correction

The first preflight was invalidated because `apply_chat_template` returned a `BatchEncoding` and the initial implementation counted its two mapping keys instead of `input_ids`. This was caught before any generation call or eligibility decision. The counter was corrected, a regression test was added, and the lock was updated before the definitive preflight.

The first corrected token audit then found a real one-token contextual mismatch (`737` early versus `738` late). The tolerance was not relaxed. The neutral block was changed generically to a JSON-terminated inert structure and re-frozen. Definitive locked Qwen tokenizer evidence:

- tokenizer class: `Qwen2Tokenizer`, local-files-only at the fixed model revision;
- fact block: 26 tokens;
- neutral block: 26 tokens;
- early call pair: `309 + 427 = 736` text tokens;
- late call pair: `309 + 427 = 736` text tokens;
- absolute difference: 0;
- target aliases A–H: one token each;
- entity aliases E1–E8: two tokens each.

This is a tooling/alias certificate only. Exact matching on real held-out instances remains untested because no held-out instances exist.

### Zero-generation runtime preflight

Definitive report: `PHASE_B_ZERO_GENERATION_PREFLIGHT_2026-08-04.json`
SHA-256: `c525c7aad7c7b6e3cce7ebfa668f835ea0c920b7be61c69218a1489b4c9e8dac`

- model `/health`: loaded/OK, exact model/revision/backend;
- generation endpoint invoked by preflight: false;
- generation calls by preflight: 0;
- explicit official ADB binary SHA-256 matched;
- port 5038, serial `emulator-5554`, boot complete;
- fallback to 5037: false;
- prompt/schema/parser conformance: pass;
- namespace imports of old EEST/controller: none;
- protected legacy WIP hashes: pass;
- fresh snapshot variants: 0;
- retained fresh base families: 0 of required 8;
- snapshot/oracle qualification: 0.0%, below required 95%;
- verdict: `NOT_ELIGIBLE_FOR_GENERATION`.

### Full regression

- The first system-Python attempt produced 14 collection errors for missing `android_env`, `android_world`, and `dm_env`; it is recorded as `INVALID_ENVIRONMENT_ATTEMPT`, not a test failure.
- A first correct-venv run was interrupted by the five-minute command timeout and is recorded as `INCOMPLETE_TIMEOUT`.
- The definitive correct-venv run collected **1,151 tests**, reached 100%, and had **1 failure / 1,150 passes**.
- The sole failure is the pre-existing `test_r78_candidate_static_manifest_validation_passes` frozen-file hash mismatch caused by the protected legacy r79 WIP. It is unrelated to this namespace. The old manifest was not changed to conceal it.

## Machine artifacts

- protocol: `04_protocols/role_binding_timing/stage1_diagnostic_v0_1.md`
- single-source contract: `05_project/contracts/role_binding_timing_stage1.v0_1.json`
- grounding/action/snapshot schemas: `05_project/schemas/role_binding_timing_*.v0_1.schema.json`
- config and empty held-out manifest: `05_project/configs/role_binding_timing/`
- immutable file lock: `stage1_v0_1.lock.json`, SHA-256 `a7bdb1619bc13d1b99f002186142d05aed8f3d2b7d841f876943373a0a06f1b9`
- implementation: `05_project/src/raven_m/role_binding_timing/`
- tests: `05_project/tests/role_binding_timing/`
- zero-generation preflight: `05_project/scripts/preflight_role_binding_timing_stage1.py`
- preflight evidence: `reports/role_binding_timing/PHASE_B_ZERO_GENERATION_PREFLIGHT_2026-08-04.json`

## Cost and contamination accounting

- external model generation calls: 0
- generated prompt/completion tokens: 0 / 0
- emulator task batches: 0
- pilot cells: 0
- Stage-1 cells: 0
- DEV screenshots promoted to held-out: 0
- official tokenizer download/load and local tokenization are infrastructure operations, not model generation
- definitive zero-generation preflight wall time: 38.3 seconds
- definitive full regression wall time: 293.7 seconds

## Claim–evidence verdict

| Claim | Evidence | Verdict |
|---|---|---|
| The two-call contract can distinguish grounding, drift, and final wrong-target action | Frozen schemas, parser, metrics, 17 focused tests | **SUPPORTED OFFLINE** |
| Early/late prompts can be token matched under the fixed Qwen tokenizer | Definitive synthetic certificate, 736 versus 736 | **SUPPORTED FOR TOOLING; REAL INSTANCES UNTESTED** |
| Model/runtime identity is ready without generation | Health and explicit-ADB preflight | **SUPPORTED** |
| Eight fresh held-out base families are qualified | Empty manifest, 0 retained families | **NOT SUPPORTED** |
| Phase C may start | Snapshot/oracle hard gate failed | **NO** |
| Timing × ambiguity raises wrong-target risk | No cells run | **UNTESTED** |
| The research direction is novel | Phase A was bounded and provisional | **UNRESOLVED** |

## Stop/continue decision

**STOP BEFORE GENERATION.** Phase C is not launched. The frozen v0.1 manifest and verdict must not be edited in place. A future, separately versioned snapshot-collection qualification may collect fresh paired PNG + UI-tree states, assign stable oracle IDs before condition assignment, and rerun the same offline gates. Only if at least eight complete base families survive at `>=95%` qualification may a separately frozen 8-family pilot be considered.
