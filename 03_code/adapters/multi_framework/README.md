# Multi-framework adapters (protocol v0.2)

These adapters are contract shims only. They may call an upstream controller,
provide its frozen observation, map its emitted action grammar, enforce the
predeclared budgets, call the official evaluator and emit normalized logs.
They must not add planning, repair targets, rewrite prompts, add retries or
recovery, expose extra observations, or provide task hints.

Every adapter is qualified in S0 before import into an episode runner. Runtime
dependencies remain isolated by system family.
