# Development Workflow

Before coding: agree Python version, dependencies, shared models and signatures; commit shared interfaces first; use separate branches; avoid concurrent edits to shared files.

Suggested branches:
- feature/dev1-injection-analysis
- feature/dev2-agent-policy
- feature/dev3-system-metrics
- feature/dev4-recovery

Day 1: agree contracts, create skeleton/tests, implement small vertical slices.
Day 2: finish tests, integrate, resolve interface mismatches, run tests cleanly, document limits/demo steps.

Each handoff includes code, tests, exact command/results, assumptions, limitations, public inputs/outputs and integration notes.

Never commit keys, .env, personal databases, virtual environments, caches or logs. Review changes before merging. A module is complete only when criteria, tests, interfaces and limitations are addressed; a polished mock screen is not a functioning protection module.
