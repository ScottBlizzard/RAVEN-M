# Top-3 GPT Pro Implementation-Ready Output Contract

> Superseded before any Pro output was accepted. This requirement was judged
> overly prescriptive. New conversations must use
> `TOP3_COMPLETE_DESIGN_OUTLINE_REQUIREMENTS_2026-08-15.md` instead.

Date: 2026-08-15

Purpose: every Open V2 Pro response must be detailed enough for an implementation agent to build, test, preregister, and qualify the selected system without inventing scientific decisions. “Detailed” means decision-complete and auditable, not merely long.

This contract does not force a critic, planner, verifier, trigger, parent arm, or auxiliary-call count. Those remain open design choices. It applies only after the Pro has independently selected one final recommendation.

## Required document structure

### 1. Executive design decision

- Exact final system name and short identifier.
- One-sentence research hypothesis.
- One recommended design only.
- Explicit verdict on the investigator's initial hypothesis: retained, modified, replaced, or rejected.
- Why this design dominates the alternatives considered.

### 2. Commit-pinned evidence audit

- Repository, branch, commit, and every cited path.
- Tables separating committed facts, derived measurements, interpretations, and unknowns.
- Evidence level for every A-series result used.
- Missing raw evidence and the exact zero-generation materialization needed.
- No unsupported corpus counts or trace claims.

### 3. Cross-task problem analysis

- Frozen unit of analysis and classifier definitions.
- Prevalence in successful versus failed tasks.
- At least three candidate failure mechanisms, counterexamples, and rejection rationale.
- Why the selected problem requires the proposed component rather than more memory text or generic extra inference.

### 4. Scientific identity and immutability boundary

- Proposed mechanism ID, experiment ID, arm/config/result/checkpoint schemas, CLI name, artifact namespace, and parent evidence commit.
- Exact parent implementation and permitted delta.
- Historical files/evidence that must remain byte-immutable.
- Version-bump rules for any later change.

### 5. Runtime architecture

- Complete event sequence from screenshot acquisition through executor/auxiliary calls, action execution, observation, state update, and next request.
- Role ownership and authority.
- Inputs visible to every component and explicitly forbidden inputs.
- A sequence diagram or equivalent ordered table.
- Behavior on terminal calls, invalid model output, transport error, missing screenshot, parse error, and environment error.

### 6. Complete state and artifact schemas

- Every resident record with field name, type, enum, units, default, bounds, provenance, and eviction/expiry.
- Global counters and audit records.
- Stable ID/hash construction and canonical serialization.
- JSON examples for config, replay report, source freeze, preflight, launch intent, live receipt, checkpoint, episode audit, and final result.
- `additionalProperties` policy and fail-closed validation rules.

### 7. Exact algorithms

- Initialization/reset.
- Deterministic feature extraction.
- Trigger/router logic, if any.
- State update and invalidation.
- Auxiliary-call preparation and response validation, if any.
- Executor-context rendering/injection.
- Post-intervention causal audit.
- Capacity enforcement and eviction.
- Pseudocode detailed enough to translate line-by-line, including ordering and off-by-one conventions.

### 8. Exact prompts and rendering

- Full system/user prompt text for every new role, with placeholders and escaping rules.
- Exact injected executor text.
- Generic active-control, shadow, or ablation prompt text.
- Parser grammar, allowed values, rejection and sanitization.
- Character, UTF-8 byte, tokenizer-token, call, latency, and episode-total limits.
- No “prompt to be decided during implementation.”

### 9. Resource and latency budget

- Executor and auxiliary calls counted separately and combined.
- Per-call and per-episode input/output token limits.
- Expected and hard maximum GPU seconds, CPU time, resident memory, serialized audit size, and wall time.
- Retry policy and whether a proposal consumes a native decision slot.
- Comparison with A0, A1, and A1-R2 envelopes.

### 10. Minimal repository integration blueprint

- Every file to add, modify, or preserve.
- Exact module, class, function, CLI flag, config, contract, factory, controller hook, wrapper, evidence, and test names.
- Function signatures and return schemas.
- Which shared code changes are unavoidable and how older arms remain reproducible.
- Source-freeze closure as an explicit finite file list, not “all relevant files.”
- No actual multi-file code output is required, but no integration decision may be deferred.

### 11. Test and adversarial matrix

- Unit tests for every state transition, threshold boundary, expiry, cap, one-shot, cooldown, and parser case.
- Controller fake-client integration tests proving exact call count, exact injected text/hash, and no forbidden action control.
- Leakage and task/app-whitelist tests.
- Hidden metadata invariance.
- Capacity maximum-state construction rather than average-state tests.
- Crash/resume, receipt cross-arm rejection, non-finite reward, single transport, and invalid-replacement tests.
- Named test files and test functions.

### 12. Zero-generation offline qualification

- Raw materialization manifest and provenance validation.
- Independent classifier or reference-segment construction.
- Frozen gates with numerator, denominator, deadlines, opportunity definition, and expected failure taxonomy.
- Replay must not self-certify using its own output labels.
- `generation_calls=0` enforcement.
- Exact preflight order and pass/fail status schema.

### 13. Server qualification and live execution

- Start-server and qualification flow.
- Model realpath/manifest, package versions, PID/cmdline, endpoint model IDs, timestamps, source/preflight hashes, and fresh receipt binding.
- Fixed task order and capability-release gates.
- Scientific failure versus infrastructure-invalid taxonomy.
- Resume rules, append-only/hash-linked checkpoints, replacement limits, and no rerun of valid episodes.

### 14. Controls and causal attribution

- No-component base.
- Appropriate resource-matched active control when extra computation is used.
- Mechanism-specific ablation.
- Exact opportunity matching and divergence definition.
- Visible progress and relapse windows.
- Treatment of silent successes and unmatched trajectories.
- Conditions under which benefit is attributed only to additional compute rather than the specialized component.

### 15. Final result and verdict formulas

- Per-task result fields and aggregate formulas.
- Pairwise comparison against A0/A1/A1-R2 where applicable.
- Independent accuracy, cost, and component-causality verdicts.
- Closure checks, artifact hashes, invalid-attempt linkage, and result immutability.
- Human-readable interpretation for every verdict combination.

### 16. Falsification and no-hot-fix policy

- Results that reject the design at offline, first-task, preservation-gate, full-suite, cost, and causal levels.
- Changes forbidden after any generation call.
- Which changes require a new experiment identity/version.
- Explicit stop conditions; no post-hoc threshold relaxation.

### 17. Implementation and review checklist

- Ordered, dependency-aware checklist from evidence materialization to final result.
- For each item: input, output artifact, acceptance test, and blocking failure.
- A final “no unresolved scientific decisions” table. Any unresolved item must be classified as either an empirical preflight measurement with a frozen decision rule or a blocker that prevents implementation/live work.

## Quality bar

The response fails this contract if it contains phrases such as “choose an appropriate threshold,” “implementation can decide,” “use a suitable prompt,” or “add tests as needed” for behavior-affecting decisions.

The response also fails if it is detailed but silently chooses facts not available in the repository. Unknown evidence must remain unknown until a specified zero-generation audit resolves it.

Passing this output contract means the document is ready for implementation and independent review. It does **not** itself authorize GPU generation: source implementation, tests, independent audits, offline replay, preflight, and a fresh live receipt must still pass.
