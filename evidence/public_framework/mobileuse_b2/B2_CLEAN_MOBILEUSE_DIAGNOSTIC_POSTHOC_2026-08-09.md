# B2 Clean MobileUse diagnostic post-hoc

## 1. Bottom line

The frozen five-task B2 diagnostic is a **negative capability result but a positive diagnostic and engineering result**.

- All 5/5 requested episodes completed with valid AndroidWorld evaluator lifecycles; there were no implementation, infrastructure, or hash-chain errors.
- B2 retained H08 full success and H14 partial reward, repaired the H12 upstream `None`-action crash, and reduced auxiliary-role overhead to 326 total model requests for 157 Operator decisions (2.076 requests/decision).
- Total reward was 1.5, below the preregistered expansion threshold of 2.0. The frozen directive is therefore `do_not_expand_preserve_diagnostic`.
- H05 is additionally **causally confounded**: the matched PF01 episode opened Markor's new-file dialog with `.md`, whereas B2 opened it with `.txt`, despite identical task parameters. The nominal score remains part of the frozen suite, but the H05 regression cannot be attributed to B2.
- The remaining failures do not support the claim that “more reflection” is sufficient. The first-broken edges are more specific: exact-value retention (H01), reflection-to-action coupling and action affordance (H12), and task-state truth binding (H14).

## 2. Frozen boundary

- arm: `B2_CLEAN_MOBILEUSE_QWEN3VL32B_AW_HARD_DEV_S20260806_V1`;
- suite: `b2_diagnostic_20260809T193415_e28d6b3c`;
- model: `Qwen/Qwen3-VL-32B-Instruct`;
- revision: `0cfaf48183f594c314753d30a4c4974bc75f3ccb`;
- AndroidWorld seed: `20260806`;
- model sampling seed: `3407`;
- sampling: temperature 0.7, top-p 0.8, top-k 20, presence penalty 1.5, repetition penalty 1.0;
- frozen controller commit: `d3a50d8cd9592eacf1a16deecd6c25d7de55655e`;
- smoke passed before the five-task diagnostic; the post-smoke source and protocol hashes are recorded in `B2_FREEZE_AFTER_SMOKE.json`.

No prompt, controller, threshold, task order, action budget, or sampling parameter was changed after the smoke freeze.

## 3. Frozen result and expansion gate

| Task | Reward | Valid | Native actions | Operator decisions | Model requests | Frozen interpretation |
|---|---:|---:|---:|---:|---:|---|
| H12 RecipeAddMultipleRecipesFromMarkor2 | 0.0 | yes | 60 | 60 | 119 | robustness repaired, capability still failed |
| H08 OsmAndMarker | 1.0 | yes | 8 | 9 | 22 | PF01 full success retained |
| H05 MarkorCreateNoteAndSms | 0.0 | yes | 18 | 18 | 40 | nominal failure; causal comparison confounded by Markor state |
| H01 BrowserMultiply | 0.0 | yes | 19 | 20 | false success after value-history overwrite |
| H14 RetroSavePlaylist | 0.5 | yes | 49 | 50 | export half passed; playlist contents failed |
| **Total** | **1.5** | **5/5** | **154** | **157** | **326** | **do not expand** |

The gate passed six checks: five valid episodes, H08 retained, at most one false success, no hash-chain errors, no implementation/infrastructure errors, and at most 2.4 requests per decision. It failed the single capability check `reward_at_least_2`. The gate is therefore failed even though the engineering checks passed.

## 4. Fair efficiency comparison

The cleanest task-level comparison excludes H05 because its initial Markor state differs and excludes H12 because PF01 crashed before producing a valid result. On the remaining matched, uncontaminated H01/H08/H14 tasks:

| Metric | PF01 MobileUse | B2 Clean | Change |
|---|---:|---:|---:|
| Total reward | 1.5 | 1.5 | unchanged |
| Model requests | 239 | 167 | -30.13% |
| Operator decisions | 75 | 79 | +5.33% |
| Requests per decision | 3.187 | 2.114 | -33.67% |

B2 therefore demonstrates a real **cost/stability improvement without a capability improvement** on the causally clean subset. H14 alone retained reward 0.5 while reducing requests from 160 to 92 (-42.5%). This is useful, but it is not evidence that B2 is a stronger task-solving method.

## 5. Layered failure diagnosis

### 5.1 H01: the model saw the values, but its free-text history rewrote them

The actual value sequence was 1, 8, 10, 7 and 2, whose product is 1120. The Operator saw these values at the relevant screens, but later progress text repeatedly reset the click count and compressed the historical list. It finally entered 120 and declared success. PF01 failed the same task with a different hallucinated list and product 1512.

This is not primarily an OCR failure. The values were individually available to the model. The failure occurred when an exact, append-only sequence was stored and updated as natural-language narrative. A useful intervention would need an externally checked typed register such as `observed_values`, `click_count` and `product`, rather than another paragraph reminding the model to remember carefully.

### 5.2 H12: the critic detected the loop, but could not bind recovery to the next action

B2 located one qualifying recipe in Markor. It then requested unsupported `long_press` actions 13 times; the adapter rejected them and requested repairs. The run subsequently degenerated into repeated taps and more than 40 swipes, never opened Broccoli, and exhausted the 60-action budget.

The Reflector and TrajectoryReflector repeatedly identified “no progress” and “meaninglessly repeating”. Thus the missing component was not failure detection. The feedback remained advisory prose: it neither prohibited the failed action family nor supplied an executable alternative. B2 fixed the PF01 crash and converted H12 from implementation-invalid to scientifically valid, but did not improve task reward.

This case also exposes an action-affordance ceiling. The frozen action protocol supported click, swipe, type, system button and terminate, but not long-press or clear-text. A memory comparison cannot be interpreted cleanly when the controller cannot express a recovery action the task naturally invites.

### 5.3 H14: local progress claims were not bound to the task predicate

The AndroidWorld evaluator gives half credit for the playlist contents and half for the exported file. B2 received 0.5. The trajectory showed the playlist `Metal Mayhem375` existed and the export path was created, but the playlist screen still contained `0 Songs`. Free-text progress nevertheless alternated between claiming the songs had been added and acknowledging that the playlist was empty.

The failure is therefore not “forgot to finish” in the abstract. The system stored an operation-level belief (“I clicked something related to adding a song”) as a task-state fact (“the song is now in this playlist”) without verifying the destination container. Reflection did not maintain one authoritative truth source across roles.

### 5.4 H05: the nominal regression is not a valid method comparison

Both PF01 and B2 used the same task-parameter hash, but the initial new-note dialog differed:

- PF01 snapshots 5 and 6: default extension `.md`;
- B2 snapshots 5 and 6: default extension `.txt`.

B2 ran H12 before H05. H12 opened `recipes.txt`, and the AndroidWorld setup log indicated that no Markor snapshot was restored. The most plausible explanation is cross-task preference carryover. Under `.txt`, B2 spent the entire 18-action budget trying to edit the extension; under `.md`, PF01 created the note and reached the SMS app, earning 0.5.

The evidence establishes initial-state inequality; the causal explanation is an inference rather than a randomized intervention. Consequently:

1. the frozen B2 reward remains 1.5 and the gate remains failed;
2. H05 cannot be cited as evidence that B2 regressed;
3. future matched runs must reset or fingerprint application preferences, not merely compare task names, seeds and parameter hashes;
4. an automated `scientifically_valid=true` flag is insufficient if it does not test initial-state equivalence.

## 6. What B2 actually teaches us

B2 rules out one tempting explanation: the PF01 limitations were not mainly caused by excessive auxiliary-role calls or the H12 exception. Cleaning role scheduling and exception handling made the system cheaper and stable, but did not cross the capability gate.

The trajectories separate three different memory/control failures:

1. **exact state retention** — H01 lost an append-only numeric sequence;
2. **feedback-to-policy enforcement** — H12 detected failure but repeated an equivalent action;
3. **state-to-predicate binding** — H14 treated an attempted action as proof that the destination object changed.

This distinction matters because one generic “better memory” module is unlikely to solve all three. The next method should be justified against a measured layer and should expose typed, machine-checkable state rather than add more free-text reflection.

## 7. Legal next step

The preregistered directive forbids expanding B2 to the full Hard suite. The next legal work is offline and developmental:

1. preserve this diagnostic and its failed gate;
2. add an initial-state equivalence audit for task-relevant application preferences and visible UI state;
3. freeze a new matched diagnostic only after the contamination boundary is specified;
4. if a new intervention is attempted, target one explicit mechanism edge—for example an append-only exact-value register plus a binding completion check—rather than silently adding multiple rescue rules;
5. do not tune on these five episodes and later describe the same task instances as held-out evidence.

## 8. Evidence integrity

The raw suite remains under the git-ignored `runs/` tree. The principal SHA-256 digests are:

| Artifact | SHA-256 |
|---|---|
| B2 aggregate | `494bf7b3d5166528faf6c5de75c0f35206323cc65b39e5d18a6d25132e1d5d0d` |
| B2 expansion gate | `21d815ee3a8ff3f75ed0d0aa37773e5660daab4e2b9afd3e267f60e68bffc2cd` |
| H01 events | `a4d67df5b3920a26ba1c028b40c478728b112bf4bdc621d4323f5db563ddfff8` |
| H05 events | `54f0f4f270455ee1ac6ceb4221aa42c6e5bc03e5fe671835d09852281feb795d` |
| H08 events | `9874dd5413f5ae6a11710327423ce124efa64678245f261d76f9414d59032bb6` |
| H12 events | `9cc9a504564514f9271c6889831a877c0c227be71cae17d44fa4e61bd99e9928` |
| H14 events | `6b423e8ea4bce236979d22cbdc506ea68b1bbea01bb8a48a2304fd3b57012ef1` |
| PF01 H05 snapshot 5/6 (`.md`) | `fd97746e3bd0e2fbad8c4b224428598d36e252b215bf9da5b56d6b86af603939` |
| B2 H05 snapshot 5/6 (`.txt`) | `cfb3cb8f9b1386fc84d53d78e19b95096e11825adb57c1e73d9e032ddfbd2c33` |

This report is post-hoc mechanism analysis. It does not alter the frozen evaluator outputs, preregistration, or expansion decision.
