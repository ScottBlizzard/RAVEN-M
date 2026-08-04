# Role-Binding Timing Phase B2 — Fresh Snapshot/Oracle Collection Qualification v0.2

Status: preregistered collection qualification only

Parent commit: `99b342563061c9bb4bebbb72aa80ba91f4fa7a23`

## Claim boundary

Phase B2 asks only whether a frozen, model-free collector can create at least eight fresh matched base families whose PNG, raw accessibility tree, pairing metadata, and target oracle pass one preregistered qualification. `generation_eligible` remains `false`. A pass means only `ELIGIBLE_FOR_PHASE_C_PREREGISTRATION`; it does not authorize a pilot and supports no timing, role-binding, memory, controller, or task-efficacy claim.

There are zero model-generation calls, zero experimental cells, and no model-assisted selection, annotation, repair, or qualification. Phase A/B files, the v0.1 snapshot manifest/lock, EEST/rXX artifacts, the formal LaTeX report, and the three protected legacy WIP files remain immutable.

## Structural definition of a base family

A base family is a distinct combination of task semantics, destination application, destination UI/layout, and destination widget family. Changing names or values within the same list template does not create a new family. The pool is invalid if it contains fewer than eight families, fewer than four applications, fewer than four destination layout/widget families, or more than two families from one application.

The frozen v0.2 pool contains exactly eight structurally distinct list-selection families in eight AndroidWorld applications:

1. Contacts contact-row selection to update a destination contact;
2. Markor note-row selection to append a retrieved code;
3. Files document-row selection to move a retrieved file value;
4. Tasks task-row selection to update a destination task note;
5. Simple Calendar event-block selection to update a destination event location;
6. Pro Expense expense-row selection to update a destination expense amount;
7. Broccoli recipe-card selection to add a retrieved ingredient;
8. Simple SMS conversation-row selection to send a retrieved code.

Each family has matched `high` and `low` role-ambiguity states with identical task text, source/destination aliases, fact field/value, destination item, app version, geometry, and reset policy. The high state contains source and destination entities as competing instances of the same widget family. The low state contains the same destination entity but omits the source entity; a deterministic non-entity control supplies a negative target candidate. Synthetic labels and values are frozen in the collection config and were not copied from prior traces.

If an installed app cannot produce the preregistered state, that family is excluded and B2 returns `NOT_ELIGIBLE`. No Contacts duplication, layout relabeling, or replacement family is permitted.

## Infrastructure and reset boundary

- Official ADB SHA-256: `957e46b8615f7af5b7292a2ddabe98d2e61940c3fb2b0545756507f080613e71`.
- ADB server port `5038`, serial `emulator-5554`, and no fallback to `5037`.
- Client/server hashes, serial, Android build, app package/version, screen geometry, density, orientation, and foreground package/activity are recorded.
- The pre-freeze audit observed a connected transport but missing Android `package`, `window`, and `activity` services. Exactly one project-AVD cold restart is permitted before candidate collection. It must launch `AndroidWorldAvd` with `ANDROID_ADB_SERVER_PORT=5038`, `-port 5554`, `-no-snapshot`, and no visible window. If framework services remain absent, collection stops before the first candidate.
- Every variant begins from home, clears only the scene's preregistered storage, verifies the reset invariant, seeds either destination-only (`low`) or source-plus-destination (`high`), launches the named app, performs only exact-text or structural-selector navigation, and records each setup command/result.
- After each variant, the app is force-stopped, scene storage is cleared, and the reset invariant is rechecked. Generic first-launch onboarding may be dismissed before the pool with exact visible selectors and is recorded.

## Same-stable-frame capture

Each variant receives three samples separated by 0.75 seconds. A sample is bracketed as screenshot-before, raw `uiautomator` XML, screenshot-after. A variant is stable only when screenshot-before equals screenshot-after in every bracket, the selected screenshot hash is identical across all three brackets, canonical accessibility semantics are identical across all three XML dumps, and package/activity/geometry/orientation remain constant. The frozen PNG and raw XML come from the third accepted bracket; every raw bracket hash is retained.

## Oracle and independent checkability

The deterministic parser resolves each frozen exact item label once in raw XML and requires exactly one enabled clickable ancestor. The ancestor's structural XPath, resource ID, class, text/content-description anchor, and bounds form the selector evidence. High states require distinct source and destination ancestors in the same frozen widget family. Low states require destination once and source zero times. A non-entity candidate is selected deterministically from the first visible enabled clickable node, ordered by bounds and structural XPath, that is not an ancestor/descendant of the destination row and has a nonempty text, content description, or resource ID.

Target aliases must be unique A–H; entity aliases must be distinct E1–E8. The destination widget ID is the frozen destination target alias. The rationale records exact XML anchors, XPath, bounds, competing candidates, and why the destination is correct. It is reproducible from only the PNG, XML, family spec, and parser.

## Freshness and contamination

All candidates are captured after the protocol-freeze commit under `05_project/artifacts/role_binding_timing/phase_b2_v0_2`. EEST, H17/rXX, P1/P2/N2, Phase-A screenshots, and prior run screenshots are reference-only. The eight Phase-A DEV PNG hashes form an explicit denylist. Selected PNG and raw XML hashes must be unique across all sixteen variants, and candidate artifact paths must remain inside the new B2 root.

## Freeze, one-shot qualification, and stop rule

The collector writes raw artifacts, a complete candidate manifest, and a pool lock containing every artifact hash before qualification. Candidate order, labels, setup, artifacts, and oracle annotations become immutable at this point. The qualifier runs exactly once over the full pool and retains every exclusion reason.

A family qualifies only if both variants pass schema, frozen-hash, fresh-path, denylist, same-frame stability, reset, package/activity, geometry, semantic pairing, exact oracle resolution, ambiguity manipulation, alias, and corpus-uniqueness checks. The family qualification rate is qualified families divided by eight. PASS requires exactly 8/8 complete families, at least 4 apps, at least 4 widget/layout families, no app above 2 families, at least 95% family qualification, zero generation calls, exactly one qualification record, and internally consistent cost/reset/hash accounting.

Any failure yields `NOT_ELIGIBLE`; the first broken edge and all exclusions are reported. No same-version recapture, code adjustment, candidate replacement, or diversity relaxation is allowed. After PASS or FAIL, stop without Phase C, a model call, an 8-family pilot, or Destination-First Binding Gate work.
