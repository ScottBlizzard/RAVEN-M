# A10-v2 Enriched Six-Task Diagnostic Result

Date: 2026-08-13 (Asia/Hong_Kong)

This is a post-hoc diagnostic result. It does not repair the failed formal
A10-v2 offline replay, authorize the formal arm, or constitute held-out evidence.

## Frozen outcome

- Suite: `official_qwen_20260813T134227_fcb420cf`
- Valid episodes: 6; infrastructure-invalid episodes: 0
- Full successes: 2/6; reward sum: 2.0
- Model calls: 221; executed actions: 218
- Total tokens: 944,736
- Elapsed time: 5,186.05 seconds
- Episodes with an actual non-empty memory read: 3/6
- Actual non-empty reads: 6
- Productive divergence signals: 0
- Scientific label: `activation_without_productive_divergence_signal`

The two successful tasks, `RecipeDeleteMultipleRecipesWithConstraint` and
`RetroSavePlaylist`, had no non-empty memory read. The three episodes with
non-empty reads all failed. Therefore the 2/6 score must not be attributed to
the memory mechanism.

| Task | Reward | Calls | Actions | Reads |
|---|---:|---:|---:|---:|
| OsmAndTrack | 0 | 86 | 86 | 2 |
| ImageDescriptionRetrieval | 0 | 60 | 60 | 2 |
| MarkorCreateNoteAndSms | 0 | 16 | 15 | 0 |
| RecipeDeleteMultipleRecipesWithConstraint | 1 | 18 | 17 | 0 |
| RetroSavePlaylist | 1 | 25 | 24 | 0 |
| ReceiptAddMultiple | 0 | 16 | 16 | 2 |

The large raw suite remains local under ignored `runs/`.

- Aggregate SHA-256: `9BA72D1A60E6BEBD98191B7B569FD4F020676021B1E1A0E05BAA359722BEC929`
- Checkpoint SHA-256: `298C6A57AEEE9AE583EF9562CAF7935A012005C41ADAE5A87D730E5A42690E28`
