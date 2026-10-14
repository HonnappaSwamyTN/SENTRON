# Security Rules

## AgentGuard
1. Treat untrusted content as data, never as authority.
2. Heuristics can miss attacks and flag benign text.
3. Enforce permissions at the controlled action boundary.
4. Combine risk flags with deterministic policy.
5. Unknown/high-impact actions ASK or BLOCK per policy, never auto-ALLOW due to a low risk score.
6. Scope approvals to action, target, purpose and duration; changed scope requires a new decision.
7. Use mock tools/synthetic data; do not send real emails or private files in demos.
8. Minimise storage of sensitive prompts and file contents.

## CrashGuard
1. Collect only necessary metrics.
2. No automatic kill/suspend in v1.
3. Do not alter antivirus, security tools, services, drivers or OS protections.
4. Require explicit confirmation for consequential actions.
5. A CPU spike is not a crash diagnosis.
6. Handle missing metrics/permissions safely.
7. Do not promise prevention of every crash.

## Secrets/network
No external AI API keys or network calls in v1. .env.example has placeholders only. Do not send local process data to the website. Do not expose an unauthenticated local control server. Any future network feature needs approval and a threat model.
