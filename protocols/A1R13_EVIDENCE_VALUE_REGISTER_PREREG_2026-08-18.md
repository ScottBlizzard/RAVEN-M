# A1-R13 EVR prospective protocol

Date: 2026-08-18
Status: prospective, pre-generation
Parent evidence commit: `aa3176286a65c16becb59772cce1d742f13d441c` (`SYS-NAG V4` sealed result)
Mechanism ID: `a1r13_evidence_value_register_v1`
Experiment ID: `A1R13_EVR_QWEN3VL32B_AW_HARD_S20260806_G3407_V1`

## 1. Question and claim boundary

A1-R2 reached 6/19 but its BrowserMultiply trace retained the claim “numbers
recorded” while discarding the five model-authored values `1, 8, 10, 7, 2`.
The model later entered `120`, while the product is `1120`. A1-R13 asks one
narrow question: can an R2-compatible, bounded register preserve explicit
model-authored integer evidence long enough for the same executor to use it?

This is a pure memory intervention. It adds no planner, critic, verifier,
retriever, OCR, UI tree, evaluator access, model call, arithmetic tool, action
override, guard, forced termination, task-name rule, app rule, or step. It does
not calculate the product. The current screenshot remains authoritative.

The V4 19-task trace is a post-hoc design/development set, not held-out or
confirmatory evidence. All live results are a matched, same-seed prospective
diagnostic and do not establish generalization.

## 2. Frozen base

- exact official Qwen3-VL-32B controller and A1 working-memory system prompt;
- model `Qwen/Qwen3-VL-32B-Instruct`, revision
  `0cfaf48183f594c314753d30a4c4974bc75f3ccb`;
- task seed `20260806`, generation seed `3407`;
- unchanged sampling, current-screenshot input, action schema, task instances,
  native per-task budgets, AndroidWorld evaluator, and single transport call;
- exact A1-R2 `CompactVerifiedPendingMemory` behavior for verified/pending,
  TTL 8, history de-duplication, ticket commit, and base renderer.

## 3. Frozen EVR state

The additional state is one episode-local list of at most six `EvidenceAtom`s.
Each atom contains only:

- exact signed integer string, 1–6 digits;
- source step and model call ID;
- source response, current screenshot, observed-field, and pending-field SHA256.

The register has an eight-request TTL, renders only from two values onward,
and is cleared when the model writes exact `pending=none`. It never crosses an
episode.

## 4. Exact write rule

The ordinary A1-R2 prefix must first be valid. The `observed=` field must
contain exactly one integer matching:

```regex
(?<![\w.])[-+]?\d{1,6}(?![\w.])
```

The same response's normalized `pending=` must contain at least one collection
cue and one arithmetic cue:

```text
collection = record | collect | remember | display
arithmetic = product | multiply | sum | total | calculate
```

Only then is the integer appended. Repeated values are retained because a
sequence may legitimately contain duplicates. The seventh candidate is
suppressed; existing evidence is not evicted. Invalid prefixes and nonmatching
responses leave the register unchanged.

These fixed English cues are generic grammar for the existing English model
contract. They are not selected by task name, application, known reward, or
screen hash.

## 5. Exact renderer

The unmodified R2 renderer is produced first. From two values onward, append
one newline and exactly:

```text
TRANSIENT MODEL-AUTHORED EVIDENCE (unverified; current screenshot remains authoritative): observed integer sequence = [{comma-space joined values}].
```

Maximum combined memory render is 1100 characters. Overflow fails closed by
omitting the EVR suffix, never by truncating values. A successful transport is
required before the read ticket is consumed.

## 6. Offline development replay

The committed fixture is derived from the byte-bound 19 valid V4 episodes and
contains only the model-authored action summaries and provenance required to
replay R2/EVR. It performs zero generation.

Required exact result:

- 19 episodes and 558 model decisions;
- one active episode only: `BrowserMultiply`;
- six R2 success tasks: zero EVR activation and zero EVR render;
- Browser: one activation, five accepted values, exact final sequence
  `[1, 8, 10, 7, 2]` visible before request step 18;
- no other task activates;
- base R2 text is byte-identical before the optional appended suffix;
- maximum combined render <=1100 chars, audit <=131072 UTF-8 bytes;
- zero calls, OCR, hidden UI, evaluator access, computation, override, or stop.

Offline PASS proves only implementation feasibility and historical silence. It
does not authorize a claim that Browser will succeed live.

## 7. Live order and stopping

The fixed order is the same 19-task manifest.

1. Run the exact six A1-R2 successes in order. Each must reward 1.0 and EVR
   must remain silent. Any valid failure or EVR activation stops the arm.
2. Run `BrowserMultiply` seventh. It must have at least one committed EVR read
   containing the exact five-value sequence and must reward 1.0. Otherwise the
   arm stops. Silent stochastic success is performance-only and does not pass
   the mechanism gate.
3. Only after 7/7 may the remaining 12 tasks run without repeating the first
   seven.

A valid scientific failure is never rerun. Infrastructure-invalid work is
retained and may be replaced only for the same task, at most once per task and
twice in the suite. Each effective model decision has exactly one transport
attempt. A server restart requires a fresh receipt but not a rerun of a valid
episode.

## 8. Verdicts

- Accuracy PASS: at least 7/19 full successes, reward >6.5, and no loss on the
  six R2 successes.
- Cost is reported separately; zero extra calls is mandatory. Full-suite
  calls, tokens, and wall time are compared with R2, but trajectory variance
  prevents equal-cost claims from silence alone.
- Mechanism candidate support: Browser contains the exact write → later
  committed render → same-request prompt hash → next action chain and finishes
  successfully. Because there is no matched empty-read fork, this remains
  ablation-unresolved candidate support, not a causal proof.
- A success with no EVR read is unattributed. Pixel change alone is not task
  progress. Partial reward is not a full success.

## 9. Failure taxonomy

`PRESERVATION_FAILURE`, `FALSE_POSITIVE_ACTIVATION`,
`TARGET_NO_ACTIVATION`, `TARGET_VALUES_INCOMPLETE`,
`COMMITTED_READ_NO_SUCCESS`, `TARGET_SUCCESS_ABLATION_UNRESOLVED`,
`COMPLETE_NO_ACCURACY_GAIN`, `COMPLETE_ACCURACY_GAIN`, and
`INFRASTRUCTURE_INVALID`.

## 10. Freeze discipline

The design, core, config, contract, shared runner/controller dependencies,
fixture, replay, preflight, server scripts, and tests are source-frozen at one
clean implementation commit. Preflight and receipt are generated afterward and
bind that commit. Any semantic change after the first valid generation requires
a new mechanism/experiment identity; thresholds are never repaired in place.
