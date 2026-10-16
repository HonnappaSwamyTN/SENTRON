# Contribution Guidelines & Team Collaboration Standards

> **V1 Specification Status: FROZEN**  
> This document outlines contribution standards, code review procedures, and the Request for Comments (RFC) process for team members contributing to SENTRON V1.

---

## 1. Core Principles

1. **Local-First & Offline**: Every contribution must work offline without external AI services, remote databases, or mandatory network calls.
2. **Honesty in Capabilities**: Never exaggerate system capabilities in documentation, UI, or commit messages. Clearly acknowledge detection limits, non-prevention of crashes, and execution boundaries.
3. **Strict Module Ownership**: Respect team boundaries established in [MODULE_OWNERSHIP.md](file:///c:/Users/Honnu/OneDrive/Desktop/kagada/SENTRON/SENTRON_Developer_Starter/MODULE_OWNERSHIP.md). Never modify another developer's module files without written agreement.
4. **Test-Driven Rigor**: Code changes must include automated tests in `tests/` verifying applicable criteria from [FEATURES_AND_ACCEPTANCE.md](file:///c:/Users/Honnu/OneDrive/Desktop/kagada/SENTRON/SENTRON_Developer_Starter/FEATURES_AND_ACCEPTANCE.md).

---

## 2. Request for Comments (RFC) Protocol for Shared Contracts

All shared data models (`src/sentron/core/models.py`), database schemas (`src/sentron/core/storage.py`), and event bus topics (`src/sentron/core/event_bus.py`) represent shared team contracts.

If an implementation task requires modifying a shared contract:
1. **Do not modify `sentron.core` files directly in your feature branch.**
2. **Draft a Contract RFC**:
   - Post an issue or proposal detailing the proposed schema change, affected modules, and backward-compatibility impact.
   - Example proposal:
     ```markdown
     ### Contract RFC: Add disk_io_read_bytes to SystemSnapshot
     - Proposed field: `disk_io_read_bytes: Optional[int] = None`
     - Reason: Needed by Dev3 for secondary I/O pressure trend evaluation.
     - Modules affected: `crashguard.metrics`, `crashguard.worker`, `core.storage`.
     - Impact on other modules: None (optional field with default None).
     ```
3. **Review & Consensus**: Obtain agreement from all affected module owners (Dev1–Dev4 and Integration Owner).
4. **Integration Owner Commits First**: The Integration Owner merges the contract change to `main` before feature branches consume it.

---

## 3. Pull Request & Review Checklist

Before opening a pull request into `main`:

### Developer Checklist
- [ ] Working branch is branched from latest `main`.
- [ ] No files outside assigned ownership were edited without documented RFC.
- [ ] Code adheres to Python 3.11+ type hints and PEP 8 guidelines.
- [ ] Unit tests are implemented in `tests/unit/` for all new logic.
- [ ] All applicable tests pass: `pytest tests/unit/ -v`.
- [ ] Secrets and API keys are redacted from logs and never hardcoded.
- [ ] CrashGuard code does not terminate or suspend processes.
- [ ] No external AI APIs or cloud infrastructure dependencies were introduced.
- [ ] Completed [MODULE_HANDOFF_TEMPLATE.md](file:///c:/Users/Honnu/OneDrive/Desktop/kagada/SENTRON/SENTRON_Developer_Starter/MODULE_HANDOFF_TEMPLATE.md) attached to the PR description.

### Reviewer Checklist
- [ ] Architectural alignment: Does the change comply with `ARCHITECTURE.md` and `DECISIONS.md`?
- [ ] Test authenticity: Were tests actually executed? Are there fake passes or untested assertions?
- [ ] Security honesty: Does the PR avoid making misleading claims about detection or protection?
- [ ] Performance: Are buffers bounded? Does the change avoid blocking the UI thread?
