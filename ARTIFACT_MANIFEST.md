# Artifact manifest and reading order

## Tier 0: task and current decision

- `assessment/夏令营考核题目.pdf`: original seven-page assignment.
- `assessment/夏令营考核题目_提取文本.txt`: searchable extraction.
- `GPT_DECISION_REQUEST.md`: authoritative current question and output contract.
- `FRAMEWORK_SELECTION_RUBRIC.md`: eligibility and comparison rules.

## Tier 1: authoritative current baseline

- `evidence/baseline/GPU_8H_GOAL_COMPLETION_AUDIT_2026-08-08.md`: requirement-by-requirement completion audit.
- `evidence/baseline/official_qwen32b_hard_pulse_2026-08-08.md`: full execution narrative, infrastructure corrections, four-task pulse, 57-instance completion, and first rescue.
- `evidence/baseline/official_qwen32b_full_hard_combined_corrected_final.json`: machine-readable final 57-key result.
- `evidence/baseline/official_qwen32b_full_hard_combined_corrected_final.md`: readable 19-class x 3-seed table.
- `evidence/baseline/official_qwen32b_full_hard_failure_taxonomy_2026-08-08.md`: whole-suite automatic failure signals and rescue qualification.
- `evidence/baseline/official_qwen32b_cross_seed_mechanism_notes_2026-08-08.md`: task-class consistency and deterministic-replay limits.
- `evidence/baseline/official_qwen32b_full_hard_case_notes_2026-08-08.md`: representative success and failure interpretations.
- `evidence/baseline/official_qwen32b_observation_reuse_final.json`: mechanical observation-reuse statistics.

## Tier 2: deterministic layer audits

- `official_qwen32b_app_launch_grounding_audit_2026-08-08.{md,json}`: correct/wrong/recovered initial app entry.
- `official_qwen32b_cross_app_handoff_audit_2026-08-08.{md,json}`: source-to-destination application funnel.
- `official_qwen32b_expected_object_transfer_audit_2026-08-08.{md,json}`: expected object identifiers entering actual target-app text actions.
- `official_qwen32b_markor_source_funnel_audit_2026-08-08.{md,json}`: source document to final write funnel.
- `official_qwen32b_markor_document_coverage_audit_2026-08-08.{md,json}`: document-scroll behavior.
- `object_role_evidence_prevalence_audit_2026-08-08.md`: clean wrong-proof-type cases across tasks and apps.

All are under `evidence/layer_audits/`. They are post-hoc deterministic audits,
not randomized causal estimates.

## Tier 3: tested interventions and negative boundaries

- `l4_transition_attestation_matched_diagnostic_2026-08-08.md`
- `evidence_qualified_progress_matched_diagnostic_2026-08-08.md`
- `offline_completion_verifier_diagnostic_2026-08-08.md`
- `visible_object_extractor_markor_diagnostic_2026-08-08.md`
- `source_document_coverage_markor_dev_stopped_2026-08-08.{md,json}`
- `source_document_coverage_gate_matched_2026-08-08.{md,json}`
- `source_document_coverage_contract_audit_2026-08-08.{md,json}`

All are under `evidence/interventions/`. A negative result is retained as a
boundary; it is not an invitation to tune the same exposed cell until it passes.

## Tier 4: prior independent reviews

The four files under `evidence/prior_reviews/` preserve earlier GPT Pro analyses.
They predate the corrected 7/57 baseline and therefore cannot override Tier 1-3
evidence. Use them to avoid repeating already occupied ideas and to understand
how the research question changed.

## Tier 5: implementation feasibility

- `protocols/`: current runbook, preregistrations, correction records, and frozen stop rules.
- `implementation/src/`: official-style controller, protocol, coverage gate, completion verifier, AndroidWorld adapter, task-instantiation code, and vLLM client.
- `implementation/scripts/`: runner, preflight, server launch, deterministic audits, merge logic, and extractor/verifier drivers.
- `implementation/configs/`: frozen model, task, extractor, and verifier configurations.
- `implementation/tests/`: compact relevant test suite.
- `final_report/`: current Chinese formal report in TeX and PDF.

### Path redirects inside frozen reports

Some reports retain their original local-repository paths so their recorded
provenance is not silently rewritten. In this curated tree, resolve them as:

| Original path prefix in a report | Current curated location |
|---|---|
| `05_project/docs/` | `protocols/` |
| `05_project/scripts/` | `implementation/scripts/` |
| `05_project/src/raven_m/` | `implementation/src/raven_m/` |
| `05_project/configs/` | `implementation/configs/` |
| `05_project/tests/` | `implementation/tests/` |
| `reports/<current baseline audit>` | `evidence/baseline/`, `evidence/layer_audits/`, or `evidence/interventions/` |

Original absolute `runs/` paths identify local raw trajectories and do not have a
GitHub redirect; their hashes and derived measurements are retained in the audit
JSON files.

## Deliberately excluded

- model weights and caches;
- the multi-gigabyte raw `runs/` tree;
- obsolete r1-r78 protocol iterations and infrastructure burn-in logs;
- early RAVEN-M module variants that are not the current comparison target;
- partial and superseded aggregates when a corrected final aggregate exists;
- local credentials, SSH configuration, environment files, and tokens.

Excluded history remains in earlier Git commits or the local research workspace.
