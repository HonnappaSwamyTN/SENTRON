# Architecture Decision Records (ADR Log)

> **V1 Specification Status: FROZEN**  
> This document records the authoritative architectural decisions governing SENTRON V1. All decisions listed below are finalized and binding.

---

## ADR-001: Architecture Pattern — Modular Monolith
- **Date**: Frozen for V1
- **Status**: Accepted
- **Context**: The team evaluated whether to split SENTRON into microservices (e.g., local daemon process communicating over gRPC/HTTP with a frontend) or organize as a modular monolith.
- **Decision**: SENTRON is implemented as a **Modular Monolith** in Python. Subsystems (`core`, `agentguard`, `crashguard`, `platform`, `ui`) run within a unified application process with strict package boundaries and decoupled interfaces.
- **Consequences**:
  - Eliminates IPC/networking latency, port conflicts, and unauthenticated local HTTP daemon vulnerabilities.
  - Simplifies local deployment, packaging, and debugging.
  - Microservices, Docker, and multi-service orchestrators are explicitly excluded from V1.

---

## ADR-002: Core Technology Stack Finalization
- **Date**: Frozen for V1
- **Status**: Accepted (Resolves previous undecided item #12)
- **Context**: The starter draft left open the exact Python version, UI framework, storage engine, and testing framework.
- **Decision**: The V1 stack is finalized as:
  - **Runtime**: Python 3.11+
  - **Desktop UI**: PySide6 (Qt 6 for Python)
  - **Local Event Store**: SQLite 3 (native embedded SQL engine)
  - **System Metrics**: `psutil` (>=5.9.0)
  - **OS Telemetry**: Windows APIs and Windows Event Logs (`win32evtlog`, `wevtutil`)
  - **Testing Framework**: `pytest` (>=7.4.0)
- **Consequences**:
  - Consistent Python 3.11+ type hints across all modules.
  - Native Windows desktop integration with thread-safe UI signals via PySide6.
  - Zero requirement for external database servers or cloud connectivity.

---

## ADR-003: UI Architecture — Movable Floating Desktop Hub
- **Date**: Frozen for V1
- **Status**: Accepted
- **Context**: User workflow requires continuous visibility into agent operations and system health without consuming heavy screen real estate.
- **Decision**: SENTRON provides a **movable floating desktop hub** built with PySide6. The hub displays a compact, always-accessible status widget showing active health metrics and pending approvals, expandable into dedicated module dashboards.
- **Consequences**:
  - Low visual overhead for users during normal desktop activity.
  - UI accurately reflects module status; it never claims a module is active or protecting if its background worker is stopped or permissions are missing.

---

## ADR-004: Zero External AI APIs & 100% Deterministic Governance in V1
- **Date**: Frozen for V1
- **Status**: Accepted
- **Context**: Evaluated whether to integrate cloud LLM APIs (e.g., OpenAI, Anthropic) or local neural models for prompt-injection detection or crash diagnosis.
- **Decision**: **AI integration is NOT required for V1.** All input analysis, policy evaluations, and sustained-risk detections must use deterministic rules, regex heuristics, and mathematical thresholds.
- **Rationale**:
  - Guarantees 100% offline, local-first operation with zero internet dependency.
  - Eliminates API key management, cloud latency, rate limits, and external service costs.
  - Ensures predictable, auditable security enforcement without generative hallucinations.
- **Future Considerations**: Component boundaries are kept clean so that optional AI-assisted analysis can be added in a future version without rewriting core abstractions. No speculative AI code may be added in V1.

---

## ADR-005: The Controlled Execution Boundary
- **Date**: Frozen for V1
- **Status**: Accepted
- **Context**: Scope of security guarantees regarding arbitrary third-party software on the host OS.
- **Decision**: SENTRON enforces security policies exclusively at its **controlled execution boundary** (`sentron.agentguard.executor`). Supported agent integrations must submit structured action requests prior to execution.
- **Consequences**:
  - SENTRON makes **no claim of universal protection** for arbitrary third-party agents or processes that do not route actions through the executor.
  - Blocked actions never reach the executor.
  - In the V1 demo, a safe mock executor is used. Arbitrary shell commands (`cmd`, `powershell`) and destructive file/network operations are strictly excluded.

---

## ADR-006: CrashGuard Non-Interference — Passive Monitoring & Advisory Recovery
- **Date**: Frozen for V1
- **Status**: Accepted
- **Context**: Evaluated whether CrashGuard should automatically terminate or suspend runaway processes when sustained memory or CPU thresholds are breached.
- **Decision**: **CrashGuard is strictly passive and advisory in V1. It will NEVER automatically kill, terminate, suspend, or pause any process.**
- **Rationale**:
  - Automatic process termination risks catastrophic data loss (e.g., terminating an editor or database with unsaved state) and stability hazards.
  - Recovery guidance presents safe, actionable recommendations (save work, close non-essential applications) for human execution.
- **Consequences**:
  - Eliminates accidental termination risks.
  - CrashGuard displays genuine observations separated from inferred hypotheses and never claims guaranteed crash prevention.

---

## ADR-007: Genuine Telemetry & Graceful Fallback
- **Date**: Frozen for V1
- **Status**: Accepted
- **Context**: Handling unavailable system metrics, restricted permissions, and simulated demonstration data.
- **Decision**: CrashGuard dashboards must display **genuine measurements** collected via `psutil` and Windows Event Logs. Simulated data must never be presented as real system telemetry.
- **Consequences**:
  - If a metric cannot be collected (e.g., Event Log access requires elevation), the system flags the metric in `unavailable_metrics`, surfaces a clear warning in the UI, and continues operating without failing.

---

## ADR-008: Local SQLite Event Store & Temporal Correlation
- **Date**: Frozen for V1
- **Status**: Accepted
- **Context**: Need for unified event logging across security audits and system health telemetry.
- **Decision**: Store all security events, policy decisions, health alerts, and recovery recommendations in a shared local SQLite database. Enable unified timeline queries and timestamp correlation.
- **Consequences**:
  - Provides a single, local, privacy-preserving audit trail.
  - Detects and redacts secrets before persistence.
  - UI and documentation explicitly state: **temporal correlation between agent actions and resource spikes provides investigative context, not proof of causation**.

---

## ADR-009: Explicit V1 Exclusions & Non-Goals
- **Date**: Frozen for V1
- **Status**: Accepted
- **Decision**: The following features are explicitly out of scope for V1:
  1. Automatic process killing, suspension, or pausing.
  2. Guaranteed crash prediction or prevention claims.
  3. Universal protection for arbitrary or unintegrated AI agents.
  4. Arbitrary shell-command execution or destructive real-world actions in the demo.
  5. Mandatory external AI APIs, cloud LLMs, or custom model training.
  6. Cloud multi-user infrastructure, microservices, or remote databases.
  7. Agent marketplaces or third-party plugin registries.
