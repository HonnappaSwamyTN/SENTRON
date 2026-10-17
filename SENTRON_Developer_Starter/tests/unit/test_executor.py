from sentron.agentguard.approval import ApprovalManager
from sentron.agentguard.executor import ControlledExecutor, InMemoryAuditLog
from sentron.agentguard.policy import PolicyEngine, PolicyRule
from sentron.core.models import ActionRequest, Decision


def request(**overrides):
    values = dict(agent_id="agent-a", tool_name="mock_tool", operation="read_file", target="demo.txt")
    values.update(overrides)
    return ActionRequest(**values)


def make_executor(rules=()):
    calls = []
    audit = InMemoryAuditLog()
    approvals = ApprovalManager()
    executor = ControlledExecutor(
        policy_engine=PolicyEngine(rules), approval_manager=approvals,
        action_handler=lambda action: calls.append(action.action_id) or {"mock": True},
        audit_sink=audit,
    )
    return executor, approvals, audit, calls


def test_blocked_action_never_reaches_handler():
    executor, _, audit, calls = make_executor()
    result = executor.execute(request(operation="disable_security"))
    assert result.status == "blocked"
    assert calls == []
    assert any(event.event_type == "policy_decision" for event in audit.events)


def test_ask_action_never_runs_without_approval():
    executor, _, audit, calls = make_executor()
    result = executor.execute(request())
    assert result.status == "approval_required"
    assert calls == []
    assert any(event.event_type == "approval_required" for event in audit.events)


def test_matching_approval_allows_ask_action_once():
    executor, approvals, audit, calls = make_executor()
    action = request()
    approval = approvals.grant(action)
    result = executor.execute(action, approval_id=approval.approval_id)
    assert result.status == "executed"
    assert result.decision is Decision.ASK
    assert calls == [action.action_id]
    assert any(event.event_type == "execution_succeeded" for event in audit.events)


def test_explicit_allow_rule_executes_without_approval():
    rule = PolicyRule(decision=Decision.ALLOW, agent_id="agent-a", operation="read_file", tool_name="mock_tool", target="demo.txt")
    executor, _, _, calls = make_executor([rule])
    action = request()
    result = executor.execute(action)
    assert result.status == "executed"
    assert result.decision is Decision.ALLOW
    assert calls == [action.action_id]


def test_invalid_approval_never_reaches_handler():
    executor, approvals, _, calls = make_executor()
    action = request()
    approval = approvals.grant(action)
    changed = request(destination="mock://different-destination")
    result = executor.execute(changed, approval_id=approval.approval_id)
    assert result.status == "approval_required"
    assert result.reason_code == "approval_scope_mismatch"
    assert calls == []


def test_handler_exception_is_audited_without_exception_message():
    audit = InMemoryAuditLog()
    executor = ControlledExecutor(
        PolicyEngine([PolicyRule(decision=Decision.ALLOW, agent_id="agent-a", operation="read_file", tool_name="mock_tool", target="demo.txt")]),
        ApprovalManager(), lambda _: (_ for _ in ()).throw(RuntimeError("contains secret text")), audit,
    )
    result = executor.execute(request())
    assert result.status == "failed"
    assert result.reason_code == "execution_failed"
    assert all("secret text" not in (event.explanation or "") for event in audit.events)
    assert any(event.event_type == "execution_failed" for event in audit.events)


def test_session_mismatch_in_executor_records_audit_and_halts_execution():
    executor, approvals, audit, calls = make_executor()
    action = request(session_id="session-1")
    approval = approvals.grant(action)
    result = executor.execute(action, approval_id=approval.approval_id, session_id="session-2")
    assert result.status == "approval_required"
    assert result.reason_code == "approval_session_mismatch"
    assert calls == []
    rejected = [e for e in audit.events if e.event_type == "approval_rejected"]
    assert len(rejected) == 1
    assert rejected[0].reason_code == "approval_session_mismatch"
    assert rejected[0].approval_id == approval.approval_id


def test_executor_rejects_supplied_session_when_request_session_is_none():
    executor, approvals, audit, calls = make_executor()
    action = request(session_id=None)
    approval = approvals.grant(action)
    result = executor.execute(action, approval_id=approval.approval_id, session_id="session-1")
    assert result.status == "approval_required"
    assert result.reason_code == "approval_session_mismatch"
    assert calls == []
    rejected = [e for e in audit.events if e.event_type == "approval_rejected"]
    assert len(rejected) == 1
    assert rejected[0].reason_code == "approval_session_mismatch"

