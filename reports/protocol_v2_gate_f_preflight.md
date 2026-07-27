# Protocol-v2 Gate F preflight

Date: 2026-07-27  
Decision: **PASS for batch 1 only**  
Automatic batch 2 transition: **disabled**

Gate F is frozen as twelve paired B3/M0 cells over six preregistered Hard
tasks, split into three separately invoked four-cell batches. Seed
`20260730` and the randomized blocked order are fixed in the experiment
manifest. Each batch contains two B3 and two M0 cells, paired variants never
share a batch, and paired variants are never adjacent.

The preflight found and repaired one metadata-only pairing defect before any
Gate-F cell ran. `SaveCopyOfReceiptTaskEval` contains a PIL image parameter;
the prior generic serializer exposed a process-local object address. Gate F
now identifies image parameters by mode, dimensions, and pixel-content
SHA-256. Repeated generation of all six frozen instances produces identical
goal and parameter hashes, while a pixel change changes the parameter hash.
No task semantics, model prompt, action policy, or evaluator was altered.

Verification completed:

- 139/139 repository tests passed;
- 9/9 Gate-F-specific tests passed;
- 19/19 Hard tasks passed the action-capability audit;
- the three Gate-E artifact hashes still match the Gate-E pass report;
- Android emulator `emulator-5554` is connected;
- the frozen 32B model health check passed with the expected revision and
  four-RTX-4090 backend;
- the Gate-F output directory was absent before launch.

Only batch 1 is authorized:

1. H01 `BrowserMultiply`, B3;
2. H17 `SportsTrackerActivitiesOnDate`, M0;
3. H03 `ExpenseAddMultipleFromMarkor`, B3;
4. H16 `SimpleCalendarAddOneEvent`, M0.

The runner writes an atomic progress checkpoint after every valid cell and
stops after the fourth cell or at the first frozen diagnostic stop condition.
It cannot launch batch 2 or Gate G automatically.
