# Protocol v2.2 r60 H01 Candidate Smoke — End-to-End Pass

## Decision

r60 passed the single authorized, isolated, non-scored H01/B3 development
smoke. The native evaluator returned reward `1.0`, the episode terminated
normally with `model_done`, semantic and reset audits passed, and no later cell
or formal Gate-F run started.

This success permits formal Gate-F **preparation**, not a formal launch.

## Verified execution

The setup path completed without creating any repeat ledger. The ledger first
appeared only when the real `Click Me` action executed at step 7.

The five actual target actions sampled:

| Click ordinal | Verified pre-action value |
|---:|---:|
| 1 | 6 |
| 2 | 2 |
| 3 | 3 |
| 4 | 9 |
| 5 | 10 |

After click 5, the answer form appeared. The ledger held
`complete=true`, `operands_complete=true`, and deterministic product `3240`.
The fourth/fifth bounded override totals were `1` and `2`. No sixth click was
proposed or executed.

## Direct evidence for the memory-reliability idea

At step 12, B3's periodic summary was stale: it still claimed only three
clicks had occurred and two remained. The verified ledger simultaneously
reported five executed clicks, all five operands, and product `3240`.

The model followed the ledger, not the stale summary: its initial next action
was to type `3240` with `text_origin=deterministic_calculation`, rather than
click again. This is the exact behavior the r59 failure motivated.

The existing input-safety guards then worked as intended:

1. the coordinate-bearing text action was repaired to a focus-activation tap;
2. the next clear-text action was repaired to a focus-preserving
   `clear_text=false` action with the same `3240` provenance;
3. `3240` was entered;
4. Submit executed;
5. the page displayed `Success!`;
6. the model returned `done`, and the native evaluator returned reward `1.0`.

Both validation blocks were resolved; no blocked action executed.

## Environment and boundary

The run used the exact frozen Qwen3-VL revision/backend. Accessibility needed
bounded retries and four recovery attempts, all without recovery errors.
There was no infrastructure attempt, reset error, model outage, or residual
experiment process.

The next safe step is to freeze this checkpoint and prepare a separate r60
formal Gate-F addendum, wrapper, and zero-call preflight. This development
result must never be relabelled as formal evidence, and formal Batch 1 must not
launch automatically.

## Evidence

Principal hashes:

- checkpoint/progress/summary:
  `379f46a3754fd5b2928088f4ff24edf11fefb6e9e9ffab79bd319c494e1aeeae`
- episode:
  `f4e672482da0ebec0da1e806eb4f50f27ee3eecb5a6914fd55dd7ac50f6eb977`
- events:
  `68fedd68544986c2580b410af37f8f3fa9d00798f0e2d3c4f12f98de3a1b2055`
- visible submitted success:
  `03574c2e29266f5ea557f5d57be3cbd9bf4eeb3331e7851f233f587a9619dd07`

The complete audit is in
`reports/protocol_v2_2_r60_h01_candidate_smoke.json`.

