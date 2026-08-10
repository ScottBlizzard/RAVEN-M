# A4 AWM donor acquisition and source lock

## Current qualification state

A4 is **not ready to run**. Two independent, real, evaluator-confirmed non-Hard donors are locally available and source-locked, but neither covers the Expense family used by the first A4 qualification task. No workflow bank is emitted until a successful independent Expense donor is acquired. This does not block A3 or A5 qualification.

The two accepted local candidates are:

- `ContactsAddContact` (Easy), seed `20260723`, evaluator reward `1.0`.
- `MarkorCreateNote` (Medium), seed `20260726`, evaluator reward `1.0`.

Their episode, event, suite-summary, suite-manifest, and scored-Hard-manifest hashes are frozen in `implementation/configs/a4_awm_donor_manifest_v1.json`. The builder also rejects every task class present in the scored 19-Hard manifest. Failed Easy/Medium episodes are never admitted.

## Zero-generation audit

Run this before acquiring anything:

```bash
python implementation/scripts/build_a4_donor_bank.py
```

Expected state before Expense acquisition: exit code `2`, `status=not_ready`, two eligible donors, and `missing_required_families=["expense"]`. The command performs no model or GPU call and writes only `evidence/a345/A4_DONOR_SOURCE_AUDIT.json`; it must not create `A4_FROZEN_DONOR_WORKFLOW_BANK.json`.

## Frozen Expense donor acquisition

Use the predeclared independent Easy task, not any of the scored 19 Hard tasks:

- task: `ExpenseAddSingle`
- seed: `20260821`
- budget: `20` actions
- source role: donor acquisition only; it is never scored as A4 evidence

Run the existing official Qwen-Mobile runner with a separate output root and diagnostic-only label. Do not change the controller, prompt, model revision, task, seed, or budget after seeing the outcome:

```bash
python implementation/scripts/run_official_qwen_mobile.py \
  --url http://127.0.0.1:18000 \
  --adb-path /root/android_sdk/platform-tools/adb \
  --task ExpenseAddSingle \
  --seed 20260821 \
  --max-steps 20 \
  --run-stage a4_donor_acquisition \
  --diagnostic \
  --output-root runs/a4_donors
```

If this frozen acquisition fails, A4 remains not ready. Do not turn a failed trace into a workflow, do not tune on it and relabel the result held-out, and do not substitute a scored Hard trajectory.

If it succeeds, add exactly one donor record to the manifest using the produced `episode.json`, `events.jsonl`, suite summary, and suite manifest, plus their SHA-256 values. Its `coverage_family` must be `expense`; the hidden evaluator reward and episode-complete event must both confirm success. Then run:

```bash
python implementation/scripts/build_a4_donor_bank.py
python implementation/scripts/build_a4_donor_bank.py --validate
```

Only two zero-exit commands authorize A4. The bank builder deterministically masks donor literal values and never copies coordinates; A4 retrieves a descriptive workflow and the live controller must still ground every action in current pixels.

## Optional breadth after minimum qualification

The manifest freezes optional Easy/Medium acquisition candidates for Recipe, Retro Music, Calendar, and Sports. They may broaden coverage later, but they are not allowed to delay A3/A5 and are not required for the first A4 qualification. Any added donor must pass the same provenance and non-Hard gates.
