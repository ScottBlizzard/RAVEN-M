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
