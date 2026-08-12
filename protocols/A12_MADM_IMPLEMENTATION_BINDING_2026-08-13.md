# A12 MADM Implementation Binding — 2026-08-13

This file binds the executable contract to
`GPT_PRO_A12_MINIMAL_ACTION_DIVERGENCE_MEMORY_DESIGN_2026-08-13.md`. It does
not add a trigger, parser, score, exception, or task-specific decision rule.

## Identity

```text
mechanism_id = a12_minimal_action_divergence_memory_v1
experiment_id = A12_MADM_QWEN3VL32B_AW_HARD_T20260806_G3407_V1
review_commit = ee30db3692bd7797722b3ea29a70266eb6256c7e
parent_evidence_commit = 5009034fa050d2f065e4eb08ff1c8c394a0ac586
task_seed = 20260806
generation_seed = 3407
```

The implementation commit must be a clean descendant of `review_commit`.

The design freezes a `port` receipt field but does not assign a numeric value.
The existing official vLLM arm convention is therefore bound deterministically
as `port = 18000`. This is infrastructure identity only and does not affect the
memory mechanism or model sampling.

## Two-layer source freeze

Layer 1 is `A12_IMPLEMENTATION_COMMIT`. The exact closure is the tuple
`a12_contract.SOURCE_FILES`. It contains design, binding, production and shared
runtime code, config, exact named tests, scripts, reference segments, source
specification, test manifest, and immutable historical evidence inputs.

Layer 1 excludes all generated layer-2 artifacts:

```text
A12_STATIC_SOURCE_FREEZE.json
A12_OFFLINE_REPLAY_REPORT.json
A12_OFFLINE_ABLATION_REPORT.json
A12_ZERO_GENERATION_PREFLIGHT.json
A12_LIVE_SERVER_RECEIPT.json
A12_FINAL_RESULT.json
```

`A12_STATIC_SOURCE_FREEZE.json` has exactly:

```json
{
  "implementation_commit": "<40-hex>",
  "files": {"exact/path": "sha256"},
  "payload_sha256": "SHA256(canonical_json({implementation_commit, files}))"
}
```

It contains no whole-file hash of itself. Replay binds `payload_sha256`;
preflight binds both `payload_sha256` and the replay whole-file hash; receipt
binds the preflight whole-file hash. There is no reverse edge.

## Preflight and live binding names

The following names are literal and cannot be aliased:

```text
implementation_commit
source_freeze_payload_sha256
offline_replay_sha256
preflight_sha256
launch_intent_sha256
served_model_id
model_realpath
model_manifest_sha256
```

Formal preflight uses `status = PASS`, `errors = []`, and
`generation_calls = 0`. The live receipt uses the same spelling for every
shared identity field. It additionally records:

```text
schema = a12_live_server_receipt_v1
status = PASS
mechanism_id
experiment_id
process_pid
process_cmdline
host
port
vllm_version
torch_version
transformers_version
observed_served_model_ids
qualification_timestamp
generation_calls = 0
```

Qualification requires exact launch-intent hash and command, a live matching
process, the exact single served model ID, model realpath and manifest,
nonempty package versions, and a receipt age no greater than 12 hours.

## Prospective suite contract

The first four valid episodes are, in order:

1. `ExpenseDeleteMultiple2`
2. `RetroSavePlaylist`
3. `SimpleCalendarAddOneEvent`
4. `SportsTrackerTotalDurationForCategoryThisWeek`

Each requires reward 1, transport-attempt maximum 1, and zero added calls,
guard, override, and forced termination. A valid scientific failure is
terminal and prevents release of the remaining fifteen tasks.

After 4/4, all remaining tasks run exactly in the order frozen in
`a12_contract.TASK_ORDER`. Exact closure requires nineteen unique valid episode
IDs, finite rewards, one valid episode per task, exact task order and seed, and
transport-attempt maximum one.

## Infrastructure-invalid replacement

Only the categories in design section 47 may be infrastructure-invalid. A
replacement is valid only for the same task and frozen identities. Every
invalid attempt contains `resolved_by_episode_id`; its replacement valid
episode contains that invalid ID in `resolves_invalid_episode_ids`. The links
must be exact in both directions. A task permits at most two invalid attempts;
a third infrastructure failure closes the suite as infrastructure incomplete.

Correctly linked and resolved invalid attempts do not invalidate exact 19/19
closure. A scientific failure cannot be replaced.

## Result boundary

Overall pass additionally requires success count at least 6, reward greater
than 5.5, model calls below 603, executed actions below 596, total tokens below
3,464,267, no more than 95 nonempty reads and 9,500 rendered memory tokens,
zero added components, at least one successful memory-active episode and at
least one productive-divergence hypothesis.

No formal pass replay, live receipt, or result is created by this binding.

## Frozen pre-implementation feasibility outcome

The independent builder was executed against the 27-episode materialized raw
trace corpus before any GPU use. It recovered all 23 frozen A10-v1 A6 loop
identities. Sixteen have loose pairwise support, but chronological simulation of
immediate second-support maturity, cooldown, semantic one-shot, and the five-read
episode cap leaves only 11/23 possible immediate reads, below the required 20/23.

The committed `A12_ZERO_GENERATION_PREFLIGHT.json` is a terminal fail-closed
record with status `PROTOCOL_INVALID`, not a formal PASS preflight. It carries
no implementation commit, source-freeze digest, replay hash, receipt, or live
authorization. The wrapper refuses to construct an A12 live command while this
record is present.
