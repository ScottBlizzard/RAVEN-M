# Official Qwen3-VL-32B Full Hard: deterministic snapshot

- Scientifically eligible: 57/57
- Complete: True
- Logged terminal records: 102
- Excluded audit records: 45
- Infrastructure-invalid records: 40
- Implementation-invalid records: 5
- Success: 7/57
- Success rate over completed episodes: 0.123
- Positive reward episodes: 9
- Partial reward episodes: 2
- Total / mean reward: 8.000 / 0.140
- Eligible model calls: 1175
- All logged model calls: 1285
- Episode wall time: 471.9 min
- False success claims: 21
- Repeated-state episodes: 39
- Stagnation episodes: 14
- Nearly unchanged actions: 385
- Protocol errors: 4
- Execution failures: 0

## Per task class

| Task | Completed | Success | Mean reward | Seeds | Rewards | Calls | Consistency |
|---|---:|---:|---:|---|---|---|---|
| BrowserMultiply | 3 | 0 | 0.000 | 20260806, 20260807, 20260808 | 0.000, 0.000, 0.000 | 13, 16, 22 | all_failure |
| ExpenseAddMultipleFromGallery | 3 | 0 | 0.000 | 20260806, 20260807, 20260808 | 0.000, 0.000, 0.000 | 16, 25, 19 | all_failure |
| ExpenseAddMultipleFromMarkor | 3 | 0 | 0.000 | 20260806, 20260807, 20260808 | 0.000, 0.000, 0.000 | 13, 7, 5 | all_failure |
| ExpenseDeleteMultiple2 | 3 | 2 | 0.667 | 20260806, 20260807, 20260808 | 1.000, 1.000, 0.000 | 18, 22, 34 | mixed |
| MarkorCreateNoteAndSms | 3 | 0 | 0.333 | 20260806, 20260807, 20260808 | 0.500, 0.500, 0.000 | 17, 18, 18 | all_failure |
| MarkorMergeNotes | 3 | 0 | 0.000 | 20260806, 20260807, 20260808 | 0.000, 0.000, 0.000 | 32, 29, 34 | all_failure |
| MarkorTranscribeVideo | 3 | 0 | 0.000 | 20260806, 20260807, 20260808 | 0.000, 0.000, 0.000 | 20, 20, 20 | all_failure |
| OsmAndMarker | 3 | 0 | 0.000 | 20260806, 20260807, 20260808 | 0.000, 0.000, 0.000 | 11, 10, 20 | all_failure |
| OsmAndTrack | 3 | 0 | 0.000 | 20260806, 20260807, 20260808 | 0.000, 0.000, 0.000 | 19, 42, 120 | all_failure |
| RecipeAddMultipleRecipesFromImage | 3 | 0 | 0.000 | 20260806, 20260807, 20260808 | 0.000, 0.000, 0.000 | 60, 60, 17 | all_failure |
| RecipeAddMultipleRecipesFromMarkor | 3 | 0 | 0.000 | 20260806, 20260807, 20260808 | 0.000, 0.000, 0.000 | 13, 11, 16 | all_failure |
| RecipeAddMultipleRecipesFromMarkor2 | 3 | 0 | 0.000 | 20260806, 20260807, 20260808 | 0.000, 0.000, 0.000 | 14, 6, 31 | all_failure |
| RecipeDeleteMultipleRecipesWithConstraint | 3 | 0 | 0.000 | 20260806, 20260807, 20260808 | 0.000, 0.000, 0.000 | 15, 11, 17 | all_failure |
| RetroSavePlaylist | 3 | 1 | 0.333 | 20260806, 20260807, 20260808 | 1.000, 0.000, 0.000 | 32, 41, 50 | mixed |
| SaveCopyOfReceiptTaskEval | 3 | 0 | 0.000 | 20260806, 20260807, 20260808 | 0.000, 0.000, 0.000 | 10, 10, 16 | all_failure |
| SimpleCalendarAddOneEvent | 3 | 3 | 1.000 | 20260806, 20260807, 20260808 | 1.000, 1.000, 1.000 | 17, 28, 19 | all_success |
| SportsTrackerActivitiesOnDate | 3 | 0 | 0.000 | 20260806, 20260807, 20260808 | 0.000, 0.000, 0.000 | 3, 9, 4 | all_failure |
| SportsTrackerTotalDistanceForCategoryOverInterval | 3 | 0 | 0.000 | 20260806, 20260807, 20260808 | 0.000, 0.000, 0.000 | 3, 5, 5 | all_failure |
| SportsTrackerTotalDurationForCategoryThisWeek | 3 | 1 | 0.333 | 20260806, 20260807, 20260808 | 1.000, 0.000, 0.000 | 3, 5, 4 | mixed |

## Completed episodes

| Episode | Reward | Calls | Termination | False success | Repeated UI | Stagnant run |
|---|---:|---:|---|---:|---:|---:|
| BrowserMultiply_20260806_3e2fd311 | 0.000 | 13 | model_answer | 0 | 4 | 1 |
| BrowserMultiply_20260807_9c7f16f4 | 0.000 | 16 | model_answer | 0 | 4 | 3 |
| BrowserMultiply_20260808_92030d8d | 0.000 | 22 | max_steps | 0 | 6 | 4 |
| ExpenseAddMultipleFromGallery_20260806_5a3bfad4 | 0.000 | 16 | model_terminate_success | 1 | 4 | 3 |
| ExpenseAddMultipleFromGallery_20260807_069ed75c | 0.000 | 25 | model_terminate_success | 1 | 5 | 1 |
| ExpenseAddMultipleFromGallery_20260808_eb8948c8 | 0.000 | 19 | model_terminate_success | 1 | 4 | 1 |
| ExpenseAddMultipleFromMarkor_20260806_705f23ab | 0.000 | 13 | model_terminate_success | 1 | 3 | 0 |
| ExpenseAddMultipleFromMarkor_20260807_c0274114 | 0.000 | 7 | model_answer | 0 | 3 | 0 |
| ExpenseAddMultipleFromMarkor_20260808_ae263c2e | 0.000 | 5 | model_answer | 0 | 2 | 1 |
| ExpenseDeleteMultiple2_20260806_0eeb0637 | 1.000 | 18 | model_terminate_success | 0 | 3 | 0 |
| ExpenseDeleteMultiple2_20260807_aa213b88 | 1.000 | 22 | model_terminate_success | 0 | 3 | 1 |
| ExpenseDeleteMultiple2_20260808_ab84a7fb | 0.000 | 34 | max_steps | 0 | 27 | 27 |
| MarkorCreateNoteAndSms_20260806_91f6e017 | 0.500 | 17 | model_terminate_success | 1 | 2 | 0 |
| MarkorCreateNoteAndSms_20260807_2d37a9c4 | 0.500 | 18 | max_steps | 0 | 3 | 2 |
| MarkorCreateNoteAndSms_20260808_1ce37f83 | 0.000 | 18 | max_steps | 0 | 4 | 1 |
| MarkorMergeNotes_20260806_4b24e296 | 0.000 | 32 | model_terminate_success | 1 | 6 | 1 |
| MarkorMergeNotes_20260807_fda66380 | 0.000 | 29 | model_terminate_success | 1 | 5 | 3 |
| MarkorMergeNotes_20260808_ad779c36 | 0.000 | 34 | model_terminate_success | 1 | 12 | 7 |
| MarkorTranscribeVideo_20260806_f19368f3 | 0.000 | 20 | max_steps | 0 | 9 | 1 |
| MarkorTranscribeVideo_20260807_26bb3d42 | 0.000 | 20 | max_steps | 0 | 5 | 1 |
| MarkorTranscribeVideo_20260808_5092435b | 0.000 | 20 | max_steps | 0 | 5 | 2 |
| OsmAndMarker_20260806_2f730163 | 0.000 | 11 | model_terminate_success | 1 | 2 | 0 |
| OsmAndMarker_20260807_601d96bd | 0.000 | 10 | model_terminate_success | 1 | 3 | 0 |
| OsmAndMarker_20260808_876e6a1b | 0.000 | 20 | max_steps | 0 | 7 | 7 |
| OsmAndTrack_20260806_d883cd01 | 0.000 | 19 | model_terminate_failure | 0 | 5 | 4 |
| OsmAndTrack_20260807_a8d3c6c0 | 0.000 | 42 | model_terminate_success | 1 | 6 | 1 |
| OsmAndTrack_20260808_df8b4a93 | 0.000 | 120 | max_steps | 0 | 72 | 72 |
| RecipeAddMultipleRecipesFromImage_20260806_a68f8831 | 0.000 | 60 | max_steps | 0 | 58 | 58 |
| RecipeAddMultipleRecipesFromImage_20260807_4e182688 | 0.000 | 60 | max_steps | 0 | 57 | 57 |
| RecipeAddMultipleRecipesFromImage_20260808_095486f8 | 0.000 | 17 | model_terminate_success | 1 | 3 | 1 |
| RecipeAddMultipleRecipesFromMarkor_20260806_d7fd8f16 | 0.000 | 13 | official_output_invalid | 0 | 2 | 0 |
| RecipeAddMultipleRecipesFromMarkor_20260807_c5b10928 | 0.000 | 11 | model_terminate_success | 1 | 3 | 0 |
| RecipeAddMultipleRecipesFromMarkor_20260808_01d70cc1 | 0.000 | 16 | official_output_invalid | 0 | 4 | 1 |
| RecipeAddMultipleRecipesFromMarkor2_20260806_b77e9af2 | 0.000 | 14 | model_terminate_success | 1 | 3 | 0 |
| RecipeAddMultipleRecipesFromMarkor2_20260807_6d7a1b36 | 0.000 | 6 | model_answer | 0 | 2 | 1 |
| RecipeAddMultipleRecipesFromMarkor2_20260808_fdb1faf3 | 0.000 | 31 | model_terminate_success | 1 | 4 | 1 |
| RecipeDeleteMultipleRecipesWithConstraint_20260806_ad293d85 | 0.000 | 15 | model_terminate_success | 1 | 2 | 0 |
| RecipeDeleteMultipleRecipesWithConstraint_20260807_7fbc3224 | 0.000 | 11 | model_terminate_success | 1 | 2 | 1 |
| RecipeDeleteMultipleRecipesWithConstraint_20260808_b0195b2f | 0.000 | 17 | model_terminate_success | 1 | 3 | 1 |
| RetroSavePlaylist_20260806_c44b826d | 1.000 | 32 | model_terminate_success | 0 | 9 | 1 |
| RetroSavePlaylist_20260807_3cf9ee3a | 0.000 | 41 | model_terminate_success | 1 | 8 | 1 |
| RetroSavePlaylist_20260808_3c3b848a | 0.000 | 50 | max_steps | 0 | 9 | 1 |
| SaveCopyOfReceiptTaskEval_20260806_d1d528de | 0.000 | 10 | model_terminate_success | 1 | 2 | 0 |
| SaveCopyOfReceiptTaskEval_20260807_76acc287 | 0.000 | 10 | model_terminate_success | 1 | 2 | 1 |
| SaveCopyOfReceiptTaskEval_20260808_05e0fc0e | 0.000 | 16 | max_steps | 0 | 3 | 2 |
| SimpleCalendarAddOneEvent_20260806_739e8ebf | 1.000 | 17 | model_terminate_success | 0 | 2 | 0 |
| SimpleCalendarAddOneEvent_20260807_2b8acc6f | 1.000 | 28 | model_terminate_success | 0 | 4 | 1 |
| SimpleCalendarAddOneEvent_20260808_4d895cc4 | 1.000 | 19 | model_terminate_success | 0 | 2 | 0 |
| SportsTrackerActivitiesOnDate_20260806_fdbba51c | 0.000 | 3 | model_answer | 0 | 1 | 1 |
| SportsTrackerActivitiesOnDate_20260807_4adf34a4 | 0.000 | 9 | official_output_invalid | 0 | 3 | 1 |
| SportsTrackerActivitiesOnDate_20260808_52f5c59f | 0.000 | 4 | official_output_invalid | 0 | 2 | 0 |
| SportsTrackerTotalDistanceForCategoryOverInterval_20260806_6fba2c5e | 0.000 | 3 | model_answer | 0 | 1 | 1 |
| SportsTrackerTotalDistanceForCategoryOverInterval_20260807_3abf6055 | 0.000 | 5 | model_answer | 0 | 3 | 1 |
| SportsTrackerTotalDistanceForCategoryOverInterval_20260808_0bbabe86 | 0.000 | 5 | model_answer | 0 | 2 | 1 |
| SportsTrackerTotalDurationForCategoryThisWeek_20260806_a575f564 | 1.000 | 3 | model_answer | 0 | 1 | 1 |
| SportsTrackerTotalDurationForCategoryThisWeek_20260807_abe1efa7 | 0.000 | 5 | model_answer | 0 | 2 | 1 |
| SportsTrackerTotalDurationForCategoryThisWeek_20260808_16e33d39 | 0.000 | 4 | model_answer | 0 | 2 | 0 |

In progress: none

## Infrastructure-invalid audit records (excluded from science)

- BrowserMultiply_20260807_4443f081
- BrowserMultiply_20260808_e89d5a37
- ExpenseAddMultipleFromGallery_20260807_97c8b274
- ExpenseAddMultipleFromGallery_20260808_18ac727e
- ExpenseAddMultipleFromMarkor_20260807_99bfcb04
- ExpenseAddMultipleFromMarkor_20260808_62c95c9c
- ExpenseDeleteMultiple2_20260807_e3e69078
- ExpenseDeleteMultiple2_20260808_19b46de8
- MarkorCreateNoteAndSms_20260807_7a54ebc2
- MarkorCreateNoteAndSms_20260808_0714ff34
- MarkorMergeNotes_20260807_87037e31
- MarkorMergeNotes_20260808_fa849241
- MarkorTranscribeVideo_20260807_5b48b4e6
- MarkorTranscribeVideo_20260808_afec15a3
- OsmAndMarker_20260807_b4912198
- OsmAndMarker_20260808_513e94d1
- OsmAndTrack_20260807_604b5ee5
- OsmAndTrack_20260808_8930ba35
- RecipeAddMultipleRecipesFromImage_20260807_7a86916b
- RecipeAddMultipleRecipesFromImage_20260808_673e6f17
- RecipeAddMultipleRecipesFromMarkor2_20260807_4ea2110b
- RecipeAddMultipleRecipesFromMarkor2_20260808_596cb248
- RecipeAddMultipleRecipesFromMarkor_20260807_12f4144e
- RecipeAddMultipleRecipesFromMarkor_20260808_f0811cfc
- RecipeDeleteMultipleRecipesWithConstraint_20260807_ad3433b2
- RecipeDeleteMultipleRecipesWithConstraint_20260808_07c93a0e
- RetroSavePlaylist_20260807_3adb5bef
- RetroSavePlaylist_20260808_fe7a1b86
- SaveCopyOfReceiptTaskEval_20260807_ff36531b
- SaveCopyOfReceiptTaskEval_20260808_87f28a56
- SimpleCalendarAddOneEvent_20260807_c2b24222
- SimpleCalendarAddOneEvent_20260808_4eecf7bd
- SportsTrackerActivitiesOnDate_20260807_96768591
- SportsTrackerActivitiesOnDate_20260808_5a877b47
- SportsTrackerTotalDistanceForCategoryOverInterval_20260807_ed8fcb2d
- SportsTrackerTotalDistanceForCategoryOverInterval_20260808_cb2f8695
- SportsTrackerTotalDurationForCategoryThisWeek_20260807_976b9f3b
- SportsTrackerTotalDurationForCategoryThisWeek_20260808_f7e9458b
- RetroSavePlaylist_20260807_eceddac6
- RetroSavePlaylist_20260808_378e13b2

## Implementation-invalid audit records (excluded from science)

- ExpenseAddMultipleFromMarkor_20260807_d600ca2c
- MarkorMergeNotes_20260808_14a2d58d
- MarkorTranscribeVideo_20260807_fac6007a
- OsmAndTrack_20260807_adcf6eaa
- RecipeAddMultipleRecipesFromMarkor2_20260808_5319e66f
