# INFRA-M7 runner-owned ADB-client authority — final result

## Verdict

**FAIL_PROCESS_IDENTITY_FALSE_REJECTION.** The one frozen M7 chain stopped at the first hard failure, during `adb_server_registered`, before emulator launch, boot, framework/display checks, burn-in or accessibility. The immutable terminal status is `PROCESS_IDENTITY_FAILED`; the exact first edge is:

`PROCESS_IDENTITY:adb_server_registered:PROCESS:1464@1785882456.172884:RUNNER_PARENT_IDENTITY_NOT_CURRENT`

No retry, policy edit, model call, held-out capture or v0.3 preparation was performed. M6 remains immutable.

## Direct evidence and root cause

The transient `start-server` client was PID 1464, identity `1464@1785882456.172884`. Two continuous-history samples independently recorded:

- exact locked `adb.exe` SHA-256 `957e46b8615f7af5b7292a2ddabe98d2e61940c3fb2b0545756507f080613e71`;
- argv beginning with the locked executable and `-P 5038`, followed by `start-server`;
- direct parent PID 1912, which exactly matched the frozen runner identity;
- no listening TCP port on the client.

The child ADB server PID 32928 had the same locked executable hash, argv `adb -L tcp:5038 fork-server server --reply-fd 728`, and exclusively owned port 5038. Therefore this was not a wrong-path, wrong-hash, wrong-port, wrapper, listener-bearing client, PID-reuse or unrelated-process event.

At the triggering snapshot, runner PID 1912 was still present in `all_processes`, and the continuous history had also captured its exact PID+creation identity. It was absent only from `structural_processes`: that subset includes relevant binaries and current ancestry, and after the short-lived client exited the runner was no longer an ancestor of the still-running server. M7 checked parent currentness against this narrower subset. The resulting root cause is **RUNNER_CURRENTNESS_EVIDENCE_SCOPE_MISMATCH**. This is a direct implementation false rejection, not evidence against the intended structural ownership criterion.

Because the client failed before entering the authorized ledger, cleanup later re-read its history record under the cleanup phase and added the secondary `RUNNER_CLIENT_START_SERVER_PHASE:cleanup` error. This did not replace the primary first edge.

## Stage and accounting summary

| Item | Result |
|---|---:|
| Frozen live chains | 1 |
| Process snapshots | 7 |
| Continuous-history samples | 7 |
| Boot | not run |
| Framework/display quorum | not run |
| Burn-in | 0/24 |
| Settings a11y | 0/3 |
| DEV grid | 0/12 |
| Generation calls / model tokens | 0 / 0 |
| Held-out captures | 0 |
| Terminal records | exactly 1 |
| Journal entries | 8 |
| Terminal schema | valid, 0 errors |
| Frozen artifact-manifest integrity | pass |

The runner invoked `kill-server`; the post-run audit found ports 5037, 5038, 5554, 5555 and 8554 all empty and no project runtime process. Emulator launch never occurred. The external M7 log directory existed but contained zero entries; after the result audit proved it was the exact qualified external path and empty, it was removed with a non-recursive empty-directory operation. The immutable run completion continues to record the original seal failure and is not rewritten.

## Claim–evidence verdict

| Claim | Verdict | Evidence boundary |
|---|---|---|
| M7 runner ADB authority is qualified | **No** | Failed before launch qualification |
| A locked direct-parent `-P 5038 start-server` client occurred | **Yes** | History path/hash/argv/parent/listener records |
| Exclusive 5038 server start and later cleanup occurred | **Yes, narrow infrastructure fact** | PID 32928 owned 5038; post-run controlled ports empty |
| Display quorum or burn-in is qualified | **Untested** | Stages never started |
| Accessibility sidecar or 12-cell DEV grid is qualified | **Untested** | 0/3 and 0/12 |
| v0.3 preparation is authorized | **No** | Requires full 12/12 DEV pass |
| Held-out role binding, memory, or model hypothesis was tested | **No** | Zero held-out captures and zero generation calls |

All scenes remain DEV-contaminated. The three protected r79 WIP hashes were unchanged before/after and remain `fc0e82e0…`, `ff89d6b7…`, and `5bb1f1e3…`.

## Stop boundary

M7 ends here as required. A future version, if separately authorized and preregistered, would need to establish runner currentness from a source that actually contains the runner (for example the full process snapshot or a separately revalidated runner identity), while retaining the structural subset for unrelated-process classification. It would also need to ensure a launch-authorized completed client is ledgered before later phase evaluation. Those are prospective repair requirements, not changes or results in M7.
