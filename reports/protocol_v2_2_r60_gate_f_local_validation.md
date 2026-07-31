# Protocol-v2.2 r60 Gate-F local validation

Date: 2026-07-31  
Decision: **local formal package passed; live preflight not yet run**

The r60 formal package preserves all twelve frozen Gate-F cells, their order,
seeds, variants, budgets, thresholds, and three isolated four-cell batches.
The formal wrapper uses a fresh suite namespace and refuses development-smoke
mode.

The prerequisite audit now checks more than the candidate report hash. It also
requires the exact non-scored H01 B3 success semantics and independently
rehashes all 13 cited raw artifacts. The immutable r56 Gate-E prerequisite is
still checked separately.

## Validation

- Focused r56/r60 and legacy Gate-F tests: **25/25 passed**.
- Complete project suite: **456/456 passed**.
- Protocol-v1 breadth seal: **197/197 files**, zero failures.
- Python compilation and `git diff --check`: passed.
- Formal r60 suite directory: absent.
- Model calls and GPU experiment cells in this phase: zero.

The next permitted action is to commit and tag this execution package, then run
one live zero-call preflight. A formal Batch 1 may not start from this local
result alone.
