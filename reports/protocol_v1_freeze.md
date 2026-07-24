# protocol-v1 freeze record

Status: **frozen**

Freeze date: 2026-07-24
Scored Hard episodes created during freeze: **0**

## Gate evidence

- G4 baseline-family development gate: passed.
- G6 inspectable-memory gate: passed.
- G7 full-method development gate: passed.
- Full project tests: 75/75 passed.
- AndroidWorld Hard manifest audit: 19/19 registered task classes passed.
- Frozen schedule: 364 unique cells with phase counts 95, 19, 114, and 136.
- Model identity: exact Qwen3-VL-32B-Instruct revision
  `0cfaf48183f594c314753d30a4c4974bc75f3ccb`.
- Backend:
  `qwen3_vl_32b_transformers_bf16_4x4090_v1`.

## Frozen digests

- Protocol-critical files: 100.
- Canonical protocol-record SHA-256:
  `0ead31e96d5b8a0769fd3cb771d5635a66fd5a327aec6658b82dbd8d95bf6de2`.
- Final preregistration-file SHA-256:
  `6cfde3bcf80a9e9ccb7adb2476350a8a132d5a244d898d576c850e20ba8ec6d7`.
- Git tag: `protocol-v1`.

The final manifest is
`05_project/metadata/preregistration_v1.json`. It records the path, byte
length, and SHA-256 of every frozen protocol-critical file.

## Enforcement

Before creating a Hard episode, the frozen runner:

1. verifies every recorded file hash;
2. requires the environment permission flag;
3. requires a passed protocol audit;
4. requires `protocol-v1` to be an ancestor of the current Git HEAD;
5. verifies the exact model revision/backend and at least 20 GiB free disk;
6. snapshots the frozen schedule and freeze identity into the run directory.

Changing any frozen prompt, config, schema, runner, method source, source
snapshot, or audit artifact blocks execution. Such a change requires a new
protocol version and cannot silently replace protocol-v1.

## Next boundary

The next permitted activity is the first blocked Hard breadth run under the
frozen launcher. Hard outcomes may be used for reporting and error analysis,
but not to retune protocol-v1.
