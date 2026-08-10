# A3/A4/A5 runbook

## No-GPU qualification

1. Build and freeze the A0/A1/A2 reference ledger.
2. Verify the three official upstream commits and the adaptation/claim table.
3. For A4 only, build its workflow bank from the frozen independent
   Easy/Medium donor protocol; reject any scored-Hard trace or reward leakage.
4. Run `python implementation/scripts/preflight_a345_memory.py`.
5. Run the no-generation emulator qualification.  Do not start a scored model
   while the report, source closure, runtime identity, or donor bank drifts.

## GPU start

Use the already frozen Qwen3-VL-32B vLLM launcher and weight manifest.  Before
the first generation create a live receipt binding PID, command line, model
realpath, full weight-manifest SHA256, vLLM/torch/transformers versions, served
model ID, port, AndroidWorld tree, emulator identity, APK identities, and the
zero-generation preflight digest.  Pass it with `--a345-launch-receipt`.

Run arms separately with `--a345-arm a3`, `a4`, or `a5`.  The runner reorders
the same frozen 19 instances to the five-task gate then the original remaining
14.  It stops after the first scientific gate failure.  Infrastructure-invalid
episodes remain in the checkpoint and may resume only the same task.

Never merge partial gate runs into a 19-task success rate.  A full aggregate is
written only after exactly 19 scientifically valid unique task/seed pairs.

