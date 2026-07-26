# Protocol-v2 Gate E rerun 1 infrastructure failure

Date: 2026-07-26  
Suite: `nonhard_capability_seed20260729_rerun1`  
Frozen tag: `protocol-v2-gate-e-rerun1-freeze`  
Valid scored cells: 0 of 8  
Decision: infrastructure-invalid; preserve the run; restart all cells

The runner stopped after two consecutive `INFRA_MODEL_UNAVAILABLE` attempts
on the first scheduled B3 `ContactsAddContact` cell. The first attempt lost
the local model forward while requesting the one permitted format repair; the
second attempt received a connection reset. The suite summary contains no
scored result (`result_count=0`), so no semantic outcome from this run is
carried into the next attempt.

The root cause was the local SSH-tunnel watchdog. The 32B Transformers server
performs one long synchronous generation at a time, so `/health` can time out
while a legitimate generation is in progress. The watchdog treated repeated
health timeouts as grounds to restart an otherwise listening tunnel. Its log
records such a restart at `2026-07-26T23:20:11+08:00`, during the Gate E
request, and another recovery restart at `23:24:08+08:00`.

The watchdog policy was corrected at the transport layer only:

- a listening SSH forward is no longer restarted because `/health` is slow;
- OpenSSH keepalives remain enabled and terminate a genuinely disconnected
  tunnel;
- the watchdog rebuilds the tunnel when the local listener disappears.

This change does not modify the model, prompts, action schemas, task
instances, schedule, seeds, step budgets, evaluator, or acceptance criteria.

Validation after the correction:

- PowerShell parser: pass;
- model health identity: exact expected revision and backend;
- real screenshot generation: pass, call
  `034a9b26-cb0a-4e60-979e-82140969f91d`;
- four watchdog health timeouts occurred during that generation;
- SSH tunnel PID remained `34456` throughout;
- health recovered automatically after generation, without a tunnel restart.

Gate E therefore restarts from all eight cells in the new immutable output
directory `nonhard_capability_seed20260729_rerun2`.
