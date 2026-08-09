# B2 Clean MobileUse execution runbook

This runbook is the only authorized execution order for the five-task B2
development diagnostic. It does not authorize the full 19-task expansion.

## Completed without a GPU

- B2 has a distinct arm id and branch.
- The five development tasks and native budgets are frozen.
- The exact model revision and sampling parameters are unchanged.
- The memory representation remains free-text MobileUse history/progress.
- All 80 repository tests pass in the AndroidWorld environment.
- The zero-generation preflight reports `status: pass` and zero generation calls.

## No-card deployment

Local repository: `D:\ZJU\Summer_Camp\RAVEN-M-PF01`.

Remote repository: `/root/autodl-tmp/RAVEN-M-PF01`.

Pull only the branch and commit reported with this runbook. Before GPU startup,
run:

```bash
cd /root/autodl-tmp/RAVEN-M-PF01
git status --short
git branch --show-current
bash -n implementation/scripts/start_mobileuse_server.sh
```

The worktree must be clean. Do not edit the controller, prompts, task manifest,
runner, model settings or preregistration on the server.

## GPU phase 1: transport and one smoke

Start the unchanged Qwen server:

```bash
cd /root/autodl-tmp/RAVEN-M-PF01
mkdir -p /root/autodl-tmp/runs/mobileuse_b2_server
RAVEN_RUN_DIR=/root/autodl-tmp/runs/mobileuse_b2_server \
nohup bash implementation/scripts/start_mobileuse_server.sh \
  >/root/autodl-tmp/runs/mobileuse_b2_server/server.log 2>&1 &
echo $! >/root/autodl-tmp/runs/mobileuse_b2_server/server.pid
```

Keep the existing local tunnel on port 18000. Confirm `/health` and model
revision, then run the unscored three-decision smoke:

```powershell
& "D:\ZJU\Summer_Camp\RAVEN-M-Research\06_local_runtime\envs\androidworld\Scripts\python.exe" `
  "D:\ZJU\Summer_Camp\RAVEN-M-PF01\implementation\scripts\run_clean_mobileuse_b2.py" `
  --mode smoke `
  --adb-path "D:\ZJU\Summer_Camp\RAVEN-M-Research\06_local_runtime\android\sdk\platform-tools\adb.exe"
```

The smoke must be scientifically valid and contain an Operator request, a B2
role-schedule decision, and a real environment action. It then writes
`B2_FREEZE_AFTER_SMOKE.json`. Do not continue if it fails.

## GPU phase 2: five-task diagnostic

After the smoke freeze, run exactly:

```powershell
& "D:\ZJU\Summer_Camp\RAVEN-M-Research\06_local_runtime\envs\androidworld\Scripts\python.exe" `
  "D:\ZJU\Summer_Camp\RAVEN-M-PF01\implementation\scripts\run_clean_mobileuse_b2.py" `
  --mode diagnostic `
  --adb-path "D:\ZJU\Summer_Camp\RAVEN-M-Research\06_local_runtime\android\sdk\platform-tools\adb.exe"
```

Order: H12, H08, H05, H01, H14. Do not stop for poor scientific performance.
The harness preserves an invalid episode and continues, but any invalid task
automatically fails the expansion gate.

## Expansion decision

The runner writes `aggregate.json` and `expansion_gate.json`. Full B2 is allowed
only if every frozen gate passes. A failed gate must be reported as a failed
development diagnostic; it must not be patched and renamed held out.

If the gate passes, stop before the full 19-task run. First create and audit a
new full-arm freeze on seed 20260807 using exactly the same behavioral code.
