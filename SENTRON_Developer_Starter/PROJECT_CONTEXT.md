# Authoritative Project Context & Vision

> **V1 Specification Status: FROZEN**  
> This document establishes the authoritative product definition, operational constraints, non-goals, and security boundaries for SENTRON V1. All team members and coding assistants must strictly adhere to these specifications.

---

## 1. Product Definition

**SENTRON** is a local-first Windows desktop protection suite designed to provide transparency, governance, and stability on developer and workstation environments where AI agents operate alongside human workflows.

SENTRON operates through a lightweight, **movable floating desktop hub** that provides unified access to two primary subsystems:

1. **AgentGuard**: Security and permission enforcement for supported AI-agent actions. It intercepts proposed actions, analyzes untrusted inputs for injection attacks, scans for sensitive data/secrets, evaluates actions against deterministic policies (`ALLOW`, `ASK`, `BLOCK`), manages scoped human-in-the-loop approvals, and dispatches permitted operations through a controlled execution gatekeeper.
2. **CrashGuard**: Real system-health monitoring, sustained-risk alerts, Windows evidence collection, and safe recovery recommendations. It continuously monitors system resources via `psutil` outside the UI thread, identifies sustained threshold breaches using duration windows and cooldowns, captures Windows Event Log evidence (crashes, hangs, critical errors), and guides users toward non-destructive recovery steps.

Security audit records and system health telemetry converge into a shared **Local SQLite Event Store**, enabling unified timeline exploration and timestamp correlation.

---

## 2. Core Operational Constraints

- **Local-First & Zero Cloud Dependencies**: SENTRON operates entirely on the local machine. Core functionality must function without network connectivity, cloud infrastructure, or external AI APIs (OpenAI, Anthropic, Google, etc.).
- **Deterministic Governance**: Authorization decisions and health alerts are computed using deterministic rules, regex patterns, and mathematical thresholds. No non-deterministic generative models are used in critical decision loops.
- **Genuine Telemetry Only**: CrashGuard relies strictly on genuine system measurements via `psutil` and Windows APIs. Simulated data must never be presented as live system telemetry. Unavailable metrics must be explicitly reported as unavailable.
- **Controlled Non-Interference**: CrashGuard is an advisory system. **It must never automatically kill, suspend, or pause running processes in V1.** All recovery actions are recommendations requiring explicit user execution.
- **Modular Monolith**: The application is organized as a single deployable Python package with strict internal separation of concerns:
  - `sentron.core` (shared contracts, SQLite storage, event bus, config)
  - `sentron.agentguard` (input risk, sensitive data, policy, approval, executor)
  - `sentron.crashguard` (metrics, worker, sustained risk, evidence, recovery)
  - `sentron.platform.windows` (Windows-specific OS adapters)
  - `sentron.ui` (PySide6 desktop hub and module dashboards)

---

## 3. Technology Stack Decisions

| Component | Selected Technology | Constraints & Rationale |
| :--- | :--- | :--- |
| **Language Runtime** | Python 3.11+ | Modern type annotations, async/threading primitives, cross-platform testing |
| **Desktop UI** | PySide6 (Qt for Python) | Native Windows look-and-feel, floating movable hub widget, robust signal/slot thread isolation |
| **Local Event Store** | SQLite 3 | Embedded, zero-configuration local ACID persistence, fast indexed querying |
| **Hardware Metrics** | `psutil` (>=5.9.0) | Cross-process CPU, memory, and disk telemetry on Windows |
| **OS Diagnostics** | Windows APIs / Event Logs | Native collection of Application Hang, Crash, and critical system events |
| **Test Automation** | `pytest` (>=7.4.0) | Automated unit, integration, and platform-specific test suites |

No microservices, multi-tenant databases, or unnecessary third-party frameworks may be introduced.

---

## 4. Security Boundary & Honest Limitations

### The Controlled Execution Boundary Axiom
**SENTRON only protects actions that actually pass through its supported integration and controlled executor.**  
If an AI agent operates outside this controlled execution path (e.g., executing direct system calls or using unintegrated tools), SENTRON cannot intercept or govern that action. We make **no claim of universal protection** for arbitrary or unintegrated third-party agents.

### Honesty in Heuristics and Pattern Detection
- **Input Risk**: Rule-based detection of prompt injections and manipulation attempts provides risk signals and evidence, not definitive mathematical proof of malice. Low risk scores never override strict policy rules.
- **Sensitive Data Detection**: Regular expressions and entropy checks detect known API-key patterns, passwords, and confidential keywords. They cannot guarantee detection of arbitrary or novel confidential formats. Raw detected secrets must be redacted before logging.
- **Crash Prediction**: CrashGuard identifies sustained resource pressure and historical error records. **It does not predict future crashes with certainty and does not claim to prevent every system failure.**
- **Temporal Correlation vs. Causation**: Correlating an AgentGuard action and a CrashGuard resource spike by timestamp provides investigative context; it is not proof of causal relationship.

---

## 5. Explicit V1 Exclusions (Out of Scope)

The following items are formally excluded from the V1 release:
1. **Automatic Process Termination**: No automatic killing, suspending, or pausing of processes.
2. **Guaranteed Crash Prediction/Prevention**: No marketing or architectural claims of absolute crash prevention.
3. **Universal Third-Party Agent Interception**: No OS-level kernel hooks or universal agent interception.
4. **Arbitrary Shell Execution in Demo**: No arbitrary shell or destructive file/network commands in the initial demo executor.
5. **Mandatory External AI APIs / Custom Model Training**: No dependency on cloud LLMs, local LLM servers, or proprietary model training.
6. **Multi-User Cloud Infrastructure**: No centralized servers, remote user databases, or cloud sync.
7. **Microservice Architectures**: No Docker, Kubernetes, or microservice split.
8. **Agent Marketplaces**: No third-party agent repositories or plugin ecosystems.
