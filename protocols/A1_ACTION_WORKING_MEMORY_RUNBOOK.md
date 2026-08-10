# A1 Action Working Memory runbook

## What is fixed

A1 uses the successful A0 official-Qwen execution path. It does not use the B2
or C0 controller. The model, model revision, vLLM runtime, one-current-image
message format, tool parser, coordinate mapping, AndroidWorld evaluator,
19 frozen Hard instances, seed `20260806`, generation seed `3407`, and native
action budgets are unchanged.

The only causal intervention is `a1_action_working_memory_v1`: the Executor
writes a bounded memory payload in Action prose and the controller injects the
most recent payloads into later requests. There are no additional model calls.

## Before GPU - run once after the source is final

From `D:\ZJU\Summer_Camp\RAVEN-M-A1`:

```powershell
python implementation\scripts\preflight_a1_working_memory.py
```

This runs no generation and no 19-task suite. It checks the frozen manifest,
the unchanged official prompt hash, targeted controller/protocol tests, and a
canary write-read-injection trace. The scored runner refuses to start if any
frozen source changes after this report.

The existing A0 emulator/action and model-weight qualification are reused
because A1 changes neither path. Repeating the C0 snapshot/reset qualification
is neither required nor allowed as an A1 prerequisite.

## Start GPU service

On the remote instance, use the same already-qualified A0 server:

```bash
nohup /root/autodl-tmp/RAVEN-M/05_project/scripts/start_official_qwen_server.sh \
  >/root/autodl-tmp/official_qwen_server.stdout.log 2>&1 &
curl http://127.0.0.1:18000/v1/models
```

Keep the existing SSH tunnel open on Windows:

```powershell
ssh -i "$env:USERPROFILE\.ssh\autodl_raven_m" -p 22252 -L 18000:127.0.0.1:18000 root@connect.westb.seetacloud.com
```

## Run the scored 19-task arm

```powershell
& implementation\scripts\run_a1_working_memory.ps1
```

H01 is both the first scored paired task and the activation gate. If it does
not log a successful memory write followed by a non-empty read, the runner
stops before H02. This avoids a separate duplicate pilot.

Every valid task is checkpointed. If infrastructure interrupts a task, keep
its suite directory and resume without rerunning earlier valid tasks:

```powershell
& implementation\scripts\run_a1_working_memory.ps1 -ResumeSuiteDir "<suite directory>"
```

Wrong model actions, parser failures, premature success, max-step exits, and
reward zero are scientific failures and are not rerun. Controller, transport,
execution, evaluator, reset, or teardown failures stop the suite and remain in
the invalid-attempt log.

## After all 19 tasks

Do not modify A1-v1. Aggregate paired A1-vs-A0 success/reward, tokens, calls,
wall time, false-success, repetition/stagnation, memory activation/compliance,
and task-level benefit/harm. Then use those results to choose the separately
preregistered A2 summary-memory mechanism; do not tune A1 and rename it A2.
