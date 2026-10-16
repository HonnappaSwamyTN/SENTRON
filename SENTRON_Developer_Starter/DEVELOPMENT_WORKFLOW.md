# Development Workflow & Setup Guide

> **V1 Specification Status: FROZEN**  
> This document provides the authoritative development setup guide, branching conventions, testing protocols, and coding standards for SENTRON V1.

---

## 1. Environment Prerequisites

- **Operating System**: Windows 10/11 (version 21H2 or later recommended for full Windows Event Log integration).
  - *Note*: Cross-platform development on Linux or macOS is supported for unit testing AgentGuard logic, policy rules, and core SQLite storage using mocked platform adapters.
- **Python Runtime**: Python 3.11 or higher (Python 3.11+ required for modern standard library features and typing).
- **Package Manager**: `pip` (bundled with Python) and `setuptools >= 68`.
- **Shell**: PowerShell 5.1+ or Windows Terminal.

---

## 2. Step-by-Step Developer Setup

### Step 1: Clone and Navigate to Developer Starter
```powershell
# Open terminal in repository root
cd SENTRON_Developer_Starter
```

### Step 2: Create Isolated Virtual Environment
```powershell
# Create virtual environment named .venv
python -m venv .venv

# Activate the virtual environment
.venv\Scripts\Activate.ps1
```

*(If running on Linux/macOS for unit testing: `source .venv/bin/activate`)*

### Step 3: Install Package in Editable Mode with Dev Dependencies
```powershell
# Install sentron package with development dependencies (pytest)
pip install -e ".[dev]"
```

Alternatively, dependencies can be installed using `requirements.txt`:
```powershell
pip install -r requirements.txt
```

### Step 4: Verify Installation
Verify that Python and test tools resolve correctly:
```powershell
python -c "import sentron, PySide6, psutil; print('SENTRON environment verified!')"
pytest --version
```

---

## 3. Automated Testing Guide

All tests reside under `tests/` and are executed using `pytest`.

```
tests/
├── unit/                         # Fast, isolated unit tests (no OS side-effects)
│   ├── test_input_risk.py        # AC-01: Suspicious-input rule matching
│   ├── test_sensitive_data.py    # AC-02: Secret detection & redaction
│   ├── test_policy.py            # AC-03, AC-06: Deterministic policy rules
│   ├── test_approval.py          # AC-04, AC-05: Scoped approval & mutation
│   ├── test_executor.py          # AC-07: Safe mock execution gating
│   ├── test_metrics.py           # AC-09: psutil genuine telemetry
│   ├── test_risk.py              # AC-10: Sustained-risk windows & cooldowns
│   ├── test_evidence.py          # AC-11: Windows Event Log evidence
│   ├── test_recovery.py          # AC-12: Safe recovery guidance
│   ├── test_worker.py            # AC-13: Worker lifecycle & ring buffers
│   ├── test_platform_fallback.py # AC-14: Graceful handling of missing perms
│   └── test_storage.py           # AC-17: SQLite redaction & retention
├── integration/                  # Cross-module & system integration tests
│   ├── test_audit_history.py     # AC-08: Security audit feed & search
│   ├── test_hub_status.py        # AC-15: Floating hub live status
│   ├── test_unified_timeline.py  # AC-16: Searchable timeline & correlation
│   └── test_offline_operation.py # AC-18: Zero external AI & offline mode
└── fixtures/                     # Synthetic test fixtures & mock event data
```

### Running Test Suites

- **Run all unit tests**:
  ```powershell
  pytest tests/unit/ -v
  ```
- **Run all integration tests**:
  ```powershell
  pytest tests/integration/ -v
  ```
- **Run cross-platform tests (excluding Windows-specific tests)**:
  ```powershell
  pytest -m "not windows_only" -v
  ```
- **Run a specific module's test suite (e.g., Dev1)**:
  ```powershell
  pytest tests/unit/test_input_risk.py tests/unit/test_sensitive_data.py -v
  ```

---

## 4. Branching & Contribution Workflow

To maintain clean module boundaries and avoid merge conflicts, team members work in dedicated feature branches:

```
main (Protected, stable release branch)
  │
  ├── feature/dev1-input-risk          (Dev1: agentguard/input_risk.py, sensitive_data.py)
  ├── feature/dev2-policy-executor     (Dev2: agentguard/policy.py, approval.py, executor.py)
  ├── feature/dev3-system-metrics      (Dev3: crashguard/metrics.py, worker.py, risk.py)
  ├── feature/dev4-recovery-evidence   (Dev4: crashguard/evidence.py, recovery.py, platform/)
  └── feature/core-ui-hub              (Integration: core/models.py, storage.py, ui/)
```

### Workflow Steps:
1. **Branch off `main`**: Ensure local `main` is up to date before creating a branch.
2. **Work only in assigned files**: Never touch another developer's module files without prior written agreement.
3. **Write tests alongside code**: Every new function or rule must have corresponding unit test coverage.
4. **Run test verification**: Ensure the test suite passes with zero warnings or errors.
5. **Complete handoff report**: Fill out `MODULE_HANDOFF_TEMPLATE.md` with exact command outputs before opening a pull request.

---

## 5. Coding Standards & Conventions

1. **Python Typing**:
   - All public function signatures, dataclass fields, and class methods must use strict type hints from `typing` (e.g., `Optional[str]`, `List[RiskSignal]`, `Dict[str, Any]`).
2. **PEP 8 Compliance**:
   - Follow standard PEP 8 naming conventions (classes: `PascalCase`, functions/variables: `snake_case`, constants: `UPPER_SNAKE_CASE`).
   - Line length soft limit: 100 characters.
3. **Decoupled Architecture**:
   - Do not import `PySide6` UI components inside domain modules (`agentguard` or `crashguard`).
   - All inter-module communication passes through `sentron.core.models` or the event bus.
4. **Safe Error Handling**:
   - Never use bare `except:` blocks.
   - Handle expected OS-level exceptions (`PermissionError`, `FileNotFoundError`, `psutil.AccessDenied`) gracefully with explicit logging or warning emission.
5. **No Secret Leaks**:
   - Never hardcode secrets, API keys, or personal paths in code, tests, or mock files.
   - Use synthetic dummy strings (e.g., `"sk-dummy-test-key-000000000000000000000000"`) for tests.

---

## 6. Pre-Handoff Checklist

Before submitting a module for integration review:
- [ ] Assigned source files follow module ownership bounds in `MODULE_OWNERSHIP.md`.
- [ ] Corresponding acceptance criteria from `FEATURES_AND_ACCEPTANCE.md` are covered by tests.
- [ ] `pytest tests/unit/ -v` passes cleanly.
- [ ] No external cloud AI SDKs or network client libraries were added.
- [ ] Detected secrets are sanitized and redacted from logs.
- [ ] No automatic process killing or suspension logic was introduced.
- [ ] `MODULE_HANDOFF_TEMPLATE.md` is populated with actual test run outputs.
