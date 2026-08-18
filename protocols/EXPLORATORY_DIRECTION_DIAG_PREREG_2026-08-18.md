# Exploratory Direction Diagnostics: C0/P1/P2/P3 over frozen A1-R2

Status: **SUPERSEDED_DRAFT_NO_LIVE**. No model generation used this draft.

This shared-four-arm architecture was retired before runner integration after
the research program was corrected to two sequential stages: first an
evidence-driven R15-success-derived system, then three independently repaired
Pro systems.  The draft is preserved verbatim as design provenance and must
not authorize a preflight, receipt, or live run.

Parent evidence commit: `46d9248fdc96721862ba4d919381846d250d960c`.
Parent behavior: `a1r2_compact_verified_pending_v1`.
Task seed: `20260806`. Generation seed: `3407`.
Model: Qwen3-VL-32B-Instruct revision
`0cfaf48183f594c314753d30a4c4974bc75f3ccb`.

This registration reopens the candidate pipeline after the confirmatory
qualification audits at commit `46d9248`. Those audits remain immutable and
correct for their stated claim. The new systems are explicitly lower-evidence
**exploratory mechanism-feasibility diagnostics**. They do not claim to satisfy
the original Pro documents' confirmatory GO gates.

## Two separate gates

### Protocol-validity G0 (live blocking)

Each arm must have a unique identity, exact config/prompt/source freeze,
zero-generation replay, tests, fresh receipt, fixed task order and bounded
resources. Runtime inputs are allowlisted and exclude reward/evaluator,
future frames, hidden UI/accessibility, activity/package, task-name branches,
known answers, and cross-episode donor state. No live hot-fix is permitted.

### Confirmatory qualification (claim limiting, not live blocking)

Historical success activation, missing blinded semantic labels, unproven
trigger precision, regression risk, and the Pro documents' original offline
GO/NO-GO affect only evidence level. They are disclosed in every result and do
not block a protocol-valid exploratory seven-task run.

## Common fixed non-fail-fast seven

1. `BrowserMultiply`
2. `ExpenseDeleteMultiple2`
3. `RetroSavePlaylist`
4. `SimpleCalendarAddOneEvent`
5. `SportsTrackerTotalDurationForCategoryThisWeek`
6. `RecipeDeleteMultipleRecipesWithConstraint`
7. `OsmAndMarker`

All seven valid episodes are retained and run even after any scientific
failure. Only exact 7/7 releases the remaining twelve official tasks in their
frozen manifest order; the seven are not repeated. These tasks and seed are
already observed and are not held out.

Only infrastructure-invalid episodes may be replaced, with the invalid raw
artifact retained. Transport retry is disabled. Every valid model call must
have exactly one transport attempt.

## Common minimal auxiliary envelope

All four systems retain byte/semantics-frozen R2 and differ primarily in when
they ask and what bounded question they ask.  Each permits at most one
additional call to the same frozen Qwen snapshot per episode, with no retry,
192 completion tokens, a 60-second transport deadline, and exact multimodal
input plus reserved completion not exceeding 8192 tokens.  The native action
budget is unchanged.  The auxiliary output is advisory text only: it cannot
execute, override, or terminate.  All auxiliary calls/tokens/latency are
separately charged.  No auxiliary text is stored in ordinary history or R2;
it is delivered on exactly one subsequent normal request and then expires.

## C0-DIAG: one-shot late evidence consolidation

- System ID: `diag_c0_late_evidence_consolidation_r2_v1`
- Experiment ID: `C0_DIAG_LEC_R2_QWEN3VL32B_S20260806_G3407_V1`
- After executed actions reach 40% of the native budget, wait for the first
  proposed task-independent result-bearing action family (`type_text` or
  `answer`).  Before executing that proposal, defer it once and ask for
  `FACTS / CHECK / RECOMMENDATION` grounded only in goal, current screenshot,
  model-authored history, current R2 ledger and the deferred action family.
  If no such proposal appears, the first normal request after 75% is a
  task-independent fallback.  The exact action text is never used by the
  trigger.  The original proposal is not silently executed; the executor
  chooses anew after the one-request advisory.
- The accountant must consolidate exact task-relevant facts already present,
  flag missing observations or unsupported derivations/constraints, and state
  what evidence should support the next result-bearing action.  It receives no
  task/app identity, hidden UI, evaluator, reward, future frame, known number
  sequence or answer.  It is not an R13--R15 parser extension.
- This is a new prospective hypothesis motivated by R15.  The historical R15
  success remains `TARGET_SUCCESS_WITHOUT_MATURE_EVR_READ_UNATTRIBUTED`; the
  previous NO-GO excludes silent-EVR causal claims, not this new identity.

## P1-DIAG: minimal one-shot recovery critic

- System ID: `diag_p1_tcra_r2_full_v1`
- Experiment ID: `P1_DIAG_TCRA_R2_FULL_QWEN3VL32B_S20260806_G3407_V1`
- Mechanism: frozen R2 plus the already implemented task-independent detector
  requiring two consecutive executions of the same canonical action family,
  each producing no detectable RGB change (`changed_pixel_fraction_gt_5 <=
  0.001`), with at least one native decision remaining.
- At the following request a one-shot recovery critic explains why the current
  approach may be failing, recommends one visibly grounded route different
  from the repeated approach, and names a visible check.  The short advisory
  is injected into that normal request; the executor remains the only action
  chooser.  There is no candidate arbitration or action override.
- Historical success activation and the heavier Pro TCRA qualification remain
  disclosed risk evidence, not runtime dependencies or live blockers.

## P2-DIAG: SYS-SCOPE-R2 Full exploratory

- System ID: `diag_p2_scope_r2_full_v1`
- Experiment ID: `P2_DIAG_SCOPE_R2_FULL_QWEN3VL32B_S20260806_G3407_V1`
- Mechanism: frozen R2 plus one Phase Coordinator call on the first normal
  request after executed actions reach `ceil(native_max_steps/2)`.
- The trigger reads only executed-action count, native max, and used/not-used.
- The Coordinator receives goal, the same current screenshot, current R2
  ledger and at most eight model-authored history items.  It returns exactly
  `CONFIRMED / OPEN / NEXT_PHASE` as a short PhaseEnvelope.
- The envelope is injected into exactly the next normal request and expires;
  there is no persistent FSM, update or replan.  It cannot emit coordinates,
  completion verdicts or terminal decisions.  Current screenshot remains
  authoritative; executor action/parser/native budget are unchanged.

## P3-DIAG: R2-SCER Full exploratory

- System ID: `diag_p3_scer_r2_full_v1`
- Experiment ID: `P3_DIAG_SCER_R2_FULL_QWEN3VL32B_S20260806_G3407_V1`
- Mechanism: frozen R2 plus one task-independent completion-evidence check.
  When the executor first proposes `answer` or `terminate(success)`, at least
  one native decision remains, and the slot is unused, the controller defers
  that terminal proposal without executing it and queues one visible-only
  outcome critic call on the next request.
- The critic sees only goal, current screenshot, current R2 ledger,
  model-authored history and the deferred proposal. It returns exactly
  `SUPPORTED / UNCONFIRMED / VERIFY_NEXT`. Its max-450-character advisory is
  injected into the reconsideration request and then expires. A later terminal
  proposal is accepted. Invalid auxiliary output fails open.
- This bounded veto plus one ordinary reconsideration is part of the treatment
  and is fully charged; it does not read reward/evaluator, directly declare
  success, execute an action, or increase the native decision budget.

## Evidence and interpretation

Each task must record opportunity, activation, auxiliary call, exact
injection/use, first comparable divergence or non-comparability, local visible
change, relapse, reward, calls/actions/tokens/wall time and attribution class.

Allowed classes include `QUALIFYING_COMPONENT_SUCCESS`,
`SUCCESS_WITH_COMPONENT_SILENT_OR_UNUSED`, `ACTIVATED_NO_GAIN`, `REGRESSION`,
`NO_OPPORTUNITY`, and `INFRA_INVALID`. Component-silent success has zero causal
credit. Without resource-matched live controls, task reward is system-level
exploratory evidence only, not specialist-component causality.

Any prompt, trigger, threshold, state, renderer, task order or budget change
after the first DIAG model generation requires a new identity. P2/P3 may not be
retuned from P1 live outcomes; all three identities are frozen by this file.
