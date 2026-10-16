# Module Ownership Matrix & Team Assignments

> **V1 Specification Status: FROZEN**  
> This document establishes team assignments, file boundaries, component responsibilities, and interface handoff protocols for SENTRON V1. Existing assignments are preserved and clarified to align with the frozen specification.

---

## 1. Developer Assignment Overview

```
+-----------------------------------------------------------------------------------+
|                                 INTEGRATION OWNER                                 |
|                (Shared Core, Desktop UI Hub, Packaging & Lifecycle)               |
|  Files: src/sentron/core/*, src/sentron/ui/*, src/sentron/main.py                 |
+-----------------------------------------+-----------------------------------------+
                                          |
                      Shared Contracts & Data Schemas
                                          |
+-----------------------------------------+-----------------------------------------+
|                  AgentGuard             |               CrashGuard                |
+--------------------+--------------------+--------------------+--------------------+
|        DEV 1       |        DEV 2       |        DEV 3       |        DEV 4       |
|    AgentGuard A    |    AgentGuard B    |    CrashGuard A    |    CrashGuard B    |
|                    |                    |                    |                    |
| - Suspicious-Input | - Deterministic    | - Metrics          | - Windows Evidence |
|   Analyzer         |   Policy Engine    |   Collector        |   Collector        |
| - Sensitive-Data   | - Scoped Approval  | - Background       | - Diagnostics &    |
|   Detector         |   Manager          |   Worker           |   Safe Recovery    |
| - Secret Redaction | - Safe Mock        | - Sustained-Risk   |   Recommendations  |
|                    |   Executor         |   Detector         |                    |
|                    | - Security Audit   |                    |                    |
|                    |   History Logger   |                    |                    |
+--------------------+--------------------+--------------------+--------------------+
```

---

## 2. Detailed Module Assignments

### Dev1 — AgentGuard A: Input & Sensitive-Data Security
- **Assigned Components**:
  1. **Suspicious-Input Analyzer**: Deterministic rule-based detection for prompt injections, system instruction overrides, jailbreaks, and agent manipulation patterns. Emits `RiskSignal` records.
  2. **Sensitive-Data Detector**: Regex/entropy identification of API keys, passwords, and confidential patterns in action payloads.
  3. **Sanitization / Redaction**: Utilities to sanitize secret tokens into `[REDACTED_*]` strings for audit logging.
- **Owned Source Files**:
  - `src/sentron/agentguard/input_risk.py`
  - `src/sentron/agentguard/sensitive_data.py`
  - `src/sentron/agentguard/__init__.py` (co-maintained with Dev2)
- **Owned Test Files**:
  - `tests/unit/test_input_risk.py`
  - `tests/unit/test_sensitive_data.py`
- **Governing Acceptance Criteria**: `AC-01`, `AC-02`.
- **Boundaries & Prohibitions**:
  - Analyzer provides **signals and evidence only**; it must never independently authorize or execute any action.
  - No external AI API calls, cloud inference, or external dependencies.
  - Must document pattern-based limits (cannot detect unknown or custom secret formats).

---

### Dev2 — AgentGuard B: Policy, Approvals, Executor & Audit
- **Assigned Components**:
  1. **Deterministic Policy Engine**: Maps `ActionRequest` objects to authoritative `PolicyDecision` (`ALLOW`, `ASK`, `BLOCK`) with reason codes. Enforces default-deny on high-impact/unknown operations.
  2. **Scoped Approval Manager**: Manages human approval tokens bound strictly by agent ID, operation, target, destination, purpose, and expiration. Handles scope invalidation on mutation.
  3. **Controlled Executor Gatekeeper**: Pre-execution gating ensuring blocked actions never execute and pending approvals halt execution. Dispatches to safe mock executor in V1 demo.
  4. **Security Audit Logger**: Records sanitized audit events to the local SQLite database.
- **Owned Source Files**:
  - `src/sentron/agentguard/policy.py`
  - `src/sentron/agentguard/approval.py`
  - `src/sentron/agentguard/executor.py`
  - `src/sentron/agentguard/audit.py`
- **Owned Test Files**:
  - `tests/unit/test_policy.py`
  - `tests/unit/test_approval.py`
  - `tests/unit/test_executor.py`
  - `tests/integration/test_audit_history.py` (co-maintained with Integration Owner)
- **Governing Acceptance Criteria**: `AC-03`, `AC-04`, `AC-05`, `AC-06`, `AC-07`, `AC-08`.
- **Boundaries & Prohibitions**:
  - Blocked actions must never reach the executor.
  - No arbitrary shell commands or destructive disk/network operations in the demo executor.
  - Must never claim protection for agents that bypass the controlled executor.

---

### Dev3 — CrashGuard A: Metrics, Background Worker & Sustained Risk
- **Assigned Components**:
  1. **Metrics Collector**: Samples authentic hardware telemetry via `psutil` (CPU total/per-core, RAM available/used, disk free/utilization, top N processes, and delta trends).
  2. **Background Monitoring Worker**: Runs sampling on a dedicated thread outside the UI loop with configurable interval (5–10s), bounded circular buffer, clean shutdown, and severe-load backoff.
  3. **Sustained-Risk Detector**: Evaluates snapshots against thresholds, duration windows, and alert cooldowns. Differentiates transient spikes from sustained pressure.
- **Owned Source Files**:
  - `src/sentron/crashguard/metrics.py`
  - `src/sentron/crashguard/worker.py`
  - `src/sentron/crashguard/risk.py`
  - `src/sentron/crashguard/__init__.py` (co-maintained with Dev4)
- **Owned Test Files**:
  - `tests/unit/test_metrics.py`
  - `tests/unit/test_worker.py`
  - `tests/unit/test_risk.py`
- **Governing Acceptance Criteria**: `AC-09`, `AC-10`, `AC-13`, `AC-14` (metrics portion).
- **Boundaries & Prohibitions**:
  - Must display genuine measurements; **simulated data must never be presented as real**.
  - High CPU utilization alone must not be reported as proof of an impending crash.
  - Worker must not block or stutter the PySide6 UI thread.

---

### Dev4 — CrashGuard B: Windows Evidence & Safe Recovery
- **Assigned Components**:
  1. **Windows Evidence Collector**: Queries Windows Event Logs (`Application Error`, `Application Hang`, unexpected shutdowns, driver/update events) via native interfaces. Gracefully degrades when unprivileged.
  2. **Diagnostics & Safe Recovery Advisor**: Formulates non-destructive user recommendations (save open work, close heavy apps, inspect runaway processes). Strictly separates confirmed facts from inferred causes.
- **Owned Source Files**:
  - `src/sentron/crashguard/evidence.py`
  - `src/sentron/crashguard/recovery.py`
  - `src/sentron/platform/windows/event_log.py`
  - `src/sentron/platform/windows/__init__.py`
- **Owned Test Files**:
  - `tests/unit/test_evidence.py`
  - `tests/unit/test_recovery.py`
  - `tests/unit/test_platform_fallback.py`
- **Governing Acceptance Criteria**: `AC-11`, `AC-12`, `AC-14` (evidence portion).
- **Boundaries & Prohibitions**:
  - **Strictly prohibited: Automatically killing, terminating, suspending, or pausing processes in V1.**
  - Never claim guaranteed crash prevention or prediction.
  - Confirmed observations must be explicitly decoupled from speculative diagnoses.

---

### Integration Owner / Core Lead
- **Scope & Role Definition**:
  - In a 4-developer team, this responsibility is formally agreed upon by the team (either held by a designated Team Lead or co-managed with one of the developer roles).
- **Assigned Components**:
  1. **Movable Floating Desktop Hub UI**: PySide6 floating desktop icon, dashboard panels for AgentGuard & CrashGuard, and accurate operational status representation.
  2. **Shared Core**: Typed models (`sentron.core.models`), configuration manager (`sentron.core.config`), in-memory event bus (`sentron.core.event_bus`), and local SQLite persistence (`sentron.core.storage`).
  3. **Unified Timeline**: Cross-module correlation search interface and retention purger.
  4. **Packaging & Startup**: Application entry point (`src/sentron/main.py`), startup scripts, and `pyproject.toml`.
- **Owned Source Files**:
  - `src/sentron/main.py`
  - `src/sentron/core/*`
  - `src/sentron/ui/*`
  - `src/sentron/__init__.py`
- **Owned Test Files**:
  - `tests/integration/test_hub_status.py`
  - `tests/integration/test_unified_timeline.py`
  - `tests/integration/test_offline_operation.py`
  - `tests/unit/test_storage.py`
- **Governing Acceptance Criteria**: `AC-15`, `AC-16`, `AC-17`, `AC-18`.

---

## 3. Inter-Module Contracts & Dependencies

```
+-----------------------------------------------------------------------------------+
| Module A              Direction  Module B              Contract Model             |
| :---                  :---:      :---                  :---                       |
| AgentGuard (Dev1/2)   ------>    Core Storage          ActionRequest, PolicyResult|
| AgentGuard (Dev2)     ------>    AgentGuard (Dev1)     RiskSignal, SecretFinding  |
| CrashGuard (Dev3)     ------>    CrashGuard (Dev4)     SystemSnapshot, RiskAlert  |
| CrashGuard (Dev3/4)   ------>    Core Storage          RiskAlert, WindowsEvidence |
| UI (Integration)      <------    Core Event Bus        UnifiedEvent, SystemSnapshot|
+-----------------------------------------------------------------------------------+
```

1. **Shared Contract Rule**: No developer may alter `src/sentron/core/models.py` without submitting an RFC and receiving agreement from all affected module owners.
2. **Decoupled Imports**: Subsystems must import shared models from `sentron.core.models` and never import internal private helpers from another subsystem.

---

## 4. Module Handoff Protocol

When a developer completes their assigned module slice:
1. All unit tests in the module's test file must pass cleanly.
2. Complete the standardized report using [MODULE_HANDOFF_TEMPLATE.md](file:///c:/Users/Honnu/OneDrive/Desktop/kagada/SENTRON/SENTRON_Developer_Starter/MODULE_HANDOFF_TEMPLATE.md).
3. The report must state exact commands run, test counts, limitations, and integration notes.
4. Peer review must verify that no out-of-scope files were edited.
