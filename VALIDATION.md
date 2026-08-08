# Decision-packet validation

Validation date: 2026-08-08 (Asia/Hong_Kong)

This repository snapshot was curated specifically for the next GPT Pro decision: selecting the first public framework to reproduce on the frozen Qwen3-VL-32B AndroidWorld Hard setup.

## Automated checks

- Implementation regression tests: **49 passed**.
  - Scope: `implementation/tests/official_qwen_mobile` and `implementation/tests/models/test_vllm_client.py`.
  - Import path: `implementation/src;implementation/runtime`.
- Decision-document relative links: **8 checked, 0 broken**.
- JSON syntax: **20 files checked, 0 invalid**.
- Secret-pattern scan: **0 hits** for common API-token, GitHub-token, AWS-key, private-key, password-assignment, and bearer-token patterns.
- Curated snapshot size: **141 files, 2,432,809 bytes**, excluding Git worktree metadata.
- Large raw episode directories are intentionally excluded; the compact evidence tables, aggregate JSON, protocols, diagnostic reports, and executable analysis/runner code needed for the decision are included.

## Provenance and safety

- The latest official-Qwen baseline and diagnostic artifacts were copied from the working research tree without modifying their contents.
- The original dirty research worktree at `D:\ZJU\Summer_Camp\RAVEN-M-Research` was not cleaned, reset, or deleted.
- Historical repository content removed from the new default snapshot remains recoverable through Git history.
- Earlier GPT analyses and the author-written formal report are intentionally excluded from the current decision snapshot to prevent anchoring; they must not be consulted through Git history for this decision.
- Frozen reports may contain their original local paths. Use the path-redirect table in `ARTIFACT_MANIFEST.md` to locate their curated equivalents.
- Some frozen Markdown reports intentionally retain two trailing spaces for Markdown line breaks. These produce `git diff --check` whitespace notices but are preserved to avoid changing evidence artifacts; the new root decision documents were checked separately.

## Empirical anchor checked into this snapshot

- 19 AndroidWorld Hard task classes × 3 seeds = 57 eligible episodes.
- 7/57 successes overall; the first seed is 4/19 and is the frozen one-seed baseline for the next comparison.
- 1,175 model calls/actions with complete L0–L5 diagnostics.
- 21 false-success declarations, 39 repeated-action episodes, and 14 stagnation episodes.
- Model revision and backend identity are frozen in the included reports and preregistration artifacts.
