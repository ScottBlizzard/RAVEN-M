# Role-Binding Timing B2.8 DEV AndroidEnv accessibility-sidecar diagnosis

Status: preregistered diagnosis route. This is DEV-contaminated infrastructure evidence only. Generation calls, held-out capture, oracle efficacy evaluation, Phase C, and memory/controller claims are forbidden.

## Question and route label

The only question is whether the pinned AndroidWorld runtime can return a nonempty, package-consistent accessibility sidecar and screenshot from one `env.get_state(...)` observation while the explicit ADB and emulator identities remain unchanged. The route is named exactly `androidenv_accessibility_sidecar`; it is not UIAutomator XML and no equivalence to XML is claimed. B2.7 remains immutable failed evidence.

## Frozen authority and provenance

The config freezes the Python executable, AndroidEnv version/metadata/wrapper hashes, AndroidWorld source commit and controller/interface/representation hashes, official ADB path/hash on port 5038, emulator gRPC port 8554 and binary hash, device serial, accessibility-forwarder component/package/APK hash, and Settings package/version/APK hash. The forwarder APK is already installed and must not be installed during this run.

AndroidWorld's upstream `get_a11y_forest()` silently refreshes its environment after a retrieval error, and that refresh path omits the explicit ADB server port. B2.8 therefore uses an independent task-agnostic subclass that disables refresh and directly invokes the pinned bounded forest acquisition. Retrieval failure is terminal; 5037 is never used. No legacy controller task logic, task selector, coordinate, or model path is imported.

Immediately before and after the single explicit observation, the runner records and requires the same 5038 listener PID and binary hash, same 8554 listener PID and emulator binary hash, no 5037 listener, exact enabled accessibility service component, installed forwarder APK hash, and the same host-side accessibility-wrapper object and gRPC port. Service/APK checks use the explicit 5038 client. Any mismatch, implicit refresh/restart, absent or ambiguous listener, or unexpected fallback is failure.

## Same-observation sidecar schema

One call to `env.get_state(wait_to_stabilize=false)` is authorized after bounded foreground readiness. Its returned `State.pixels`, raw protobuf `State.forest`, and `State.ui_elements` are the only observation payload. The runner saves:

- C-order `uint8` pixel bytes with shape/dtype/hash and a PNG encoded from exactly that array;
- deterministic protobuf bytes using `SerializeToString(deterministic=true)`, plus a recursive manifest of protobuf message/field numbers, labels, scalar/message types, and repeated status;
- every one of the 22 fields declared by the pinned `UIElement` dataclass, in exact field order, using typed canonical JSON. Integers are decimal strings, finite floats use hexadecimal form, bytes use base64, dataclasses retain qualified class and ordered fields, dictionaries retain typed keys and values, and unsupported/nonfinite values fail instead of being coerced;
- a raw declared/observed field-type manifest, null counts, artifact hashes, foreground witnesses, and strong oracle-candidate IDs.

Serialization is accepted only if two serializations are byte-identical, canonical JSON reparses to identical canonical bytes, all declared fields occur, the raw forest is nonempty/deterministic, the screenshot is C-contiguous `uint8` with frozen shape, and every recorded artifact hash revalidates. A strong oracle candidate requires the expected package, class, in-bounds pixel box, a resource name or resource ID, and a unique hash of those fields. Text alone is insufficient.

## One bounded Settings diagnostic

The runner resets to home, force-stops Settings, starts its native component without `-W`, and samples activity/window/process evidence at most 10 times at two-second intervals. Two consecutive foreground agreements are required, followed by a fixed three-second settle. Failure to reach readiness ends before the explicit observation.

Exactly one explicit `get_state` call is then made; there are no observation retries. PASS requires a nonempty sidecar, Settings among sidecar element packages, activity/window/AndroidWorld foreground agreement, valid screenshot and forest, all-field lossless serialization, at least one unique strong oracle candidate, complete identity continuity, artifact/schema validation, zero generation calls, and clean reset/close. Any failure stops B2.8 before the 12-cell grid is frozen.

If and only if this diagnostic passes, a separately versioned and separately committed 12-cell DEV grid protocol/implementation may be frozen. No held-out pool is prepared by this diagnosis.
