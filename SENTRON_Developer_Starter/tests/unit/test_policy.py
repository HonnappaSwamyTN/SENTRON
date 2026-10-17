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
