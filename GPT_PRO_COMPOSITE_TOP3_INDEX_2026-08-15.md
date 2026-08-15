# GPT Pro Composite Top-3 Index

The first request drafts were intentionally preserved but are superseded for
new conversations by the forthcoming `OPEN_V2` requests. The v2 requests use
the same three problem families while allowing Pro to reject or replace the
investigator's initial mechanism hypothesis.

## Open V2 requests — use these

All three outputs must satisfy
`evidence/composite/TOP3_IMPLEMENTATION_READY_OUTPUT_CONTRACT_2026-08-15.md`.

| Problem family | Request | Required output |
|---|---|---|
| Recovery after recognized failure | `GPT_PRO_OPEN_V2_RECOVERY_AFTER_FAILURE_REQUEST_2026-08-15.md` | `GPT_PRO_OPEN_V2_RECOVERY_AFTER_FAILURE_DESIGN_2026-08-15.md` |
| Long-horizon decomposition/coordination | `GPT_PRO_OPEN_V2_LONG_HORIZON_COORDINATION_REQUEST_2026-08-15.md` | `GPT_PRO_OPEN_V2_LONG_HORIZON_COORDINATION_DESIGN_2026-08-15.md` |
| Action-outcome/completion judgment | `GPT_PRO_OPEN_V2_OUTCOME_JUDGMENT_REQUEST_2026-08-15.md` | `GPT_PRO_OPEN_V2_OUTCOME_JUDGMENT_DESIGN_2026-08-15.md` |

Use three fresh GPT Pro conversations, one per request. Do not merge their contexts or ask one Pro to solve multiple tracks.

Frozen evidence commit for all three: `9f9a611728826ada1daf809dccd7613de39660ac`.

| Priority | Track | Request | Required output |
|---:|---|---|---|
| 1 | SYS-TRC-R2 | `GPT_PRO_SYS_TRC_R2_DESIGN_REQUEST_2026-08-15.md` | `GPT_PRO_SYS_TRC_R2_TRIGGERED_RECOVERY_CRITIC_DESIGN_2026-08-15.md` |
| 2 | SYS-HMP-R2 | `GPT_PRO_SYS_HMP_R2_DESIGN_REQUEST_2026-08-15.md` | `GPT_PRO_SYS_HMP_R2_HIERARCHICAL_MILESTONE_PLANNER_DESIGN_2026-08-15.md` |
| 3 | SYS-VOV-R2 | `GPT_PRO_SYS_VOV_R2_DESIGN_REQUEST_2026-08-15.md` | `GPT_PRO_SYS_VOV_R2_SPARSE_VISIBLE_OUTCOME_VERIFIER_DESIGN_2026-08-15.md` |

All are unreviewed design tracks, not A-series arms and not live-authorized. After receiving the three outputs, audit them independently and select only proposals that pass evidence, leakage, feasibility, cost, and attribution review. Do not combine components without a later factorial preregistration.
