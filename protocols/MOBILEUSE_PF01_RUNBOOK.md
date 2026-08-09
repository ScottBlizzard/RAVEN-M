# PF01 MobileUse execution runbook

This runbook is the only authorized execution order for the first public-framework arm.

## Frozen scope

- Framework: MadeAgents MobileUse `MultiAgent` at commit `babec07fd0e5faa7e7bcc7d3d0ee2320f6b83347`.
- Model: Qwen3-VL-32B-Instruct revision `0cfaf48183f594c314753d30a4c4974bc75f3ccb`.
- Runtime: vLLM 0.26.0, BF16, tensor parallel 1, one concurrent sequence.
- Server difference from the validated official-Qwen arm: maximum images per prompt is three, because MobileUse legitimately sends one, two, or three chronological screenshots.
- Scored set: AndroidWorld Hard, seed 20260806, frozen order H06 through H07 in the preregistration.
- No prompt, controller, parser, action adapter, sampling, budget, task, or evaluator change is allowed after the smoke freeze.

## Phase A — GPU-less qualification

1. Work only in `D:\ZJU\Summer_Camp\RAVEN-M-PF01` locally and `/root/autodl-tmp/RAVEN-M-PF01` remotely.
2. Run all unit tests, zero-generation preflight, and baseline replay.
3. Confirm the server model directory and vLLM environment exist.
4. Confirm `torch.cuda.is_available()` is false while in GPU-less mode.
5. Syntax-check the server script with `bash -n`.

GPU mode must not be enabled until all five checks pass.

## Phase B — GPU transport qualification

On the server after GPU mode is enabled:

```bash
cd /root/autodl-tmp/RAVEN-M-PF01
mkdir -p /root/autodl-tmp/runs/mobileuse_pf01_server
nohup bash implementation/scripts/start_mobileuse_server.sh \
  > /root/autodl-tmp/runs/mobileuse_pf01_server/server.log 2>&1 &
echo $! > /root/autodl-tmp/runs/mobileuse_pf01_server/server.pid
```

Open a local tunnel and keep it running:

```powershell
ssh -i "$env:USERPROFILE\.ssh\autodl_raven_m" -p 22252 `
  -L 18000:127.0.0.1:18000 root@connect.westb.seetacloud.com
```

Then run exactly three unscored model calls locally—one image, two ordered images, and three ordered images:

```powershell
& "D:\ZJU\Summer_Camp\RAVEN-M-Research\06_local_runtime\envs\androidworld\Scripts\python.exe" `
  "D:\ZJU\Summer_Camp\RAVEN-M-PF01\implementation\scripts\live_preflight_mobileuse.py"
```

Do not start an emulator task unless `PF01_LIVE_MULTI_IMAGE_PREFLIGHT.json` says `status: pass`, contains image counts `[1, 2, 3]`, and reports zero emulator mutations and zero scored tasks.

## Phase C — one authorized smoke

With the local AndroidWorld emulator already running, execute only `ContactsAddContact`, seed 20260805, with at most three native decisions:

```powershell
& "D:\ZJU\Summer_Camp\RAVEN-M-Research\06_local_runtime\envs\androidworld\Scripts\python.exe" `
  "D:\ZJU\Summer_Camp\RAVEN-M-PF01\implementation\scripts\run_mobileuse_hard.py" `
  --mode smoke `
  --adb-path "D:\ZJU\Summer_Camp\RAVEN-M-Research\06_local_runtime\android\sdk\platform-tools\adb.exe"
```

The smoke is unscored. It qualifies the framework only if the logs contain Operator, Reflector, Progressor and a real environment action. Passing it creates `PF01_FREEZE_AFTER_SMOKE.json` with hashes of all behavior-relevant files.

## Phase D — scored first seed

Only after the smoke freeze exists, run the 19 preregistered Hard tasks:

```powershell
& "D:\ZJU\Summer_Camp\RAVEN-M-Research\06_local_runtime\envs\androidworld\Scripts\python.exe" `
  "D:\ZJU\Summer_Camp\RAVEN-M-PF01\implementation\scripts\run_mobileuse_hard.py" `
  --mode scored `
  --adb-path "D:\ZJU\Summer_Camp\RAVEN-M-Research\06_local_runtime\android\sdk\platform-tools\adb.exe"
```

Stop immediately on source-hash drift, model/version drift, missing role logs, evaluator errors, emulator infrastructure errors, or a scientifically invalid episode. Do not tune on the scored seed. Preserve every L0–L5 event and post-hoc mechanism metric, including failures.
