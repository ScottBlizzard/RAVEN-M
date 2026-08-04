# B2.10 accessibility-forwarder lifecycle audit

## Verdict

**`AUDIT_COMPLETE_SAFE_GENERIC_REPAIR_SUPPORTED`**, with the causal boundary still open. The frozen B2.9 failure is more precisely located at **device forwarder → host accessibility gRPC delivery**, not at Settings rendering, task logic, model output, UI-tree construction, APK identity, or the emulator-control gRPC service.

The strongest direct trace contains 313 device-side `sendForest` attempts to the exact B2.9 endpoint `10.0.2.2:50069`, 313 timeout warnings, and zero successful responses. B2.9 simultaneously recorded the host sidecar listener as qualified. This supports one bounded, task-agnostic DEV intervention, but it does **not** yet prove which transport/lifecycle mechanism caused the timeout.

No device mutation, AndroidEnv creation, refresh, service restart, model call, held-out capture, oracle evaluation, or hypothesis test occurred in this audit.

## Direct evidence

### Frozen B2.9 state

- The exact frozen completion record SHA-256 remains `e81e391dd4d39d882fb3a35cc0c9d572777ecc1df99d9c70b4d458f486b2fc7e`.
- The accessibility component was present under `Enabled services` and `Binding services`; `Bound services` and `Crashed services` were empty.
- The host sidecar was qualified during B2.9 on port 50069, ADB stayed on PID 29964 at port 5038, emulator control gRPC stayed on PID 7172 at port 8554, and port 5037 had no listener.
- One authorized `get_state` call exhausted five bounded forest fetches and returned no `State`.

### Preserved device logs

The bounded raw logcat capture retains the exact bytes and hashes. It shows this ordered chain:

1. `ENABLE_ACCESSIBILITY_TREE_LOGS` was received and enabled.
2. Before endpoint configuration, 52 samples reported that the gRPC port had not been set.
3. `SET_GRPC` was received, and the receiver logged `Setting gRPC endpoint to 10.0.2.2:50069.`
4. The forwarder built a channel and attempted to send a forest 313 times.
5. Every attempt represented in the trace ended in `TimeoutCancellationException`; zero `gRPC request for tree succeeded` lines exist.
6. Repeated channel recreation produced 909 `ManagedChannelOrphanWrapper` matching lines, consistent with the APK resetting its stub without explicitly shutting down prior channels.

The logs prove that the service thread could read/build a tree far enough to invoke `sendForest`; they contradict a simple “no a11y tree was ever created” explanation.

### Current read-only identity

- The enabled component, package, and APK still match the frozen identity; installed APK SHA-256 is `97a56a544e44d79f9b3181fc7dbdd72cffa908efd3d53c82afad1773061a350a`.
- The forwarder process remains PID 4909 and still appears as enabled/binding, not bound, in `dumpsys accessibility`.
- The stale global `no_proxy` value remains `10.0.2.2:50069`, while no host listener now remains on 50069 after the B2.9 environment closed.
- ADB 5038 and emulator gRPC 8554 retain PIDs 29964 and 7172; 5037 has no listener.

This post-run state is lifecycle/residue evidence only. It is not used to revise B2.9's immutable verdict.

## Pinned implementation audit

The pinned AndroidEnv wrapper:

- enables the accessibility service by writing `enabled_accessibility_services`, but does not wait for a framework `Bound` witness;
- enables tree logging before creating the host server;
- creates the host server with `grpc.local_server_credentials()` and `add_secure_port([::]:port, ...)`;
- later configures the guest endpoint during reset;
- embeds `--ei "port" ...` inside the broadcast action string, while the pinned ADB parser passes the complete action as one argv item;
- contains no explicit `ENABLE_GRPC` broadcast in the inspected wrapper path.

The pinned APK source:

- connects from the emulator guest to `10.0.2.2:<port>` with `ManagedChannelBuilder.usePlaintext()`;
- builds the accessibility forest before the gRPC send;
- resets the stub after a timeout without explicitly shutting down the previous channel.

The pinned gRPC 1.82.1 runtime documents that local server credentials check whether TCP peers are local. The emulator guest reaches the host through `10.0.2.2`, not host loopback. Therefore **local-only host credentials versus an emulator-guest plaintext client** is a source/runtime-concordant candidate mechanism. It remains an inference until a preregistered transport intervention succeeds or fails.

The broadcast construction and absent explicit `ENABLE_GRPC` are real source-contract defects, but they cannot alone explain B2.9: the frozen device log proves that the exact endpoint was set and gRPC sending was active. A fresh lifecycle qualification must configure both flags explicitly to avoid relying on retained in-process state.

AndroidWorld's standard `refresh_env()` is unsafe for this study because it reconstructs the controller without forwarding `adb_server_port`; it can therefore fall back to 5037. B2.9 correctly suppressed that path, and B2.10 must continue to do so.

## Failure classification

| Candidate class | Verdict | Evidence boundary |
|---|---|---|
| Enabled but unbound | Concurrent fact, not unique root | `dumpsys` says Binding and not Bound, but the process actively built/sent forests |
| Bound/running but no tree at host | Supported at the effective-delivery level | 313 sends, 313 timeouts, zero success, no host forest |
| Host not listening | Contradicted during frozen B2.9 | B2.9 host listener qualification passed on port 50069 |
| APK/service mismatch | Contradicted | Component and APK hash match the frozen contract |
| Host service 8554 failure | Contradicted as this edge | 8554 is emulator-control gRPC, not the random a11y sidecar port; its PID remained stable |
| Exact transport mechanism | Not causally proven | Credentials/lifecycle mismatch is supported by source and logs but untested by intervention |

## Claim–evidence matrix

| Claim | Verdict |
|---|---|
| B2.9 was a model or role-binding failure | Rejected; no model call and no returned observation |
| Settings failed to render | Rejected by B2.9 foreground/screenshot-side evidence |
| Forwarder APK could not construct a tree | Rejected as a complete explanation; `sendForest` was invoked repeatedly |
| Device-to-host a11y delivery was the first broken edge | Supported |
| Local-only credentials caused all timeouts | Plausible, not yet causally proven |
| A task-agnostic bounded DEV repair is justified | Supported |
| A 12-cell grid may run immediately | Rejected; repeated Settings qualification must pass first |
| v0.3 or Phase C is authorized | Rejected |
| Memory/controller/oracle efficacy was tested | Not tested |

## Authorized next boundary

The next revision may preregister exactly one DEV-only lifecycle matrix using the locked 5038 ADB server and 8554 emulator endpoint. It may:

- start a fresh fail-closed AndroidEnv session whose accessibility host server accepts emulator-guest plaintext traffic;
- explicitly set the current random host port and explicitly enable gRPC/tree delivery through the documented receiver;
- perform a bounded same-port service rebind/restart if preregistered;
- require PID/service identity continuity, no 5037 listener, no implicit refresh, nonempty losslessly serialized elements, and a usable screenshot from each same observation.

Only repeated Settings success can unlock the already specified single 12-cell multi-app DEV grid. Failure at any lifecycle-matrix edge stops B2.10 without a grid, held-out protocol, or model generation.

## Audit artifacts and boundary

The machine-readable result is `05_project/artifacts/role_binding_timing/phase_b2_10_accessibility_forwarder_lifecycle_audit/lifecycle_audit.json`. Its companion manifest hashes every raw command stream, the 20,000-line bounded logcat, source anchors, filtered logs, and the result itself. The three protected r79 WIP hashes are unchanged before/after. Generation calls, model tokens, held-out traces, and oracle evaluations are all zero.
