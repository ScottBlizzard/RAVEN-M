# INFRA-M3 external-log maintenance result

## Verdict

`FAIL_TERMINAL_ACCOUNTING`. The frozen M3 run is not a valid maintenance qualification and was not retried.

The external-log correction did prevent another old-artifact mutation, and the new emulator produced a bounded live signal for exclusive 5038 registration through boot. However, the runner then failed to write its required terminal completion record because it called a nonexistent helper (`M1.write_json_atomic`). With no completion record, the in-memory runtime edge between boot readiness and framework setup is unrecoverable. Under the frozen stop rule, burn-in, a11y, and v0.3 preparation all remain unqualified.

## What is directly supported

- Protocol-freeze commit/tag: `2086166b4f0e18325045d67865cf17a3dddc589f` / `role-binding-timing-infra-m3-freeze-20260805`.
- Residual project 5038 was stopped; a fresh server started as PID 32988.
- The exact AVD launched as PID 38304 with qemu PID 6648.
- All eight boot snapshots showed no 5037 listener. Attempt 8 showed `emulator-5554` through 5038, `get-state=device`, and `sys.boot_completed=1`.
- The last complete gate was boot readiness. There are zero framework artifacts, zero burn-in cycles, zero Settings observations, and zero grid cells.
- Terminal cleanup commands were issued; the emulator, 5038 server, and ports 5037/5038/5554/5555/8554 are now absent. Unknown PIDs 11316 and 17716 were not targeted.
- Live emulator logs were written to a fresh OS-temporary directory outside the repository. The legacy M1 log remained exactly 9,590 bytes with SHA-256 `ffddf9d…`.
- After runner termination, Windows Restart Manager showed no remaining owner for either external log. The logs were then sealed once into the M3 result root and the temporary root removed. This postmortem cleanup is evidence preservation, not a runner PASS.
- Model-generation calls: 0. Held-out captures: 0.

## Failure chain

| Stage | Result | Evidence boundary |
|---|---|---|
| Pre-run frozen lock and offline gates | PASS | 8/8 focused tests; namespace passed; full regression retained only the known r79 manifest conflict. |
| External live-log routing | PASS as a mechanism observation | Emulator stdout/stderr existed only below the OS temporary root while processes were live; the old frozen log did not change. |
| Exclusive 5038 launch and boot | Bounded PASS signal | Fresh 5038/launcher/qemu identities, no 5037, and boot attempt 8 passed. |
| Framework readiness | NOT COMPUTABLE | No framework artifact was written. The in-memory edge was lost when terminal accounting failed. |
| Burn-in | NOT RUN | 0/24 cycles. |
| Settings/a11y | NOT RUN | 0/3 observations. |
| DEV grid | NOT RUN | 0/12 cells. |
| Runner log seal/completion | **FAIL** | No runner completion or manifest was produced. The terminal traceback is `AttributeError: module 'frozen_infra_m1_runner' has no attribute 'write_json_atomic'` at M3 runner line 552. |
| Postmortem cleanup/seal | PASS for evidence preservation only | No owners/listeners remained; stdout 10,029 bytes (`05efdfe4…`), stderr 0 bytes; external temporary root removed. |

The exact earlier runtime edge cannot be reconstructed honestly: the final confirmed event is boot PASS, and the next durable event is terminal cleanup. It is therefore recorded as “after boot readiness, before the first framework artifact,” not guessed as a controller, emulator, or service failure.

## Claim boundary and stop decision

M3 supports only two narrow observations: the external log route prevented mutation of prior frozen artifacts, and the verified environment can register/boot the emulator through 5038 without creating 5037. It does not qualify framework stability, 24-cycle burn-in, AndroidEnv accessibility, the 12-cell grid, v0.3 preparation, held-out data, or the role-binding timing hypothesis.

Decision: `STOP_INFRA_M3_NO_RETRY_NO_A11Y_NO_V0_3`. No same-version patch, restart, a11y session, held-out capture, model call, LaTeX edit, or push was performed.
