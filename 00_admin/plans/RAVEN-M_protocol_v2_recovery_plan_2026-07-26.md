# RAVEN-M protocol v2 recovery and experiment plan

Date: 2026-07-26  
Status: `planning_only`  
Current experiment state: protocol-v1 breadth complete, later v1 phases halted  
Purpose: obtain an interpretable summer-camp result without repeating the
cost and scientific risk of the 95-cell breadth run

---

## 1. Executive decision

The remaining 269 protocol-v1 cells must not be started.

The completed 95 cells are retained as an immutable diagnostic pilot.  They
proved that the end-to-end system, logging, pairing, retry, and evaluator
pipeline can run, but they also exposed:

- 15 breadth cells whose task evaluator requires an unsupported `answer`
  action;
- a supported-task success floor of 1/80;
- widespread repeated-action loops;
- an M0 completion contract that can enter a delayed-FACT deadlock;
- a development gate that tested engineering validity but not full
  task-action compatibility.

Any change that adds `answer`, changes completion semantics, or enforces loop
recovery is a semantic protocol change.  It must be implemented under a new
protocol-v2 identity and cannot be described as a protocol-v1 hotfix.

Protocol v2 will use a staged, stop-gated process:

1. seal and classify v1;
2. implement and test v2 without GPU experiments;
3. pass an eight-cell non-Hard capability gate;
4. pass a twelve-cell paired Hard micro-gate;
5. extend the same frozen run to 24 cells only if the micro-gate passes;
6. add a held-out second seed only if the 24-cell pilot is non-floor;
7. run compute controls or ablations only after a positive main/mechanism
   signal appears.

No stage starts automatically after the previous stage.  Every GPU stage ends
with a written gate report and an explicit go/no-go decision.

---

## 2. Evidence and cost baseline

### 2.1 What protocol v1 actually cost

| Quantity | Realized value |
|---|---:|
| Completed breadth cells | 95 |
| Wall-clock interval | about 48 h including outages and recovery |
| Summed episode wall time | 22.01 h |
| Model latency | 13.22 h |
| Model calls | 4,021 |
| Tokens | 17,971,842 |
| Invalid infrastructure attempts | 11 |
| Cells affected by infrastructure retries | 8 |
| Official successes | 1 |

The bottleneck is not merely GPU throughput.  One Android emulator executes
GUI actions serially, every model step incurs remote inference latency, and a
VPN interruption can invalidate the active attempt.  More GPUs do not make
one serial Android trajectory proportionally faster.

### 2.2 Why the old 364-cell plan is no longer acceptable

The original schedule contains:

| Phase | Cells | Variants |
|---|---:|---|
| Breadth | 95 | B0/B1/B2/B3/M0 on 19 tasks |
| Confirmatory additional | 114 | B0/B3/M0, two more seeds |
| Strict control | 19 | S0 |
| Ablation and budget controls | 136 | MREL, five M0 ablations, B3_CTX, B3_CALL, S0 |
| Total | 364 | 14 variant labels |

Thirty-six cells use the three information-retrieval task classes that require
`answer`; 15 are already in breadth and 21 remain.  Continuing the old
schedule would knowingly produce structural zeroes.

At the observed average of 13.9 episode-minutes, the remaining 269 cells imply
about 62 serial episode-hours before outage and recovery overhead.  This
compute is not authorized by this plan.

---

## 3. Research question after the breadth diagnosis

Protocol v2 keeps the Selective-Trust Memory Routing thesis but makes its
operational question more precise:

> Can a GUI agent use uncertain memory to guide low-risk exploration while
> requiring verified evidence for state-changing or terminal decisions,
> without becoming trapped in verification or recovery loops?

This reframing covers both failure directions observed in v1:

- **over-trust:** a hypothesis can influence a consequential action without
  adequate verification;
- **under-trust:** useful current-screen evidence is rejected because it has
  not survived a delayed routing cycle as FACT.

The central mechanism comparison remains:

- M0: reliability-aware routing;
- MREL: relevance-only routing with otherwise matched architecture.

The system comparison remains:

- M0 versus B3;
- M0 versus B0 as secondary.

B1 and B2 are not required in the first v2 pilot.  They add cost but do not
directly test the refined mechanism.  B3_CTX, B3_CALL, and component ablations
are conditional follow-ups, not default work.

---

## 4. Non-negotiable boundaries

### 4.1 Protocol-v1 preservation

- Do not edit or delete any v1 raw trajectory, screenshot, evaluator result,
  or scored result.
- Do not mix v1 and v2 cells in one statistical table.
- Label v1 as `diagnostic pilot / halted after breadth`.
- Preserve the current v1 Git tags, reports, and checksum evidence.
- A v2 success cannot retroactively turn a v1 result into a valid v2 result.

### 4.2 Changes that are forbidden

- no per-Hard-task prompt instructions;
- no per-task coordinate scripts or action macros;
- no evaluator feedback exposed to the model;
- no budget increase based on a task's observed failure;
- no model or revision switch during a direct comparison;
- no cherry-picking only the tasks where M0 looked best;
- no semantic code change after a stage is frozen;
- no automatic transition from one experimental gate to the next;
- no overnight full-suite run before the 24-cell pilot passes.

### 4.3 Changes that are permitted in v2

- completing a missing benchmark action interface;
- generic action-loop recovery;
- generic completion verification;
- generic provenance rules for observed or computed text;
- new audit fields and preflight checks;
- a new exploratory task subset chosen by capability coverage before v2
  results exist.

---

## 5. Repository and artifact separation

All v2 work must be isolated from v1.

Proposed identities:

```text
Git branch: protocol-v2-exploratory
Protocol label: androidworld_protocol_v2_exploratory
Development tag: protocol-v2-dev
Pilot freeze tag: protocol-v2-pilot-freeze
Output root: runs/protocol_v2/
```

Proposed tracked artifacts:

```text
04_protocols/protocol_v2_spec.md
05_project/configs/task_capabilities_v2.json
05_project/configs/experiments/v2_capability_gate.json
05_project/configs/experiments/v2_hard_micro_gate.json
05_project/configs/experiments/v2_pilot.json
05_project/metadata/protocol_v2_preregistration.json
05_project/scripts/audit_task_action_coverage.py
05_project/scripts/audit_protocol_v2.py
05_project/scripts/run_protocol_v2_suite.py
05_project/tests/...v2...
reports/protocol_v2_gate_*.md
```

Proposed runtime output names:

```text
runs/protocol_v2/nonhard_capability_seed20260729/
runs/protocol_v2/hard_micro_seed20260730/
runs/protocol_v2/pilot_seed20260730/
runs/protocol_v2/heldout_seed20260731/
```

The micro-gate results may be reused in the 24-cell pilot only when:

1. the code commit, prompts, schemas, model revision, task parameters, and
   budgets remain byte-identical;
2. the micro schedule was already declared as the B3/M0 portion of the pilot;
3. no result-dependent tuning occurs after the micro-gate;
4. the reuse rule is written before the first micro cell runs.

If any semantic file changes, the twelve micro cells remain diagnostic and
must not be merged with later results.

---

## 6. Work package A: seal protocol v1

Estimated time: 30–60 minutes  
GPU: none

Required outputs:

1. SHA-256 manifest for:
   - 95 `scored_result.json` files;
   - 95 raw `episode.json` files;
   - `suite_summary.json`;
   - `schedule.snapshot.json`;
   - all protocol amendment manifests.
2. A machine-readable status record:
   - `breadth_complete=true`;
   - `later_phases_halted=true`;
   - `scientific_status=diagnostic_only`;
   - `halt_reason=task_interface_gap_and_floor_effect`.
3. A list of 15 breadth cells affected by missing `answer`.
4. A list of all 36 scheduled v1 cells affected by missing `answer`.
5. Confirmation that the v1 tree is not used as the v2 output root.

Gate A passes only when the manifests reproduce exactly and the Git worktree
contains no uncommitted v1 protocol changes.

---

## 7. Work package B: task-action capability audit

Estimated time: 1–2 hours  
GPU: none

Create an explicit capability matrix for every selected task class.

Minimum fields:

```json
{
  "task_class": "SportsTrackerActivitiesOnDate",
  "required_actions": ["open_app", "tap", "swipe", "answer"],
  "requires_derived_text": true,
  "requires_cross_app_transfer": false,
  "has_irreversible_action": false,
  "terminal_channel": "answer",
  "supported_by_protocol_v2": true,
  "evidence": ["source file and line anchors"]
}
```

Capability categories for the 19 original Hard tasks:

| Tasks | Capability stress |
|---|---|
| H01 | file open, browser interaction, arithmetic, derived input |
| H02 | image reading, multi-row transfer |
| H03 | text-file reading, filtering, cross-app multi-row transfer |
| H04 | list search and repeated deletion |
| H05 | note creation, cross-app share, irreversible SMS send |
| H06 | long text retention and ordered merge |
| H07 | multi-frame visual transcription and derived input |
| H08 | map search and marker persistence |
| H09 | long map workflow and ordered waypoints |
| H10 | image OCR and multiple structured recipes |
| H11 | text extraction and multiple structured recipes |
| H12 | conditional filtering and multiple structured recipes |
| H13 | semantic constraint and repeated deletion |
| H14 | search, ordered playlist, file export |
| H15 | file copy and destination persistence |
| H16 | multi-field calendar persistence |
| H17 | information retrieval and `answer` |
| H18 | information retrieval, aggregation, unit conversion, `answer` |
| H19 | information retrieval, temporal filtering, aggregation, `answer` |

The audit script must fail closed when:

- a required action is absent from the schema;
- the adapter cannot map it;
- the controller cannot execute its terminal semantics;
- a prompt does not document it;
- a task requires derived text while the prompt forbids derived text.

Gate B passes only when every task intended for a v2 experiment has complete
action coverage.  Unsupported tasks are excluded before schedule generation,
not allowed to run and fail.

---

## 8. Work package C: protocol-v2 semantic corrections

Estimated time: 3–5 hours  
GPU: none

### 8.1 Add terminal `answer`

Add the canonical form:

```json
{
  "status": "done",
  "action": {
    "type": "answer",
    "text": "the task answer"
  }
}
```

Required behavior:

1. `answer` is accepted only when the goal asks for returned information.
2. The adapter maps it to AndroidWorld:

```python
JSONAction(action_type="answer", text=...)
```

3. The controller executes the answer before terminating.
4. The raw record logs:
   - answer action;
   - answer text hash and length;
   - whether `interaction_cache` was populated;
   - evaluator reward only after termination and never in a later prompt.
5. A normal `done` action remains null for state-changing GUI tasks.
6. Reset must clear `interaction_cache`.

The exact answer text must remain available in the raw episode for scientific
error analysis, while summary tables may use a hash when desired.

### 8.2 Correct the text-origin rule

Replace:

> type_text may contain only a value explicitly requested by TASK.

With:

> Text may be entered only when it is (a) explicitly supplied by the task, or
> (b) directly observed or deterministically computed as a required task
> variable. Optional labels and unrequested values must never be invented.

Every `type_text` and `answer` decision records:

```text
text_origin = task_literal | current_screen | verified_memory | deterministic_calculation
source_memory_ids = [...]
```

This metadata is audited but does not expose hidden evaluator state.

### 8.3 Enforce loop recovery

Define a loop fingerprint:

```text
(current_page_signature, canonical_action)
```

A recovery trigger occurs when:

- the same fingerprint produces no visible change twice; or
- the same canonical action repeats three times on an effectively unchanged
  page; or
- an A-B-A-B page/action cycle repeats twice.

After a trigger:

1. the same action on the same page is blocked for the next decision;
2. the critic must return one concrete recovery class:
   - change target;
   - reverse scroll direction;
   - navigate back;
   - reopen app;
   - inspect a different visible control;
   - fail safely;
3. the executor prompt includes the blocked fingerprint and required recovery;
4. the controller validates that the following action obeys the constraint;
5. no more than one extra repair call is allowed;
6. loop detection, critic recommendation, and compliance are logged.

There is no task-specific coordinate replacement.

### 8.4 Replace delayed completion FACT deadlock

Protocol v1 requires an already routed FACT before M0 may return `done`.
Protocol v2 uses same-turn completion adjudication:

1. executor emits a completion candidate;
2. the current screenshot, planner requirements, routed memory, and claimed
   completion evidence are sent to the existing critic;
3. completion is accepted when:
   - the current screenshot directly supports the claim, or
   - currently valid FACT memory supports it;
   - no unresolved planner requirement remains;
   - the critic does not reject completion;
4. rejected completion returns a concrete missing requirement or recovery
   action, not a generic forced wait;
5. unchanged screenshots cannot generate unlimited completion retries;
6. M0 and MREL use the same completion adjudicator so that their difference
   remains the routing policy.

The evaluator stays hidden and runs only after agent termination.

### 8.5 Risk-sensitive authority record

Each decision receives one risk class:

```text
observe/navigation
reversible_edit
irreversible_commit
terminal_answer_or_completion
```

Minimum authority policy:

- HYPOTHESIS may guide observation and navigation.
- A reversible edit needs current-screen support or valid memory.
- An irreversible commit needs direct current-screen support or routed FACT.
- A terminal answer/completion needs same-turn critic approval plus direct
  evidence or routed FACT.
- SUPPRESS memory is never exposed or citable.
- ALERT can constrain recovery but cannot independently justify a commit.

The first v2 implementation should keep the enforcement small and auditable.
Do not add a second large learned subsystem.

---

## 9. Work package D: no-GPU verification

Estimated time: 1–2 hours  
GPU: none

### 9.1 Unit tests

All existing 86 tests must continue to pass.  Add tests for:

- valid and invalid `answer` schema cases;
- `answer` adapter mapping;
- controller executes answer before termination;
- exact `interaction_cache` propagation;
- reset clears `interaction_cache`;
- answer does not leak evaluator output;
- literal, observed, verified-memory, and calculated text origins;
- third identical no-effect action is blocked;
- changed page resets the loop guard;
- A-B-A-B cycle recovery;
- completion accepted from same-screen evidence;
- completion rejected with a concrete unmet requirement;
- M0 and MREL share completion logic;
- v1 artifacts are not written by v2 code;
- capability audit rejects a deliberately unsupported task.

Target: all existing tests plus at least 15 new focused tests, with 100% pass.

### 9.2 Local Android integration tests

Without a real model:

1. initialize a simple information-retrieval fixture;
2. submit the correct answer through the adapter;
3. confirm `interaction_cache`;
4. confirm evaluator success;
5. repeat with a wrong answer and confirm evaluator failure;
6. tear down and reset three times;
7. confirm no answer leaks into the next task.

Also execute one instance of every canonical action against the emulator or an
appropriate fixture, including `answer`.

### 9.3 Gate D

Go only if:

- all tests pass;
- no v1 file hash changes;
- all selected task capabilities are covered;
- answer success/failure behavior matches AndroidWorld exactly;
- reset isolation passes three consecutive times;
- no uncommitted semantic files remain.

Then commit and tag `protocol-v2-dev`.

---

## 10. Experimental gate E: non-Hard capability suite

Maximum cells: 8  
Expected active experiment time: 1–1.5 h  
Hard cap including recovery: 2 h  
Variants: B3 and M0  
GPU: four-RTX-4090 inference server  
Execution: one local Android emulator, serial

Use four non-Hard task families:

1. `SimpleCalendarEventsOnDate` — required `answer`;
2. `ContactsAddContact` — ordinary persistence;
3. `ExpenseAddSingle` — multiple fields and category choice;
4. `FilesMoveFile` — file operation and destination persistence.

Use one preregistered development seed per task and run both variants on the
same generated instance.

Required pass conditions:

- 8/8 valid scored episodes;
- zero task-action compatibility errors;
- both information-retrieval cells populate `interaction_cache`;
- at least one information-retrieval variant answers correctly;
- at least 4/8 overall task successes;
- B3 and M0 each have at least one success;
- zero unhandled third identical no-effect action;
- zero M0 completion deadlocks;
- 100% valid output after one bounded repair;
- no evaluator leakage or cross-episode memory;
- no infrastructure-invalid attempt counted as a result.

If any required condition fails:

- stop;
- write a capability gate failure report;
- diagnose and change code under a new dev commit;
- rerun this gate from scratch;
- do not touch Hard tasks.

---

## 11. Experimental gate F: paired Hard micro-gate

Maximum cells: 12  
Expected active experiment time from v1 measurements: about 2.2 h  
Hard cap including recovery: 3.5 h  
Variants: B3 and M0  
Seed: `20260730`  
Batch size: at most 4 cells  
Automatic continuation to the next batch: forbidden

### 11.1 Fixed task subset

| Task | Reason for inclusion | V1 B3+M0 time |
|---|---|---:|
| H01 BrowserMultiply | derived calculation and text input | 16.2 min |
| H03 ExpenseAddMultipleFromMarkor | long cross-app variable retention | 53.8 min |
| H05 MarkorCreateNoteAndSms | irreversible cross-app commit | 19.0 min |
| H15 SaveCopyOfReceiptTaskEval | file persistence | 9.6 min |
| H16 SimpleCalendarAddOneEvent | known-solvable multi-field persistence | 24.0 min |
| H17 SportsTrackerActivitiesOnDate | terminal `answer` | 11.0 min in v1, structurally invalid there |

Total v1-observed B3+M0 episode time for these task classes was approximately
134 minutes.  The 3.5-hour cap includes slower v2 completion adjudication and
one infrastructure recovery margin.

The subset is selected before v2 results for six distinct capabilities.  H16
is included as a positive-control task because at least one v1 variant solved
it; this is disclosed and not presented as random task sampling.

### 11.2 Scheduling

- generate all six task instances before running;
- verify B3/M0 goal and parameter hashes match within each pair;
- block-randomize the twelve cells;
- separate paired variants where possible to reduce immediate-state effects;
- execute three batches of at most four cells;
- produce a checkpoint and gate snapshot after every batch;
- do not inspect method-level success to tune code between batches.

### 11.3 Required pass conditions

- 12/12 valid scored episodes after excluding documented infrastructure
  attempts;
- zero pairing or audit errors;
- H17 `answer` channel functions in both variants;
- at least 3 of 6 task instances are solved by at least one variant;
- at least 3/12 total successes (25%);
- B3 and M0 each succeed at least once;
- at least one M0 episode terminates normally rather than all reaching budget;
- zero third consecutive identical no-effect action;
- 100% compliance with loop-recovery constraints;
- zero delayed-FACT completion deadlock;
- zero answer or typed-text provenance audit errors;
- M0/B3 mean model-call ratio no greater than 1.5;
- M0/B3 mean wall-time ratio no greater than 1.6;
- no context-cap, cross-episode, reset, or evaluator-leakage error.

These thresholds are feasibility gates, not claims that M0 is superior.

### 11.4 Stop conditions

Stop the gate immediately after the current atomic cell if:

- an unsupported required action is discovered;
- pairing hashes differ;
- a semantic controller exception occurs;
- the same no-effect action is executed a third time despite the guard;
- answer text is produced but `interaction_cache` remains empty;
- a raw result would need semantic repair after completion;
- two consecutive cells fail for the same infrastructure cause;
- projected active time exceeds 3.5 hours.

If the final gate fails, do not run B0 or MREL.  The twelve cells become a
diagnostic v2 micro-run and the project returns to local diagnosis.

---

## 12. Experimental gate G: 24-cell exploratory pilot

Maximum total cells including the micro-gate: 24  
Additional cells after gate F: 12  
Variants: B0, B3, MREL, M0  
Tasks and seed: identical to gate F  
Expected total active time: 3.5–4.5 h  
Hard cap: 6 h

If gate F passes without any semantic code change, reuse its twelve B3/M0
cells and add B0/MREL for the same six task instances.  Otherwise no reuse is
permitted.

### 12.1 Scientific contrasts

Primary mechanism:

```text
M0 versus MREL
```

Primary system:

```text
M0 versus B3
```

Secondary:

```text
M0 versus B0
```

Report:

- task success;
- normal termination, premature completion, and budget exhaustion;
- repeated-action and recovery metrics;
- completion-candidate acceptance/rejection;
- memory route and citation counts;
- answer correctness;
- model calls, tokens, latency, and wall time;
- qualitative traces for at least one success and one failure.

### 12.2 Pilot continuation gate

Go to a held-out seed only if:

- at least 4/24 total successes;
- at least 3/6 task instances are solvable;
- M0 and MREL each succeed at least once;
- the main contrasts are not all tied at zero;
- no method is structurally prevented from completing a task;
- M0 completion and loop constraints pass;
- no invalid comparison is caused by unequal task parameters;
- M0 compute ratios remain within the gate-F caps;
- a manual audit of at least 30 memory-citing decisions has:
  - complete source provenance;
  - complete action-risk labels;
  - no SUPPRESS citation;
  - no unexplained irreversible action justified only by HYPOTHESIS;
  - no completion accepted without valid evidence.

The pilot does not need to prove statistical significance.  It must prove
that the task/model regime is non-floor and the mechanism is measurable.

---

## 13. Experimental gate H: held-out focused validation

Maximum additional cells: 24  
Combined v2 Hard total: 48  
Seed: `20260731`, fixed before execution  
Tasks/variants: same six tasks and four variants  
Expected additional active time: 3.5–4.5 h  
Hard cap: 6 h

The second seed is held out from code and prompt development.  No semantic
change is allowed between pilot and held-out validation.

Analysis separates:

- seed `20260730`: development/pilot evidence;
- seed `20260731`: held-out validation evidence;
- combined 48: explicitly labelled exploratory aggregate.

Use paired descriptive statistics:

- paired success differences;
- exact McNemar test where informative;
- paired bootstrap confidence intervals;
- median calls/tokens/wall-time differences;
- failure-mode and authority-violation counts.

With only twelve task-seed pairs, absence of statistical significance is not
a failure.  The deliverable should emphasize effect direction, mechanism
traces, reproducibility, and honest uncertainty.

Gate H is the planned stopping point for the summer-camp project unless the
evidence clearly justifies more experiments.

---

## 14. Conditional controls—not default experiments

No controls or ablations run when all main contrasts remain at the floor.

### 14.1 Compute controls

Run B3_CTX and/or B3_CALL only if:

- M0 exceeds B3 on at least two task-seed pairs; and
- M0 uses materially more context or calls.

Maximum initial compute-control expansion:

```text
6 tasks × 2 seeds × 1 control = 12 cells
```

Add the second compute control only if the first does not resolve the
explanation.

### 14.2 Component ablations

Run a component ablation only when process evidence identifies a specific
mechanism:

- remove loop recovery only if loop recovery changes behavior;
- remove verified ledger only if FACT authority is used;
- remove critic only if completion/recovery critic events matter;
- remove failure memory only if transferable failures are retrieved.

Do not run five ablations merely because they were listed in the original
364-cell schedule.

### 14.3 Maximum optional expansion

The initial optional expansion is capped at 24 cells.  Anything beyond that
requires a new written analysis showing:

- exact claim enabled by the extra cells;
- estimated runtime;
- why existing cells cannot answer it;
- stop condition;
- user approval.

---

## 15. Compute, server, and batching policy

### 15.1 Hardware assignment

- Four RTX 4090 GPUs: primary Qwen3-VL-32B BF16 inference service.
- Local Windows machine: one AndroidWorld emulator and controller.
- A40 server: reserve/fallback; do not add it merely to claim more compute.

One emulator remains the serial bottleneck.  A second inference server does
not help unless a second fully isolated emulator/controller/environment is
validated, which is outside the first v2 plan.

### 15.2 Batch policy

- maximum four cells per launched batch;
- target batch duration under 90 minutes;
- no batch spans two experimental gates;
- completed cell result written atomically before the next cell;
- suite progress updated after every cell;
- model and emulator health checked before every batch;
- local disk free space checked before every batch;
- no automatic next-batch launch.

### 15.3 Connection policy

The local machine and VPN must remain connected only during an active batch.
After a batch checkpoint completes, the local machine may be shut down.

If VPN/model connectivity is lost:

1. stop or invalidate only the active attempt;
2. preserve completed cells;
3. archive the invalid raw attempt;
4. recheck exact model identity;
5. resume from the next permitted attempt;
6. never score a partial connectivity failure.

### 15.4 Retry policy

- infrastructure failures are distinct from agent failures;
- at most three ordinary infrastructure attempts per cell;
- no retry for a valid agent failure;
- retry regeneration must match goal and canonical parameter hashes;
- no ad hoc fourth/fifth attempt without a written exception;
- two consecutive same-cause infrastructure failures stop the batch.

---

## 16. Monitoring and observability

Every active batch requires:

- runner PID and start time;
- current phase, batch, sequence, pair, variant, and attempt;
- latest successful checkpoint time;
- model-server health and exact revision;
- emulator/ADB responsiveness;
- VPN/model-unavailable count;
- episode elapsed time versus task-specific budget;
- local disk remaining;
- log growth heartbeat.

Alert states:

```text
WARN:
  no checkpoint for 20 minutes on a short-budget task
  one model or emulator outage
  disk free space below the preregistered reserve

STOP:
  no log growth and no model call for 10 minutes
  two consecutive same-cause outages
  model revision/backend mismatch
  pairing mismatch
  semantic controller error
  batch time cap reached
```

Monitoring is for recovery and integrity, not for changing prompts or choosing
methods based on live success.

---

## 17. Data integrity and analysis policy

### 17.1 Before a GPU stage

Freeze:

- Git commit and tag;
- protocol specification;
- model/backend/revision;
- prompts and schemas;
- task list and seeds;
- variant order randomization;
- step and model-call budgets;
- retry policy;
- all pass/fail thresholds;
- output directory;
- analysis script hash.

### 17.2 During a stage

Allowed live checks:

- infrastructure health;
- file completeness;
- schema validity;
- pairing hashes;
- context and budget caps.

Forbidden live adaptations:

- prompt tuning;
- route threshold tuning;
- method removal because it looks weak;
- task removal because it fails;
- budget extension;
- result-driven seed replacement.

### 17.3 After a stage

Produce:

- machine-readable audit JSON;
- immutable suite summary;
- SHA-256 manifest;
- concise human gate report;
- explicit go/no-go decision;
- representative trace list;
- exact compute and outage accounting.

---

## 18. Decision table

| Observation | Required action |
|---|---|
| Any selected task lacks an executable required action | Stop before GPU; fix capability coverage |
| Non-Hard answer does not populate cache | Stop; do not run Hard |
| Non-Hard success below 4/8 | Stop; diagnose controller/model interface |
| Hard micro has fewer than 3 successes | Stop; do not add B0/MREL |
| Hard micro has fewer than 3 solvable task pairs | Stop; task regime remains floor |
| M0 has zero successes or zero normal terminations in micro | Stop; completion/memory path still unsuitable |
| Third identical no-effect action executes | Stop; loop guard failed |
| 24-cell main contrasts all tie at zero | Stop the project experiments; write negative result |
| 24-cell pilot is non-floor but M0 has no directional benefit | Stop main expansion; analyze failure mechanism |
| M0 beats B3 but not MREL | Evidence favors architecture/compute, not selective trust |
| M0 beats MREL but not B3 | Mechanism may work without system-level benefit |
| M0 beats both B3 and MREL | Proceed to held-out seed |
| Held-out direction reproduces | Consider one compute control |
| Held-out direction reverses | Report instability; do not launch ablation matrix |

---

## 19. Estimated total time and maximum exposure

| Stage | Cells | Expected active time | Hard cap |
|---|---:|---:|---:|
| V1 sealing + v2 design/code/tests | 0 | 5–10 h work | no GPU |
| Non-Hard capability | 8 | 1–1.5 h | 2 h |
| Hard micro | 12 | about 2.2 h | 3.5 h |
| Add B0/MREL to pilot | +12 | 1.5–2.5 h | pilot total 6 h |
| Held-out seed | +24 | 3.5–4.5 h | 6 h |
| Planned total model episodes | 56 | about 8–10 h | 14 h across all gates |

The 56 cells include eight non-Hard development cells and 48 Hard exploratory
cells.  They are not launched together.  The maximum unreviewed GPU exposure
is one four-cell batch, normally below 90 minutes.

This is deliberately smaller than the remaining 269-cell v1 plan.  Expansion
occurs only when each preceding block proves that the next block can answer a
specific scientific question.

---

## 20. Expected summer-camp deliverable

Even if v2 does not show a positive M0 success effect, the project can still
produce a strong and honest submission:

1. a complete reproducible GUI-memory agent implementation;
2. a documented 95-cell diagnostic breadth run;
3. discovery and proof of a benchmark action-interface incompatibility;
4. quantitative failure taxonomy for loops, premature completion, and
   verification deadlock;
5. a redesigned risk-sensitive selective-trust mechanism;
6. a small but valid, non-floor v2 evaluation or a clearly bounded negative
   result;
7. representative traces showing when memory helps, misleads, or blocks
   completion;
8. exact compute, integrity, and limitation reporting.

The project should be judged by whether each claim is supported, not by
whether all 364 originally imagined cells were consumed.

---

## 21. Immediate next round

After this plan is approved, the next round contains **no GPU experiment**.

Execute only:

1. seal v1 hashes and status;
2. create the v2 branch and protocol specification;
3. build the 19-task capability matrix;
4. implement `answer`, text provenance, loop guard, and completion
   adjudication;
5. add and run all unit/integration tests;
6. produce gate-D report.

Only after gate D passes should the user be asked to authorize the eight-cell
non-Hard capability suite.
