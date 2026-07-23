# Frozen failure and invalid-run codebook

This codebook applies to protocol v1 and is frozen before any scored Hard
episode. AndroidWorld evaluator output is never visible to an agent.

## Infrastructure-invalid codes

Only these codes permit rerunning the same seed, at most twice:

| Code | Definition |
|---|---|
| `INFRA_EMULATOR_LOST` | Emulator crashed, ADB device disappeared, or reset could not complete. |
| `INFRA_MODEL_UNAVAILABLE` | Model endpoint failed after two identical transport retries and no action was produced. |
| `INFRA_ASSET_CORRUPT` | Required app/asset installation is damaged and manual reproduction confirms it was not caused by the agent. |
| `INFRA_EVALUATOR_EXCEPTION` | Evaluator raised a code exception instead of returning failure. |
| `INFRA_HOST_RESOURCE` | Host OOM or full disk prevented action execution or artifact persistence. |

Every invalid attempt remains archived. A replacement uses the identical
variant, task instance, payload hashes, and seed.

## Agent failures

These outcomes are never excluded:

| Code | Definition |
|---|---|
| `MODEL_OUTPUT_INVALID_AFTER_REPAIR` | Action remains schema-invalid after one bounded repair. |
| `TASK_UNSUCCESSFUL_AT_BUDGET` | Native environment-step budget is exhausted with evaluator reward 0. |
| `PREMATURE_COMPLETION` | Agent proposes done but evaluator returns 0. |
| `MODEL_DECLARED_INFEASIBLE` | Agent proposes fail before budget exhaustion. |
| `MODEL_CALL_BUDGET_EXHAUSTED` | The frozen per-variant model-call cap is reached before task completion. |
| `GROUNDING_ERROR` | Action targets the wrong visible control or location. |
| `WRONG_VALUE` | Typed, selected, or retained task value is incorrect. |
| `OMITTED_REQUIRED_FIELD` | Required task value or operation is missing. |
| `LOOP_NO_PROGRESS` | Repeated transition meets the frozen loop definition without progress. |
| `STALE_MEMORY_USE` | An incompatible or invalidated memory item materially informs an action. |
| `MEMORY_INDUCED_ERROR` | The routed memory changes a paired decision from correct/neutral to harmful. |
| `RECOVERY_FAILED` | Frozen recovery cap is exhausted without returning to a progress state. |

Manual mechanism labels are secondary annotations and never change the binary
AndroidWorld success label or episode denominator.
