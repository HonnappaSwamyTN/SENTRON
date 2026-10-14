# Four Module Assignments

## Dev1 — AgentGuard A: Untrusted-input / injection-risk analysis
Owns: agentguard/input_risk.py and tests/unit/test_input_risk.py.
Build local deterministic heuristics that accept untrusted text and return structured risk flags/explanations. Include suspicious and benign test cases. Analyse only; do not execute actions or grant permissions. No APIs, network calls or arbitrary file access. Do not claim perfect detection.

## Dev2 — AgentGuard B: Policy, approval and controlled executor
Owns: agentguard/policy.py, approval.py, executor.py and related tests.
Build deterministic ALLOW/ASK/BLOCK decisions, scoped approvals, audit events and a safe mock executor. Require fresh approval when action, target, recipient, operation, purpose or scope changes. Never treat approval as universal permanent consent. Do not run destructive tools or claim protection for agents that bypass the executor.

## Dev3 — CrashGuard A: Metrics and sustained-risk detection
Owns: crashguard/metrics.py, risk.py and related tests.
Collect local CPU/RAM/available-memory/process metrics; represent unavailable metrics honestly; use configurable thresholds, sustained windows and cooldowns. Use simulated snapshots in unit tests. Do not kill/suspend processes, collect unrelated personal data or claim confirmed root cause.

## Dev4 — CrashGuard B: Recovery recommendations and safe controls
Owns: crashguard/recovery.py and related tests.
Explain risk events, rank safe recommendations, use mock actions initially, require explicit confirmation for consequential actions and record before/after observations where possible. Consume Dev3's shared snapshot interface. Never silently kill/suspend processes or claim guaranteed crash prevention.

## Integration ownership
Assign one person to own shared core, UI, packaging and integration. If there are only four developers, agree who handles this in addition to their module. Each handoff includes code, tests, exact test results, assumptions, limitations and integration notes.
