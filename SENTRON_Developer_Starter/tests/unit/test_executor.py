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


def test_missing_or_invalid_approval_prevents_protected_execution():
    executor, approvals, audit, calls = make_executor()
    action = request()

    # 1. Missing approval_id completely
    res1 = executor.execute(action, approval_id=None)
    assert res1.status == "approval_required"
    assert calls == []

    # 2. Non-existent approval_id
    res2 = executor.execute(action, approval_id="non-existent-uuid")
    assert res2.status == "approval_required"
    assert res2.reason_code == "approval_not_found"
    assert calls == []

    # 3. Agent A's approval used by Agent B
    approval_a = approvals.grant(action)
    action_b = request(agent_id="agent-b")
    res3 = executor.execute(action_b, approval_id=approval_a.approval_id)
    assert res3.status == "approval_required"
    assert res3.reason_code == "approval_scope_mismatch"
    assert calls == []


def test_policy_denial_prevents_execution():
    # 1. Always prohibited operation
    executor, _, audit, calls = make_executor()
    res1 = executor.execute(request(operation="disable_security"))
    assert res1.status == "blocked"
    assert res1.reason_code == "prohibited_operation"
    assert calls == []

    # 2. Configured BLOCK rule
    block_rule = PolicyRule(decision=Decision.BLOCK, operation="delete_file", reason_code="admin_block")
    exec_blocked, _, _, calls_blocked = make_executor([block_rule])
    res2 = exec_blocked.execute(request(operation="delete_file"))
    assert res2.status == "blocked"
    assert res2.reason_code == "admin_block"
    assert calls_blocked == []

    # 3. Invalid agent identity fails closed and prevents execution
    class MockInvalidAgent:
        agent_id = "*"
        tool_name = "mock_tool"
        operation = "read_file"
        action_id = "act-bad"
        risk_flags = ()
        session_id = None

    res3 = executor.execute(MockInvalidAgent())
    assert res3.status == "blocked"
    assert res3.reason_code == "invalid_agent_identity"
    assert calls == []


def test_dev1_suspicious_input_risk_triggers_approval_requirement():
    # Even if an ALLOW rule exists for safe_read, Dev1 risk flags require approval
    rule = PolicyRule(
        decision=Decision.ALLOW,
        agent_id="agent-a",
        tool_name="mock_tool",
        operation="read_file",
        target="demo.txt",
    )
    executor, approvals, audit, calls = make_executor([rule])

    # Action with suspicious input risk flag (Dev1 AC-01 integration)
    flagged_action = request(risk_flags=("prompt_injection_pattern",))
    result = executor.execute(flagged_action)
    assert result.status == "approval_required"
    assert result.reason_code == "risk_flags_present"
    assert calls == []

    # When approved specifically with that risk flag, execution proceeds
    approval = approvals.grant(flagged_action)
    approved_res = executor.execute(flagged_action, approval_id=approval.approval_id)
    assert approved_res.status == "executed"
    assert calls == [flagged_action.action_id]


def test_dev1_sensitive_data_triggers_approval_requirement():
    # Confidential data overrides allow rule and requires approval
    rule = PolicyRule(
        decision=Decision.ALLOW,
        agent_id="agent-a",
        tool_name="mock_tool",
        operation="read_file",
        target="demo.txt",
    )
    executor, approvals, audit, calls = make_executor([rule])
    sens_action = request(data_classification="confidential")
    result = executor.execute(sens_action)
    assert result.status == "approval_required"
    assert result.reason_code == "sensitive_data_requires_review"
    assert calls == []


def test_audit_event_records_session_id_consistently():
    executor, approvals, audit, calls = make_executor()
    action = request(session_id="session-trace-42")
    approval = approvals.grant(action, session_id="session-trace-42")
    executor.execute(action, approval_id=approval.approval_id, session_id="session-trace-42")

    # All generated audit events must carry the session_id
    assert len(audit.events) >= 3  # policy_decision, approval_accepted, execution_succeeded
    for event in audit.events:
        assert event.session_id == "session-trace-42"


def test_unknown_policy_decision_blocks_execution_and_handler_not_called():
    class DummyUnknownPolicy:
        def evaluate(self, req):
            class FakeResult:
                decision = "UNKNOWN_MAYBE"
                reason_code = "weird_rule"
                explanation = "Unrecognized decision."
                risk_flags = ()
            return FakeResult()

    calls = []
    audit = InMemoryAuditLog()
    executor = ControlledExecutor(
        policy_engine=DummyUnknownPolicy(),
        approval_manager=ApprovalManager(),
        action_handler=lambda a: calls.append(a.action_id),
        audit_sink=audit,
    )
    result = executor.execute(request())
    assert result.status == "blocked"
    assert result.decision is Decision.BLOCK
    assert result.reason_code == "unknown_policy_decision"
    assert calls == []


def test_handler_never_called_on_any_authorization_failure():
    """AC-09/AC-10: Verify the action handler is never dispatched on any authorization failure."""
    calls = []
    approvals = ApprovalManager()
    audit = InMemoryAuditLog()

    rule = PolicyRule(
        decision=Decision.ALLOW,
        agent_id="agent-legit",
        tool_name="mock_tool",
        operation="read_file",
        target="demo.txt",
    )
    executor = ControlledExecutor(
        policy_engine=PolicyEngine([rule]),
        approval_manager=approvals,
        action_handler=lambda a: calls.append(a.action_id),
        audit_sink=audit,
    )

    legit_req = ActionRequest(
        agent_id="agent-legit",
        tool_name="mock_tool",
        operation="read_file",
        target="demo.txt",
        session_id="sess-1",
    )

    # 1. Prohibited operation (BLOCK)
    executor.execute(request(operation="disable_security"))
    assert calls == []

    # 2. ASK without approval
    unallowed_req = request(agent_id="agent-unallowed")
    executor.execute(unallowed_req, approval_id=None)
    assert calls == []

    # 3. ASK with non-existent approval
    executor.execute(unallowed_req, approval_id="does-not-exist")
    assert calls == []

    # 4. ASK with session mismatch
    unallowed_sess = request(agent_id="agent-unallowed", session_id="sess-1")
    app_sess1 = approvals.grant(unallowed_sess, session_id="sess-1")
    executor.execute(unallowed_sess, approval_id=app_sess1.approval_id, session_id="sess-different")
    assert calls == []

    # 5. ASK with scope mismatch (different agent)
    app_unallowed = approvals.grant(unallowed_req)
    impostor_req = request(agent_id="agent-impostor")
    executor.execute(impostor_req, approval_id=app_unallowed.approval_id)
    assert calls == []

    # 6. Malformed request (None)
    executor.execute(None)
    assert calls == []

    # Verify calls list remained completely untouched throughout all failure modes
    assert calls == []



