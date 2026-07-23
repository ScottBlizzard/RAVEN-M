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

## Not yet complete

- fresh v15 retrieval audit, component smoke and final G7 decision;
- final preregistration commit and `protocol-v1` tag;
- 364 frozen Hard episodes;
- manual case annotation, frozen statistics and final report.
