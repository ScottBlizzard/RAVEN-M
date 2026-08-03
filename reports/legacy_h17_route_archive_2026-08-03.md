# Legacy H17 Route Archive

Date: 2026-08-03  
Purpose: recovery-only preservation of the discontinued H17/rXX development route before starting the independent evidence-state research line.

## Frozen boundary

- Last completed reproducible legacy result: tag `protocol-v2-2-r78-h17-stopped`.
- Frozen result commit: `0327603a772f1ba923483f299b13bd53ca2983da`.
- Current audited HEAD: `0173df45e64b5bca7da782d7c9ff6e8cf0f16840`.
- The current HEAD is a descendant of the r78 stop commit and adds only the independent research-audit document.
- No r79 or r80 live suite, preflight, package, report, or scored result exists.
- No relevant experiment or pytest process was running at archive time.

## Preserved unfinished r79 working tree

These files belong exclusively to the discontinued H17-specific route. They are not part of the new method and must not be used as efficacy evidence.

| Working-tree file | Legacy purpose | SHA-256 |
|---|---|---|
| `05_project/src/raven_m/controller/episode_controller.py` | compact a critic-constraint repair prompt observed in r78 | `fc0e82e0fde90119365d4f685f080eb4519bf2f602e4bda58de5d4809a40fe33` |
| `05_project/src/raven_m/controller/protocol_v2_guard.py` | expose controller-observed date-row y-centres after the r78 H17 failure | `ff89d6b70be4b4738646d262beb67d7b7e932e9eb95956d940b1c5000a999d10` |
| `05_project/tests/scripts/test_protocol_v2_2_r79_r78_trace_replay.py` | replay the same H17/r78 coordinate and prompt failures | `5bb1f1e3de673a1072cfee62938b761a62fd69c187d5eadf54bc46b115a3fd0a` |

The two tracked modifications contain 62 added lines in total. The third file is untracked. None is silently committed into the active research line, reset, deleted, or overwritten.

## Recovery objects

- Recovery-only tracked snapshot commit: `a5a20af1a9292e5ba7e435be4b2cdba8ec989a7a`.
- Annotated recovery tag: `legacy-h17-r79-wip-tracked-archive-20260803`.
- Standalone Git blob for the untracked replay test: `1fd4c480ec3858b36438d2df9c4f23d7f4c394ec`.

The tracked snapshot was created with `git stash create`, which wrote an unreachable-style recovery commit without applying a stash or changing the worktree/index. The annotated tag makes that object durable. The untracked test was stored as a Git blob without changing the file.

Recovery commands, to be used only on a separate branch or worktree:

```powershell
git switch -c recover-legacy-h17-r79 legacy-h17-r79-wip-tracked-archive-20260803
git show 1fd4c480ec3858b36438d2df9c4f23d7f4c394ec > 05_project/tests/scripts/test_protocol_v2_2_r79_r78_trace_replay.py
```

The second command is documentation only; normal development must continue to preserve the existing working-tree copy rather than reconstructing it in place.

## Validation state at archive time

- The new r79 replay test passed 6/6 locally.
- The focused affected-controller regression chain passed.
- A full legacy test run reached 100% and had one failure: the frozen r78 manifest correctly detected that legacy controller source bytes no longer matched the r78 source commit. This is expected for uncommitted r79 work and is not evidence for the new research method.
- No r79 model call was made and no r79 live smoke was launched.

## Contamination and exclusion manifest

The following are permanently excluded from new-method efficacy claims:

- H17 / `SportsTrackerActivitiesOnDate`;
- seed `20260730` used in the r61-r78 chain;
- the repeatedly inspected OpenTracks date-row layout;
- target-date row-centre logic and date-list repair patterns;
- H17 field crops, row identities, routed evidence, prompts, and replay fixtures;
- every rule added in the unfinished r79 working tree described above.

They may be used only for retrospective analysis, legacy regression, and motivation.

## New-line boundary

The new research line must use an independent source namespace, experiment ID family, configuration family, report directory, and run directory. It must not import the legacy H17 guard, use H17-derived coordinates or date-row patterns, or alter protocol-v1 and frozen B0-B3/M0 artifacts. The old working-tree changes remain visible and recoverable but are outside the new execution path.
