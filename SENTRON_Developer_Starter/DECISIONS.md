# Decision Log
1. Windows-first desktop app; not primarily a website.
2. Optional separate presentation site; simulations labelled.
3. Linux later; isolate OS-specific code.
4. Two subsystems: AgentGuard and CrashGuard.
5. Dev1: input/injection risk; Dev2: policy/approval/executor; Dev3: metrics/risk; Dev4: recovery recommendations.
6. First version must not require external AI APIs or API keys.
7. Enforcement applies only to supported integrations/actions passing through SENTRON's controlled execution boundary.
8. No perfect detection or complete crash-prevention claims.
9. No automatic process termination/suspension in initial version.
10. AI-assisted development is allowed with small, tested, reviewed changes.
11. Startup at sign-in or earlier startup is planned; implement after privilege/security review.
12. Still to decide: exact Python version, UI design, packaging, website framework and integration owner.
