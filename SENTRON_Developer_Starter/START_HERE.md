# START HERE — SENTRON V1 Developer Onboarding

Welcome to **SENTRON**. This repository contains the architecture, specifications, interfaces, and development starter files for SENTRON V1.

---

## 1. Understand What SENTRON V1 Is (And Isn't)

- **What it is**: A local-first Windows desktop application featuring a movable floating hub, deterministic AI-agent action enforcement (**AgentGuard**), and host system health telemetry with safe recovery guidance (**CrashGuard**).
- **Technology Stack**: Python 3.11+, PySide6, SQLite 3, `psutil`, Windows Event Logs, and `pytest`.
- **What it is NOT**: It is not a cloud service, does not require an OpenAI/Anthropic/external AI API, does not claim universal protection over unintegrated agents, does not claim guaranteed crash prediction, and **does not automatically kill or suspend processes in V1**.

---

## 2. The 4-Step Onboarding Process

### Step 1: Read the Authoritative Documentation
Familiarize yourself with the system architecture and project bounds:
1. [PROJECT_CONTEXT.md](file:///c:/Users/Honnu/OneDrive/Desktop/kagada/SENTRON/SENTRON_Developer_Starter/PROJECT_CONTEXT.md) — Product vision, boundaries, non-goals, and core definitions.
2. [ARCHITECTURE.md](file:///c:/Users/Honnu/OneDrive/Desktop/kagada/SENTRON/SENTRON_Developer_Starter/ARCHITECTURE.md) — Subsystems, schemas, workflows, and boundary rules.
3. [DECISIONS.md](file:///c:/Users/Honnu/OneDrive/Desktop/kagada/SENTRON/SENTRON_Developer_Starter/DECISIONS.md) — Formal frozen architecture decisions.

### Step 2: Identify Your Role & Scope
Open [MODULE_OWNERSHIP.md](file:///c:/Users/Honnu/OneDrive/Desktop/kagada/SENTRON/SENTRON_Developer_Starter/MODULE_OWNERSHIP.md) to locate your assigned component:
- **Dev1**: AgentGuard A — Suspicious-input analyzer, sensitive-data detector, secret redaction.
- **Dev2**: AgentGuard B — Deterministic policy engine (`ALLOW`/`ASK`/`BLOCK`), scoped approval manager, safe mock executor, audit history.
- **Dev3**: CrashGuard A — `psutil` metrics collector, background monitoring worker, sustained-risk detector.
- **Dev4**: CrashGuard B — Windows evidence collector, diagnostics & safe recovery advisor.
- **Integration Owner**: PySide6 floating hub, SQLite event store, shared schemas, packaging.

### Step 3: Review Rules & Acceptance Criteria
Before writing any code or prompting an AI assistant:
1. [FEATURES_AND_ACCEPTANCE.md](file:///c:/Users/Honnu/OneDrive/Desktop/kagada/SENTRON/SENTRON_Developer_Starter/FEATURES_AND_ACCEPTANCE.md) — Review the 18 testable acceptance criteria relevant to your module.
2. [SECURITY_RULES.md](file:///c:/Users/Honnu/OneDrive/Desktop/kagada/SENTRON/SENTRON_Developer_Starter/SECURITY_RULES.md) — Strict rules on secret redaction, safe defaults, and execution boundaries.
3. [AI_WORK_RULES.md](file:///c:/Users/Honnu/OneDrive/Desktop/kagada/SENTRON/SENTRON_Developer_Starter/AI_WORK_RULES.md) — Mandated guidelines if using LLM assistants to generate code.

### Step 4: Setup Environment & Run Verification
Follow [DEVELOPMENT_WORKFLOW.md](file:///c:/Users/Honnu/OneDrive/Desktop/kagada/SENTRON/SENTRON_Developer_Starter/DEVELOPMENT_WORKFLOW.md):
```powershell
# 1. Create virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# 2. Install editable package with dev dependencies
pip install -e ".[dev]"

# 3. Run test runner
pytest -v
```

---

## 3. Strict Development Rules

1. **Do not modify shared models or interfaces unilaterally**: Shared schemas in `src/sentron/core/models.py` must be agreed upon by all module owners. If a change is needed, submit an RFC as outlined in [CONTRIBUTING.md](file:///c:/Users/Honnu/OneDrive/Desktop/kagada/SENTRON/SENTRON_Developer_Starter/CONTRIBUTING.md).
2. **Never commit secrets or cloud credentials**: V1 requires zero external AI keys. Do not add API client libraries or network telemetry.
3. **Never present simulated telemetry as real data**: In CrashGuard, use genuine `psutil` measurements and Windows Event Logs. Handle missing counters gracefully with explicit `unavailable_metrics` warnings.
4. **Adhere to the execution boundary**: AgentGuard only protects actions that pass through its controlled executor. Never claim universal agent interception.
5. **No auto-kill in V1**: CrashGuard must provide actionable recommendations only. It must never terminate or suspend processes.
