# First 72-hour execution report

Generated: 2026-07-23
Protocol status: infrastructure/dev only; no Hard result is scored or permitted.

## Outcome

The fatal infrastructure path is now closed:

```text
AndroidWorld/API33 on Windows
  -> current PNG + task-only B0 prompt
  -> SSH-tunneled private Qwen3-VL service
  -> strict action.v1 validation / one bounded repair
  -> deterministic AndroidWorld action adapter
  -> before/after screenshot logging
  -> official evaluator
  -> teardown and reset
```

The exact Qwen checkpoint produced real Android actions, and two complete
`ContactsAddContact` dry runs received official evaluator reward `1.0`.

## Frozen environment evidence

| Item | Measured value |
|---|---|
| AndroidWorld tasks registered | 116 |
| AVD | `AndroidWorldAvd`, API 33, Pixel 6 |
| Model | `Qwen/Qwen3-VL-32B-Instruct` |
| Revision | `0cfaf48183f594c314753d30a4c4974bc75f3ccb` |
| Snapshot bytes | 66,726,519,322 |
| Backend | `qwen3_vl_32b_transformers_bf16_4x4090_v1` |
| GPUs | four RTX 4090s, 22 GiB placement cap each |
| Transport | private SSH tunnel; no public model port |
| Frozen context cap | 8,192 total tokens |
| Maximum output | 256 tokens |

The first real model smoke used an authentic AndroidWorld screenshot, returned
`open_app(Contacts)`, took 5.305 seconds, and reported peak VRAM
18,254,616,576 bytes.

## Action contract and controller

Implemented artifacts:

- `05_project/schemas/action.v1.schema.json`
- `05_project/prompts/executor_v0.md`
- strict parser with first-pass/extraction/repair accounting
- hashed and idempotent model client
- normalized-coordinate AndroidWorld adapter
- B0 observe-call-parse-execute-observe controller
- immutable JSONL events, screenshots, evaluator result and HTML replay
- deterministic golden-step fixture

B0 never receives evaluator state, package/activity metadata, hidden task state
or memory. The evaluator is called only after the episode ends.

## Real dry runs

| Episode | Outcome | Decisions | Calls | First-pass JSON | Repair-complete JSON | Note |
|---|---:|---:|---:|---:|---:|---|
| `b0_ContactsAddContact_20260723T142944_324921de` | 0.0 | 8 | 9 | 0% | 100% | retained failure; Markdown fences and step budget exhausted |
| `b0_ContactsAddContact_20260723T144049_6e121ef0` | **1.0** | 10 | 12 | 80% | 100% | model visibly confirmed save and terminated |
| `b0_ContactsAddContact_20260723T145005_77952eef` | **1.0** | 10 | 11 | **90%** | 100% | evaluator passed; model did not terminate before budget |

All three runs performed normal initialization, model-driven actions, official
evaluation, teardown and post-episode reset. Raw trajectories remain excluded
from Git and excluded from all scored results.

## Maximum-shape gate

An initial padding fixture used a token that split into multiple tokenizer
tokens and caused an over-cap OOM. This is retained as a calibration failure,
not misreported as a valid 16K test. The server was restarted to clear allocator
state and then tested with server-reported token counts:

- one 7,204-token multimodal calibration: passed;
- ten consecutive 7,704-token multimodal requests: **10/10 passed**;
- mean latency: 10.003 seconds;
- maximum latency: 10.425 seconds;
- maximum reported peak VRAM: 19,554,077,184 bytes;
- every response passed action schema parsing.

The reference context cap is therefore frozen at 8,192.

## Known issues retained for the next gate

1. G3 still requires at least 50 development decisions. The current best
   10-decision run reaches the 90% first-pass threshold but is only provisional.
2. B0 twice typed an invented `TechCorp` value into an unrequested Company
   field despite explicit instructions. This is a real instruction-following
   failure and a useful future error-analysis case.
3. One successful run continued into the edit screen instead of declaring
   completion. This is direct motivation for completion verification, but the
   RAVEN-M Critic must not be implemented until baseline/dev gates pass.
4. AndroidWorld emits recoverable Contacts snapshot and first-launch ADB timeout
   warnings. Episodes still initialize, evaluate, tear down and reset; these
   warnings must be monitored across the five-task dev block.

## Next gate

Run five non-Hard B0 development episodes spanning at least 50 decisions, report
first-pass and repaired JSON rates, invalid infrastructure rate, p50/p90
latency, resets and evaluator completion. Then implement B1/B2/B3 and freeze the
19-task protocol. Do not start scored Hard runs or memory implementation yet.
