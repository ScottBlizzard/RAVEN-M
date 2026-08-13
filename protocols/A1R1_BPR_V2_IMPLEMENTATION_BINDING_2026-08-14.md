# A1-R1 BPR v2 Implementation Binding

Date: 2026-08-14 (Asia/Hong_Kong)

Status: normative clarification of the frozen v2 design; no formula, cap,
renderer, trigger, or runtime capability is added.

Design SHA-256:
`e6ff3a975484502e2b7368dd3f9775956957a613e3cf4a355e4e7e1c8d1ffc07`.

Normative bundle SHA-256:
`61adeb079ac1b0ff286c5dff5e15ef258f3465ccbf9a888e161569d0e547fcb4`.

## 1. R3 legacy-envelope definition

The denominator is the ordered 514 executed A1 records with a valid
`MEMORY[...]` prefix and non-`none` pending field. Duplicate strings remain
separate records. Terminal/non-executed prefixes are excluded. Each extracted
legacy pending string is measured after whitespace-collapse and strip using the
same extraction rules as the v1 raw-trace audit. `joint fit` means that the one
legacy pending string satisfies both `codepoints <= 100` and
`UTF-8 bytes <= 128`; it does not claim that a future BPR `op + proof` pair fits.

The independent reconstruction is 511/514, above the frozen threshold 489.
The three misses are duplicate 122-character OsmAnd pending strings. The formal
replay must reconstruct the ordered-record digest and may not merely copy this
number.

## 2. Controller interface and step coordinates

The production class is `BoundedPendingReceiptV2` and exposes:

```text
read(context) -> (text, audit)
commit_injection(ticket_id, final_prompt_sha256)
cancel_injection(ticket_id, reason)
history_summary(action_summary) -> text
observe_step(**existing_controller_kwargs) -> audit
audit_record() -> audit
```

`read_enabled` is a constructor/config value. `read()` prepares a ticket but
does not consume receipt or episode budgets. The controller constructs the
exact final prompt, calls `commit_injection`, and only then sends that request.
If prompt construction fails it calls `cancel_injection`; a transport failure
after request construction retains the committed audit but belongs to an
infrastructure-invalid episode. At most one prepared ticket may exist.

All step numbers are zero-based controller request ordinals. `read()` occurs
before request `r`; an executed action is observed after request `r` as
`source_step=r`; eligible reads are `r=s+1..s+4`; `s+5` expires before read.
Terminal, answer, parse-error, or unexecuted actions never call `observe_step`.

## 3. Retirement and counter precedence

After a committed injection, retirement precedence is:

```text
episode_budget (the eighth episode read)
> read_cap (the second receipt read)
```

Both trigger flags are audited, but there is one tombstone reason. The eighth
read immediately retires the active receipt. A receipt normally retires on its
second read, so a later `receipt_read_cap` eligibility suppression is not
expected; the counter records a retirement trigger, not a third-read attempt.

Only exact lowercase ASCII `none` is the sentinel. `None` and `NONE` are normal
field text. Same-op identity is NFKC/whitespace/casefold exact identity only;
semantic paraphrases are different operations and may replace the receipt.
Only the most recently retired operation is protected by the one tombstone.

## 4. History and prompt audit

For a valid prefix, history retains only its imperative. Invalid prefixes
retain the raw summary. `attestation_applied` is true only when the committed
summary differs from the model summary. Every read audit records resident
history SHA, rendered base-prompt SHA, final-prompt SHA, exact injected bytes,
ticket ID, and request step.

## 5. Five-task gate and R5

Performance stages remain:

```text
A0 four tasks 4/4 -> RecipeDelete 1/1 -> remaining 14
```

R5 is separate from performance. Its values are:

```text
PROSPECTIVE_UNKNOWN_PRELIVE
NOT_FALSIFIED_GATE5
FALSIFIED_GATE5
PROSPECTIVE_UNOBSERVED_GATE5
NOT_EVALUABLE_INFRA
```

Five-task 5/5 releases the remaining tasks. R5 becomes
`NOT_FALSIFIED_GATE5` only if RecipeDelete has a relevant accepted receipt and
its required read opportunity is not lost to the episode budget. A silent or
otherwise unexposed 5/5 is `PROSPECTIVE_UNOBSERVED_GATE5`, not cap evidence.

## 6. Primary and empty-read arms

Primary and empty-read have distinct config, receipt, checkpoint, result, and
experiment identities. Empty-read runs only after a complete primary 19-task
result. Its fixed five tasks run non-fail-fast; scientific failures are retained
and never rerun. Each arm independently allows at most two infrastructure-
invalid replacements.

Exact causal matching uses a `common_core_config_sha256` that excludes only
experiment ID and `read_enabled`. The pre-read causal-state projection excludes
arm identity and read-derived counters, but includes active receipt, tombstone,
write lifecycle, visible screen, resident history, prior canonical actions, and
ordinary base prompt. After the first behavioral divergence, later matches are
normally unavailable and may not use near matching.

Productive recognition may use read-time RGB only when it already visibly
satisfies the receipt proof, the next primary decision is a correct terminal
decision, the exact empty-read decision differs, and the primary episode fully
succeeds. This is a recognition path, not post-read screen progress. Other
productive reads use the frozen action/progress/relapse path.

## 7. Immutable artifact chain

Each JSON artifact has a `content_sha256` computed from canonical JSON after
omitting only `content_sha256`. The exact whole-file SHA (including the trailing
LF) is recorded only by its successor or an external manifest; a file never
claims to contain its own whole-file SHA.

The chain is:

```text
implementation commit
-> source freeze
-> offline replay
-> zero-generation preflight
-> arm-specific live receipt
-> append-only arm-specific checkpoints
-> immutable arm-specific result
-> causal-read report
-> final adjudication
```

Primary result reports `MECHANISM_PENDING_ABLATION`. Final mechanism judgment
exists only in final adjudication after both results and the causal report.
Early primary scientific stop makes Accuracy FAIL, Cost
`NOT_EVALUABLE_EARLY_STOP`, and Mechanism `NOT_EVALUABLE_NO_ABLATION`.

Source freeze binds the implementation commit's Git blobs. The implementation
commit must be an ancestor of the evidence commit and current production source
bytes must match its blobs; generated evidence is excluded from the source map.

## 8. Live qualification

Offline replay and preflight must both be `PASS`, have `errors=[]`, zero
generation calls, and retain R5 as `PROSPECTIVE_UNKNOWN_PRELIVE`. Preflight must
set `live_generation_authorized=true`. Each arm needs its own launch intent and
receipt bound to `read_enabled`, experiment/config hashes, source freeze,
offline replay, preflight, model manifest, process command, package versions,
environment, observed served model ID, PID, port, and qualification timestamp.
The runner revalidates the receipt and source closure immediately before live
generation.

Checkpoints are ordinal, append-only, arm-specific files with previous
checkpoint whole-file SHA, attempt-chain head, episode artifact hash, gate
state, receipt chain, and content digest. A mutable `checkpoint.json` may only
point at the authoritative latest ordinal file.
