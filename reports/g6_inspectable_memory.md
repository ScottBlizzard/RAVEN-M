# G6 inspectable-memory gate

Status: **passed**

G6 is a non-Hard engineering gate. It does not contain or imply an
AndroidWorld Hard result.

## Evidence

- The complete project test suite passes 54 tests; the G6-focused
  memory/history/role/schema subset passes 43 tests.
- Core representations are fixed FIFO working memory, verified episodic facts,
  failure/recovery items, and episode-local page hints.
- Append-only event replay reconstructs byte-equivalent ordered state.
- Cross-episode reads and writes are rejected.
- Every persistent item carries observation/action IDs and screenshot paths
  with SHA-256 verification.
- Decision-time model deltas are bound to the pre-action screenshot; only the
  deterministic loop detector binds evidence to the post-action screenshot.
- Page-local items are invalidated after the transition and before the next
  retrieval. Stale, contradicted, revoked, superseded, and archived items can
  never route as FACT.
- Twenty deterministic corruption fixtures cover stale facts, contradictions,
  unverified wrong-page hints, and wrong-page failure transfer. All 20 were
  rejected as FACT.

Machine-readable evidence:

- `05_project/metadata/g6_audit.json`
- `05_project/metadata/corruption_stress.json`

## Scope decision

Cross-episode procedural memory remains optional and excluded from the core
protocol. This avoids Hard-trajectory reuse and keeps the contribution focused
on auditable episode-local reliability and harm measurement.
