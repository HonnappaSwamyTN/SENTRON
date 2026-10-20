# Dev 2 Implementation Notes: AgentGuard Policy, Approval, and Execution

## Implemented in this version

- `src/sentron/core/models.py`:
  - Shared `ActionRequest`, `Decision`, `PolicyResult`, `AuditEvent`, and `ExecutionResult` contracts.
  - Added `session_id: str | None = None` to `AuditEvent` dataclass for end-to-end audit session correlation.
  - Fail-closed constructor validation ensuring `agent_id`, `tool_name`, and `operation` are non-empty strings.
- `src/sentron/agentguard/policy.py`:
  - Strict agent-specific policy scoping: ALLOW rules require explicit `agent_id`, `tool_name`, `operation`, and resource target or destination.
  - Overly broad rule rejection: Rejects wildcards (`*`, `?`) and broad catch-alls (`all`, `any`) in ALLOW rules.
  - Deterministic evaluation:
    - Precedence: `BLOCK` > `ASK` > `ALLOW`.
    - Always-block operations (`disable_security`, `steal_credentials`, `exfiltrate_data`, `format_disk`).
    - Dev1 suspicious-input `risk_flags` trigger `Decision.ASK` (`risk_flags_present`).
    - Sensitive data classifications trigger `Decision.ASK` (`sensitive_data_requires_review`).
    - Fallback is `Decision.ASK` (`no_matching_allow_rule`).
  - Safe denial on malformed requests: Missing or invalid agent identities (`*`, empty, none) return `Decision.BLOCK` with `invalid_agent_identity`.
- `src/sentron/agentguard/approval.py`:
  - Bound approval scopes capturing agent, tool, operation, target, destination, recipient, purpose, task ID, data classification, risk flags, untrusted context references, and session ID.
  - Strict bidirectional session validation: Rejects session mismatches, and prevents sessionless requests from being authorized using unrelated supplied session IDs.
  - Prevents cross-agent authorization: Approval granted to Agent A cannot authorize Agent B.
  - Safe expiry and single-use consumption.
- `src/sentron/agentguard/executor.py`:
  - Absolute fail-closed boundary: Injected handler is only dispatched when policy evaluates to `Decision.ALLOW` or a valid scoped approval is verified and consumed.
  - Full audit emission across all lifecycle events (`policy_decision`, `approval_required`, `approval_rejected`, `approval_accepted`, `execution_succeeded`, `execution_failed`) preserving `session_id`.
  - Secret protection: Exception messages from action handlers are not leaked to audit records.
- `src/sentron/agentguard/audit.py`:
  - Persistent SQLite audit logging (`SqliteAuditLog`) storing privacy-conscious, redacted event records.
  - `session_id` persisted in payload and searchable via `search_events(session_id=...)`.

## Quick usage example

```python
from sentron.agentguard.approval import ApprovalManager
from sentron.agentguard.executor import ControlledExecutor, InMemoryAuditLog
from sentron.agentguard.policy import PolicyEngine, PolicyRule
from sentron.core.models import ActionRequest, Decision

request = ActionRequest(
    agent_id="demo-agent",
    tool_name="mock_file_tool",
    operation="read_file",
    target="sample.txt",
    session_id="session-001",
)
policy = PolicyEngine([
    PolicyRule(
        decision=Decision.ALLOW,
        agent_id="demo-agent",
        tool_name="mock_file_tool",
        operation="read_file",
        target="sample.txt",
        reason_code="demo_read_allowed",
        explanation="Explicitly permitted mock read.",
    )
])
approvals = ApprovalManager()
audit = InMemoryAuditLog()
executor = ControlledExecutor(policy, approvals, lambda action: {"status": "success"}, audit)
result = executor.execute(request)
print(result.status)  # executed
```

## Validation performed

Run from `SENTRON_Developer_Starter`:

```bash
python -m pytest tests -q
python -m compileall -q src tests
```

- Total tests passed: **102 passed** (including 54 Dev2 unit tests, 22 Dev1 input risk / sensitive data tests, and 26 system/integration/UI tests).
- Python syntax compilation: 100% clean (code 0).

