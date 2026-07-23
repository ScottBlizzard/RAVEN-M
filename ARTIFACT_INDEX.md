# Artifact index

This index distinguishes verified artifacts from planned work. No file listed
here is evidence of a scored Hard result unless explicitly marked as such.

## Verified infrastructure

| Artifact | Purpose | Status |
|---|---|---|
| `04_protocols/environment_lock.yaml` | machine, model, transport and gate lock | current through B0 dry-run gate |
| `05_project/metadata/model_snapshot_manifest.json` | exact 66.7 GB checkpoint inventory and hashes | verified |
| `05_project/metadata/server_real_model_smoke.json` | real AndroidWorld screenshot-to-action call | verified, non-scored |
| `05_project/metadata/server_audit_4090_post_model.json` | post-restart model-host audit | verified |
| `05_project/metadata/model_max_shape_stress.json` | ten-request 7,704-token stress result | 10/10 passed |
| `06_local_runtime/metadata/runtime_audit.json` | Windows Android host audit | verified |
| `06_local_runtime/metadata/androidworld_smoke.json` | AndroidWorld initialization/observation smoke | verified |

## Implemented B0 path

| Artifact | Purpose | Status |
|---|---|---|
| `05_project/schemas/action.v1.schema.json` | shared canonical action contract | implemented and tested |
| `05_project/prompts/executor_v0.md` | memory-free B0 policy prompt | dev v0 |
| `05_project/src/raven_m/models/transformers_client.py` | hashed private model client | implemented |
| `05_project/src/raven_m/env/androidworld_adapter.py` | normalized-to-pixel action adapter | implemented |
| `05_project/src/raven_m/controller/episode_controller.py` | thin B0 episode loop and logger | implemented |
| `05_project/scripts/run_b0_dry_run.py` | real excluded-protocol runner | implemented |
| `05_project/tests/fixtures/golden_episode/` | deterministic parse/map replay | passing |
| `reports/first_72_hours.md` | measured execution report | current |

Raw trajectories are under `runs/excluded_protocol_dry_run/`, excluded from
Git, and excluded from formal results.

## Not yet complete

- 50-decision/five-task G3 development gate;
- B1, B2 and B3 baselines;
- frozen 19-task Hard protocol and preregistration hash;
- RAVEN-M memory and logical roles;
- scored Hard comparisons, ablations, statistics and final report.
