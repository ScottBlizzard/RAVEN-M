# A10-v2 / A11 prospective dual-arm namespace binding

Status: prospective, zero-generation only until each arm independently passes
its own replay and preflight.

Parent evidence commit:
`4548b932bc3b189507e1442e312c73c8f35dbdb8`.

## Isolation

| Field | A10-v2 | A11 |
|---|---|---|
| arm | `a10v2` | `a11` |
| CLI | `--a10-v2-emobf` | `--a11-crc-ecobf` |
| mechanism | `a10_v2_evidence_matured_obligation_branch_frontier_v2` | `a11_confirmed_route_contraction_ecobf_v1` |
| experiment | `A10_V2_EMOBF_QWEN3VL32B_AW_HARD_S20260806_G3407_V1` | `A11_CRC_ECOBF_QWEN3VL32B_AW_HARD_T20260806_G3407_V1` |
| result key | `a10v2_result` | `a11_result` |
| evidence root | `evidence/a10_v2/` | `evidence/a11/` |
| checkpoint schema | `a10_v2_emobf_checkpoint_v1` | `a11_crc_ecobf_checkpoint_v1` |

The two CLI flags are mutually exclusive. A memory instance is fresh for every
episode. A preflight, receipt, checkpoint, suite, episode, or result from one
arm is invalid for the other. Historical A10-v1 artifacts stay byte-for-byte
immutable and reproducible at commit `4548b932...`; this new source tree does
not re-sign them.

## Shared live ordering and transport boundary

Both arms run the frozen four preservation tasks first and unlock the remaining
15 only after reward 4/4. A scientific reward failure is terminal and cannot be
resumed. An infrastructure-invalid episode may be replaced only by the same
task with reciprocal episode identifiers. Every valid step has exactly one
transport attempt, zero retry, zero extra model call, no guard, no action
override, and no forced termination.

## Artifact cycle

Source-freeze manifests contain design, binding, implementation, configuration,
runner/controller integration, exact test manifests, and immutable historical
inputs. Generated replay reports, preflight reports, launch intents, live
receipts, checkpoints, and results are excluded from their own source closure;
each generated artifact instead records the source commit and source-freeze
hash that produced it.
