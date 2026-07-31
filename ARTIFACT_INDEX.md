# Artifact index

This index distinguishes verified artifacts from planned work. No file listed
here is evidence of a scored Hard result unless explicitly marked as such.

## Verified infrastructure

| Artifact | Purpose | Status |
|---|---|---|
| `04_protocols/environment_lock.yaml` | machine, model, transport and gate lock | current through G6; G7 v15 running |
| `05_project/metadata/model_snapshot_manifest.json` | exact 66.7 GB checkpoint inventory and hashes | verified |
| `05_project/metadata/server_real_model_smoke.json` | real AndroidWorld screenshot-to-action call | verified, non-scored |
| `05_project/metadata/server_audit_4090_post_model.json` | post-restart model-host audit | verified |
| `05_project/metadata/model_max_shape_stress.json` | ten-request 7,704-token stress result | 10/10 passed |
| `05_project/metadata/g3_dev_suite_audit.json` | normalized v0/v1 G3 audit and hashes | v1 gate passed |
| `05_project/metadata/g4_audit.json` | B0/B1/B2/B3 non-Hard family gate | passed |
| `05_project/metadata/g6_audit.json` | memory lifecycle/schema/replay gate | 73/73 full tests passed |
| `05_project/metadata/corruption_stress.json` | deterministic unsafe-memory fixtures | 20/20 rejected as FACT |
| `06_local_runtime/metadata/runtime_audit.json` | Windows Android host audit | verified |
| `06_local_runtime/metadata/androidworld_smoke.json` | AndroidWorld initialization/observation smoke | verified |

## Implemented baselines and method

| Artifact | Purpose | Status |
|---|---|---|
| `05_project/schemas/action.v1.schema.json` | shared canonical action contract | implemented and tested |
| `05_project/prompts/executor_v0.md` | retained failed G3 policy prompt | dev v0 diagnostic |
| `05_project/prompts/executor_v1.md` | memory-free B0 policy prompt | G3 gate version |
| `05_project/src/raven_m/models/transformers_client.py` | hashed private model client | implemented |
| `05_project/src/raven_m/env/androidworld_adapter.py` | normalized-to-pixel action adapter | implemented |
| `05_project/src/raven_m/controller/episode_controller.py` | thin B0 episode loop and logger | implemented |
| `05_project/scripts/run_b0_dry_run.py` | real excluded-protocol runner | implemented |
| `05_project/scripts/run_g3_dev_suite.py` | resumable five-task dev runner and aggregator | implemented |
| `05_project/src/raven_m/history/policies.py` | B1/B2/B3 and RAVEN-M history policies | implemented and tested |
| `05_project/src/raven_m/memory/` | provenance, lifecycle, replay, scoring and routing | implemented and tested |
| `05_project/src/raven_m/roles/` | bounded Planner/Critic role contracts | implemented and tested |
| `05_project/scripts/run_method_dev_suite.py` | S0/M0 non-Hard G6/G7 runner | v15 waiting on locked model host |
| `05_project/scripts/run_component_smoke_suite.py` | eight ablation/control path smoke | implemented; fresh rerun pending v15 |
| `05_project/scripts/run_frozen_hard_suite.py` | frozen, resumable scored runner | implemented; mechanically blocked before freeze |
| `05_project/tests/fixtures/golden_episode/` | deterministic parse/map replay | passing |
| `reports/first_72_hours.md` | measured execution report | current |
| `reports/g3_dev_gate.md` | v0 failure, v1 rerun and gate decision | current |

Raw trajectories are under `runs/excluded_protocol_dry_run/` and
`runs/dev_nonhard_g3/`, excluded from Git, and excluded from scored results.

## Protocol-v2.2 requalification

| Artifact | Purpose | Status |
|---|---|---|
| `reports/protocol_v2_2_r39_gate_d_freeze.json` | r39 frozen source, model, schema, and runtime hashes | verified |
| `reports/protocol_v2_2_gate_e_r39_preflight.json` | clean preflight before the formal run | passed |
| `reports/protocol_v2_2_r39_sequence4_authorization.json` | live Files regression authorization | passed |
| `reports/protocol_v2_2_r39_gate_e_final.json` | machine-readable eight-cell result and manual review | Gate E passed |
| `reports/protocol_v2_2_r39_gate_e_final.md` | human-readable outcome, limitations, and paired analysis | current |
| `reports/protocol_v2_2_r39_expense_m0_diagnostic.json` | machine-readable causal trace for the retained M0 failure | reviewed |
| `reports/protocol_v2_2_r39_expense_m0_diagnostic.md` | generic lifecycle/action-consistency repair specification | current |
| `04_protocols/protocol_v2_2_r40_candidate_addendum.md` | post-r39 candidate contract without rewriting the frozen r39 specification | local candidate |
| `reports/protocol_v2_2_r40_local_validation.json` | machine-readable repair, test, compatibility, and integrity evidence | passed locally |
| `reports/protocol_v2_2_r40_local_validation.md` | human-readable r40 candidate validation and evidence boundary | current |
| `reports/protocol_v2_2_r40_candidate_preflight.json` | candidate source, instance, model, and emulator freeze check | passed |
| `05_project/scripts/run_protocol_v2_2_r40_candidate_smoke.py` | isolated r40 non-scored smoke entry point | ready |
| `reports/protocol_v2_2_r40_paired_expense_smoke.json` | machine-readable paired smoke and causal boundary | candidate rejected |
| `reports/protocol_v2_2_r40_paired_expense_smoke.md` | B3 pass, M0 budget failure, and r41 repair scope | current |
| `04_protocols/protocol_v2_2_r41_candidate_addendum.md` | complete supersession and narrow repeat/focus guards | local candidate |
| `reports/protocol_v2_2_r41_local_validation.json` | machine-readable 345-test, v1-seal, and compatibility evidence | passed locally |
| `reports/protocol_v2_2_r41_local_validation.md` | r41 rationale, risk boundary, and next live action | current |
| `reports/protocol_v2_2_r41_candidate_preflight.json` | r41 source, instance, model, and emulator freeze check | passed |
| `05_project/scripts/run_protocol_v2_2_r41_candidate_smoke.py` | isolated r41 M0 smoke entry point | ready |
| `reports/protocol_v2_2_r41_m0_expense_smoke.json` | machine-readable r41 M0 failure and guard audit | candidate rejected |
| `reports/protocol_v2_2_r41_m0_expense_smoke.md` | input-proof and layout-axis boundary for r42 | current |
| `04_protocols/protocol_v2_2_r42_candidate_addendum.md` | one-step activation proof and visible-layout recovery contract | local candidate |
| `reports/protocol_v2_2_r42_local_validation.json` | machine-readable 349-test, v1-seal, and historical compatibility evidence | passed locally |
| `reports/protocol_v2_2_r42_local_validation.md` | r42 rationale, bounded risk, and next live action | current |
| `05_project/scripts/run_protocol_v2_2_r42_candidate_smoke.py` | isolated r42 M0 smoke entry point | ready |
| `reports/protocol_v2_2_r42_candidate_preflight.json` | source, 27-file freeze, four instances, model, and emulator check | passed |
| `reports/protocol_v2_2_r42_m0_expense_smoke.json` | machine-readable r42 failure, guard audit, visual hashes, and r43 boundary | candidate rejected |
| `reports/protocol_v2_2_r42_m0_expense_smoke.md` | verified-progress versus repeated-action causal analysis | current |
| `04_protocols/protocol_v2_2_r43_candidate_addendum.md` | progress-conditioned swipe streak with tap-loop exclusion | local candidate |
| `reports/protocol_v2_2_r43_local_validation.json` | machine-readable 352-test, v1-seal, and two-level compatibility audit | passed locally |
| `reports/protocol_v2_2_r43_local_validation.md` | r43 evidence boundary and authorized next action | current |
| `05_project/scripts/run_protocol_v2_2_r43_candidate_smoke.py` | isolated r43 M0 smoke entry point | ready |
| `reports/protocol_v2_2_r43_candidate_preflight.json` | source, 27-file freeze, four instances, model, and emulator check | passed |
| `reports/protocol_v2_2_r43_m0_expense_smoke.json` | machine-readable hidden ADB retry evidence and invalidation boundary | invalid infrastructure-contaminated attempt |
| `reports/protocol_v2_2_r43_m0_expense_smoke.md` | non-idempotent partial-text retry causal analysis | current |
| `04_protocols/protocol_v2_2_r44_candidate_addendum.md` | retry-idempotent clear-and-type executor boundary | local candidate |
| `reports/protocol_v2_2_r44_local_validation.json` | machine-readable 357-test, v1-seal, and 404-trajectory compatibility audit | passed locally |
| `reports/protocol_v2_2_r44_local_validation.md` | r44 rationale, bounded timeout, and authorized next action | current |
| `05_project/scripts/run_protocol_v2_2_r44_candidate_smoke.py` | isolated r44 M0 smoke entry point | ready |
| `reports/protocol_v2_2_r44_candidate_preflight.json` | source, 27-file freeze, four instances, model, and emulator check | passed |
| `reports/protocol_v2_2_r44_m0_expense_smoke.json` | machine-readable r44 retry qualification, budget cause, and r43 boundary | valid task failure |
| `reports/protocol_v2_2_r44_m0_expense_smoke.md` | exact-text retry evidence and horizontal-row causal audit | current |
| `04_protocols/protocol_v2_2_r45_candidate_addendum.md` | task-agnostic horizontal clipped-row navigation contract | local candidate |
| `reports/protocol_v2_2_r45_local_validation.json` | machine-readable 357-test, prompt-parity, v1-seal, and historical audit | passed locally |
| `reports/protocol_v2_2_r45_local_validation.md` | r45 rationale, compatibility boundary, and authorized next action | current |
| `05_project/scripts/run_protocol_v2_2_r45_candidate_smoke.py` | isolated r45 M0 smoke entry point | ready |
| `reports/protocol_v2_2_r45_candidate_preflight.json` | source, 27-file freeze, four instances, model, and emulator check | passed |
| `reports/protocol_v2_2_r45_m0_expense_smoke.json` | machine-readable r45 behavior, r43 fourth-swipe boundary, budget cause, and raw hashes | valid task failure |
| `reports/protocol_v2_2_r45_m0_expense_smoke.md` | live qualification and no-r46 scientific disposition | current |
| `05_project/configs/experiments/v2_2_capability_gate_r45.json` | persistent eight-cell r45 Gate-E manifest and 27-file freeze | frozen |
| `05_project/scripts/run_protocol_v2_2_gate_e_r45.py` | exact-source r45 Gate-E entry point | ready |
| `reports/protocol_v2_2_r45_gate_e_preflight.json` | zero-call source, instance, model, emulator, and fresh-directory preflight | passed |
| `reports/protocol_v2_2_r45_gate_d_freeze.json` | Gate-D evidence review and one-launch authorization | passed |
| `reports/protocol_v2_2_r45_gate_e_stopped.json` | machine-readable VPN-attempt separation, five-cell result, and sequence-5 causal trace | Gate E stopped/failed |
| `reports/protocol_v2_2_r45_gate_e_stopped.md` | human-readable r45 stop decision and bounded r46 scope | current |
| `04_protocols/protocol_v2_2_r46_candidate_addendum.md` | task-grounded planning and activate-before-type repair boundary | local candidate |
| `reports/protocol_v2_2_r46_local_validation.json` | machine-readable 359-test, exact failure-shape, and v1-seal evidence | passed locally |
| `reports/protocol_v2_2_r46_local_validation.md` | human-readable r46 rationale, compatibility, and next live action | current |
| `05_project/scripts/run_protocol_v2_2_r46_candidate_smoke.py` | isolated r46 M0 Contacts smoke entry point | ready |
| `reports/protocol_v2_2_r46_candidate_preflight.json` | source, 27-file freeze, four instances, model, emulator, and fresh smoke directory | passed |
| `reports/protocol_v2_2_r46_m0_contacts_smoke.json` | machine-readable task-scope qualification and activation/loop conflict | candidate rejected |
| `reports/protocol_v2_2_r46_m0_contacts_smoke.md` | live r46 failure analysis and bounded r47 repair scope | current |
| `04_protocols/protocol_v2_2_r47_candidate_addendum.md` | repair-only input-activation repeat exception and preserved guard boundary | local candidate |
| `reports/protocol_v2_2_r47_local_validation.json` | machine-readable 360-test, full-chain, audit-counter, and v1-seal evidence | passed locally |
| `reports/protocol_v2_2_r47_local_validation.md` | human-readable r47 rationale, compatibility, and next live action | current |
| `05_project/scripts/run_protocol_v2_2_r47_candidate_smoke.py` | isolated r47 M0 Contacts smoke entry point | ready |
| `reports/protocol_v2_2_r47_candidate_preflight.json` | source, 27-file freeze, four instances, model, emulator, and fresh smoke directory | passed |
| `reports/protocol_v2_2_r47_m0_contacts_smoke.json` | machine-readable task-scope qualification, readiness accounting, and visible-control retry conflict | candidate rejected |
| `reports/protocol_v2_2_r47_m0_contacts_smoke.md` | live r47 failure analysis and bounded r48 repair scope | current |
| `04_protocols/protocol_v2_2_r48_candidate_addendum.md` | single-use named non-commit visible-control activation retry boundary | local candidate |
| `reports/protocol_v2_2_r48_local_validation.json` | machine-readable 369-test, denial-case, audit-record, and v1-seal evidence | passed locally |
| `reports/protocol_v2_2_r48_local_validation.md` | human-readable r48 rationale, compatibility, and next live action | current |
| `05_project/scripts/run_protocol_v2_2_r48_candidate_smoke.py` | isolated r48 M0 Contacts smoke entry point | ready |
| `reports/protocol_v2_2_r48_candidate_preflight.json` | source, 27-file freeze, four instances, exact model, emulator, and fresh smoke directory | passed |
| `reports/protocol_v2_2_r48_m0_contacts_smoke.json` | machine-readable successful task-scope smoke and branch-qualification boundary | passed |
| `reports/protocol_v2_2_r48_m0_contacts_smoke.md` | human-readable native success and deterministic-only r48 branch evidence | current |
| `reports/protocol_v2_2_r48_gate_d_freeze.json` | immutable r48 Gate-D review and one-launch authorization | passed |
| `reports/protocol_v2_2_r48_gate_e_stopped.json` | machine-readable four-success stop and sequence-4 causal evidence | Gate E stopped/failed |
| `reports/protocol_v2_2_r48_gate_e_stopped.md` | human-readable circular verification-navigation critic diagnosis | current |
| `04_protocols/protocol_v2_2_r49_candidate_addendum.md` | exact Android Files post-transfer destination-navigation boundary | local candidate |
| `reports/protocol_v2_2_r49_local_validation.json` | machine-readable 377-test, full-chain, denial-case, and v1-seal evidence | passed locally |
| `reports/protocol_v2_2_r49_local_validation.md` | human-readable r49 rationale, safety boundary, and next live action | current |
| `05_project/scripts/run_protocol_v2_2_r49_candidate_smoke.py` | isolated r49 M0 Files smoke entry point | ready |
| `reports/protocol_v2_2_r49_candidate_preflight.json` | source, 27-file freeze, four instances, exact model, emulator, and fresh smoke directory | passed |
| `reports/protocol_v2_2_r49_m0_files_smoke.json` | machine-readable native success, max-step stop, and absent live-branch evidence | Gate D withheld |
| `reports/protocol_v2_2_r49_m0_files_smoke.md` | source-folder drift diagnosis and bounded r50 scope | current |
| `04_protocols/protocol_v2_2_r50_candidate_addendum.md` | exact post-commit source-directory exit and preserved root-tile boundary | local candidate |
| `reports/protocol_v2_2_r50_local_validation.json` | machine-readable 385-test, full-chain, negative-case, and v1-seal evidence | passed locally |
| `reports/protocol_v2_2_r50_local_validation.md` | human-readable r50 rationale, safety boundary, and next live action | current |
| `05_project/scripts/run_protocol_v2_2_r50_candidate_smoke.py` | isolated r50 M0 Files smoke entry point | ready |
| `reports/protocol_v2_2_r50_candidate_preflight.json` | source, 27-file freeze, four instances, exact model, emulator, and fresh smoke directory | passed |
| `reports/protocol_v2_2_r50_m0_files_smoke.json` | machine-readable native success, live source-exit qualification, and over-constrained destination-navigation evidence | Gate D withheld |
| `reports/protocol_v2_2_r50_m0_files_smoke.md` | human-readable r50 trajectory audit and bounded r51 scope | current |
| `04_protocols/protocol_v2_2_r51_candidate_addendum.md` | exact Android Files destination content-label binding with top-region and commit denials | local candidate |
| `reports/protocol_v2_2_r51_local_validation.json` | machine-readable 389-test, real-shape full-chain, negative-case, and v1-seal evidence | passed locally |
| `reports/protocol_v2_2_r51_local_validation.md` | human-readable r51 rationale, safety boundary, and next live action | current |
| `05_project/scripts/run_protocol_v2_2_r51_candidate_smoke.py` | isolated r51 M0 Files smoke entry point | ready |
| `reports/protocol_v2_2_r51_candidate_preflight.json` | source, 27-file freeze, four instances, exact model, emulator, and fresh smoke directory | passed |
| `reports/protocol_v2_2_r51_m0_files_smoke.json` | machine-readable valid pre-commit failure and post-activation Ctrl+A evidence | Gate D withheld |
| `reports/protocol_v2_2_r51_m0_files_smoke.md` | human-readable 14-item selection diagnosis and bounded r52 scope | current |
| `04_protocols/protocol_v2_2_r52_candidate_addendum.md` | post-activation clear-text focus proof and exact bounded repair contract | local candidate |
| `reports/protocol_v2_2_r52_local_validation.json` | machine-readable 392-test, r51-shape regression, denial-case, and v1-seal evidence | passed locally |
| `reports/protocol_v2_2_r52_local_validation.md` | human-readable r52 rationale, safety boundary, and next live action | current |
| `05_project/scripts/run_protocol_v2_2_r52_candidate_smoke.py` | isolated r52 M0 Files smoke entry point | ready |
| `reports/protocol_v2_2_r52_candidate_preflight.json` | source, 27-file freeze, four instances, exact model, emulator, and fresh smoke directory | passed |
| `reports/protocol_v2_2_r52_m0_files_smoke.json` | machine-readable cross-modal stale-accessibility invalidation and readiness gap | invalid attempt; Gate D withheld |
| `reports/protocol_v2_2_r52_m0_files_smoke.md` | human-readable drawer/root mismatch audit and bounded r53 scope | current |
| `04_protocols/protocol_v2_2_r53_candidate_addendum.md` | before-decision cross-modal freshness and preserved protocol boundary | local candidate |
| `reports/protocol_v2_2_r53_local_validation.json` | machine-readable 393-test, stale-tree integration, failure-audit, and v1-seal evidence | passed locally |
| `reports/protocol_v2_2_r53_local_validation.md` | human-readable r53 rationale, evidence boundary, and next live action | current |
| `05_project/scripts/run_protocol_v2_2_r53_candidate_smoke.py` | isolated r53 M0 Files smoke entry point | ready |
| `reports/protocol_v2_2_r53_candidate_preflight.json` | source, 27-file freeze, four instances, exact model, emulator, and fresh smoke directory | passed |
| `reports/protocol_v2_2_r53_m0_files_smoke.json` | machine-readable native success, r50-r53 live branch, recovery, and one-commit evidence | Gate-D preparation allowed |
| `reports/protocol_v2_2_r53_m0_files_smoke.md` | human-readable r53 Files success audit and formal-execution boundary | current |
| `05_project/configs/experiments/v2_2_capability_gate_r53.json` | frozen eight-cell r53 Gate-E manifest with unchanged schedule and acceptance | prepared |
| `05_project/scripts/run_protocol_v2_2_gate_e_r53.py` | exact-source r53 formal preflight and one-launch entry point | prepared |
| `reports/protocol_v2_2_r53_gate_e_preflight.json` | zero-call audit of source, freeze, instances, exact model, emulator, and fresh formal namespace | passed |
| `reports/protocol_v2_2_r53_gate_d_freeze.json` | machine-readable r53 Gate-D freeze and bounded formal-launch authorization | passed; one fresh Gate-E launch authorized |
| `reports/protocol_v2_2_r53_gate_e_stopped.json` | machine-readable formal stop, infrastructure quarantine, invalid coordinate/activation trace, and immutable hashes | Gate E failed at 1/8 |
| `reports/protocol_v2_2_r53_gate_e_stopped.md` | human-readable r53 formal failure analysis and bounded r54 direction | current |
| `04_protocols/protocol_v2_2_r54_candidate_addendum.md` | task-literal malformed-coordinate activation contract and preserved boundaries | local candidate |
| `reports/protocol_v2_2_r54_local_validation.json` | machine-readable 395-test, safe activation, direct-text denial, and v1-seal evidence | passed locally |
| `reports/protocol_v2_2_r54_local_validation.md` | human-readable r54 rationale, evidence boundary, and next live action | current |
| `05_project/scripts/run_protocol_v2_2_r54_candidate_smoke.py` | isolated r54 B3 Contacts smoke entry point | ready |
| `reports/protocol_v2_2_r54_candidate_preflight.json` | source, 27-file freeze, four instances, exact model, emulator, and fresh Contacts smoke directory | passed |
| `reports/protocol_v2_2_r54_b3_contacts_smoke.json` | machine-readable native success, focus-chain audit, deterministic/live boundary, and immutable hashes | Gate-D preparation allowed |
| `reports/protocol_v2_2_r54_b3_contacts_smoke.md` | human-readable r54 Contacts success audit and formal-execution boundary | current |
| `05_project/configs/experiments/v2_2_capability_gate_r54.json` | frozen eight-cell r54 Gate-E manifest with unchanged schedule and acceptance | prepared |
| `05_project/scripts/run_protocol_v2_2_gate_e_r54.py` | exact-source r54 formal preflight and one-launch entry point | prepared |
| `reports/protocol_v2_2_r54_gate_e_preflight.json` | zero-call audit of source, freeze, instances, exact model, emulator, and fresh formal namespace | passed |
| `reports/protocol_v2_2_r54_gate_d_freeze.json` | machine-readable r54 Gate-D freeze and bounded formal-launch authorization | passed; one fresh Gate-E launch authorized |
| `reports/protocol_v2_2_r54_gate_e_stopped.json` | machine-readable four-success formal stop, overlong repair rationale, and immutable hashes | Gate E stopped/failed at 4/8 |
| `reports/protocol_v2_2_r54_gate_e_stopped.md` | human-readable r54 formal result and bounded r55 direction | current |
| `04_protocols/protocol_v2_2_r55_candidate_addendum.md` | exact post-destination Back-repair rationale normalization and preserved boundaries | local candidate |
| `reports/protocol_v2_2_r55_local_validation.json` | machine-readable 399-test, exact r54 replay, negative boundaries, and v1-seal evidence | passed locally |
| `reports/protocol_v2_2_r55_local_validation.md` | human-readable r55 rationale, evidence boundary, and next live action | current |
| `05_project/scripts/run_protocol_v2_2_r55_candidate_smoke.py` | isolated r55 M0 Files smoke entry point | ready |
| `reports/protocol_v2_2_r55_candidate_preflight.json` | source, 27-file freeze, four instances, exact model, emulator, and fresh Files smoke directory | passed |
| `reports/protocol_v2_2_r55_m0_files_smoke.json` | machine-readable valid failure, exact-target/Search-loop trace, memory boundary, and immutable hashes | Gate D withheld |
| `reports/protocol_v2_2_r55_m0_files_smoke.md` | human-readable r55 failure analysis, server-health clarification, and bounded r56 direction | current |
| `04_protocols/protocol_v2_2_r56_candidate_addendum.md` | exact-target ambiguity trigger, sole DocumentsUI view-toggle repair, and preserved boundaries | local candidate |
| `reports/protocol_v2_2_r56_local_validation.json` | machine-readable 405-test validation, real AVD accessibility probe, and v1-seal evidence | passed locally |
| `reports/protocol_v2_2_r56_local_validation.md` | human-readable r56 rationale, live zero-call evidence, and next-action boundary | current |
| `05_project/scripts/run_protocol_v2_2_r56_candidate_smoke.py` | isolated r56 M0 Files smoke entry point | prepared |
| `reports/protocol_v2_2_r56_candidate_preflight.json` | source, 27-file freeze, four instances, exact model, emulator, and fresh Files smoke directory | passed |
| `reports/protocol_v2_2_r56_m0_files_smoke.json` | machine-readable native success, r55 live normalization, r56 evidence boundary, and immutable hashes | Gate-D preparation allowed |
| `reports/protocol_v2_2_r56_m0_files_smoke.md` | human-readable r56 Files success, reliability observation, and formal boundary | current |
| `05_project/configs/experiments/v2_2_capability_gate_r56.json` | frozen eight-cell r56 Gate-E manifest with unchanged schedule and acceptance | prepared |
| `05_project/scripts/run_protocol_v2_2_gate_e_r56.py` | exact-source r56 formal preflight and one-launch entry point | prepared |
| `reports/protocol_v2_2_r56_gate_e_preflight.json` | zero-call audit of source, freeze, instances, exact model, emulator, and fresh formal namespace | passed |
| `reports/protocol_v2_2_r56_gate_d_freeze.json` | machine-readable r56 Gate-D freeze and bounded formal-launch authorization | passed; one fresh Gate-E launch authorized |
| `reports/protocol_v2_2_r56_gate_e_final.json` | machine-readable eight-cell result, 19-criterion audit, retained M0 Contacts failure, Files guard trace, and immutable hashes | Gate E passed at 7/8 |
| `reports/protocol_v2_2_r56_gate_e_final.md` | human-readable r56 Gate-E result, planner-reliability finding, descriptive pairing, and Gate-F boundary | current |
| `04_protocols/protocol_v2_2_r56_gate_f_addendum.md` | r56 Gate-F compatibility mapping, preserved controls, zero-call requirements, and authorization boundary | frozen |
| `05_project/configs/experiments/v2_2_hard_micro_gate_r56.json` | exact-source twelve-cell r56 Hard manifest with unchanged task/order/budget controls and frozen prerequisites | prepared |
| `05_project/scripts/run_protocol_v2_2_gate_f_r56.py` | r56 Gate-F zero-call or one-explicit-batch entry point | prepared |
| `reports/protocol_v2_2_r56_gate_f_preflight.json` | machine-readable 28-file freeze, Gate-E prerequisite, six paired Hard instances, model, emulator, and v1-seal audit | passed; zero calls/cells |
| `reports/protocol_v2_2_r56_gate_f_preflight.md` | compatibility decision, 411-test validation, frozen Batch-1 schedule, and manual-launch boundary | current |
| `reports/protocol_v2_2_r56_gate_f_batch1_stopped.json` | immutable one-cell checkpoint, infrastructure isolation, verified repeated-tap trace, and raw artifact hashes | Gate F stopped/failed at 1/12 |
| `reports/protocol_v2_2_r56_gate_f_batch1_stopped.md` | task-grounded repetition incompatibility analysis and bounded next-candidate scope | current |
| `04_protocols/protocol_v2_2_r57_candidate_addendum.md` | finite task-count repeated-tap trigger, denial boundaries, and preserved r56 result | local candidate |
| `reports/protocol_v2_2_r57_local_validation.json` | machine-readable 423-test, exact H01 replay, denial matrix, and v1-seal evidence | passed locally |
| `reports/protocol_v2_2_r57_local_validation.md` | human-readable r57 contract, validation result, and zero-call boundary | current |
| `05_project/scripts/run_protocol_v2_2_r57_h01_candidate_smoke.py` | exact-source candidate preflight and isolated non-scored H01 B3 entry point | prepared |
| `reports/protocol_v2_2_r57_candidate_preflight.json` | machine-readable 28-file freeze, inherited Gate-E prerequisite, six paired Hard instances, exact model, emulator, and v1-seal audit | passed; zero calls/cells |
| `reports/protocol_v2_2_r57_candidate_preflight.md` | human-readable zero-call result and one-cell non-scored H01 authorization boundary | current |
| `reports/protocol_v2_2_r57_h01_candidate_smoke_stopped.json` | immutable non-scored H01 failure, delayed-DOM causal audit, denial counters, and raw hashes | r57 stopped; formal Gate F withheld |
| `reports/protocol_v2_2_r57_h01_candidate_smoke_stopped.md` | human-readable r57 failure analysis and bounded delayed-progress reconciliation direction | current |
| `04_protocols/protocol_v2_2_r58_candidate_addendum.md` | delayed semantic convergence reconciliation, task-control binding, and preserved denial boundaries | local candidate |
| `reports/protocol_v2_2_r58_local_validation.json` | machine-readable 430-test, denial-matrix, v1-seal, exact-source, model, and emulator evidence | passed locally; preflight preparation allowed |
| `reports/protocol_v2_2_r58_local_validation.md` | human-readable r58 rationale, validation result, and zero-call boundary | current |
| `05_project/scripts/run_protocol_v2_2_r58_h01_candidate_smoke.py` | exact-source r58 preflight and isolated non-scored H01 B3 entry point | prepared |
| `reports/protocol_v2_2_r58_candidate_preflight.json` | machine-readable 28-file freeze, paired instances, inherited prerequisite, exact model, emulator, and v1-seal audit | passed; zero calls/cells |
| `reports/protocol_v2_2_r58_candidate_preflight.md` | human-readable zero-call result and one-cell non-scored r58 authorization boundary | current |
| `reports/protocol_v2_2_r58_h01_candidate_smoke_stopped.json` | immutable live reconciliation/override success, sixth-tap denial, stale-summary failure, and raw hashes | r58 stopped; formal Gate F withheld |
| `reports/protocol_v2_2_r58_h01_candidate_smoke_stopped.md` | human-readable verified-ledger versus stale-summary analysis and bounded next direction | current |
| `04_protocols/protocol_v2_2_r59_candidate_addendum.md` | verified repeat-progress ledger, summary-precedence rule, deterministic complete-count aggregation, and preserved safety boundaries | local candidate |
| `reports/protocol_v2_2_r59_local_validation.json` | machine-readable 439-test, exact-source, historical-freeze, v1-seal, model, emulator, and zero-call evidence | passed locally; preflight preparation allowed |
| `reports/protocol_v2_2_r59_local_validation.md` | human-readable r58 causal bridge, r59 evidence contract, validation result, and zero-call boundary | current |
| `05_project/scripts/run_protocol_v2_2_r59_h01_candidate_smoke.py` | exact-source r59 preflight and isolated non-scored H01 B3 entry point | prepared |
| `reports/protocol_v2_2_r59_candidate_preflight.json` | machine-readable 28-file freeze, paired instances, inherited prerequisite, exact model, emulator, and v1-seal audit | passed; zero calls/cells |
| `reports/protocol_v2_2_r59_candidate_preflight.md` | human-readable zero-call result and one-cell non-scored r59 authorization boundary | current |
| `reports/protocol_v2_2_r59_h01_candidate_smoke_stopped.json` | immutable wrong-control ledger binding, load-time operand semantics, five-click trace, retrospective correction, and raw hashes | r59 stopped; formal Gate F withheld |
| `reports/protocol_v2_2_r59_h01_candidate_smoke_stopped.md` | human-readable setup-button false binding, correct 3240 operand sequence, and bounded two-axis state-machine direction | current |

The r39 raw trajectories are under
`runs/protocol_v2_2/nonhard_capability_v2_2_seed20260729_r39/` and remain
excluded from Git. This is a non-Hard protocol requalification artifact, not a
Hard benchmark result or evidence that M0 outperforms B3.

## Not yet complete

- fresh v15 retrieval audit, component smoke and final G7 decision;
- final preregistration commit and `protocol-v1` tag;
- 364 frozen Hard episodes;
- manual case annotation, frozen statistics and final report.
