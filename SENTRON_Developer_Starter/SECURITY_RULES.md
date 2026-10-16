# Security, Privacy & Integrity Rules

> **V1 Specification Status: FROZEN**  
> This document establishes the mandatory security rules, privacy safeguards, and architectural boundaries for SENTRON V1. Every line of code, policy definition, and diagnostic routine must strictly follow these rules.

---

## 1. The Execution Boundary Axiom

**SENTRON enforces policy and security governance exclusively at its supported integration and controlled execution boundary.**

- **No Universal Protection Claim**: SENTRON cannot intercept or control arbitrary third-party AI agents or background processes that do not route tool invocations through the `sentron.agentguard.executor` interface. We must never claim universal endpoint protection.
- **Strict Pre-Execution Gating**: No supported tool, action, or side-effect may be invoked before the Deterministic Policy Engine evaluates the action and returns `ALLOW` (or an approved `ASK`).
- **Blocked Actions**: Actions evaluated as `BLOCK` must be terminated immediately. The execution adapter must never be called for a blocked action.

---

## 2. Local-First Privacy & Zero-Cloud Operation

1. **Zero External AI Services**: SENTRON V1 operates with 100% local, deterministic algorithms. No external cloud AI services (OpenAI, Anthropic, Google, Azure, etc.) may be invoked for core functionality.
2. **Zero Mandatory Network Connectivity**: Core desktop governance, metrics collection, risk evaluation, and database querying must function completely offline.
3. **No External Telemetry or Tracking**: The application must never transmit telemetry, user metrics, prompt text, or hardware logs to external servers or cloud endpoints.
4. **Local SQLite Persistence**: All security audit logs and health metrics remain on the user's local disk in an embedded SQLite database.
5. **Configurable Event Retention**: The local storage engine must provide configurable retention periods (e.g., purge logs older than 7, 30, or 90 days) to prevent unbounded disk growth.

---

## 3. Sensitive Data Detection & Sanitization

1. **Detection Patterns**: The Sensitive-Data Detector must identify recognizable API keys (e.g., `sk-...`, `ghp_...`, `AKIA...`), passwords, private tokens, and confidential data patterns.
2. **Mandatory Redaction in Logs**: Whenever an action request or prompt text is recorded in the SQLite audit log or application log, detected secrets must be sanitized with replacement tokens (e.g., `[REDACTED_API_KEY]`, `[REDACTED_PASSWORD]`).
3. **No Raw Secrets in Cleartext**: Raw credentials must never be written to plaintext log files, exported in unencrypted diagnostics, or presented in plain text on dashboards.
4. **Honesty on Pattern Limits**: Pattern-based regular expressions and entropy checks cannot guarantee detection of all confidential data or custom secret formats. Documentation and UI must state this limitation explicitly.

---

## 4. Policy Engine & Approval Security

1. **Default-Deny for Unknown & High-Impact Operations**:
   - Unknown operations, malformed requests, or requests with missing required fields must evaluate to `BLOCK` or `ASK`. They must **never default to `ALLOW`**.
   - High-impact operations (file deletion, execution of binaries, secret transmission, external network requests) must require explicit human approval (`ASK`) or be blocked.
2. **Decoupled Risk Signals**:
   - Findings from the Suspicious-Input Analyzer are risk signals, not authorization permits.
   - A low risk score from the input analyzer can never override a policy rule requiring approval.
3. **Scoped Approval Invalidation**:
   - Approvals are strictly non-transferable and scoped to: Agent ID, Operation, Target canonical path/resource, Destination/recipient, Stated Purpose, and Expiration timestamp.
   - Any modification to an approved action (e.g., changing the target file from `draft.txt` to `passwords.txt`) immediately invalidates the approval token and halts execution.
   - No blanket or permanent approvals are permitted in V1.

---

## 5. CrashGuard Operational Safety & Non-Interference

1. **Strictly Non-Destructive Advisory in V1**:
   - CrashGuard is an observational and advisory system.
   - **CRITICAL**: The application must **NEVER automatically kill, suspend, pause, or terminate processes in V1**.
   - All recovery actions must be presented as safe, informative recommendations for the human user to execute manually.
2. **Observation vs. Causation Separation**:
   - Diagnostic output must strictly distinguish confirmed facts (e.g., "Memory utilization reached 96%") from inferred hypotheses (e.g., "Process Y may be leaking memory").
   - Temporal correlation between an AgentGuard action and a CrashGuard resource spike must never be presented as proven causation.
3. **No Guaranteed Crash Prevention**:
   - CrashGuard detects sustained hardware pressure and Windows crash records. It does **not guarantee crash prediction or prevention**. Marketing or technical claims of absolute crash immunity are prohibited.

---

## 6. Telemetry Honesty & Integrity

1. **Genuine Telemetry Only**:
   - CrashGuard must display real system measurements obtained via `psutil` and Windows APIs.
   - **Simulated data must never be presented as real system telemetry.**
   - In unit tests where synthetic data is utilized, tests must be explicitly isolated from production dashboard feeds.
2. **Honest Availability Reporting**:
   - The UI must never display a module as "Active" or "Protecting" if the background worker is stopped, permissions are missing, or required adapters are disconnected.
   - Missing or inaccessible metrics (e.g., due to unprivileged access to specific Windows Event Logs) must be recorded in `unavailable_metrics` and reported transparently.

---

## 7. Performance & Resource Bounding

1. **Non-Blocking UI**: All system metrics collection, Windows Event Log queries, and file I/O must execute outside the PySide6 UI thread. The UI must remain responsive (latency < 50ms).
2. **Bounded Buffers**: Metrics history in memory must use bounded circular buffers (e.g., maximum 60 samples) to prevent memory leaks during long-running sessions.
3. **Severe Resource Pressure Backoff**: If host CPU exceeds 95% or available memory drops below 5%, the monitoring worker must suppress expensive optional diagnostics (such as deep process tree inspection or heavy log scans) to avoid contributing to system collapse.
4. **Managed Lifecycle**: Background threads and workers must implement clean shutdown hooks responding to application exit signals within 2 seconds.
