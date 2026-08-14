# A1-R2 Compact Verified/Pending Ledger Preregistration

Date: 2026-08-14 (Asia/Hong_Kong)

Status: prospective design; no live generation is authorized until its own
source freeze, real-trace replay, tests, preflight, and fresh receipt pass.

## Motivation and version boundary

A1-R1 BPR-v2 failed the first A0 preservation task. Its only read represented
an app-drawer navigation operation, while the later task ledger cleared the
still-unfinished `Bike Repairs` deletion and the model terminated incorrectly.
The original A1 trace on the same task retained `verified=Public Transit and
Tuition Fees deleted; pending=locate and delete Bike Repairs` and succeeded.

A1-R2 is not a repair or continuation of BPR-v2. It has a new mechanism and
experiment identity. It restores the already-scored A1 writer contract exactly
and changes only deterministic storage and rendering.

## Identity

- mechanism: `a1r2_compact_verified_pending_v1`
- experiment: `A1R2_CVP_QWEN3VL32B_AW_HARD_T20260806_G3407_V1`
- model/task/generation seeds, sampling, screenshots, action schema, task
  instances, native step budgets, and evaluator are identical to A0/A1.
- system prompt: exact frozen `A1_WORKING_MEMORY_SYSTEM_PROMPT`; A1-R2 adds no
  new response syntax.

## Single intervention

The model continues to emit A1's exact form:

`MEMORY[observed=...; verified=...; pending=...] | <ordinary Action imperative>`

The deterministic episode-local memory:

1. removes the `MEMORY[...] |` prefix from ordinary Action history;
2. discards `observed`, because the current screenshot is authoritative;
3. retains exactly one latest `(verified, pending)` pair;
4. replaces the pair on the next valid model-authored prefix;
5. clears when `pending=none`;
6. expires after eight request ordinals without a valid refresh;
7. injects only the latest pair, using a fixed renderer;
8. adds zero model calls and never blocks, overrides, repairs, or terminates an
   action.

Fixed renderer:

```text
Latest compact task ledger from your own previous Action:
VERIFIED: {verified}
PENDING: {pending}
The current screenshot is authoritative. Continue the pending task only when it remains consistent with what is visible.
```

Maximum resident records: one. Maximum rendered characters: 1,100. A read is
consumed only after the exact text is appended to the real next request and its
final prompt hash is recorded.

## Zero-generation replay gate

Replay the complete immutable A1 19-episode suite
`official_qwen_20260810T122419_26573d7c` without model generation. It must show:

- exactly 19 episode JSON files and 596 executed actions;
- at least 500 valid A1 memory prefixes;
- every A0-four success and the Recipe gain has at least one valid pending
  state and one projected non-empty A1-R2 read;
- projected compact rendered characters are at most 35% of A1's actual
  rendered-memory characters;
- zero hidden UI/evaluator/future data and zero generation calls.

Replay is feasibility/cost evidence only; it cannot predict live reward.

## Prospective execution

Fixed order:

1. the four A0 successes, fail-fast and requiring 4/4;
2. `RecipeDeleteMultipleRecipesWithConstraint`, fail-fast and requiring 5/5;
3. the remaining fourteen frozen tasks without rerunning the first five.

Scientific failure is never rerun. Infrastructure-invalid attempts remain
linked and may replace only the same task under the frozen replacement limit.

Accuracy pass requires more than A1's five full successes, reward above 5.5,
and no loss on A1's five successes. Cost pass independently requires fewer
than 603 calls, 3,464,267 total tokens, and 14,595.492 seconds. Mechanism
activation or reduced context alone is not an accuracy claim.

## Falsification

Any A0-four failure rejects the arm immediately. Recipe failure rejects A1
gain preservation. A successful task with no committed read is performance
only and unattributed. Thresholds or syntax cannot be changed after the first
valid live generation; any change creates a new version.

All JSON-to-JSON artifact bindings use canonical object content hashes rather
than platform-dependent file-byte hashes, so CRLF/LF checkout policy cannot
change the scientific identity.
