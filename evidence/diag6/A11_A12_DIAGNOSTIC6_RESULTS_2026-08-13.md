# A11 and A12 Enriched Six-Task Diagnostic Results

Date: 2026-08-13 (Asia/Hong_Kong)

These are post-hoc diagnostic results. They do not repair the failed formal A11
offline replay or A12's `A12_PROTOCOL_INVALID` verdict, and they are not held-out
evidence.

## A11 CRC-ECOBF

- Suite: `official_qwen_20260813T151055_b8d6faee`
- Completion: 6 valid episodes; 1 infrastructure-invalid attempt, resolved by a
  fresh `OsmAndTrack` replacement
- Full successes: 2/6; reward sum: 2.0
- Model calls: 128; executed actions: 122; transport maximum: 1
- Total tokens: 489,910; valid elapsed time: 3,147.675261 seconds
- Actual non-empty reads: 4, in two failed episodes
- Productive-divergence signals: 0

The successful tasks were `RecipeDeleteMultipleRecipesWithConstraint` and
`RetroSavePlaylist`; both were memory-silent. A11's generic top-level
`memory_active_episode_count=0` is a known aggregation-schema error: A11 stores
its read evidence under nested mechanism records. The causal audit recovered all
four exact reads. Correcting that count does not change the scientific result:
all read-active episodes failed and no read met the productive-divergence test.

| Task | Reward | Calls | Actions | Reads | Tokens |
|---|---:|---:|---:|---:|---:|
| OsmAndTrack | 0 | 25 | 24 | 2 | 97,494 |
| RecipeAddMultipleRecipesFromImage | 0 | 34 | 33 | 2 | 132,580 |
| RecipeAddMultipleRecipesFromMarkor | 0 | 15 | 14 | 0 | 55,350 |
| RecipeDeleteMultipleRecipesWithConstraint | 1 | 19 | 18 | 0 | 71,200 |
| RetroSavePlaylist | 1 | 25 | 24 | 0 | 96,581 |
| SaveCopyOfReceiptTaskEval | 0 | 10 | 9 | 0 | 36,705 |

- Aggregate SHA-256: `57A6380BADDEF7FE753451343121595AF87D7F8476EFEADAA4D7E5B517D1C49D`
- Checkpoint SHA-256: `C3EA4BF771C6A783FE7360161A1A8F856692DF3FA98C8E788971D275A07016F5`

## A12 MADM

- Suite: `official_qwen_20260813T172341_41d3d7e4`
- Completion: 6 valid episodes; 0 infrastructure-invalid attempts
- Full successes: 1/6; reward sum: 1.0
- Model calls: 158; executed actions: 154; transport maximum: 1
- Total tokens: 629,936; valid elapsed time: 4,131.601948 seconds
- Actual non-empty reads: 3, in two failed episodes
- Productive-divergence signals: 0

The only successful task was `RetroSavePlaylist`, which was memory-silent. The
three reads occurred in `RecipeAddMultipleRecipesFromImage` and
`RecipeAddMultipleRecipesFromMarkor`; both failed. The generic top-level read
count is zero, but the arm-native episode records and causal audit agree on three
actual reads.

| Task | Reward | Calls | Actions | Reads | Tokens |
|---|---:|---:|---:|---:|---:|
| OsmAndTrack | 0 | 27 | 27 | 0 | 105,775 |
| RecipeAddMultipleRecipesFromImage | 0 | 60 | 60 | 2 | 256,374 |
| RecipeAddMultipleRecipesFromMarkor | 0 | 19 | 18 | 1 | 71,209 |
| RecipeDeleteMultipleRecipesWithConstraint | 0 | 16 | 15 | 0 | 59,510 |
| RetroSavePlaylist | 1 | 25 | 24 | 0 | 96,583 |
| SaveCopyOfReceiptTaskEval | 0 | 11 | 10 | 0 | 40,485 |

- Aggregate SHA-256: `018D17C6CB08B45097DA5A0E9D81F7EB73E5C9DED5484C9BA13D79EFCE44D826`
- Checkpoint SHA-256: `0B2FEF36088C85766EDDE22F0438CFE5BD743C7AE008E4CF2FB41F855FED2E14`

## Joint interpretation

A10-v2, A11, and A12 all activated on some enriched diagnostic episodes, but
none produced a preregistered productive-divergence signal. Across A11 and A12,
every read-active episode failed and every success was memory-silent. The live
diagnostic therefore supports the narrow conclusion that these trigger/state
designs can inject memory, but provides no causal evidence that their injected
memory improved task behavior.
