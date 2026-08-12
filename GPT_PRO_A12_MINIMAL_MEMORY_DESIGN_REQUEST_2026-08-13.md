# GPT Pro Request: A12 Minimal Standalone Memory Design

Date: 2026-08-13  
Repository: <https://github.com/ScottBlizzard/RAVEN-M>  
Branch: `a2-verified-progress-audit-20260810`  
Evidence parent commit: `5009034fa050d2f065e4eb08ff1c8c394a0ac586`

## Your role and sole deliverable

You are continuing the design review of RAVEN-M after A10-v2 and A11 were
implemented and independently audited. Read the current repository rather than
relying on the earlier conversation. Produce exactly one Markdown document:

`GPT_PRO_A12_MINIMAL_ACTION_DIVERGENCE_MEMORY_DESIGN_2026-08-13.md`

Do not edit code, emit patches, launch experiments, or split the answer across
multiple files. The document must be sufficiently deterministic that a separate
implementation team can implement and audit it without inventing behavioral
rules.

Do not promise that A12 will beat the baseline. Give an explicit `GO` or `NO-GO`
recommendation. If your scientific conclusion is that no standalone A-class
memory can reasonably improve this controller under the stated constraints,
say so and explain the falsifying evidence. If you recommend `GO`, design the
smallest credible prospective arm.

## Mandatory repository reading

At minimum, inspect:

- `HANDOFF_2026-08-12.md`
- `GPT_PRO_A10_V2_STANDALONE_MEMORY_DESIGN_2026-08-12.md`
- `GPT_PRO_A11_STANDALONE_MEMORY_DESIGN_2026-08-12.md`
- `protocols/A10_V2_EMOBF_IMPLEMENTATION_BINDING_2026-08-12.md`
- `protocols/A11_CRC_ECOBF_IMPLEMENTATION_BINDING_2026-08-12.md`
- `implementation/src/raven_m/official_qwen_mobile/a10_v2_obligation_branch_frontier.py`
- `implementation/src/raven_m/official_qwen_mobile/a11_confirmed_route_contraction.py`
- `implementation/scripts/replay_a10_v2_offline_traces.py`
- `implementation/scripts/replay_a11_offline_traces.py`
- `evidence/a10_v2/A10_V2_OFFLINE_REPLAY_REPORT.json`
- `evidence/a11/A11_OFFLINE_REPLAY_REPORT.json`
- the A0/A1/A6/A8-v2/A9 episode evidence referenced by the handoff and replay
  manifests
- the shared controller, runner, working-memory interface, contracts, and tests

Do not treat unit-test success as mechanism evidence. Recompute or spot-check
important report claims directly from materialized traces where needed.

## Current facts that your design must explain

The best completed paired result remains A1: 5/19 with reward 5.5, versus A0:
4/19 with reward 4.5. A1 is positive but substantially more expensive. A6 is a
complete 0/19 negative control. A7 is 4/19 and does not add a new success.

A10-v2 and A11 pass their software tests but fail zero-generation qualification:

- A10-v2 verifies 27 episodes and 1,668 frozen files totaling 442,138,413
  bytes, with zero generation calls. Under the current strict replay it has
  23 qualifying A6 reference segments but 0 timely eligible reads and 0 T1/T2
  timely segments. It also fails the A9 exposure/kind gate.
- A11 verifies the same materialized corpus with zero generation calls. Under
  the current conservative strict branch-pair replay it qualifies 5/23 A6
  segments (21.739%), far below the required 20/23. It also fails the A8-v2
  Expense and A9 Retro independent-segment gates. On competent histories it is
  sparse (one nonempty read, density 0.014925, 346 rendered characters), so its
  failure is principally low recall/timing rather than uncontrolled injection.
- Both formal no-GPU preflights correctly stop at failed real offline replay.
  Neither arm is authorized for live generation.

Previous checker versions inflated apparent qualification by counting candidate
creation without proving a mature, eligible, correctly bound read inside the
segment. Your protocol must make this class of false pass impossible.

The central tension is therefore empirical: permissive memory fires often and
pollutes competent behavior; evidence-heavy memory becomes precise but fires too
late or almost never. A12 must address this tension directly, not disguise it
with a larger state machine.

## Scientific objective

Determine whether a minimal, high-recall, action-divergence memory can preserve
A0 competence while helping the controller escape immediately repeated
no-progress actions. The initial hypothesis to evaluate is:

> On the same visible page, after the same canonical action family has produced
> no material visible progress twice, a short one-shot reminder of the failed
> action and an instruction to try a different action family or target is more
> useful than route reconstruction, long-lived obligation graphs, or general
> task summaries.

You may reject or refine this hypothesis, but any added trigger class must be
justified by frozen trace evidence and an ablation. Do not simply merge A10-v2
and A11.

## Non-negotiable A-class boundary

A12 must remain directly comparable with A0/A1:

- same Qwen3-VL-32B model revision, task instances, seed `20260806`, port/model
  seed `3407`, sampling parameters, native max steps, action schema, system
  prompt, emulator setup, and fixed task order;
- controller-authored memory only, using visible RGB observations and already
  executed actions;
- no additional model call, planner, critic, verifier, reflection pass, tool,
  hidden UI tree, accessibility hierarchy, evaluator state, reward, future
  observation, task/page whitelist, action guard, action override, retry policy,
  or early termination;
- memory may only add bounded text to the existing controller context;
- one fresh memory instance per episode and exactly one transport attempt per
  model step;
- no mechanism declaration that the task succeeded or failed;
- bounded resident state, audit, reads, rendered characters, and tokens;
- frozen A0/A1 and previous-arm evidence must never be overwritten.

Use the same seed as A0. A new seed would destroy the intended paired control.

## Simplicity and cost target

Prefer one primary trigger family plus cancellation/expiry rules. Avoid global
route graphs, multi-phase obligation models, broad query parsing, and five-way
trigger taxonomies unless you demonstrate that each additional part is necessary
on frozen traces.

Set and justify explicit limits. The preferred operating envelope is:

- at most 100 rendered tokens and 240 visible characters per nonempty read;
- at most 5 nonempty reads and 500 rendered memory tokens per episode;
- one-shot delivery for a matched failure signature, with a short global
  cooldown;
- immediate invalidation on material visible progress or loss of the bound
  screen/action context;
- audit JSON at most 128 KiB and resident-state delta at most 2 MiB;
- zero extra generation calls.

If you exceed an envelope, provide the exact evidence and ablation that warrants
it. Complexity must be counted explicitly: state records, trigger classes,
thresholds, regexes, persistent bytes, rendered tokens, and expected runtime.

## Required design content

Your one document must contain:

1. A concise causal diagnosis of A1, A6, A8-v2, A9, A10-v2, and A11, separating
   low recall, false positive injection, stale context, prompt burden, and lack
   of causal action divergence.
2. A `GO` or `NO-GO` decision for A12 and the evidence supporting it.
3. If `GO`, one precise causal thesis and the minimal trigger/read/cancel state
   machine. Freeze all terms: screen equivalence, canonical action family,
   material progress, repeat count, timing window, eligibility, cooldown,
   one-shot signature, eviction, and rendered text.
4. Exact schemas and capacity limits for every persistent and audit record.
5. Deterministic pseudocode for `reset`, `read`, `observe`, serialization, and
   post-read causal auditing. State ordering and off-by-one semantics must be
   explicit.
6. An anti-leakage and A-class equivalence proof, including dynamic tests that
   mutate hidden/evaluator metadata and demonstrate identical behavior.
7. An implementation file map with unique A12 mechanism, experiment, config,
   replay, preflight, receipt, checkpoint, and result identities. Do not modify
   or relabel historical A10-v2/A11 artifacts.
8. A minimal unit/adversarial/integration test manifest, including maximum legal
   simultaneous-state serialization rather than filling only one capacity axis.
9. A zero-generation replay protocol, a live four-task gate, and an exact
   terminal decision rule for whether the remaining fifteen tasks may run.
10. A cost comparison against A0 and A1 and an ablation plan that can attribute
    any gain to memory rather than extra computation or unrelated controller
    changes.

## Replay and causal-evidence requirements

Do not derive a reference segment from A12's own output and then use it to prove
A12. Freeze independent segment identities before running the arm. At minimum,
reuse and verify the 23 A6 reference segments used by the current qualification,
and define independent A8-v2 Expense and A9 Retro segments.

Every claimed qualified segment must bind all required fields, including episode,
segment lower and upper step bounds, source frontier/screen descriptor, branch or
action family, phase/mask if the design uses them, maturity step, eligibility at
read time, actual nonempty read step, read signature, and expiry. A candidate
created before a segment, on another frontier, after its deadline, or never
delivered is not a qualified read.

The offline corpus never received A12 text. Therefore historical next actions
cannot prove that the new text causally changed model behavior. Keep two claims
separate:

- offline qualification may establish trigger recall, precision, timing,
  boundedness, and the existence of an actionable alternative;
- only prospective live episodes can establish that the rendered memory caused
  useful action divergence and improved reward/success.

Define a prospective post-read causal audit without using reward or evaluator
state to choose actions. It should at least record whether the next action truly
differs from the failed canonical family/target, whether visible progress follows
within a frozen horizon, and whether the controller immediately returns to the
same failed behavior. Do not count a nonempty read itself as benefit.

## Minimum gates to evaluate and refine

These are starting scientific constraints, not permission to weaken the test
until an arm passes:

- A6 failure-segment availability: at least 20/23 independently frozen segments
  receive a timely mature eligible read.
- A0 preservation histories: no more than 2 total nonempty reads across the four
  competent histories, zero anti-leakage violations, and no broad navigation
  reminder.
- A8-v2 Expense and A9 Retro: independently bound timing/precision checks, not
  merely “some candidate exists in the episode.”
- all capacity, cooldown, one-shot, source-freeze, manifest-hash, tokenizer,
  no-generation, no-retry, and transport checks pass before live startup.
- live preservation gate: run the same four A0-success tasks first, in frozen
  order, requiring 4/4 valid successes before any of the remaining fifteen.
- if the four-task gate passes only because A12 stays silent, classify it as
  preservation evidence, not improvement evidence.

Propose a preregistered full-suite superiority criterion that is honest about the
small sample. The project target is to exceed both A0 (4/19, reward 4.5) and A1
(5/19, reward 5.5), while remaining materially cheaper than A1. Explain what can
and cannot be inferred from one 19-task paired run.

## Protocol closure requirements

Avoid the defects found in earlier protocols:

- no source-freeze self-reference to a report that contains its own hash or
  implementation commit;
- no preflight/receipt field-name mismatch;
- no receipt reuse across arms or processes;
- no resume across mechanism/experiment/config/source-freeze identities;
- only infrastructure-invalid episodes may be replaced, with bidirectional
  linkage; scientific failures are terminal;
- formal replay reports must bind the exact current mechanism and replay source
  hashes;
- source closure must list exact files and tests, not “all A12 tests”;
- any behavior-changing change after formal replay requires a new version and a
  fresh replay, preflight, and receipt.

End the document with: (a) the smallest implementable A12 definition, (b) a
pre-GPU checklist, (c) the exact four-task and 19-task stop rules, (d) expected
token/time overhead, and (e) the strongest reason A12 may still fail.
