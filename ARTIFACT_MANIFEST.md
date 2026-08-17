# RAVEN-M A0-A12 Research Artifact Manifest

## 2026-08-18 R15 and three-direction candidate pipeline

- `evidence/r15_browser_forensics/R15_BROWSER_FORENSIC_2026-08-18.md` and
  `.json` - step-aligned BrowserMultiply forensics. R15 succeeded, but EVR
  render/read was zero; no reusable R15-derived live arm was authorized.
- `evidence/p1_failure_recovery/P1_TCRA_R2_ZERO_GENERATION_AUDIT.json` - P1
  recovery G0. The detector hits a successful Calendar trajectory and is
  sealed `PREFLIGHT_INVALID_NO_LIVE`.
- `evidence/p2_long_horizon/P2_SCOPE_R2_ZERO_GENERATION_AUDIT.json` - P2
  coordination G0. Raw midpoint exposure is bound, but the required blinded
  semantic annotation does not exist.
- `evidence/p3_outcome_judgment/P3_SCER_R2_ZERO_GENERATION_AUDIT.json` - P3
  outcome-judgment G0. Raw R2 materialization passes; independent visible-only
  labels and false-reject adjudication remain absent.
- `evidence/candidate_pipeline/CANDIDATE_PIPELINE_RESULT_2026-08-18.md` and
  `.json` - final four-direction matrix. No new candidate passed G0; therefore
  no seven-task live run was authorized and no invalid arm is reported as
  `0/7`.
- `design_reviews/pro_candidates/2026-08-15/` - byte-preserved original Pro
  blueprints plus P1/P2/P3 adjudications. Pro prose is explicitly not evidence.

## 2026-08-15 A1-R3 prospective entry points

- `protocols/A1R3_STALE_RESISTANT_PENDING_PREREG_2026-08-15.md` - frozen
  evidence-derived mechanism, six-task gate, independent verdicts, and version
  boundary.
- `implementation/src/raven_m/official_qwen_mobile/a1r3_stale_resistant_pending.py`
  - one compact pending ledger, non-refreshing TTL, one tombstone, and one
  bounded repeated-failure fact.
- `evidence/a1r3/A1R3_SRPL_OFFLINE_REPLAY_REPORT.json` - real zero-generation
  replay of all 19 valid A1-R2 episodes.
- `evidence/a1r3/A1R3_SRPL_SOURCE_FREEZE.json` - exact 24-file decision-source
  closure at implementation commit `4bbac3214c69d921912219f59f027424c921ec8e`.
- `evidence/a1r3/A1R3_SRPL_ZERO_GENERATION_PREFLIGHT.json` - formal PASS report;
  it does not itself replace the required fresh live server receipt.
- `evidence/a1r3/A1R3_SRPL_PREFLIGHT_SUMMARY_2026-08-15.md` - concise human
  interpretation and live stopping boundary.
- `implementation/scripts/start_a1r3_srpl_server.sh`,
  `implementation/scripts/qualify_a1r3_srpl_server.py`, and
  `implementation/scripts/run_a1r3_srpl.py` - fresh server, receipt, and frozen
  six-first execution path.

A1-R3 first reached `PROSPECTIVE_ZERO_GENERATION_QUALIFIED`. Replay exposure did
not predict reward and authorized only the frozen live gate.

Live status supersedes that qualification-only statement: A1-R3 is now
`FORMAL_GATE_TERMINAL` after a valid 0-reward failure on the first capability
task. Entry points:

- `evidence/a1r3/A1R3_SRPL_PRIMARY_GATE_RESULT_2026-08-15.json` - exact scored
  counters, mechanism inactivity, and raw-artifact hashes.
- `evidence/a1r3/A1R3_SRPL_PRIMARY_GATE_RESULT_2026-08-15.md` - interpretation
  boundary: the arm regressed, while the new lifecycle itself was never used.

## 2026-08-14 A1-R2 scored entry points

- `evidence/a1r2/A1R2_CVP_SCORED_RESULT_2026-08-14.md` - concise scored
  interpretation, independent accuracy/cost/mechanism verdicts, and explicit
  result-layer repair boundary.
- `evidence/a1r2/A1R2_CVP_SCORED_RESULT_2026-08-14.json` - hash-bound 19-task
  result with per-episode IDs/hashes, paired A0/A1 deltas, memory totals, and
  the resolved infrastructure-invalid attempt.
- `implementation/scripts/finalize_a1r2_cvp.py` - zero-generation finalizer for
  the already-complete suite. It exists because the frozen shared runner
  misroutes A1-R2 into an A12-only result branch after episode completion.
- `implementation/tests/official_qwen_mobile/test_a1r2_finalizer.py` - order,
  gate, and deterministic-content-hash tests for the finalizer.

A1-R2 is `FORMAL_SCORED_PAIRED_WITH_RESULT_LAYER_REPAIR`: all 19 prospective
episodes are source-frozen and valid, while aggregate construction required a
separate read-only finalizer. It scored 6/19 and reward 6.5. Accuracy passed;
the strict cost rule failed because calls equalled A1's 603; causal mechanism
attribution remains unestablished without a matched ablation.

## 2026-08-13 current entry points

- `HANDOFF_2026-08-13.md` - current verified status and vertical research direction.
- `GPT_PRO_A1_VERTICAL_REFINEMENT_DESIGN_REQUEST_2026-08-13.md` - constrained
  request for the next A1-derived prospective arm.
- `evidence/diag6/A10V2_DIAGNOSTIC6_RESULT_2026-08-13.md` - compact, hash-bound
  post-hoc A10-v2 six-task result; explicitly not a formal-arm repair.
- `evidence/diag6/A11_A12_DIAGNOSTIC6_RESULTS_2026-08-13.md` - compact,
  hash-bound post-hoc A11/A12 terminal results and read-causality audit.
- `protocols/ENRICHED_MEMORY_DIAGNOSTIC6_PROTOCOL_2026-08-13.md` - immutable
  post-hoc diagnostic protocol for A10-v2, A11, and A12.
- `evidence/a1r1/A1R1_V1_RAW_TRACE_AUDIT_2026-08-13.json` - zero-generation,
  hash-bound raw A1 distribution audit that deterministically rejects BPR v1 R3.
- `evidence/a1r1/A1R1_V1_DESIGN_AUDIT_2026-08-13.md` - retained BPR core, v1
  failure boundary, and required narrow revision.
- `GPT_PRO_A1_VERTICAL_BPR_V2_REVISION_REQUEST_2026-08-13.md` - constrained
  request for a newly identified, evidence-valid BPR v2 design.
- `evidence/composite/COMPONENT_EVIDENCE_LEDGER_2026-08-13.md` - evidence-classed
  component ledger and common boundary for post-memory system proposals.
- `GPT_PRO_COMPOSITE_TRACKS_INDEX_2026-08-13.md` - launcher and coordination
  rules for seven independent `SYS-*` Pro design studies.
- `GPT_PRO_SYS_HMP_DESIGN_REQUEST_2026-08-13.md` - hierarchical milestone
  planning request.
- `GPT_PRO_SYS_VOV_DESIGN_REQUEST_2026-08-13.md` - visible-outcome verification
  request.
- `GPT_PRO_SYS_TRC_DESIGN_REQUEST_2026-08-13.md` - triggered recovery critic
  request.
- `GPT_PRO_SYS_CAA_DESIGN_REQUEST_2026-08-13.md` - candidate-action arbitration
  request.
- `GPT_PRO_SYS_BTM_DESIGN_REQUEST_2026-08-13.md` - zero-call trajectory monitor
  request.
- `GPT_PRO_SYS_EPHC_DESIGN_REQUEST_2026-08-13.md` - evidence-preserving history
  compression request.
- `GPT_PRO_SYS_FWRE_DESIGN_REQUEST_2026-08-13.md` - frozen workflow retrieval
  executor request.

The seven request documents are `UNREVIEWED_PROPOSAL` inputs. They do not create
experiment identities, preregistrations, preflights, or live authorization.

## Evidence classes

- `FORMAL_SCORED_PAIRED`: complete seed-matched scored evidence such as A0-A2.
- `FORMAL_SCORED_PAIRED_WITH_RESULT_LAYER_REPAIR`: complete prospective paired
  episodes whose frozen runner failed only after episode completion and whose
  aggregate was rebuilt by a hash-validating, zero-generation finalizer, such
  as A1-R2.
- `FORMAL_GATE_TERMINAL`: a prospective arm stopped by its frozen gate.
- `FULL_SCORED_NEGATIVE_WITH_PROTOCOL_CAVEAT`: complete negative evidence whose
  execution schedule had a documented protocol defect, such as A6.
- `TRANSPARENT_STITCHED_CONTROL`: auditable results joined across explicitly
  disclosed run/amendment boundaries, such as A7.
- `FORMAL_OFFLINE_REPLAY_FAIL`: qualification failed before authorized live
  generation, including A10-v1, A10-v2, and A11.
- `FORMAL_PROTOCOL_INVALID`: the frozen experiment contract is infeasible or
  invalid, including A12.
- `POST_HOC_ENRICHED_DIAGNOSTIC`: exploratory diagnostic evidence that cannot
  repair a formal arm, including A10-v2/A11/A12 diagnostic six.
- `HISTORICAL_STRUCTURAL_SUPPORT`: retrospective trace structure that motivates
  a hypothesis but is not prospective causal evidence.
- `UNREVIEWED_PROPOSAL`: a design request or response not independently
  adjudicated.

## 2026-08-12 historical entry points

- `HANDOFF_2026-08-12.md` — current verified status and next execution.
- `GPT_PRO_MEMORY_MECHANISM_DESIGN_REQUEST_2026-08-12.md` — constrained design
  assignment for the next standalone memory arm.
- `evidence/a678/A89_INITIAL_GATE_RESULTS_2026-08-12.json` — compact immutable
  summary of the first A8-v2/A9 prospective gates.
- `protocols/A89_FOUR_TASK_DIAGNOSTIC_REPLICATION_AMENDMENT_2026-08-12.md` —
  fresh all-four diagnostic schedule that does not overwrite the first gates.

Independent review basis: `GPT_PRO_A2_AUDIT_REQUEST.md` and the returned `A2_PRO_AUDIT.md` supplied outside this repository.

## Assignment and paired evidence

- `assessment/夏令营考核题目.pdf`
- `evidence/baseline/official_qwen32b_full_hard_combined_corrected_final.md` — A0 evidence; seed 20260806 is the paired control.
- `evidence/a1/A1_ACTION_WORKING_MEMORY_RESULTS_2026-08-10.md` — A1 result/cost analysis.
- `evidence/a2/A0_A1_PAIRED_REFERENCE_20260810.json` — exact per-episode A0/A1 ledger rebuilt from raw traces.
- `evidence/a2/A1_EXACT_GUARD_REPLAY_20260810.json` — zero-generation corrected-guard replay.
- `evidence/a2/A2_DESIGN_RATIONALE_AND_A1_REPLAY_2026-08-10.md` — targeted design rationale.

## Runtime identity and qualification

- `evidence/a2/A2_RUNTIME_REMOTE_MODEL.json` — all manifest-listed Qwen model files recomputed on the no-GPU server.
- `evidence/a2/A2_RUNTIME_LOCAL_ANDROID.json` — AndroidWorld source digest, emulator/ADB identity, resolution, and ordered tasks.
- `evidence/a2/A2_RUNTIME_QUALIFICATION.json` — combined zero-generation receipt.
- `evidence/a2/A2_ZERO_GENERATION_PREFLIGHT.json` — final source-frozen A2 gate (generated only after all edits/tests).

## Frozen protocol and implementation

- `protocols/A2_VERIFIED_PROGRESS_MEMORY_PREREG_2026-08-10.md`
- `protocols/A2_VERIFIED_PROGRESS_MEMORY_RUNBOOK.md`
- `implementation/configs/a2_verified_progress_memory_hard_seed20260806.json`
- `implementation/src/raven_m/official_qwen_mobile/progress_memory.py`
- `implementation/src/raven_m/official_qwen_mobile/controller.py`
- `implementation/src/raven_m/official_qwen_mobile/a2_suite.py`
- `implementation/src/raven_m/models/vllm_client.py`
- `implementation/scripts/run_official_qwen_mobile.py`
- `implementation/scripts/run_a2_verified_progress.ps1`
- `implementation/scripts/start_a2_verified_progress_server.sh`
- `implementation/scripts/qualify_a2_runtime.py`
- `implementation/scripts/qualify_a2_live_server.py`
- `implementation/scripts/build_a2_reference_ledger.py`
- `implementation/scripts/replay_a1_exact_guard.py`
- `implementation/scripts/validate_a2_paired_suite.py`

## Tests

- `implementation/tests/official_qwen_mobile/test_progress_memory.py`
- `implementation/tests/official_qwen_mobile/test_official_qwen_controller.py`
- `implementation/tests/official_qwen_mobile/test_a2_suite.py`
- `implementation/tests/models/test_vllm_client.py`

## Scope and claim limits

A2-v1r1 is a compound arm: one-state outcome-aware memory, history deduplication, and a separately logged exact repeated-no-progress guard. It uses one seed and supports a descriptive paired diagnostic only. `verified` is a model-authored screenshot assertion, not objective verification. The evaluator remains the only success authority. Guard-exposed gains are never reported as pure memory effects.

Superseded RAVEN-M revisions, MobileUse/B2/C0 code, and earlier planning packets are deliberately absent from this audit branch but remain recoverable in Git history. The exact A1 implementation is recoverable at commit `fbc25dc`.
