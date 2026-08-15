# SYS-TRRC-R2 one-shot triggered recovery preregistration

Date: 2026-08-15 (Asia/Hong_Kong)

Status: scientific contract only. No implementation, qualification, or live
generation is authorized by this document.

## 1. Identity and claim boundary

- Protocol ID: `SYS_TRRC_R2_ONE_SHOT_RECOVERY_PREREG_V1`
- System family: `SYS-TRRC`
- Frozen parent mechanism: `a1r2_compact_verified_pending_v1`
- Frozen parent evidence commit:
  `83c0de5bed18740719b46b5bdd1fccf7904ba0cb`
- Task seed: `20260806`
- Executor generation seed: `3407`
- Executor and auxiliary model: the same frozen Qwen3-VL-32B revision and
  runtime identity used by the qualified A1-R2 line

This is a composite-system study, not an A-class memory arm. The detector is a
policy scheduler, the auxiliary call is additional policy-side inference, and
neither is part of the R2 memory mechanism. Its scientific description is:

> immutable A1-R2 memory plus a deterministic episode-local scheduler and at
> most one same-Qwen auxiliary recovery-reasoning call per episode.

Any Full-system gain is first attributed to the composite intervention. It may
be attributed specifically to specialized recovery reasoning only if Full
beats the resource-matched Generic active control. It must never be reported as
a pure-memory gain, an R2-memory gain, or evidence that the immutable R2 ledger
itself improved.

A1-R2 remains the positive reference at 6/19, reward 6.5, 603 executor calls,
595 executed actions, 2,685,730 total tokens, and 11,230.182856 valid seconds.
All 19 tasks and this seed have already been observed; the study is a matched
prospective diagnostic, not held-out generalization.

## 2. Four frozen arms

### B: Base

- Arm ID: `SYS-TRRC-R2-BASE`
- Exact A1-R2 executor and memory.
- No detector and zero auxiliary calls.
- No new prompt content or control path.

### D: Detector-only

- Arm ID: `SYS-TRRC-R2-DETECTOR`
- Exact Base plus the frozen detector in shadow mode.
- Zero auxiliary calls.
- Detector output is audit-only and cannot alter R2 state, prompts, history,
  actions, termination, or native budgets.

### G: Generic active control

- Arm ID: `SYS-TRRC-R2-GENERIC`
- Exact Detector-only arm plus at most one same-Qwen auxiliary call when the
  same detector triggers.
- The auxiliary role performs an ordinary independent second reasoning pass.
- Its valid three-field output is rendered once into the next executor request.

### F: Full specialized recovery

- Arm ID: `SYS-TRRC-R2-FULL`
- Identical to Generic except for one frozen auxiliary role-instruction line.
- The auxiliary role identifies the visibly unsupported or recurring approach
  and proposes one screenshot-grounded counterfactual recovery strategy.

The required contrasts are:

| Contrast | Permitted interpretation |
|---|---|
| Full - Base | value of the complete composite system |
| Detector-only - Base | detector wiring and CPU/timing effects |
| Generic - Detector-only | value of generic extra inference plus advice |
| Full - Generic | value of specialized recovery reasoning |

Full versus Base alone cannot establish specialized-component causality.

## 3. Immutable R2 boundary

Across all four arms, A1-R2's parser, `verified + pending` ledger, TTL, state
replacement/refresh/clear semantics, renderer, history-prefix deduplication,
read ticket semantics, model-visible screenshot policy, executor system prompt,
action protocol, sampling, and native task budgets remain unchanged.

The detector and auxiliary component must not:

- write to, clear, refresh, or reinterpret the R2 ledger;
- copy advice into ordinary history or persistent memory;
- expose evaluator/reward, hidden accessibility/UI trees, activity/package,
  database state, future frames, task/app whitelists, or known outcomes;
- override, reject, repair, or directly execute an executor action;
- terminate the episode or enlarge a native action-step limit;
- carry state across episodes.

The auxiliary output is ephemeral non-authoritative advice. It is visible in
one executor request and is then destroyed regardless of the executor result.

## 4. Detector contract

The detector is frozen as
`two_consecutive_same_family_no_rgb_progress`. For before/after RGB arrays of
equal shape, define:

```text
delta = count(max_c(abs(after[p,c] - before[p,c])) > 5) / (H * W)
```

The detector recomputes `delta` from the first three integer RGB channels and
requires the controller-recorded `changed_pixel_fraction_gt_5` to match within
`1e-12`. A transition supports the detector only when:

```text
same_shape = true
0 <= changed_pixel_fraction_gt_5 <= 0.001
```

Missing, malformed, non-finite, out-of-range, shape-invalid, or attestation-
mismatched transition evidence cannot be interpreted as no visible change.

The frozen canonical action families are:

- tap and long-press remain distinct and use integer half-up buckets
  `q(u)=min(20,max(0,floor(20*clip(u,0,1)+0.5)))`, producing
  `tap:q(x):q(y)` or `long_press:q(x):q(y)`;
- swipe uses the dominant axis and sign to produce
  `swipe:left|right|up|down`, with horizontal priority on an exact tie;
- type-text uses whitespace collapse, casefold, and full UTF-8 SHA-256; raw
  text is neither rendered nor retained as detector prose;
- `press_back`, `press_home`, `press_enter`, `press_recents`, and `wait` are
  discrete families;
- malformed, non-finite, zero-length, terminal, unknown, or unsupported actions
  do not support a trigger.

The first supported no-change transition creates one support record. A
different supported family replaces it as the new first support; a material or
unsupported transition clears it. The immediately following transition creates
the only trigger receipt if and only if it is also no-change and has the same
family. The receipt is eligible on the next executor request. After the first
trigger, pending receipt, or used auxiliary call, no second support or trigger
can be created in that episode.

The detector must be:

- deterministic, task-agnostic, app-agnostic, episode-local, and bounded;
- based only on already executed canonical actions, current/past visible RGB
  evidence or frozen RGB-derived scalars, request/action ordinals, and bounded
  controller-visible history;
- unable to inspect the evaluator, reward, task outcome, hidden UI, activity,
  package, future actions, or future screenshots;
- limited to at most one trigger per episode;
- eligible only when at least one native executor decision slot remains.

The detector formula, action families, threshold, two-support rule, one-shot
cap, next-request eligibility, and evidence hashing are immutable under this
protocol. Any semantic change requires a new protocol/system identity.

Detector-only must produce byte-identical R2 memory segments, history, and
executor prompts on every replayed step. A prompt or R2-state difference is an
implementation-integrity failure, not a model result.

### 4.1 Exact zero-generation exposure binding

The detector-development replay is bound to:

- evidence file:
  `evidence/sys_trrc/SYS_TRRC_R2_DETECTOR_REPLAY.json`;
- schema: `sys_trrc_r2_detector_replay_v1`;
- status: `PASS`;
- report `content_sha256`:
  `ed47170cdceb0ea4354ac04c3761a9ae1a5d5a03458c027aea871ce0c739c55b`;
- evidence-file SHA-256:
  `02a564601310c7c476b07553bd8ea6cd8f541abf573eeefd5996b92b1ce25777`;
- source suite: `official_qwen_20260814T145307_50081981`;
- source checkpoint-file SHA-256:
  `5c4e433f8ce1fd53e1efc56c513c20116dd8479791391bc0b163c298dcecf621`;
- 19 valid episodes and zero generation calls.

Base-versus-Detector memory, history, and prompt bytes were equivalent on all
19 episodes, with no mismatch steps. All six R2 successes had zero triggers and
there were no success-preservation exposure risks. Exactly eight R2 failures
had one trigger each:

| Task | Source step | Eligible request | Receipt ID | Evidence SHA-256 |
|---|---:|---:|---|---|
| `BrowserMultiply` | 13 | 14 | `trrc_013_99fe3b903d12` | `99fe3b903d12f2d076a727a70b0d9a569b9e955ce5a55d208752d909124a5254` |
| `ExpenseAddMultipleFromMarkor` | 13 | 14 | `trrc_013_9c5b58571078` | `9c5b585710780f6b3773e0775e426041604fa5b8ea861e472bac2c2c92813628` |
| `MarkorCreateNoteAndSms` | 12 | 13 | `trrc_012_70e4e2057e63` | `70e4e2057e6356c84848e27994ae7f1fdc6b207dd0501bb5c6ea3341eacad7e9` |
| `MarkorMergeNotes` | 12 | 13 | `trrc_012_50ba4d761341` | `50ba4d761341d59e76e710c87538f38abd5dd893fde08b63ba778a848a28d913` |
| `OsmAndTrack` | 14 | 15 | `trrc_014_4a741530f182` | `4a741530f18204f6aabadc787634df5b7eb328055800b52ee7bec73faa334257` |
| `RecipeAddMultipleRecipesFromImage` | 5 | 6 | `trrc_005_34b40e47f3e0` | `34b40e47f3e02edca8847f26358410a5944b7000be9cf09ff6ddb2acded30ca3` |
| `RecipeAddMultipleRecipesFromMarkor` | 14 | 15 | `trrc_014_ed73d71a395d` | `ed73d71a395d230273f8ca8dd33146ee4d92f17df5ae090039074a0c92c1c5dd` |
| `RecipeAddMultipleRecipesFromMarkor2` | 19 | 20 | `trrc_019_d354af31072b` | `d354af31072b4b52fab4dd17ded97ecd790d980c75f3badce28cb951ffec2006` |

The remaining five R2 failures were detector-silent:
`ExpenseAddMultipleFromGallery`, `MarkorTranscribeVideo`,
`SaveCopyOfReceiptTaskEval`, `SportsTrackerActivitiesOnDate`, and
`SportsTrackerTotalDistanceForCategoryOverInterval`.

This replay is development/calibration evidence only. It establishes detector
reachability, sparsity, cross-task exposure, Base/Detector byte equivalence,
and the frozen activation-gate choice. It is not evidence that an auxiliary
call improves behavior, not a Full-system result, and not held-out evidence.
The frozen activation task is `BrowserMultiply`, the first detector-positive
R2 failure in the remaining-13 order.

## 5. Auxiliary call and decision-slot accounting

For Generic and Full:

- maximum auxiliary calls per episode: `1`;
- maximum auxiliary retries: `0`;
- maximum auxiliary completion: `192` exact tokenizer tokens;
- maximum auxiliary input plus output: `8,192` exact tokenizer tokens;
- maximum auxiliary call latency: `60` seconds;
- unused call capacity is not filled with a dummy call.

For this multimodal request, an exact tokenizer token means one non-padding
model-input ID after the frozen Qwen `AutoProcessor` has applied the chat
template and expanded the current screenshot into visual input tokens. The
count therefore includes text tokens, chat and generation-prompt special
tokens, visual start/end tokens, and every processor-expanded image token. It
does not count the base64 transport characters as language tokens.

Immediately before the HTTP request, Generic and Full must:

1. load `AutoProcessor` from the same hash-bound model source and exact snapshot
   as the served Qwen model, with no processor or image-size override;
2. process the exact auxiliary system text, exact auxiliary user text, and the
   exact current PNG used by the request, preserving the request order of
   system text followed by user text and then the image;
3. call `apply_chat_template` with `tokenize=True`,
   `add_generation_prompt=True`, `return_dict=True`, and
   `return_tensors="pt"`;
4. set `exact_multimodal_input_tokens` to the sum of the single example's
   `attention_mask`, and require it to equal the unpadded `input_ids` sequence
   length; and
5. authorize the HTTP request only when
   `exact_multimodal_input_tokens + 192 <= 8,192`.

The completion reserve is always the frozen maximum of 192 tokens rather than
a prediction of the eventual output length. Processor loading or counting
failure, padding inconsistency, or a projected over-budget request fails closed
before network transport; the implementation must not truncate, resize,
rewrite, or otherwise repair the request.

Each attempted auxiliary request must preserve the processor/model snapshot
identity and processor-file hashes; current-PNG SHA-256 and pixel dimensions;
the exact request-messages SHA-256; `image_grid_thw`; expanded image-token
count; `exact_multimodal_input_tokens`; the 192-token reserve; projected total;
and the pre-HTTP pass/fail decision. After a response, the server-reported
`usage.prompt_tokens` must exactly equal the precomputed multimodal input count,
and the reported completion and total must remain within the 192 and 8,192
limits. A prompt-token mismatch is infrastructure-invalid and cannot be treated
as a component outcome.

This paragraph is a pre-live implementation clarification of the already
frozen 8,192-token ceiling. It changes neither the numerical threshold nor any
arm's available input, output, or compute budget, and it may not be reinterpreted
after the first live auxiliary request.

The auxiliary call occurs after a valid detector trigger and before the next
ordinary executor request. It produces no Android action and consumes no native
Android action slot. The next ordinary executor call remains the only decision
slot that may produce an action.

Every model request is nevertheless counted:

```text
combined_model_calls = executor_calls + auxiliary_calls
```

Costs must be reported separately for:

- executor prompt, completion, calls, and latency;
- auxiliary prompt, completion, calls, and latency;
- executor prompt-token increase caused by rendered advice;
- detector CPU time;
- combined calls, tokens, and wall time.

An auxiliary transport/server failure before the executor request is
infrastructure-invalid. A normal model response that is empty, unparsable,
overlong, or schema-invalid is a valid component failure: the call is charged,
no advice is injected, and the ordinary exact-R2 executor request proceeds.

## 6. Matched Generic and Full prompts

Generic and Full receive the same current screenshot, task goal, exact R2
ledger, bounded recent executed-action summaries, detector evidence, token
budget, output schema, wrapper, sampling contract, and expiry.

The common auxiliary prompt is:

```text
You are a bounded auxiliary reasoner. You do not act, terminate, edit memory,
or decide whether the task is complete.

{ROLE_INSTRUCTION}

Use only the supplied task goal, current screenshot, exact R2 ledger, bounded
recent executed-action summaries, and detector evidence. The current screenshot
is authoritative. Do not use hidden UI, evaluator information, future state,
or outside task knowledge. Return exactly three single-line fields:

ASSESSMENT: <brief visible-evidence assessment>
RECOMMENDATION: <one concise suggestion for the executor's next decision>
VISIBLE_CHECK: <what visible evidence the executor should inspect next>
```

The only role-instruction difference is:

Generic:

```text
Independently review the supplied visible evidence and provide one concise
next-decision suggestion.
```

Full:

```text
Identify the currently recurring or visibly unsupported approach and provide
one materially different, screenshot-grounded recovery strategy for the next
decision.
```

Both arms use the identical executor wrapper:

```text
AUXILIARY ADVICE (non-authoritative; expires after this request):
ASSESSMENT: {assessment}
RECOMMENDATION: {recommendation}
VISIBLE_CHECK: {visible_check}
The current screenshot is authoritative. The executor must decide the next action.
```

The exact whitespace, encoding, field bounds, parser, tokenizer projection, and
prompt hashes must be frozen before live generation. There is no free-form
fallback and no second call.

## 7. Causal opportunity and evidence chain

Each triggered opportunity must preserve the following chain:

```text
detector trigger
-> exact auxiliary request and response
-> parsed bounded advice
-> committed one-request injection
-> exact executor request and response
-> executed canonical action
-> visible screen-change audit
-> relapse audit
-> sealed final evaluator result
```

The frozen labels are:

- `ACTIVATED`: detector triggered;
- `DELIVERED`: a valid auxiliary response was committed into the executor
  request;
- `BEHAVIOR_CHANGED`: at an exact-prefix matched opportunity, the Full next
  action hash differs from Generic or Detector-only;
- `VISIBLE_CHANGE`: within the first four executed canonical actions after the
  committed injection, at least one transition has unequal RGB shape or a
  recomputed `changed_pixel_fraction_gt_5 > 0.001`;
- `QUALIFYING_RECOVERY_SUCCESS`: an operational Full-arm record with exactly
  one detector trigger, one valid auxiliary response, one committed injection,
  an executed canonical action from the immediately following ordinary
  executor request, `VISIBLE_CHANGE`, no return during that four-action window
  to any screenshot SHA-256 in the two detector-support transitions, and final
  full task success;
- `PRODUCTIVE_INTERVENTION`: a post-hoc causal record in which an exact-prefix
  matched Full opportunity is both `QUALIFYING_RECOVERY_SUCCESS` and
  `BEHAVIOR_CHANGED` relative to Generic or Detector-only.

`QUALIFYING_RECOVERY_SUCCESS` is deliberately a single-arm operational label.
It can release a run gate but cannot establish that the advice, generic extra
inference, or specialized role caused the success. `PRODUCTIVE_INTERVENTION`
is deliberately unavailable until the required exact-prefix matched contrast
has been audited.

Pixel change is always called visible screen change, never semantic progress or
completion.

An opportunity is exact-prefix matched only when source/config/model identity,
all earlier executor prompts/responses/actions/screenshots, R2 ledger state,
detector state, task state, and seed/RNG contract match through the trigger.
The Generic and Full auxiliary inputs must then differ only in the frozen role
instruction, and their executor requests may differ only in rendered advice.

If any required prefix hash differs, the comparison is
`FULL_SUCCESS_ABLATION_UNRESOLVED`. A common seed is not a substitute for
hash-level matching. A later implementation should prefer a frozen
emulator/controller/RNG checkpoint at the trigger and branch Generic and Full
from that checkpoint; if exact branching is unavailable, causal claims are
downgraded rather than guessed.

## 8. Offline and preflight gates

Before implementation freeze and live generation:

1. Materialize and hash-bind all 19 valid A1-R2 episodes plus every retained
   infrastructure-invalid attempt and its replacement.
2. Replay Base and Detector-only with zero generation calls and prove exact R2
   prompt/history/ledger equivalence. The bound replay in Section 4.1 satisfies
   this design-development gate for the current source closure.
3. Verify the exact eight-row detector manifest in Section 4.1, including each
   source step, next eligible request, receipt ID, evidence hash, six-success
   zero exposure, and five detector-silent failures. Counts alone are
   insufficient.
4. Verify `BrowserMultiply` as the immutable activation-gate task. It cannot be
   replaced by a later or apparently easier detector-positive task after live
   results are observed.
5. Project Generic and Full input/output tokens, advice-render tokens, state,
   CPU, and worst-case suite cost.
6. Test no-leakage taints, episode reset, one-call cap, no-retry behavior,
   malformed output, timeout, terminal/no-slot suppression, and advice expiry.
7. Bind four independent arm identities, configs, source freezes, preflights,
   and fresh live receipts to the same model/runtime manifest.

The implementation blueprint assigns the complete multimodal pre-request
projection, fail-closed authorization, and post-response usage attestation to
`implementation/src/raven_m/official_qwen_mobile/sys_trrc_token_budget.py`.
That module is a mandatory member of the hash-bound implementation source
closure for every SYS-TRRC source freeze, preflight, launch receipt, and live
result. Omitting it, loading a non-identical processor snapshot, or allowing an
unbound fallback counter is a source-integrity failure.

The live AndroidWorld controller remains in its frozen Windows environment.
Because that environment intentionally lacks Torch/Torchvision, Generic and
Full perform the deterministic pre-HTTP projection in an isolated local Python
subprocess using a local processor snapshot whose required file hashes exactly
match the server preflight. The remote vLLM process and model weights remain
bound by their independent receipt. The subprocess performs no generation,
receives only the exact auxiliary prompts and current PNG, returns only the
projection record, and its executable hash, processor hashes, projection time,
expanded image-token count, and result are audited. This deployment split is
an implementation boundary, not an additional reasoning component.

Any detector, prompt, schema, wrapper, budget, gate, or task-order change after
source freeze requires a new protocol identity. A valid scientific failure is
never rerun under the same identity.

## 9. Live gate sequence

### Gate L1: first-task four-arm audit

On `ExpenseDeleteMultiple2`, run each arm once in the frozen order:

1. Base
2. Detector-only
3. Generic
4. Full

All valid outcomes are retained. Full must succeed to continue. Full success
without a trigger is a valid silent preservation result and does not count as
component evidence. Control-arm failures do not authorize a Full rerun.

### Gate L2: R2-six preservation

Full and Generic then run, without repeating completed episodes, in this order:

1. `ExpenseDeleteMultiple2`
2. `RetroSavePlaylist`
3. `SimpleCalendarAddOneEvent`
4. `SportsTrackerTotalDurationForCategoryThisWeek`
5. `RecipeDeleteMultipleRecipesWithConstraint`
6. `OsmAndMarker`

Full must finish 6/6. Any valid Full failure permanently stops Full. Generic is
an active control and keeps its valid failures; its result cannot rescue or
invalidate Full's capability verdict. Base and Detector-only need not repeat
the remaining five tasks after Gate L1 if offline byte-equivalence and the
first-task integrity audit passed.

Recovery is expected to remain silent on an unproblematic success path.
Therefore activation on the first success task is not mandatory and must not be
created by widening a trigger after observing live results.

### Gate L3: operational qualifying recovery

After Full reaches 6/6, always run Base, Detector-only, Generic, and Full once
on the frozen activation task `BrowserMultiply`; a qualifying event on an
earlier preservation task never substitutes for this fixed L3 record. Its
development trigger occurred after
source step 13 and was eligible at request 14; the live detector must still
derive its trigger only from the live arm's own allowed past evidence. The
development step and receipt identity are expected audit references, not a
runtime task rule or forced trigger. The arm-specific operational records are:

- Base: presence of one valid retained episode and sealed evaluator outcome;
- Detector-only: exactly one valid detector trigger and zero auxiliary calls;
- Generic: exactly one valid detector trigger and one `DELIVERED` auxiliary
  response, without any success requirement;
- Full: one `QUALIFYING_RECOVERY_SUCCESS`.

The Base record is descriptive. Detector-only and Generic failures to meet
their operational records are retained and downgrade or prevent later matched
causal claims; they do not erase a valid Full result, authorize a rerun, or
substitute for Full's qualifying requirement. None of these four single-arm
records is by itself a `PRODUCTIVE_INTERVENTION`.

The activation-task episode counts toward the 19-task result and is never
repeated.

### Gate L4: release of the complete 19

Full may run the remaining tasks only after:

- Full is 6/6 on the R2 successes;
- L3 has one `QUALIFYING_RECOVERY_SUCCESS`;
- all integrity, leakage, source, runtime, and resource gates remain valid.

Generic proceeds through the same frozen remaining order so that Full versus
Generic remains a resource-matched component comparison. Completed gate
episodes are retained and not rerun.

If Full and Generic both succeed on the activation task, Full may continue for
system-accuracy measurement, but specialized recovery causality remains
unestablished. If no exact-prefix matched opportunity exists, Full may still
receive an accuracy verdict but not a specialized-component causal verdict.

The separation of `QUALIFYING_RECOVERY_SUCCESS` from
`PRODUCTIVE_INTERVENTION` is a pre-live disambiguation of operational gating
versus post-hoc causal attribution. It changes no arm, detector, prompt,
resource threshold, task order, or success threshold, and it cannot be revised
after the first live arm episode.

## 10. Frozen result taxonomy

Every episode and every triggered opportunity must use one of the following
labels where applicable:

- `NO_TRIGGER_SILENT_SUCCESS`
- `NO_TRIGGER_VALID_FAILURE`
- `PRESERVATION_FAILURE_PRE_TRIGGER_UNATTRIBUTED`
- `DETECTOR_TRIGGERED_AUX_TRANSPORT_INVALID`
- `AUX_OUTPUT_INVALID_VALID_FAILURE`
- `ADVICE_NOT_COMMITTED`
- `COMMITTED_NO_ACTION_DIVERGENCE`
- `DIVERGENCE_NO_VISIBLE_CHANGE`
- `VISIBLE_CHANGE_RELAPSED`
- `VISIBLE_CHANGE_NO_FULL_SUCCESS`
- `QUALIFYING_RECOVERY_SUCCESS`
- `FULL_SUCCESS_ABLATION_UNRESOLVED`
- `GENERIC_MATCHES_FULL`
- `FULL_BEATS_GENERIC_CAUSAL_SUPPORT`
- `FULL_LOSES_TO_GENERIC_SPECIALIZATION_HARM`
- `INFRASTRUCTURE_INVALID`

A silent success is not attributed to the auxiliary component. A pre-trigger
loss is a capability failure but not evidence that recovery advice caused harm.
A post-trigger Full loss is only candidate harm until an exact-prefix matched
Generic or Detector-only contrast supports attribution.

## 11. Independent verdicts

### System accuracy

Pass requires:

- at least 7/19 Full successes;
- reward greater than 6.5;
- zero Full losses among the six A1-R2 successes.

### Specialized recovery causality

Pass requires:

- Full beats Generic by at least one paired full success;
- no Full paired loss among the R2 six;
- at least two trace-grounded `PRODUCTIVE_INTERVENTION` records;
- at least one exact-prefix matched Full-versus-Generic opportunity supporting
  the success difference.

If Generic and Full tie, any gain may be attributed only to generic additional
reasoning, not to the specialized recovery role. Full losing to Generic is
evidence that specialization is harmful or overconstrained.

### Cost

Report, without substitution between metrics:

- executor calls versus A1-R2's 603;
- auxiliary and combined calls;
- executor, auxiliary, advice-induced, and combined tokens versus 2,685,730;
- detector, auxiliary, executor, and combined elapsed time versus
  11,230.182856 seconds;
- compliance with the one-call, 192-completion-token, 8,192-total-token, and
  60-second per-call envelope.

Accuracy may pass while cost or causality fails. Lower cost cannot substitute
for an accuracy gain, and extra inference cannot be hidden inside a memory
verdict.

## 12. Evidence preservation and stopping rules

Every arm must preserve arm/config/source/preflight/live-receipt hashes; model
realpath, manifest, revision, packages, PID, and command line; task and
generation seeds; all detector inputs/events; exact auxiliary and executor
request/response hashes; auxiliary schema and advice text; injection tickets;
R2 ledger/history hashes; canonical actions; RGB transition and screenshot
hashes; evaluator record; calls/tokens/time; episode/checkpoint/result hashes;
and infrastructure-invalid replacement linkage.

Only an infrastructure-invalid attempt may be replaced, at most once per task
and at most twice per arm across the suite. Source mismatch, leakage, a second
auxiliary call, a retry, action override, native-budget increase, or unreported
model computation invalidates the arm. A valid scientific failure is retained,
stops Full when required by the gate, and is never hot-fixed or rerun under the
same identity.
