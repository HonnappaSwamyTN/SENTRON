# SENTRON — Local-First Windows Protection & Health Monitoring

> **V1 Specification Status: FROZEN**  
> SENTRON is a local-first Windows desktop application that combines deterministic AI-agent action governance (**AgentGuard**) with real-time operating system health monitoring and safe recovery guidance (**CrashGuard**).

---

## 1. Executive Overview

Modern desktop environments are increasingly shared between human users and autonomous AI agents. While agents execute local operations (file manipulation, API requests, data retrieval), the host operating system faces both security vulnerabilities (prompt injection, secret leaks, unauthorized execution) and stability risks (uncontrolled resource consumption, application hangs, memory exhaustion).

SENTRON provides a unified, local-first control layer through a lightweight, movable floating desktop hub:

- **AgentGuard**: Intercepts, inspects, and enforces permissions on supported AI-agent action requests before execution. Utilizes deterministic rule-based analysis for prompt injections and sensitive data detection, scoped human-in-the-loop approvals, and a safe controlled execution gatekeeper.
- **CrashGuard**: Continuously monitors host operating system health metrics (CPU, RAM, disk, process trends) via `psutil` and Windows Event Logs. Detects sustained resource pressure using configurable duration windows and cooldowns, surfaces diagnostic evidence, and recommends safe, non-destructive recovery actions.
- **Unified Event History**: Aggregates security audit logs and system health telemetry in a local, private SQLite database with temporal correlation capabilities.

```
                              +---------------------------------------+
                              |      Movable Floating Desktop Hub     |
                              |               (PySide6)               |
                              +-------------------+-------------------+
                                                  |
                                                  v
                              +---------------------------------------+
                              |              SENTRON Core             |
                              |  (Local SQLite Event Store & Config)  |
                              +---------+-------------------+---------+
                                        |                   |
                     +------------------+                   +------------------+
                     v                                                         v
  +-------------------------------------+                   +-------------------------------------+
  |             AgentGuard              |                   |             CrashGuard              |
  |  - Suspicious-Input Analyzer        |                   |  - Metrics Collector (psutil)       |
  |  - Sensitive-Data Detector          |                   |  - Background Worker (5-10s loop)   |
  |  - Deterministic Policy Engine      |                   |  - Sustained-Risk Detector          |
  |  - Scoped Approval Manager          |                   |  - Windows Evidence Collector       |
  |  - Controlled Executor (Safe Mock)  |                   |  - Safe Recovery Advisor            |
  |  - Security Audit History           |                   |  - Non-Destructive Advisory         |
  +-------------------------------------+                   +-------------------------------------+
```

---

## 2. Core Architectural Principles & Decisions

1. **Local-First & Offline**: Zero mandatory cloud infrastructure, external AI services, or remote telemetry. All decisions and diagnostic evaluations execute entirely on the local machine.
2. **Deterministic Governance**: Input analysis, policy evaluations (`ALLOW`, `ASK`, `BLOCK`), and health diagnostics use deterministic rules and heuristics. No LLM calls are in the critical decision loop.
3. **Controlled Execution Boundary**: SENTRON protects actions that pass through its supported integration and controlled executor. It makes no claim of universal protection for arbitrary third-party agents that bypass this boundary.
4. **Honest Telemetry & Safe Diagnostics**: CrashGuard displays genuine OS metrics and Windows event evidence. It never displays simulated data as real, never claims guaranteed crash prediction, and **never automatically kills or suspends processes in V1**.
5. **Privacy by Design**: Recognizable secrets (API keys, passwords, confidential patterns) are detected and redacted before logging to the local SQLite database.

---

## 3. Technology Stack

| Layer | Technology | Rationale |
| :--- | :--- | :--- |
| **Language** | Python 3.11+ | Modern typing, asyncio/threading capabilities, robust standard library |
| **Desktop UI** | PySide6 (Qt for Python) | Native desktop rendering, floating movable hub widget, thread-safe signals |
| **Metrics** | `psutil` | Reliable cross-process CPU, memory, and disk telemetry on Windows |
| **OS Diagnostics** | Windows APIs & Event Logs | Native access to Application Crash/Hang events, critical errors, driver updates |
| **Storage** | SQLite 3 | Embedded, zero-configuration, ACID-compliant local event storage |
| **Testing** | `pytest` | Automated unit and integration test framework |
| **Architecture** | Modular Monolith | Single deployable package with isolated subsystem boundaries |

---

## 4. Repository Structure

The core codebase, tests, and detailed developer documentation are located in [`SENTRON_Developer_Starter/`](file:///c:/Users/Honnu/OneDrive/Desktop/kagada/SENTRON/SENTRON_Developer_Starter):

```
SENTRON/
├── README.md                                 # Top-level repository overview (this document)
└── SENTRON_Developer_Starter/               # Core application workspace
    ├── START_HERE.md                         # 4-step developer onboarding guide
    ├── PROJECT_CONTEXT.md                    # Authoritative vision, goals, non-goals, security boundary
    ├── ARCHITECTURE.md                       # Comprehensive architecture, data schemas, workflows
    ├── FEATURES_AND_ACCEPTANCE.md            # 18 testable acceptance criteria & test mapping
    ├── MODULE_OWNERSHIP.md                   # Dev1–Dev4 assignments and integration ownership
    ├── SECURITY_RULES.md                     # Security, privacy, redaction, safe defaults
    ├── DEVELOPMENT_WORKFLOW.md               # Environment setup, pytest workflow, git hygiene
    ├── DECISIONS.md                          # Frozen Architecture Decision Records (ADRs)
    ├── AI_WORK_RULES.md                      # Instructions for pair-programming AI assistants
    ├── CONTRIBUTING.md                       # Contributor guide & RFC process for shared models
    ├── MODULE_HANDOFF_TEMPLATE.md            # Module completion and handoff template
    ├── WEBSITE_SCOPE.md                      # Scope and boundaries of optional presentation site
    ├── pyproject.toml                        # Build configuration, dependencies, pytest configuration
    ├── requirements.txt                      # Pinned Python package dependencies
    ├── .env.example                          # Local environment variable template (no cloud keys)
    ├── src/sentron/                          # Application source code
    │   ├── core/                             # Shared models, SQLite storage, event bus, config
    │   ├── agentguard/                       # AgentGuard subsystem (input risk, policy, approval, executor)
    │   ├── crashguard/                       # CrashGuard subsystem (metrics, worker, risk, recovery)
    │   ├── platform/windows/                 # Windows OS adapters (event logs, startup helpers)
    │   └── ui/                               # PySide6 movable floating hub and dashboard views
    ├── tests/                                # Automated test suite
    │   ├── unit/                             # Isolated unit tests for each module
    │   ├── integration/                      # Cross-module and database integration tests
    │   └── fixtures/                         # Synthetic test fixtures and mock data
    └── website/                              # Optional static presentation website
```

---

## 5. Developer Quick Start

### Prerequisites
- Windows 10/11 (required for Windows Event Log integration; cross-platform unit tests runnable on Linux/macOS)
- Python 3.11 or higher
- PowerShell or Windows Terminal

### Setup Instructions
1. Navigate into the application workspace:
   ```powershell
   cd SENTRON_Developer_Starter
   ```
2. Create and activate a virtual environment:
   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```
3. Install package dependencies and development tools:
   ```powershell
   pip install -e ".[dev]"
   ```
4. Verify the test suite:
   ```powershell
   pytest
   ```

For detailed module-by-module instructions, read [START_HERE.md](file:///c:/Users/Honnu/OneDrive/Desktop/kagada/SENTRON/SENTRON_Developer_Starter/START_HERE.md).

---

## 6. Explicit V1 Exclusions

The following capabilities are strictly **out of scope** for V1:
- Automatic process termination, suspension, or process pausing.
- Guaranteed crash prediction or crash prevention claims.
- Universal protection for third-party AI agents that do not route actions through SENTRON.
- Arbitrary shell-command execution or destructive real-world actions in the demo.
- Mandatory external AI APIs, cloud inference, or custom model training.
- Multi-tenant cloud infrastructure, microservices, or agent marketplaces.

---

## 7. Documentation Index

For detailed documentation, refer to the following authoritative guides in `SENTRON_Developer_Starter/`:

- [Architecture Reference](file:///c:/Users/Honnu/OneDrive/Desktop/kagada/SENTRON/SENTRON_Developer_Starter/ARCHITECTURE.md) — Subsystems, schemas, workflows, and boundary specifications.
- [Project Context & Scope](file:///c:/Users/Honnu/OneDrive/Desktop/kagada/SENTRON/SENTRON_Developer_Starter/PROJECT_CONTEXT.md) — Product requirements, non-goals, and boundary rules.
- [Features & Acceptance Criteria](file:///c:/Users/Honnu/OneDrive/Desktop/kagada/SENTRON/SENTRON_Developer_Starter/FEATURES_AND_ACCEPTANCE.md) — The 18 testable acceptance criteria.
- [Module Ownership Matrix](file:///c:/Users/Honnu/OneDrive/Desktop/kagada/SENTRON/SENTRON_Developer_Starter/MODULE_OWNERSHIP.md) — Dev1 through Dev4 responsibilities.
- [Security & Privacy Rules](file:///c:/Users/Honnu/OneDrive/Desktop/kagada/SENTRON/SENTRON_Developer_Starter/SECURITY_RULES.md) — Redaction, default-deny, and offline operation standards.
- [Development Workflow & Setup](file:///c:/Users/Honnu/OneDrive/Desktop/kagada/SENTRON/SENTRON_Developer_Starter/DEVELOPMENT_WORKFLOW.md) — Branching, testing, and implementation protocols.
- [Architecture Decision Log](file:///c:/Users/Honnu/OneDrive/Desktop/kagada/SENTRON/SENTRON_Developer_Starter/DECISIONS.md) — Formally frozen design decisions.
