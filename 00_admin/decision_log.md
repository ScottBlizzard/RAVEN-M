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
