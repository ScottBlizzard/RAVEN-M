# EEST-AC v0.2.3 Claim-Evidence Verdict

Overall: **`FAIL_COLLECTION / measurement-infrastructure floor`**. No held-out oracle evaluation occurred, so eligibility for a separate live oracle qualification is **false**.

| ID | Final verdict | Evidence | Claim boundary |
|---|---|---|---|
| O-C1 | PASS, offline candidate only | Single contract, generated schema, parser/oracle tests; focused suite 116/116. | No held-out or live qualification. |
| O-C2 | NOT TESTED held-out | Contaminated DEV replay directionally accepts semantic transitions without exact pixels. | DEV evidence cannot establish the claim. |
| O-C3 | NOT QUALIFIED | Property/DEV pixel-only controls reject directionally. | No false-accept rate can be reported without held-out traces. |
| O-C4 | NOT QUALIFIED | Missing/contradictory evidence property tests pass. | Held-out false-accept evidence is absent. |
| O-C5 | FAIL prerequisite | The definitive collector rerun wrote raw records but no valid completion or corpus manifest. | Per-held-out-row provenance does not exist. |
| O-C6 | FAIL | Held-out traces 0; evaluations 0; exact matrix metrics not computable. | Not eligible for live oracle qualification. |
| O-C7 | PASS | All nine replay rows and all collector attempts are DEV-contaminated/ineligible. | None contributes to PASS. |
| O-C8 | PASS | v0.2.2 remains FAIL and its artifacts were not rewritten. | No retroactive relabelling. |

Stopping evidence:

- definitive DEV rerun collection record: `4583af1cabdbf8684165d1f210f04219b95bec096cfe70d28704174a52aee2b2`;
- definitive stderr: `847f37008c2949239c2e2dd405429759f291e2038c5f2a6356f2fc5fe5219d8f`;
- `ground_truth_qualification_pass=false` because the pre critical semantic evidence was unavailable;
- cleanup failed because the frozen 5038 reverse listener was absent;
- `collection_complete.json` absent;
- generation calls 0, held-out rows 0, held-out evaluations 0.
