# Qwen3-VL-32B official-public Mobile Agent recipe port

This arm ports the prompt, message order, text-history convention, tool schema,
and 0--999 coordinate convention from Qwen3-VL's published
`cookbooks/mobile_agent.ipynb` at commit
`96588727e44c78b25ba03ea03b8e12f7e64fd0da`.

The execution extractor follows the notebook's operative boundary: it validates
and executes the single JSON object inside `<tool_call>...</tool_call>`.  The
prompt still requests one-line Thought and Action prose, but prose formatting
alone is not allowed to discard an otherwise valid official tool call.  Tool
name, action schema, arguments and coordinate range remain fail-closed; multiple
tool calls are rejected as ambiguous.  This behavior supersedes the earlier
local adapter that incorrectly made prose-line shape part of action validity.

The stock vLLM runtime and Qwen's published Instruct evaluation generation
settings are used: temperature 0.7, top-p 0.8, top-k 20, presence penalty 1.5,
repetition penalty 1.0, seed 3407, and maximum output length 32768.
The vLLM context cap is 65536 so the prompt and the published maximum output
length can coexist; only one generation is admitted at a time.

It is **not** a reproduction of the notebook model or the unreleased internal
AndroidWorld harness: the notebook example uses
`qwen3vl-235A22-instruct`, while this experiment deliberately keeps the frozen
common backbone `Qwen/Qwen3-VL-32B-Instruct` at revision
`0cfaf48183f594c314753d30a4c4974bc75f3ccb`.
The local ModelScope mirror is frozen by a complete SHA-256 manifest; shard 13
also matches the SHA-256 published for that file in the official Hugging Face
revision.  The zero-generation preflight checks both anchors before any run.

## Remote server

The one-time dependency install is:

```bash
/root/autodl-tmp/RAVEN-M/05_project/scripts/bootstrap_official_qwen_server.sh
```

After the GPU instance starts:

```bash
nohup /root/autodl-tmp/RAVEN-M/05_project/scripts/start_official_qwen_server.sh \
  >/root/autodl-tmp/official_qwen_server.stdout.log 2>&1 &
curl http://127.0.0.1:18000/v1/models
```

The service binds only to remote localhost.  From Windows, keep this tunnel
open in a separate terminal:

```powershell
ssh -i "$env:USERPROFILE\.ssh\autodl_raven_m" -p 22252 -L 18000:127.0.0.1:18000 root@connect.westb.seetacloud.com
```

## Local AndroidWorld runner

The guarded one-command H01 path (it refuses to run if no GPU is attached) is:

```powershell
& 05_project/scripts/run_official_qwen_h01.ps1
```

The equivalent manual commands are retained below for diagnosis.

First run a single, non-scored connectivity/task smoke:

```powershell
& 06_local_runtime/envs/androidworld/Scripts/python.exe 05_project/scripts/run_official_qwen_mobile.py --url http://127.0.0.1:18000 --adb-path 06_local_runtime/android/sdk/platform-tools/adb.exe --task ContactsAddContact --seed 20260723 --max-steps 8
```

Only after that run is valid, run the frozen one-task H01 Hard pulse:

```powershell
& 06_local_runtime/envs/androidworld/Scripts/python.exe 05_project/scripts/run_official_qwen_mobile.py --url http://127.0.0.1:18000 --adb-path 06_local_runtime/android/sdk/platform-tools/adb.exe --manifest 05_project/configs/task_manifests/hard_pulse_v0_3/H01.json
```

The model sees the current screenshot and official text action summaries only.
There is no RAVEN-M planner, memory, critic, guard, output-repair call, or hidden
evaluator feedback.  A model `terminate(success)` call is merely logged as a
claim; only AndroidWorld's `task.is_successful(env)` sets `success=true`.
