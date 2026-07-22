# Runtime metadata

Small machine-readable audit files generated after installation are stored here. They record versions and validation status, not machine credentials or model API keys.

- `runtime_audit.json` records SDK, emulator, dependency, app, cache, and test status.
- `androidworld_smoke.json` is the first full setup-and-task initialization test.
- `androidworld_repeat_smoke.json` verifies that a later run can reuse the local cache and configured emulator.
- The matching PNG files are actual AndroidWorld screen observations captured through the environment API.

The ignored `../runs/local_validation_utf8/` directory contains a complete
episode artifact written by the official runner with the no-cost `random_agent`.
Its task reward is intentionally not a quality benchmark; its purpose is to
verify the entire evaluator and result-writing path.
