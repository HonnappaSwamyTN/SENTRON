import pytest

from sentron.agentguard.policy import PolicyEngine, PolicyRule
from sentron.core.models import ActionRequest, Decision


def request(**overrides):
    values = dict(agent_id="agent-a", tool_name="mock_file_tool", operation="read_file", target="notes.txt")
    values.update(overrides)
    return ActionRequest(**values)


def safe_read_allow_rule(**overrides):
    values = dict(
        decision=Decision.ALLOW,
        agent_id="agent-a",
        tool_name="mock_file_tool",
        operation="read_file",
        target="notes.txt",
        reason_code="safe_read",
        explanation="Read-only mock operation is allowed.",
    )
    values.update(overrides)
    return PolicyRule(**values)


def test_unknown_action_defaults_to_ask():
    result = PolicyEngine().evaluate(request())
    assert result.decision is Decision.ASK
    assert result.reason_code == "no_matching_allow_rule"


def test_explicit_agent_and_target_scoped_allow_rule_allows_matching_action():
    engine = PolicyEngine([safe_read_allow_rule()])
    assert engine.evaluate(request()).decision is Decision.ALLOW


def test_allow_rule_does_not_apply_to_a_different_agent():
    engine = PolicyEngine([safe_read_allow_rule()])
    result = engine.evaluate(request(agent_id="agent-b"))
    assert result.decision is Decision.ASK
    assert result.reason_code == "no_matching_allow_rule"


def test_allow_rule_rejects_missing_agent_scope():
    with pytest.raises(ValueError, match="agent_id"):
        PolicyRule(
            decision=Decision.ALLOW,
            tool_name="mock_file_tool",
            operation="read_file",
            target="notes.txt",
        )


def test_allow_rule_rejects_wildcard_target_for_file_operation():
    with pytest.raises(ValueError, match="must specify a target"):
        PolicyRule(
            decision=Decision.ALLOW,
            agent_id="agent-a",
            tool_name="mock_file_tool",
            operation="read_file",
        )


def test_allow_rule_rejects_rules_without_target_or_destination():
    with pytest.raises(ValueError, match="target or destination"):
        PolicyRule(
            decision=Decision.ALLOW,
            agent_id="agent-a",
            tool_name="mock_file_tool",
            operation="list_status",
        )


def test_risk_flag_overrides_allow_rule():
    engine = PolicyEngine([safe_read_allow_rule()])
    result = engine.evaluate(request(risk_flags=("prompt_injection_pattern",)))
    assert result.decision is Decision.ASK
    assert result.reason_code == "risk_flags_present"


def test_sensitive_data_overrides_allow_rule():
    engine = PolicyEngine([safe_read_allow_rule()])
    result = engine.evaluate(request(data_classification="confidential"))
    assert result.decision is Decision.ASK
    assert result.reason_code == "sensitive_data_requires_review"


def test_prohibited_operation_is_blocked():
    result = PolicyEngine().evaluate(request(operation="disable_security"))
    assert result.decision is Decision.BLOCK
    assert result.reason_code == "prohibited_operation"


def test_block_rule_wins_over_allow_rule():
    engine = PolicyEngine([
        safe_read_allow_rule(),
        PolicyRule(decision=Decision.BLOCK, operation="read_file", reason_code="blocked_by_admin"),
    ])
    result = engine.evaluate(request())
    assert result.decision is Decision.BLOCK
    assert result.reason_code == "blocked_by_admin"


def test_agent_can_use_own_narrowly_scoped_allowed_permission():
    rule = PolicyRule(
        decision=Decision.ALLOW,
        agent_id="agent-finance",
        tool_name="ledger_tool",
        operation="read_file",
        target="q4_budget.xlsx",
        reason_code="finance_audit_read",
        explanation="Finance agent permitted to read Q4 budget.",
    )
    engine = PolicyEngine([rule])
    req = ActionRequest(
        agent_id="agent-finance",
        tool_name="ledger_tool",
        operation="read_file",
        target="q4_budget.xlsx",
    )
    result = engine.evaluate(req)
    assert result.decision is Decision.ALLOW
    assert result.reason_code == "finance_audit_read"


def test_agent_a_permission_cannot_authorize_agent_b():
    rule = PolicyRule(
        decision=Decision.ALLOW,
        agent_id="agent-a",
        tool_name="ledger_tool",
        operation="read_file",
        target="q4_budget.xlsx",
    )
    engine = PolicyEngine([rule])
    req_b = ActionRequest(
        agent_id="agent-b",
        tool_name="ledger_tool",
        operation="read_file",
        target="q4_budget.xlsx",
    )
    result = engine.evaluate(req_b)
    assert result.decision is Decision.ASK
    assert result.reason_code == "no_matching_allow_rule"


def test_overly_broad_allow_rules_rejected_or_denied():
    # Wildcard in agent_id
    with pytest.raises(ValueError, match="ALLOW rules cannot contain wildcards"):
        PolicyRule(
            decision=Decision.ALLOW,
            agent_id="*",
            tool_name="file_tool",
            operation="read_file",
            target="report.txt",
        )

    # Broad term 'all' in agent_id
    with pytest.raises(ValueError, match="ALLOW rules cannot contain wildcards"):
        PolicyRule(
            decision=Decision.ALLOW,
            agent_id="all",
            tool_name="file_tool",
            operation="read_file",
            target="report.txt",
        )

    # Wildcard in tool_name
    with pytest.raises(ValueError, match="ALLOW rules cannot contain wildcards"):
        PolicyRule(
            decision=Decision.ALLOW,
            agent_id="agent-a",
            tool_name="*",
            operation="read_file",
            target="report.txt",
        )

    # Wildcard in operation
    with pytest.raises(ValueError, match="ALLOW rules cannot contain wildcards"):
        PolicyRule(
            decision=Decision.ALLOW,
            agent_id="agent-a",
            tool_name="file_tool",
            operation="*",
            target="report.txt",
        )

    # Wildcard in target
    with pytest.raises(ValueError, match="ALLOW rules cannot contain wildcards"):
        PolicyRule(
            decision=Decision.ALLOW,
            agent_id="agent-a",
            tool_name="file_tool",
            operation="read_file",
            target="*",
        )

    # Wildcard in destination
    with pytest.raises(ValueError, match="ALLOW rules cannot contain wildcards"):
        PolicyRule(
            decision=Decision.ALLOW,
            agent_id="agent-a",
            tool_name="mail_tool",
            operation="send_message",
            destination="*",
        )

    # Empty string target
    with pytest.raises(ValueError, match="must specify a target"):
        PolicyRule(
            decision=Decision.ALLOW,
            agent_id="agent-a",
            tool_name="file_tool",
            operation="read_file",
            target="   ",
        )


def test_missing_or_invalid_agent_id_cannot_bypass_authorization():
    # Model construction rejects empty/whitespace agent_id
    with pytest.raises(ValueError, match="agent_id must be a non-empty string"):
        ActionRequest(agent_id="", tool_name="tool", operation="read_file")

    with pytest.raises(ValueError, match="agent_id must be a non-empty string"):
        ActionRequest(agent_id="   ", tool_name="tool", operation="read_file")

    # If a bypassed/duck-typed object with wildcard/invalid agent_id is passed to PolicyEngine:
    class MockBypassRequest:
        agent_id = "*"
        tool_name = "tool"
        operation = "read_file"
        target = "file.txt"
        risk_flags = ()
        session_id = None

    engine = PolicyEngine([safe_read_allow_rule()])
    result = engine.evaluate(MockBypassRequest())
    assert result.decision is Decision.BLOCK
    assert result.reason_code == "invalid_agent_identity"

    class MockNoneAgentRequest:
        agent_id = None
        tool_name = "tool"
        operation = "read_file"
        target = "file.txt"
        risk_flags = ()
        session_id = None

    result_none = engine.evaluate(MockNoneAgentRequest())
    assert result_none.decision is Decision.BLOCK
    assert result_none.reason_code == "invalid_agent_identity"


def test_malformed_requests_fail_safely():
    engine = PolicyEngine([safe_read_allow_rule()])

    # None request
    res_none = engine.evaluate(None)
    assert res_none.decision is Decision.BLOCK
    assert res_none.reason_code == "malformed_request"

    # Missing tool_name
    class MockNoTool:
        agent_id = "agent-a"
        tool_name = ""
        operation = "read_file"
        risk_flags = ()

    res_no_tool = engine.evaluate(MockNoTool())
    assert res_no_tool.decision is Decision.BLOCK
    assert res_no_tool.reason_code == "malformed_request"

    # Missing operation
    class MockNoOp:
        agent_id = "agent-a"
        tool_name = "mock_tool"
        operation = "  "
        risk_flags = ()

    res_no_op = engine.evaluate(MockNoOp())
    assert res_no_op.decision is Decision.BLOCK
    assert res_no_op.reason_code == "malformed_request"

    # Wildcard in tool_name or operation
    class MockWildcardTool:
        agent_id = "agent-a"
        tool_name = "mock_*"
        operation = "read_file"
        risk_flags = ()

    res_wildcard_tool = engine.evaluate(MockWildcardTool())
    assert res_wildcard_tool.decision is Decision.BLOCK
    assert res_wildcard_tool.reason_code == "malformed_request"


def test_distinct_agent_identities_not_silently_normalized():
    # ALLOW rule specifically for 'agent-alpha'
    rule = PolicyRule(
        decision=Decision.ALLOW,
        agent_id="agent-alpha",
        tool_name="file_tool",
        operation="read_file",
        target="data.txt",
    )
    engine = PolicyEngine([rule])

    # Distinct casing 'Agent-Alpha' must NOT match 'agent-alpha'
    req_upper = ActionRequest(
        agent_id="Agent-Alpha",
        tool_name="file_tool",
        operation="read_file",
        target="data.txt",
    )
    res_upper = engine.evaluate(req_upper)
    assert res_upper.decision is Decision.ASK
    assert res_upper.reason_code == "no_matching_allow_rule"

    # Distinct identity with suffix
    req_other = ActionRequest(
        agent_id="agent-alpha-2",
        tool_name="file_tool",
        operation="read_file",
        target="data.txt",
    )
    res_other = engine.evaluate(req_other)
    assert res_other.decision is Decision.ASK
    assert res_other.reason_code == "no_matching_allow_rule"


