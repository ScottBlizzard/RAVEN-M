# EEST-AC v0.2.2 Measurement Contract v2 Amendment Audit

Status: frozen before any v0.2.2 generation call. This is the only permitted settling-window revision in this round.

## Preserved v1 batch

- Verbatim report: `reports/eest_ac/eest_ac_v0_2_2_measurement_contract_v1_failed.json`
- Report SHA-256: `36c17f82f972bbf3574d49e0f194f9161bab1316cea75eee6cac886e5ab58e16`
- Model generation calls: `0`
- Live-evidence eligibility: `false`

| Scene | Raw transition canonical SHA-256 | v1 result | Frozen interpretation |
|---|---|---|---|
| stable_positive_settings_scroll | `471c0c6f4e1832b0c70e987ce1f5719c1c3dabe2560056ebe35094783237d5ba` | rejected: `terminal_pixels_unsettled` | The page and a11y changed and the last two a11y hashes agreed, but sample 3 still contained pixel-level scrollbar fade. Three samples were insufficient for the exact screenshot-hash definition. |
| dynamic_negative_camera | `fa00cb591fd5669826fc270b4070384a589b4bfa60b8af21f523d9b939a3be02` | correctly rejected: `terminal_pixels_unsettled` | Dynamic preview frames must remain a negative under v2. |
| a11y_missing_negative_notification_shade | `d537c182c15d0b86a3866339e06258f8374a2b7558e132451e5d2f30768313af` | incorrectly accepted as stable no-op | The gesture began at normalized `y=0.01`, did not enter the system shade, and left the Dialer state unchanged. It did not instantiate the intended missing-a11y negative. |

The preserved state-signature sequences are:

- Settings: `d2eaf48c460b6a619ad6482514adcf80fb4f431a4e120986a5e09f794c6c3231`, `764d0e8de633e56e81e8477ef2dad6a9482a10a6bebad5d16f3887ce4fcc7d02`, `ff3cb5236d094137c03321f6316f47d0dbe1cb9a6192d4fb10b4ba310d9c41b7`.
- Camera: `31deb4dc1de620be5d9781ac1d9552cbe83de3e3aa4c088c3512d26683f4a5ff`, `8bbf6b9b65272a0d0e142b4d51f9fff33004a3e7b5662adce392e108b726758b`, `618fdc97e583b2353511627a8257552f079849bfbe3a9967423ccb2c5a312eab`.
- Notification negative attempt: `d9086ed9eb87dadc2146c3e751b7ec7117cbae9fa8334b52d491b623981bf553` twice.

## One-time v2 definition

After an action, capture exactly four bounded observations: one immediate sample followed by three samples at one-second intervals. The terminal window is the final two samples. A stable required change exists only if both terminal samples have a11y, their screenshot SHA-256, a11y SHA-256, and package-name sets agree exactly, and the terminal state signature differs from the pre-action signature. There is no fallback or adaptive extension.

The missing-a11y negative starts at the true screen top edge (`y=0.0`). This changes only the development measurement scene; it does not add a production task/App/coordinate branch.

## One-shot stopping rule

The v2 three-scene batch is rerun once, in full, after this contract is committed and tagged. It must accept the Settings scroll and reject both the dynamic Camera and missing-a11y negative. The frozen 5038 route must also pass its stress audit. Any failure produces a measurement/infrastructure-floor `FAIL`, forbids a third window definition, and forbids all live probes in this round.
