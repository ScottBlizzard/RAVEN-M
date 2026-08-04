# B2.9 AndroidEnv accessibility-sidecar revision verdict

## Verdict

**`FAIL_SETTINGS_DIAGNOSTIC — A11Y_FOREST_DELIVERY_UNAVAILABLE`.** B2.9 fixed and qualified the generic bytes/text preflight boundary, then ran the one frozen Settings DEV diagnosis. The diagnosis reached its sole authorized `env.get_state` call, but the accessibility-forwarder path did not deliver an `accessibility_tree` within the pinned five-attempt bounded acquisition. The fail-closed controller propagated `RuntimeError: Could not get a11y tree.` without invoking AndroidWorld's implicit refresh path.

The preregistered stop rule therefore applies. No 12-cell DEV grid was frozen or run, no v0.3 held-out protocol was prepared, and no same-version patch or retry occurred. This is infrastructure evidence only; it is not role-binding, memory, controller-efficacy, or oracle-efficacy evidence.

## Frozen revision and offline gates

- B2.8 remained immutable at commits `6a13504`, `b988b2a`, and `b557b60`.
- B2.9 implementation freeze: `e7ef0f456025a95de7659e012cbb2fc2d5ea440b`.
- Freeze tag: `role-binding-timing-b2.9-sidecar-diagnosis-freeze-20260804`.
- The only runner semantic change was the generic framework-service command-output contract. Exact `bytes` are hashed, decoded with UTF-8 and `errors=strict`, then checked against the normalized `Service <expected-name>: found` grammar. Strings, bytes subclasses, non-UTF-8, NULs, empty/malformed output, wrong service names, nonzero status, timeout, and nonempty stderr fail closed.
- Focused tests: 14/14 passed, including the exact contaminated B2.8 bytes and all required corruption cases.
- Role-binding namespace: all passed.
- Full regression: only the already declared protected r79/r78 frozen-manifest conflict remained.
- Before live: zero model calls, zero held-out captures, zero `get_state` calls, and an empty B2.9 result root.

## Failure chain

1. All three framework service checks passed through official ADB on port 5038. The package check reproduced the exact B2.8 stdout bytes and now passed the frozen parser.
2. AndroidEnv and `FailClosedA11yController` were created. The host accessibility sidecar listened on port 50069.
3. Home/force-stop and non-waiting Settings launch passed. Two consecutive readiness samples agreed on process PID 16906 and package `com.android.settings` in both activity and window evidence.
4. Observation-before identity qualified: ADB PID 29964, emulator gRPC PID 7172, exact enabled component, installed forwarder APK SHA-256 `97a56a544e44d79f9b3181fc7dbdd72cffa908efd3d53c82afad1773061a350a`, host sidecar listener, and no 5037 listener all passed.
5. The raw concurrent accessibility dump showed the component under `Enabled services` and `Binding services`, while `Bound services` was empty and `Crashed services` was empty. This is direct concurrent evidence. It is a plausible explanation for missing delivery, but this run does not prove it is the unique root cause.
6. The only `get_state` call performed its pinned five bounded forest fetches. None contained `accessibility_tree`; `_get_a11y_forest` raised `RuntimeError`.
7. The stack terminated through the B2.8/B2.9 fail-closed override. It contains no `refresh_env` frame and did not raise the override's `IMPLICIT_ANDROIDENV_REFRESH_FORBIDDEN`, so no implicit refresh/reconnect was attempted.
8. Because AndroidWorld adds the forest during `_process_timestep`, failure occurred before a `State` was returned. Consequently no same-observation screenshot, protobuf forest, `UIElement` list, field/type manifest, or live serialization record could be saved. Their offline serializers remain tested but live-unqualified.

## Accounting and residue

| Item | Result |
|---|---:|
| Model calls / tokens | 0 / 0 |
| Held-out captures | 0 |
| Explicit `get_state` calls | 1 |
| Bounded forest fetch attempts | 5 |
| Returned `State` objects | 0 |
| Observation records | 0 |
| Settings readiness samples | 2/2 passed |
| Wall time | 127.844 s |
| Cleanup reset / env close | passed / closed |

After cleanup, ADB 5038 still listened on PID 29964, emulator gRPC 8554 on PID 7172, and 5037 had no listener. Home and Settings force-stop passed, no experiment Python process remained, and the three protected WIP hashes were unchanged.

## Claim–evidence verdict

| Claim | Verdict |
|---|---|
| B2.8 bytes/str defect is generically fixed | Supported by 14 corruption tests and three successful live framework checks |
| Settings foreground/readiness works in this run | Supported by two consecutive activity/window/process samples |
| Accessibility sidecar service identity was present | Supported before observation; component was enabled and binding, APK/hash and host listener matched |
| AndroidEnv sidecar returned a usable observation | Rejected for this run; no tree and no returned `State` |
| The empty `Bound services` entry uniquely caused failure | Not proven; concurrent evidence only |
| Automatic AndroidWorld refresh rescued or contaminated the run | Rejected; fail-closed path propagated without refresh |
| 12-cell grid or v0.3 preparation is authorized | Rejected by the Settings stop rule |
| Role-binding timing hypothesis received evidence | Not tested |

## Artifacts and final boundary

The authoritative terminal record is `05_project/artifacts/role_binding_timing/phase_b2_9_androidenv_sidecar_diagnosis/diagnosis_completion.json`, SHA-256 `e81e391dd4d39d882fb3a35cc0c9d572777ecc1df99d9c70b4d458f486b2fc7e`. `result_summary.json` records the machine-readable broken edge and non-claims. An artifact manifest enumerates all retained raw commands, readiness witnesses, service/APK identity, cleanup streams, and their hashes.

B2.9 stops here: **do not run the grid, do not prepare v0.3, do not generate, and do not reinterpret this infrastructure failure as hypothesis evidence.**
