# Decision log

## 2026-07-23 — Reference model deployment

- **Decision:** use the exact `Qwen/Qwen3-VL-32B-Instruct` revision
  `0cfaf48183f594c314753d30a4c4974bc75f3ccb` in BF16 across four RTX 4090s.
- **Reason:** the A40 host refused connections, while the 4090 host had four
  project-available GPUs and the exact 66,726,519,322-byte snapshot fit without
  quantization.
- **Consequence:** this is numerically higher fidelity than the planned A40
  4-bit fallback, but backend, revision, GPU visibility, dtype and context cap
  must remain fixed within every direct comparison.

## 2026-07-23 — Private split-host transport

- **Decision:** bind the model server only to `127.0.0.1:8000` and reach it from
  Windows through an SSH tunnel on `127.0.0.1:18000`.
- **Reason:** no public inference port is needed; idempotency keys and call IDs
  allow one bounded retry without duplicate generations.

## 2026-07-23 — Canonical action coordinates

- **Decision:** action v1 uses normalized screenshot coordinates in `[0, 1]`;
  the adapter logs normalized and actual pixel values and rejects out-of-range
  coordinates.
- **Reason:** this follows the Qwen mobile-agent convention and is independent
  of screenshot resolution. `open_app` is retained because AndroidWorld's
  official baseline action interface supports it and all comparison variants
  will receive the same action space.

## 2026-07-23 — Context cap reduced to 8192

- **Decision:** freeze `total_context_cap: 8192` for the first reference
  backend.
- **Evidence:** an uncalibrated multi-token padding request exceeded the
  intended shape and OOMed. After restarting with
  `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`, a 7,204-token calibration
  passed and ten consecutive 7,704-token screenshot requests completed without
  OOM. Maximum reported peak VRAM was 19,554,077,184 bytes.
- **Consequence:** no direct comparison may silently use a larger cap. A future
  12K/16K backend is a separately identified deployment experiment.

## 2026-07-23 — Dry-run failures are retained

- **Decision:** preserve the failed first B0 trajectory and both successful
  trajectories under `runs/excluded_protocol_dry_run/`.
- **Reason:** the first run exposed Markdown-fence formatting and action-budget
  failures; later runs exposed irrelevant field filling and inconsistent
  completion. They are engineering and mechanism evidence, not scored results.

## 2026-07-23 — G3 passed only after a frozen executor revision

- **Decision:** retain the failed executor-v0 five-task suite, freeze
  `executor_v1.md`, and rerun the same non-Hard task classes, seeds and budgets
  in a separate suite.
- **Evidence:** normalized v0 rates were 40/54 (74.07%) first-pass and 51/54
  (94.44%) after one repair. V1 reached 52/55 (94.55%) and 55/55 (100%),
  respectively, with zero infrastructure errors.
- **Consequence:** G3 is passed by executor v1. The 2/5 evaluator success rate
  is exploratory and exposes remaining strategy errors; it is not a Hard
  benchmark result. Scored Hard runs remain forbidden until preregistration.

## 2026-07-23 — G4 baseline-family gate passed

- **Decision:** accept B0/B1/B2/B3 as the frozen baseline interfaces after the
  non-Hard G4 suite and machine audit.
- **Evidence:** B1 completed 2/2 tasks, B2 2/2, and B3 3/5; parse validity was
  95–100% first-pass by variant and 100% after one repair, with zero
  infrastructure errors and every request inside the 8192-token cap. The two
  B3 task failures were retained.
- **Reset contract:** pair instances by task class, seed, goal hash, and
  generated-parameter hash. Nine repeated init/teardown/reset lifecycles had
  stable pairing hashes and foreground activities. Exact pixels and sampled
  accessibility trees are diagnostic only because render/a11y sampling is
  asynchronous; their observed variation is retained in the raw audits.
- **Consequence:** protocol preparation may continue. Hard scoring remains
  forbidden until G7 and the protocol-v1 preregistration hash/tag.

## 2026-07-23 — Novelty claims narrowed after 2026 refresh

- **Decision:** do not claim that training-free GUI memory, multi-role
  orchestration, state tracking, trajectory retrieval, utility pruning, or
  structured executable memory are novel.
- **Evidence:** the refreshed nearest-neighbor set includes Darwinian Memory,
  EchoTrail-GUI, CES, Executable Agentic Memory, MemGUI-Bench, and ExpAct in
  addition to HyMEM, MAGNET, UI-Copilot, D-Artemis, PG-Agent, HAR-GUI, and
  LAMO.
- **Consequence:** RAVEN-M is framed as an auditable controlled prototype:
  episode-local item provenance, explicit contradiction/stale/invalidation
  states, harmful-memory metrics, and paired context/call-budget controls.

## 2026-07-23 — Failed method-development iterations remain archived

- **Decision:** stop but retain the first two G6/G7 development suites, then
  rerun with a new suite ID after each correction.
- **V1 finding:** the executor prompt under-specified the nested action object,
  causing invalid `action_details`/`action_args` outputs.
- **V2 finding:** decision-time `state_delta` evidence was incorrectly bound to
  the post-action frame, a one-frame provenance error.
- **Correction:** every model-emitted delta is now tied to the pre-action image
  and `evidence=action_outcome` to the previous outcome actually supplied to
  that decision. Deterministic loop evidence remains tied to the post-action
  frame. Page-local deltas are written before transition invalidation, so they
  become stale immediately when the action leaves their supporting page.

## 2026-07-23 — Bound terminal output before G7

- **Finding:** v3 reached 4 S0 episodes with no invariant or stale-FACT event,
  but one otherwise correct completion response emitted too many state deltas
  and was truncated at the frozen 256-token generation limit. Its single
  repair repeated the same truncation.
- **Decision:** a continue decision may emit at most two deltas; done/fail must
  emit an empty delta array because terminal deltas have no following
  transition and are not persisted by the controller.
- **Consequence:** v3 remains archived and v4 reruns the complete unchanged
  non-Hard task/seed schedule. The model context and generation budgets are not
  increased.

## 2026-07-23 — Working-memory slots are explicitly non-citable

- **Finding:** v4 reached 4 S0 episodes with no invariant or stale-FACT event.
  One invalid decision treated an unnumbered FIFO working-memory slot as a
  persistent item and invented the citation `working_memory_0`.
- **Decision:** citations may only copy exact IDs from
  `MEMORY_CONTEXT.items[].memory_id`; FIFO working transitions are context,
  not evidence-bearing persistent items, and cannot be cited.
- **Consequence:** the repair instruction removes malformed, unavailable, or
  invented IDs and uses an empty list when no valid item remains. The complete
  non-Hard schedule is rerun as v5; v4 remains archived.

## 2026-07-23 — Role outputs require literal compact contracts

- **Finding:** v5 completed all 5 S0 and 8 M0 development episodes with zero
  infrastructure errors, no stale FACT routes, and 77/78 valid executor
  decisions after one repair. However, 24 conditional Planner/Critic events
  remained invalid after repair. The dominant Planner output used an
  unsupported outer `plan` object and frequently exhausted the frozen
  256-token limit; Critic outputs invented wrapper keys or verdict strings.
- **Decision:** retain v5 as failed development evidence and add literal,
  compact, schema-valid JSON examples plus explicit key/type/enumeration
  constraints to the Planner and Critic system prompts. The role generation
  budget remains 256 tokens and the task/seed schedule remains unchanged.
- **Consequence:** v6 must rerun the complete non-Hard schedule and pass the
  role-output audit before protocol freeze. Hard scoring remains forbidden.

## 2026-07-23 — Native success is authoritative for outcome coding

- **Finding:** a v6 development episode reached native evaluator reward 1
  after its last attempted decision failed schema repair, producing the
  contradictory pair `success=true` and
  `failure_code=MODEL_OUTPUT_INVALID_AFTER_REPAIR`.
- **Decision:** native evaluator success maps to `failure_code=null`.
  `model_output_error` and valid-after-one-repair rates remain unchanged and
  continue to expose the formatting failure.
- **Consequence:** this is a result-labeling correction only; it does not alter
  prompts, actions, memory, budgets, evaluator timing, or G7 acceptance.

## 2026-07-23 — Completion guard made explicit before G7

- **Finding:** v6 completed all five S0 episodes and three M0 episodes with
  valid Planner outputs and no memory invariant errors. Two M0 episodes then
  ended on the same executor error: the model repeated `status=done` although
  no currently routed FACT cited visible completion. This was an implicit
  controller rule but absent from the executor prompt.
- **Decision:** stop and retain the partial v6 suite. The executor must first
  use a one-second wait plus a direct-screen completion delta linked to the
  Planner requirement, then cite the resulting routed FACT on the next
  observation before emitting done.
- **Consequence:** v7 reruns the complete unchanged non-Hard task, seed, and
  budget schedule. The controller guard, 256-token limit, router, and native
  evaluator are unchanged; Hard scoring remains forbidden.

## 2026-07-23 — Planner output bounded below the 256-token limit

- **Finding:** v7 completed all five S0 and five M0 episodes with 100% executor
  validity, no memory error, and valid Critic coverage. One FilesMoveFile
  Planner refresh nevertheless expanded to three completion requirements and
  was truncated at exactly 256 tokens in both initial and repair calls.
- **Decision:** stop and retain the partial v7 suite. Planner output now uses
  exactly one combined completion requirement, at most one open requirement,
  at most four short variables, short descriptions, and a 180-token target.
- **Consequence:** v8 reruns the identical full non-Hard schedule. Generation
  and context limits are not increased; Hard scoring remains forbidden.

## 2026-07-24 — Interrupted tunnel is infrastructure, not a method result

- **Finding:** v8 completed three normal S0 episodes, then the local SSH
  forward on `127.0.0.1:18000` disappeared. Every later attempted episode
  failed before its first model response with `WinError 10061`, zero decisions,
  and `INFRA_OR_CONTROLLER`.
- **Decision:** stop and retain the partial v8 suite as infrastructure-failure
  evidence. Recreate the private tunnel, require both `/health` identity checks
  and a real screenshot inference smoke, and rerun the unchanged non-Hard
  schedule as v9.
- **Evidence:** the recovered endpoint reported the frozen model revision and
  backend, and call `19a74b8a-7088-429b-9f6d-ab19359e08b7` completed against
  screenshot SHA-256
  `c1f060f97f3c4dc370f0a9445d962296ce1b6b2541e817caffa73de5f37987b0`.
- **Consequence:** v8 is excluded from G7 acceptance. No prompt, router,
  controller, model, budget, task, or seed was changed; Hard scoring remains
  forbidden.

## 2026-07-24 — Long-run tunnel watchdog is operational only

- **Decision:** run an append-only local watchdog for the private SSH forward
  during long development and frozen pipelines.
- **Behavior:** it validates the locked model revision/backend every 15 seconds,
  immediately recreates a missing listener, and only recycles a repeatedly
  unhealthy listener when no model connection is active.
- **Boundary:** this does not retry or alter agent outputs, actions, tasks,
  evaluators, budgets, or result labels. The scored runner retains its
  preregistered maximum of three infrastructure attempts per identical task
  instance and stops after exhausted or unclassified infrastructure errors.

## 2026-07-24 — Warm emulator required before a clean G7 suite

- **Finding:** v9 retained a first-episode `INFRA_OR_CONTROLLER` after the
  native Contacts evaluator's ADB content query exceeded 10 seconds. The agent
  itself completed all ten decisions and the model tunnel remained healthy.
  One infrastructure episode among five S0 episodes necessarily exceeds the
  fixed 10% G7 infrastructure ceiling.
- **Decision:** stop and retain v9, cold-restart the emulator without a
  snapshot, and require two no-LLM AndroidWorld task initialization/state
  smokes before v10. The first smoke overlapped Android's post-boot settling;
  the repeat completed in 42.2 seconds with 116 registered tasks, a valid
  2400-by-1080 screen, and 19 UI elements.
- **Consequence:** v10 reruns the same complete non-Hard manifest. No agent,
  prompt, memory, task, seed, generation, context, evaluator, or budget
  setting changes. Hard scoring remains forbidden.

## 2026-07-24 — Transport retry waits for watchdog recovery

- **Finding:** v10 passed all five S0 episodes and two M0 episodes, then its
  third M0 episode lost the local SSH listener before decision 9. The two
  protocol-permitted identical transport attempts occurred immediately, while
  the watchdog restored the listener 36 seconds after the episode error. The
  episode was correctly retained as infrastructure-invalid, but necessarily
  breaks the fixed M0 infrastructure-rate gate.
- **Decision:** retain and exclude partial v10. Insert a 45-second recovery
  window after the first connection/timeout error and before the sole identical
  retry. Payload, call ID, idempotency key, model, prompt, images, temperature,
  and budgets remain unchanged.
- **Validation:** 66/66 tests pass, including exact payload/header reuse. A
  real fault-injection smoke stopped the forward before generation; the
  watchdog restored it and the second attempt completed in 56.218 seconds
  under call `6b5655b4-fec3-4651-97ef-7df6e0df65d8`.
- **Consequence:** v11 reruns the full unchanged non-Hard schedule. Hard
  scoring remains forbidden.

## 2026-07-24 — Role repair rebuilds instead of echoing malformed JSON

- **Finding:** v11 passed all five S0 and the first three M0 task executions
  without infrastructure or memory invariants, but the step-9 Expense Planner
  omitted the closing `]` of `completion_requirements`. The generic repair
  prompt embedded that malformed response, and the model repeated it
  byte-for-byte. G7 correctly recorded one role-output error.
- **Decision:** retain and exclude partial v11. A role repair no longer echoes
  invalid output. It supplies the validation error, requires a from-scratch
  object in the already frozen role schema, and explicitly checks balanced
  object/array delimiters; Planner repair states that its single
  `completion_requirements` object must close with `}]` before `plan_summary`.
- **Boundary:** the initial role prompt, role triggers, role schema, model,
  256-token cap, task/seed schedule, executor, memory router, and action
  budgets are unchanged. There is still exactly one bounded role repair.
- **Validation:** replaying the exact malformed v11 response as the first
  response and delegating only its repair to the locked 32B model produced a
  valid `plan.v1` object in one repair. The repair call was
  `55d4ce54-a185-43b4-94d1-50ac498d0c3a`; schema, delimiter, and allowed-memory
  checks all passed.
- **Consequence:** v12 reruns the complete non-Hard schedule. Hard scoring
  remains forbidden.
