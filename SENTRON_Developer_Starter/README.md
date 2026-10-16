# SENTRON — Developer Starter & Implementation Guide

> **V1 Specification Status: FROZEN**  
> SENTRON is a local-first Windows desktop protection suite featuring **AgentGuard** (deterministic AI-agent permission and execution governance) and **CrashGuard** (operating system health telemetry and non-destructive recovery recommendations).

---

## 1. Quick Navigation & Reading Order

Before writing code or configuring an AI assistant, read the project documentation in this recommended order:

| Step | Document | Purpose |
| :---: | :--- | :--- |
| **1** | [START_HERE.md](file:///c:/Users/Honnu/OneDrive/Desktop/kagada/SENTRON/SENTRON_Developer_Starter/START_HERE.md) | 4-step onboarding checklist for developers and pair-programming AIs |
| **2** | [PROJECT_CONTEXT.md](file:///c:/Users/Honnu/OneDrive/Desktop/kagada/SENTRON/SENTRON_Developer_Starter/PROJECT_CONTEXT.md) | Product vision, boundaries, non-goals, and security definitions |
| **3** | [ARCHITECTURE.md](file:///c:/Users/Honnu/OneDrive/Desktop/kagada/SENTRON/SENTRON_Developer_Starter/ARCHITECTURE.md) | Technical architecture, data schemas, module flows, and boundary rules |
| **4** | [MODULE_OWNERSHIP.md](file:///c:/Users/Honnu/OneDrive/Desktop/kagada/SENTRON/SENTRON_Developer_Starter/MODULE_OWNERSHIP.md) | Dev1–Dev4 team assignments and Integration Owner scope |
| **5** | [FEATURES_AND_ACCEPTANCE.md](file:///c:/Users/Honnu/OneDrive/Desktop/kagada/SENTRON/SENTRON_Developer_Starter/FEATURES_AND_ACCEPTANCE.md) | The 18 testable acceptance criteria with test mapping |
| **6** | [SECURITY_RULES.md](file:///c:/Users/Honnu/OneDrive/Desktop/kagada/SENTRON/SENTRON_Developer_Starter/SECURITY_RULES.md) | Redaction standards, default-deny policy, and execution boundary rules |
| **7** | [DEVELOPMENT_WORKFLOW.md](file:///c:/Users/Honnu/OneDrive/Desktop/kagada/SENTRON/SENTRON_Developer_Starter/DEVELOPMENT_WORKFLOW.md) | Virtualenv setup, pytest commands, branch flow, and code conventions |
| **8** | [DECISIONS.md](file:///c:/Users/Honnu/OneDrive/Desktop/kagada/SENTRON/SENTRON_Developer_Starter/DECISIONS.md) | Formal Architecture Decision Records (ADRs) |
| **9** | [AI_WORK_RULES.md](file:///c:/Users/Honnu/OneDrive/Desktop/kagada/SENTRON/SENTRON_Developer_Starter/AI_WORK_RULES.md) | Guardrails and prompt templates for AI coding assistants |
| **10** | [CONTRIBUTING.md](file:///c:/Users/Honnu/OneDrive/Desktop/kagada/SENTRON/SENTRON_Developer_Starter/CONTRIBUTING.md) | Contribution standards and contract change RFC protocol |

---

## 2. Frozen V1 Technology Decisions

- **Python Runtime**: Python 3.11+
- **Desktop UI**: PySide6 (Qt for Python) — implements the movable, floating desktop hub and dashboard views
- **System Metrics**: `psutil` — real-time cross-process CPU, memory, and disk counters
- **Operating System Telemetry**: Windows Event Logs (`Application Hang`, `Application Error`, critical system events, driver/update events) via Windows interfaces
- **Local Persistence**: SQLite 3 — embedded database for unified event history and audit logs
- **Testing Suite**: `pytest` — automated unit and integration tests
- **Architecture**: Modular Monolith — single codebase with clean, decoupled package boundaries
- **Operation Mode**: 100% Local-First — zero mandatory external AI APIs, zero external telemetry, zero internet requirements

---

## 3. Subsystem Overview

### AgentGuard
- **Suspicious-Input Analyzer**: Deterministic rule-based checks for known prompt injections, manipulation phrases, and untrusted payload patterns. Emits risk signals and evidence; does not independently authorize actions.
- **Sensitive-Data Detector**: Regex and pattern-based recognition of API keys, passwords, and confidential data. Redacts detected values before logging.
- **Deterministic Policy Engine**: Maps structured action requests to an authoritative decision (`ALLOW`, `ASK`, `BLOCK`) with reason codes. Unknown, underspecified, or high-impact actions default to `ASK` or `BLOCK`.
- **Scoped Approval Manager**: Enforces fine-grained approval bounds (agent, operation, target, destination, purpose, expiry). Invalidation triggers if action parameters mutate.
- **Controlled Executor**: Safe mock execution layer for the V1 demo. Blocked actions never reach the executor; actions requiring approval halt until granted.
- **Security Audit History**: Writes sanitized records to SQLite. AgentGuard dashboard displays the latest 5 events and supports historical search.

### CrashGuard
- **Metrics Collector**: Continuously collects real system metrics (CPU, RAM, disk, process summaries/trends) via `psutil`. No fabricated data.
- **Monitoring Worker**: Decoupled background worker (5–10s configurable cadence) with bounded circular buffers and graceful shutdown.
- **Sustained-Risk Detector**: Evaluates telemetry against configured thresholds, duration windows, and alert cooldowns. Distinguishes temporary spikes from sustained pressure.
- **Windows Evidence Collector**: Retrieves crash and hang events from Windows Event Logs where available and permitted; degrades gracefully when permissions or counters are unavailable.
- **Diagnostics & Safe Recovery Recommendations**: Presents observed data, separates confirmed facts from inferred causes, and advises safe user interventions (save work, close non-essential apps). **No automatic process killing or suspension in V1.**

### Shared Core & Desktop UI
- **Movable Floating Desktop Hub**: Unobtrusive floating desktop icon opening the SENTRON hub with live module status indicators and warning badges.
- **Unified SQLite Event Store**: Shared `events` table correlating security and system health events by timestamp (acknowledging temporal correlation does not imply causation).

---

## 4. Local Setup & Testing

### 1. Setup Virtual Environment
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2. Install Editable Package & Test Dependencies
```powershell
pip install -e ".[dev]"
```

### 3. Run Automated Tests
```powershell
pytest -v
```

---

## 5. Teammate AI Assistant Prompt

When delegating tasks to a pair-programming AI assistant, use the following standardized prompt:

```text
"Read the SENTRON project documents in SENTRON_Developer_Starter/. I am Dev[N] (1=AgentGuard Input Risk, 2=AgentGuard Policy/Executor, 3=CrashGuard Metrics/Risk, 4=CrashGuard Recovery/Evidence, or Integration Owner). 

Before editing any files:
1. Summarize the product and the frozen V1 scope.
2. State my specific module assignment and permitted files.
3. List the shared interfaces and contracts I must adhere to.
4. List the exact acceptance criteria applicable to my module.
5. Identify all dependencies, boundary limitations, and integration risks.

Do not edit any code until I review and confirm your summary."
```
