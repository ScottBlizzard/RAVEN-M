# R15 + three Pro candidate pipeline result (2026-08-18)

## Outcome

The four-direction pipeline is complete. No new candidate passed its own
zero-generation G0, so no seven-task live run was scientifically authorized.
This is a completed negative qualification campaign, not four `0/7` results.

| System / direction | Evidence level | 7-task result | 19-task result | Activation / use | Decision |
|---|---|---:|---:|---|---|
| A1-R2 | formal scored reference | not rerun | 6/19, reward 6.5 | compact pending ledger active | best complete pure-memory parent |
| SYS-NAG V4 | formal scored composite reference | historical protocol | 6/19, reward 6.5 | 4 route blocks, 0 new successes | preserved R2; no gain |
| R15 target-first | formal one-task diagnostic | Browser 1/1 only | not a suite | EVR render/read 0 | unattributed; no R15-derived arm |
| R15-derived pure-memory candidate | forensic G0 | NOT RUN | NOT RUN | no reusable primitive | NO-GO |
| P1 failure recovery / TCRA-R2 | zero-generation G0 | NOT RUN | NOT RUN | detector covers 6 failures but fires twice in successful Calendar | PREFLIGHT_INVALID_NO_LIVE |
| P2 long-horizon / SYS-SCOPE-R2 | zero-generation G0 | NOT RUN | NOT RUN | 12 midpoint opportunities; semantic labels unavailable | PREFLIGHT_INVALID_NO_LIVE |
| P3 outcome judgment / R2-SCER | zero-generation G0 | NOT RUN | NOT RUN | T2 exposes all 6 successes; visible-only labels unavailable | PREFLIGHT_INVALID_NO_LIVE |

## Why no seven-task run was skipped

The fixed non-fail-fast seven-task requirement applies to candidates that pass
G0 and can produce scientifically valid live evidence. None did:

- R15 forensics found no reusable, task-independent primitive and explicitly
  rejected parser patch continuation.
- P1 violated its own success-negative-control gate before generation.
- P2 requires two independent blinded semantic reviewers; none exists.
- P3's raw suite is now complete, but its independent visible-only annotation
  and false-reject reference is absent. It exposes every R2 success at T2, so
  bypassing that reference would be especially unsafe.

Calling the GPU anyway would turn protocol-invalid systems into uninterpretable
numbers. `PREFLIGHT_INVALID_NO_LIVE` is not `0/7`, and no task was selectively
skipped after a valid G0.

## Most credible scientific conclusions

1. **Positive:** R2's compact pending ledger remains the only complete pure
   memory parent with a positive full-suite result: 6/19, reward 6.5, 0 paired
   losses versus A1.
2. **Positive but limited:** R15 proves that BrowserMultiply can succeed in a
   formal target-first episode, and gives a valuable successful trace for
   diagnosis.
3. **Attribution boundary:** R15 retained only `[8,2]`; EVR never rendered or
   read. Its success therefore cannot be credited to EVR or stitched with R2
   as a 7/19 system.
4. **Composite evidence:** SYS-NAG V4 preserves 6/19 and costs fewer calls than
   R2, but its four active route blocks create no new success. Activation is
   not benefit.
5. **Recovery lesson:** a plausible recurrence detector can cover several
   failures and still hit a successful task. Offline success counterexamples
   are essential.
6. **Coordination/judgment lesson:** semantic constructs cannot be validated by
   trajectory length, RGB change, final reward, or the same model's prose.
   Independent event-time labels are missing infrastructure, not an optional
   nicety.

## Summer-camp reporting value

This campaign supports a coherent research story rather than “nothing worked”:

- establish a strong compact-memory parent;
- show that parser accretion and complex memory state do not reliably improve
  task success;
- demonstrate why activation, local action divergence, and final reward must
  be separated;
- use success-path counterexamples to reject an apparently broad recovery
  detector before wasting GPU;
- expose the methodological bottleneck for planner/judge components: obtaining
  independent, event-time semantic labels without evaluator leakage;
- preserve every negative qualification result instead of hiding it as an
  unreported failed run.

## Integrity

Machine-readable summary:
`evidence/candidate_pipeline/CANDIDATE_PIPELINE_RESULT_2026-08-18.json`

Canonical content SHA-256:
`f158b875018e618ad2d793a4bf9171944dd33b2c59f6f5fb43c7e5bb1671a737`

All three raw Pro documents remain byte-for-byte committed as unvalidated
blueprints under `design_reviews/pro_candidates/2026-08-15/`.
