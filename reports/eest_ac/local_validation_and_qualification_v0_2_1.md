# EEST-AC v0.2.1 Validation, Runtime, and Integrity Record

## Offline gates

- v0.2 replay: 18/18 classified; confusion = 18 original invalid, 8 safe normalize, 10 must repair, 0 canonical direct, 9 identical invalid-action repairs.
- Generated contract artifacts: exact.
- Prompt/schema/adapter action conformance: 10/10.
- Maximum Qwen serialization: 200 tokens < 256.
- EEST focused suite: 59 passed, 0 failed.
- Full regression: 1,059 passed, 1 expected legacy frozen-manifest conflict.
- Source isolation: no forbidden imports or task/App/coordinate guard literals; M-RISK online false.

## Final zero-call runtime preflight

- Status: pass.
- Generation calls: 0.
- Model/revision/backend: exact frozen match.
- Emulator observation: 2400×1080 RGB, a11y available.
- Run root before qualification: empty.
- Preflight SHA-256: `a6c0a82b67bb1a9dd894a51782d84007196b647529d5d13d59c684a7460c39da`.

## Qualification execution

- Started with lock commit `564426f` and candidate source `1722430f7674247fb41a4f297ccc2792f1c1863a`.
- Executed 1/3 cells; stopped at the first preregistered hard failure.
- Stop reason: `hard_failure_after_Q-SWIPE`.
- Model calls: 2; task actions executed: 0; final reset: pass.
- No code/config change occurred after first generation.
- No efficacy batch was started.

## Lock and legacy integrity

Qualification lock at end: 22 checked, 0 mismatches.

| Protected legacy WIP | Start hash | End hash | Verdict |
|---|---|---|---|
| `05_project/src/raven_m/controller/episode_controller.py` | `fc0e82e0fde90119365d4f685f080eb4519bf2f602e4bda58de5d4809a40fe33` | same | preserved |
| `05_project/src/raven_m/controller/protocol_v2_guard.py` | `ff89d6b70be4b4738646d262beb67d7b7e932e9eb95956d940b1c5000a999d10` | same | preserved |
| `05_project/tests/scripts/test_protocol_v2_2_r79_r78_trace_replay.py` | `5bb1f1e3de673a1072cfee62938b761a62fd69c187d5eadf54bc46b115a3fd0a` | same | preserved |

No qualification/preflight Python process remained after the early stop. These three legacy files remain the only pre-existing dirty/untracked paths and must not be included in the qualification analysis commit.
