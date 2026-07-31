# Protocol v2.2 r61 H17 Candidate Preflight

## Decision

**PASS.** The frozen r61 package may run exactly one isolated, non-scored
H17/M0 development smoke at sequence 2. This does not authorize any formal
Gate-F batch or any other development sequence.

## Verified boundary

- Source commit/tag: `baa398babf9707f32eb94d1287e5bc2d728a84bb` /
  `protocol-v2-2-r61-local-candidate`
- Preflight execution commit: `2b576eb2904bed31c96cb7a50d939bf23683b22f`
- Frozen files: **28/28**
- Frozen tasks/pairs: **6/6**, restart-stable at seed `20260730`
- Protocol-v1 breadth seal: **197/197**
- Model: `Qwen/Qwen3-VL-32B-Instruct`
- Revision: `0cfaf48183f594c314753d30a4c4974bc75f3ccb`
- Backend: `qwen3_vl_32b_transformers_bf16_4x4090_v1`
- Emulator: connected
- Fresh r61 candidate suite directory: absent
- Model calls: **0**
- GPU experiment cells: **0**
- Automatic batch or Gate-G launch: disabled

The exact JSON report is byte-frozen with SHA-256
`db36952a95f93c2a2a41e37e4c2a5e18b72066a951152e71fb2c323b93cb5b69`.

## Launch boundary

The only authorized command uses
`--development-smoke-sequence 2`. The wrapper rejects `--batch`, missing
development scope, and every other sequence. The resulting namespace must be
`runs/protocol_v2_2_development/hard_micro_v2_2_seed20260730_r61_candidate_development_smoke_sequence_2`.

After the cell terminates, its raw episode, semantic audit, reset audit, and
r61 reconciliation records must be frozen and reviewed before any further
experiment decision.
