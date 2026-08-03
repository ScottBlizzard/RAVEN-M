# EEST-AC v0.2 Validation, Isolation, and Blind-run Record

## Pre-run gates

- Focused EEST-AC replay/negative suite: 35 passed.
- Full repository regression at the final pre-lock implementation: 1,035 passed and 1 failed.
- The one failure was the transparently expected legacy r79/r78 frozen-manifest conflict: `test_r78_candidate_static_manifest_validation_passes`.
- No old manifest was edited to hide that conflict.
- Static source isolation found no forbidden imports, task/instance literals, or online M-RISK path.
- Runtime preflight passed with the frozen Qwen3-VL-32B backend and AndroidWorld emulator.
- Zero-model-call preflight count: 0 generation calls.
- Novelty audit found no prior occurrence of the three selected task classes in old runs/configs/reports.
- Protocol lock checked 23 frozen implementation/configuration files before the batch.

## Blind execution discipline

- The nine-cell order was frozen before execution.
- No cell trajectory was opened and no code/configuration was changed while the batch was running.
- The runner completed exactly 9 cells, wrote `batch_complete.json`, stopped with `preregistered_nine_cell_batch_complete_no_auto_expand`, and only then released the blind lock and wrote the unblinded instances.
- No model call was made after batch completion during analysis.

## Legacy WIP isolation

The three pre-existing legacy WIP files remained untouched with the same hashes:

| Path | SHA-256 |
|---|---|
| `05_project/src/raven_m/controller/episode_controller.py` | `fc0e82e0fde90119365d4f685f080eb4519bf2f602e4bda58de5d4809a40fe33` |
| `05_project/src/raven_m/controller/protocol_v2_guard.py` | `ff89d6b70be4b4738646d262beb67d7b7e932e9eb95956d940b1c5000a999d10` |
| `05_project/tests/scripts/test_protocol_v2_2_r79_r78_trace_replay.py` | `5bb1f1e3de673a1072cfee62938b761a62fd69c187d5eadf54bc46b115a3fd0a` |

These files remain modified/untracked exactly as legacy WIP; they are not part of the EEST-AC v0.2 result commit.

## Post-batch analysis validation

- The analysis is reproducible from `batch_complete.json`, the nine episode summaries, raw model-call JSONL files, and the post-batch unblinded gold file.
- The analyzer refuses to run unless `cell_count == 9` and `trajectory_blind_lock_released == true`.
- It performs no model or emulator calls.
- Post-batch hard gates: 0 schema truncations, 18/18 raw calls accounted, and 9/9 evaluator results.
