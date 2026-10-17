# Dev 2 Implementation Notes

## Implemented in this starter patch

- `src/sentron/core/models.py`: shared `ActionRequest`, `Decision`, `PolicyResult`, `AuditEvent`, and `ExecutionResult` contracts. This file was missing even though `ARCHITECTURE.md` described it.
- `src/sentron/agentguard/policy.py`: deterministic rules; default `ASK`; explicit `ALLOW`; `BLOCK` takes precedence; risk flags and sensitive classifications require review; selected prohibited operations are blocked.
- `src/sentron/agentguard/approval.py`: expiring, single-use-by-default approvals bound to agent/tool/operation/target/destination/recipient/purpose/task/data classification/risk flags/untrusted-context references/session.
- `src/sentron/agentguard/executor.py`: controlled execution boundary; blocks execution before authorization; records policy, approval, and execution outcomes through an injected audit sink; does not log exception messages.
- Unit tests covering policy decisions, scope changes, expiry, session binding, executor gating, and audit events.

## Current limitations (intentional)

- `ApprovalManager` is in-memory. Approval persistence is not implemented.
- `InMemoryAuditLog` is for development/tests only. It must later be connected to the shared SQLite event store through the `AuditSink` interface.
- The action handler is injected. Use only a safe mock handler for the initial demo; this patch does not implement real file, network, email, or shell actions.
- Dev 1's analyzer is not implemented here. Its structured `risk_flags` can be passed into `ActionRequest` once the Dev 1 interface is agreed.
- The policy defaults to `ASK` unless an explicit allow rule matches. Do not add broad allow rules just to make the demo look smoother.
- `ALWAYS_BLOCK_OPERATIONS` is a conservative initial list and should be reviewed against the final operation vocabulary before release.

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
)
policy = PolicyEngine([
    PolicyRule(
        decision=Decision.ALLOW,
        tool_name="mock_file_tool",
        operation="read_file",
        reason_code="demo_read_allowed",
        explanation="Explicitly permitted mock read.",
    )
])
approvals = ApprovalManager()
audit = InMemoryAuditLog()
executor = ControlledExecutor(policy, approvals, lambda action: {"mock": True}, audit)
result = executor.execute(request)
print(result.status)  # executed
```

## Validation performed

Run from the project root:

```bash
python -m pytest -q
python -m compileall -q src tests
```

At the time this patch was prepared, pytest reported **18 passed** and compileall completed successfully. This starter ZIP did not contain a `.git` directory, so Git status/diff could not be inspected in this extracted copy.
