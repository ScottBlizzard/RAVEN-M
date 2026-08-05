# Multi-framework AndroidWorld Hard benchmark protocol v0.2

Date: 2026-08-05
Decision: **GO_WITH_REVISIONS**
Status: **BINDING; S0 AUTHORIZED; MODEL GENERATION AND ANDROID ACTIONS FORBIDDEN UNTIL THEIR STAGE GATES PASS**

## 1. Binding source and scope

The complete scientific protocol is the GPT Pro decision
`2026_08_05_20_14.md`, SHA-256
`6edb43edb9727d7744716ab9ea52496f39601c371a4f813e6a67592775f019cd`.
That decision is incorporated here by reference. If this compact execution
document and the decision differ, the decision controls and execution stops.

This is a reproducibility benchmark, end-to-end system comparison and process
failure diagnostic. It is not a new RAVEN-M method claim. The previous STOP on
RAVEN-M as a memory method, EEST-AC, reminder timing, correct-memory/wrong-target,
destination-first binding and loop binding remains binding.

## 2. Frozen sources and tasks

- RAVEN detached source: `08b21d06db165d1fb6908c457f955988061b10ca`.
- AndroidWorld: `3e50888527ef9f29b9157ecd537e408008bb1c85`.
- Existing 19-task manifest:
  `05_project/configs/task_manifests/androidworld_hard_v1.json`, SHA-256
  `e651aedeb18f112be3a06562328618d19e9d33eaea94187b1edec51cb00f6ca7`.
- v0.2 instance manifest may add only seeds, parameter hashes and execution
  order. It must not change task classes or native action budgets.
- The official state evaluator is authoritative. A controller finish claim
  never overrides it.

## 3. Frozen arm set

Tier A (S1/S2/S3): `CB-PX-B3`, `CB-PX-M0`, `NS-PX-GO15`,
`NS-PX-MA35`, `NS-PX-SCUA32`, `NS-PX-UIV4`.

Tier B (S1/S2 only): `CB-PX-B0`, `CB-ST-M3A`, `CB-PX-MU`.

No arm is an exact official reproduction. Common-backbone arms are adapter
comparisons; native arms are configuration-equivalent reproductions. Native
differences are descriptive and cannot establish a framework-only causal
effect. UI trees remain hidden from every pixel-only arm.

## 4. Stage gates

1. **S0, zero generation / zero Android actions.** All 15 static gates must
   pass per arm. Timebox: four hours per arm and two calendar days overall.
2. **S1, excluded DEV smoke.** Run only `ContactsAddContact` and
   `ClockStopWatchRunning`, seed `20260805`, at most eight environment actions
   each. A task failure is not rerun; one confirmed infrastructure rerun is
   allowed. Task success is not a qualification criterion.
3. **S2, developmental Hard breadth.** Seed `20260806`, all 19 task classes.
   Tier A first runs the fixed integrity pulse `H01,H06,H09,H17`; only
   infrastructure and contract integrity may stop it.
4. **S3, fresh-instance confirmation under seen task classes.** Tier A only,
   seeds `20260807` and `20260808`. Selection is independent of performance.

Hard calls require all of: S0 global gates, S1 arm gates, unchanged protected
hashes, frozen first-call manifest, B3 and M0, at least two external native
arms from at least two external code/checkpoint families, and at least four
core arms total.

## 5. Budgets and reruns

For native action budget `B`: model calls are capped at `min(4B,240)`, input
tokens at `min(20000B,1000000)`, output tokens at
`min(2048B,131072)`, and wall time at
`max(30 min,min(120 min,90B sec))`. The step multiplier is exactly `1.0`.
Scientific/task failures have zero reruns. One infrastructure rerun is allowed
and must link to the original attempt. All actual Android commands, including
wait, answer and environment-mediated finish, count as actions.

## 6. Integrity boundary

- Do not edit the seven protected paths and hashes recorded in the binding
  decision and v0.2 configuration.
- Do not edit old frozen outputs or old reports.
- Do not tune a prompt, checkpoint, controller, runtime, metric or threshold
  after the first Hard call.
- Do not expose evaluator state, task hints, online search, RAG, MCP or hidden
  task knowledge to agents.
- Do not add mechanism ports or new arms based on observed results.
- Preserve raw prompts, responses, screenshots and evaluator outputs with a
  SHA-256 manifest.

Any protected drift, evaluator leakage, answer-contract failure, minimum-set
failure, post-first-call contract drift, required task-specific patch, or
uncovered scientific interpretation is a mandatory return to GPT Pro.
