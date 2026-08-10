# A6/A7/A8 minimal integration plan

The isolated implementation was merged only after A5 terminated. A6/A7/A8 are
new experiment IDs; no A3/A4/A5 result may be overwritten or relabelled.

## 1. Integrated files

The following files are now part of the frozen A678 source closure:

- `implementation/src/raven_m/official_qwen_mobile/a678_memory.py`
- `implementation/src/raven_m/official_qwen_mobile/a678_contract.py`
- `implementation/configs/a6_short_episodic_hard_seed20260806.json`
- `implementation/configs/a7_goal_item_ledger_hard_seed20260806.json`
- `implementation/configs/a8_exact_revisit_cache_hard_seed20260806.json`
- `implementation/scripts/preflight_a678.py`
- `implementation/scripts/qualify_a678_live_server.py`
- `implementation/scripts/run_a678_arm.py`
- `implementation/tests/official_qwen_mobile/test_a678_memory.py`
- `implementation/tests/official_qwen_mobile/test_a678_contract.py`

The staging directory is not used at execution time.

## 2. Controller and protocol

No controller or protocol change is required.

The current controller already calls:

```python
rendered_memory, memory_read = working_memory.read(
    context={"before": before, "goal": effective_goal}
)
...
working_memory.observe_step(
    source_step=step_index,
    action_summary=decision.action_summary,
    canonical_action=canonical_action,
    transition=transition,
    before=before,
    after=after,
    source_call_id=call.call_id,
    source_response_sha256=call.response_sha256,
    source_screenshot_sha256=str(before["screenshot_sha256"]),
)
```

All new classes implement exactly these methods and deliberately do not
implement `history_summary`.  Therefore the official action prose is committed
to history unchanged.  Every new arm must pass `OFFICIAL_SYSTEM_PROMPT`; do not
add an A6/A7/A8 system-prompt suffix and do not require a response prefix.

## 3. Minimal runner changes

Apply the following only after taking a clean snapshot of the completed A5
suite and committing the frozen A345 tree.

1. Import the three memory classes and the A678 contract constants/helpers.
2. Add mutually exclusive `--a678-arm {a6,a7,a8}` and a separate
   `--a678-preflight-report`.  Reject use with A1/A2/A345 or any diagnostic,
   step cap, alternate observation backend, alternate manifest, sampling drift,
   or transport retry.
3. Include `bool(args.a678_arm)` in `scored_memory_arm` so resume/checkpoint and
   infrastructure validity remain enforced.
4. Filter the frozen manifest to seed `20260806`, require 19 unique instances,
   and retain their original manifest order.  Do **not** move the four A0
   successes to the front and do not reuse `A345_GATE_TASKS`.
5. Bind in `run_signature.json`: arm, exact config SHA256, A678 preflight SHA256,
   model ID/revision/weights/launcher receipt, generation settings, ordered
   task/seed/params/goal/budget closure, official prompt SHA256, mechanism ID,
   capacities, and zero retry policy.
6. Instantiate one fresh memory object per episode:

   ```python
   ShortTransitionEpisodicBuffer(capacity=2, max_chars=240)       # a6
   GoalItemStatusLedger(max_items=6, max_item_chars=48, max_chars=320)  # a7; first request empty
   ExactVisualRevisitActionOutcomeCache(max_entries=12, max_matches=2, max_chars=260)  # a8
   ```

7. Use `OFFICIAL_SYSTEM_PROMPT` for all three.  Leave action parser, history
   policy, evaluator, reset, native action budget, screenshot input, and one
   call per step unchanged.
8. Do not execute `_a345_activation_valid`, the A345 first-task stop, or the
   A345 five-task reward gate for A678.  Conditional inactivity is valid for
   A7/A8.  A reward failure is a scientific outcome and must not stop the run.
9. Infrastructure-invalid episodes remain checkpointed and may resume only the
   same task.  Scientific task failures may not be rerun.
10. Before aggregate, call `exact_completion_errors(...)`.  Write an aggregate
    only for exactly 19 ordered unique valid task/seed pairs, evaluator present,
    one transport attempt per model call, no unresolved invalid attempt, and no
    lifecycle error.
11. Add `preservation_report(summaries)` to the aggregate.  The four known A0
    successes are a nonblocking paired diagnostic, never a continuation gate.
12. Store each step's rendered memory and hash in the actual request evidence,
    plus automatic write provenance.  Report writes, nonempty reads, tokens,
    actions, elapsed time, and per-task exposure.  Exposure is not causal proof.

## 4. Required source closure

Use the new A678 closure instead of editing the historical A345 report. It
must contain the new modules/configs/tests/preflight, the final runner,
controller, protocol, VLLM client, environment adapter, task-instance loader,
Hard manifest, preregistration, runbook, and this integration rationale.  Bind
the final live launcher receipt to the post-merge A678 preflight digest.

## 5. P0 gates before GPU generation

- Staged unit tests and final-repository unit tests pass with zero generation.
- Official system prompt hash remains
  `9d060af15f62acb31b9fb197649ec001d4096491d7fb102de929316944b3e26d`.
- A6/A7/A8 response-prefix requirement is false; controller does all writes.
- A7 can only claim `pending` or `attempted`; it never claims completion.
- A8 fingerprint is exact cropped-pixel SHA256 and has no near-match path.
- No memory accepts evaluator, UI tree, activity/package, guard output, or
  action-repair input.
- Full original-order 19-task closure is enforced; reward fail-fast is absent.
- Source freeze, launch receipt, device/APK identity, model weights, server
  command, runtime versions, port, and served model ID are mutually bound.

## 6. Recommended execution order

Run A6 first, then A7, then A8.  Each arm is a separate frozen suite.  Stop
only for infrastructure/source/signature invalidity, not task reward.  If a
mechanism is changed after seeing results, assign a new version and rerun all
19; do not patch a partial suite in place.

## 7. Qualification and local launch commands

On the remote vLLM host, create the live receipt only after the zero-generation
preflight has passed and the launch intent describes the actually running PID:

```bash
python implementation/scripts/qualify_a678_live_server.py \
  --launch-intent /path/to/A678_SERVER_LAUNCH_INTENT.json \
  --preflight evidence/a678/A678_ZERO_GENERATION_PREFLIGHT.json \
  --output evidence/a678/A678_LIVE_SERVER_RECEIPT.json
```

The local wrapper always invokes
`06_local_runtime/envs/androidworld/Scripts/python.exe`; it does not inherit an
arbitrary caller interpreter. First inspect the exact dry-run command, then add
`--execute` only after the live receipt has been copied locally and validated:

```powershell
python implementation/scripts/run_a678_arm.py --arm a6 --adb-path adb `
  --launch-receipt evidence/a678/A678_LIVE_SERVER_RECEIPT.json
```
