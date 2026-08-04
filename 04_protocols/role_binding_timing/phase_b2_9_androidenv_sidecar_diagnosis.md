# Role-Binding Timing B2.9 DEV AndroidEnv sidecar revision

Status: preregistered B2.9 revision. B2.8 remains immutable `FAIL_SETTINGS_DIAGNOSTIC` evidence and is neither edited nor reinterpreted.

## Authorized change

B2.9 changes only the generic command-output boundary that failed in B2.8. Raw stdout and stderr must have exact Python type `bytes`, are hashed before interpretation, and are decoded once with UTF-8 plus `errors=strict`. NULs, malformed UTF-8, bytes subclasses, strings, nonzero return codes, timeouts, nonempty stderr, empty output, wrong service names, and output outside the normalized grammar `Service <expected-name>: found` fail closed. Case and whitespace variation inside that grammar are accepted after decoded-text normalization. Raw bytes are always retained unchanged.

The exact contaminated B2.8 stdout bytes `Service package: found\r\n` are an offline regression fixture only. They do not become new live evidence.

## Audit of the inherited runner

The B2.8 source was reviewed for every `stdout`, `stderr`, `decode`, `casefold`, `lower`, `str`, and `bytes` use. The failed framework-service line was the only location applying a case-insensitive text operation directly to bytes. Other command payloads are explicitly decoded before exact path/hash/component/package parsing; a decode replacement at those sites cannot authorize success because subsequent exact identity or package checks remain fail closed. The B2.9 live runner contains no direct raw-stream `casefold` and retains byte-level artifacts.

No app selector, coordinate, task template, retry, AndroidWorld task logic, model endpoint, UIAutomator route, or old-artifact mutation is introduced.

## Frozen diagnosis and stop rules

All B2.8 sidecar observation requirements remain unchanged: official ADB on 5038 with no 5037 fallback; emulator gRPC on 8554; exact service/APK and PID identity; fail-closed AndroidWorld controller with no implicit refresh; one bounded Settings DEV scene; at most one explicit `env.get_state`; same-state pixels, protobuf forest, and all 22 `UIElement` fields; deterministic serialization; package-consistent nonempty elements; and at least one unique strong oracle candidate.

The Settings diagnosis runs once after a separately committed/tagged lock. Any failure stops B2.9 and prohibits a grid. Only a complete Settings PASS authorizes a separate grid protocol/freeze. The grid, if authorized, is one frozen 4-app × 3-round DEV run and must pass 12/12 with unchanged 5038/8554 and accessibility identities, zero 5037, zero implicit restart, nonempty package-consistent elements, usable screenshots, and stable serialization/oracle fields. A grid PASS may prepare—but not run—a new v0.3 held-out protocol. Generation, held-out capture, Phase C, LaTeX edits, pushes, and efficacy claims remain forbidden.
