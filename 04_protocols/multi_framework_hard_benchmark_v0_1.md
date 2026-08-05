# Multi-framework AndroidWorld Hard benchmark protocol v0.1

Date: 2026-08-05
Status: **DRAFT FOR GPT PRO AUDIT; NO MODEL GENERATION OR ANDROID EPISODE IS AUTHORIZED**

## 1. Why this study exists

The project should not stop merely because the latest proposed intervention is
not novel enough. The previous Hard runs instead motivate a different, useful
question: when several representative GUI-agent systems face the same difficult
tasks, which parts of the observed failure chain do they repair, and which parts
remain broken?

This is a benchmark-and-diagnosis study, not a disguised new-method claim. It
has three possible informative outcomes:

1. one or more systems obtain non-zero Hard success under the frozen evaluator;
2. task success remains zero but a system measurably changes a process failure,
   such as an exact-action loop or feedback-to-action non-response;
3. both task and process outcomes remain unchanged, narrowing the remaining
   bottleneck beyond memory selection, reflection, or simple loop breaking.

## 2. Two comparisons that must not be mixed

### 2.1 Common-backbone diagnostic lane

Where an official framework can preserve its action semantics while using the
existing OpenAI-compatible Qwen3-VL-32B service, compare it with the same model
revision. This lane asks whether the controller/framework changes behavior.
Calling an incompatible prompt or action rewrite an exact reproduction is
forbidden.

### 2.2 Native-system benchmark lane

Run the official or closest documented system configuration. This lane asks how
capable the complete public system is on the frozen Hard suite. Differences may
include model, UI-tree/accessibility privilege, tools, prompts, and action space.
They must be disclosed and cannot support a clean causal claim about the
framework alone.

DroidRun, which can use direct accessibility/tool interfaces, must be reported
in a visibly separate privileged-observation block unless GPT Pro supplies a
stronger defensible matching rule.

## 3. Candidate systems

The complete candidate ledger is
`03_code/manifests/multi_framework_candidates_v0_1.csv`.

The intended core pool is:

- AndroidWorld M3A;
- project B0 and M0 under the pinned Qwen3-VL-32B backend;
- GUI-Owl-1.5 and Mobile-Agent-v3.5;
- MobileUse MultiAgent and ColorMobileAgent;
- DroidRun;
- ScaleCUA after the official source snapshot and model are complete.

UI-TARS-1.5 is a candidate pending runner verification. VLAA-GUI is not a
direct AndroidWorld reproduction and may only enter a later mechanism-port
study. K2-Agent remains a paper-level reported reference until a stable official
repository and runnable recipe are verified.

## 4. Frozen benchmark material

- AndroidWorld commit: `3e50888527ef9f29b9157ecd537e408008bb1c85`.
- Hard task manifest: `05_project/configs/task_manifests/androidworld_hard_v1.json`.
- Manifest SHA-256:
  `e651aedeb18f112be3a06562328618d19e9d33eaea94187b1edec51cb00f6ca7`.
- Task count: 19.
- Native AndroidWorld step budgets remain authoritative.
- The official database/state evaluator remains authoritative. An agent's
  `finish` output never counts as success by itself.

Existing seeds and repeatedly diagnosed trajectories are historical evidence,
not new held-out evidence. The draft proposes fresh seeds `20260806`,
`20260807`, and `20260808`, subject to GPT Pro audit before any generation.

## 5. Stages

### S0: static and runtime qualification

Record the official repository, commit, license, checkpoint, dependency
environment, observation privileges, action space, model service, and adapter
mapping. No generation is allowed.

### S1: excluded non-Hard smoke

Run `ContactsAddContact` and `ClockStopWatchRunning` only to repair interface,
serialization, coordinate, reset, and logging defects. These runs are excluded
from all scored conclusions. Task-specific policy tuning is forbidden.

### S2: one-seed Hard breadth

Every mechanically qualified arm runs all 19 Hard task classes on seed
`20260806`. A system is not dropped merely because its success is low. Expansion
is disabled until the validity audit is complete.

### S3: two-seed confirmation

Run seeds `20260807` and `20260808` only when S2 has no unresolved
infrastructure-class cells, the arm has not changed after its first S2 Hard
cell, and the expansion decision is independent of S2 success rate.

## 6. Required logging

Every valid cell must record at least:

- task class, instance seed, generated instruction and parameter hash;
- system name, repository commit, model ID/revision, prompt hash;
- screenshot/UI-tree/accessibility/tool privileges;
- normalized action plus executed coordinates or structured target;
- model calls, input/output tokens, actions and wall-clock time;
- critic/verifier/recovery events and their next executed action;
- official evaluator result and terminal-state evidence;
- teardown/reset result and infrastructure classification.

The normalized post-hoc audit must compute exact-action runs of length at least
3 and 10, feedback followed by action change, feedback followed by exact action
repeat, rejected finish claims, and the first broken failure-chain edge.

## 7. Fairness and contamination rules

1. A task failure is never rerun merely to improve a score.
2. Infrastructure reruns are capped, linked to the original attempt, and kept.
3. No Hard trajectory may be used to tune an arm and later be relabelled
   held-out.
4. Framework-specific task hints, golden action sequences, and evaluator access
   are forbidden.
5. Native-system model and observation advantages are disclosed, not hidden by
   one headline success-rate column.
6. The old frozen results and the pre-existing dirty r79 worktree are immutable.
7. An Android adaptation of a desktop/different-benchmark system is labelled a
   mechanism port, not an exact reproduction.

## 8. Interpretation rules

- Non-zero task success is task-level evidence only under the official
  evaluator.
- Lower loop frequency with zero task success is process improvement, not task
  completion.
- An all-zero success table does not prove systems are equivalent; process
  metrics and uncertainty remain necessary.
- Cross-system native-configuration differences are descriptive, not a causal
  estimate of memory, verification, or reflection.
- A same-backbone result is interpretable only if the framework's official
  semantics survive the adapter.

## 9. Decision requested from GPT Pro

GPT Pro must either approve or rewrite the exact arm set, lane membership,
fresh seeds, privilege separation, model revisions, and expansion rule. It must
also identify any major public AndroidWorld system omitted from the candidate
ledger and reject any candidate that cannot be reproduced honestly within the
available time and hardware.
