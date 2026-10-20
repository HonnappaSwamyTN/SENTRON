from datetime import datetime, timedelta, timezone

import pytest

from sentron.agentguard.approval import ApprovalManager
from sentron.core.models import ActionRequest


def request(**overrides):
    values = dict(
        agent_id="agent-a", tool_name="mock_mail_tool", operation="send_message",
        target="draft-1", recipient="alice@example.test", destination="mock://mailbox",
        purpose="send requested test message", task_id="task-7", session_id="session-1",
    )
    values.update(overrides)
    return ActionRequest(**values)


def test_approval_matches_exact_scope_and_is_single_use_by_default():
    manager = ApprovalManager()
    action = request()
    approval = manager.grant(action, session_id="session-1")
    assert manager.validate_and_consume(approval.approval_id, action, session_id="session-1")[0]
    valid, reason = manager.validate_and_consume(approval.approval_id, action, session_id="session-1")
    assert not valid
    assert reason == "approval_not_found"


def test_changed_destination_requires_new_approval():
    manager = ApprovalManager()
    action = request()
    approval = manager.grant(action, session_id="session-1")
    changed = request(destination="mock://different-mailbox")
    valid, reason = manager.validate_and_consume(approval.approval_id, changed, session_id="session-1")
    assert not valid
    assert reason == "approval_scope_mismatch"


def test_approval_is_bound_to_session_when_requested():
    manager = ApprovalManager()
    action = request()
    approval = manager.grant(action, session_id="session-1")
    valid, reason = manager.validate_and_consume(approval.approval_id, action, session_id="session-2")
    assert not valid
    assert reason == "approval_session_mismatch"


def test_expired_approval_is_rejected():
    manager = ApprovalManager()
    action = request()
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    approval = manager.grant(action, ttl_seconds=5, now=now)
    valid, reason = manager.validate_and_consume(
        approval.approval_id, action, session_id="session-1", now=now + timedelta(seconds=6)
    )
    assert not valid
    assert reason == "approval_expired"


def test_changed_untrusted_context_requires_new_approval():
    manager = ApprovalManager()
    action = request(untrusted_context_refs=("context-a",))
    approval = manager.grant(action)
    changed = request(untrusted_context_refs=("context-b",))
    valid, reason = manager.validate_and_consume(approval.approval_id, changed)
    assert not valid
    assert reason == "approval_scope_mismatch"


def test_request_session_is_used_when_granting_and_validating():
    manager = ApprovalManager()
    action = request(session_id="session-1")
    approval = manager.grant(action)
    assert manager.validate_and_consume(approval.approval_id, action, session_id="session-1")[0]


def test_supplied_session_mismatch_rejected_when_request_session_is_none():
    manager = ApprovalManager()
    action = request(session_id=None)
    approval = manager.grant(action)
    valid, reason = manager.validate_and_consume(approval.approval_id, action, session_id="session-1")
    assert not valid
    assert reason == "approval_session_mismatch"


def test_grant_rejects_session_mismatch_when_request_session_is_none():
    manager = ApprovalManager()
    action = request(session_id=None)
    with pytest.raises(ValueError, match="session_id must match the action request session"):
        manager.grant(action, session_id="session-1")


def test_valid_approval_permits_only_intended_action():
    manager = ApprovalManager()
    action = request(session_id="sess-xyz")
    approval = manager.grant(action, session_id="sess-xyz")

    # Valid consumption for exact matching request
    valid, reason = manager.validate_and_consume(approval.approval_id, action, session_id="sess-xyz")
    assert valid is True
    assert reason == "approval_valid"

    # Subsequent consumption fails (single-use)
    valid2, reason2 = manager.validate_and_consume(approval.approval_id, action, session_id="sess-xyz")
    assert valid2 is False
    assert reason2 == "approval_not_found"


def test_approval_with_mismatched_session_is_rejected():
    manager = ApprovalManager()
    action_sess_1 = request(session_id="session-alpha")
    approval = manager.grant(action_sess_1, session_id="session-alpha")

    # Request presents session-beta
    action_sess_2 = request(session_id="session-beta")
    valid, reason = manager.validate_and_consume(approval.approval_id, action_sess_2, session_id="session-beta")
    assert valid is False
    assert reason == "approval_session_mismatch"


def test_missing_request_session_cannot_be_bypassed_by_supplying_unrelated_session_id():
    manager = ApprovalManager()
    action_no_session = request(session_id=None)
    approval = manager.grant(action_no_session)

    # Caller tries to supply an unrelated session ID during validation
    valid, reason = manager.validate_and_consume(
        approval.approval_id, action_no_session, session_id="unrelated-session-123"
    )
    assert valid is False
    assert reason == "approval_session_mismatch"

    # Conversely, if an approval was granted for session-1, a sessionless request cannot consume it
    action_with_session = request(session_id="session-1")
    app_with_sess = manager.grant(action_with_session)
    valid2, reason2 = manager.validate_and_consume(app_with_sess.approval_id, action_no_session)
    assert valid2 is False
    assert reason2 == "approval_session_mismatch"


def test_approval_for_one_action_cannot_authorize_another_action():
    manager = ApprovalManager()
    original_action = request(
        agent_id="agent-sender",
        tool_name="mock_mail_tool",
        operation="send_message",
        target="draft-42",
        recipient="alice@company.test",
        purpose="legitimate business communication",
        session_id="sess-99",
    )
    approval = manager.grant(original_action, session_id="sess-99")

    # 1. Different agent cannot use Agent A's approval
    agent_b_action = request(
        agent_id="agent-impostor",
        tool_name="mock_mail_tool",
        operation="send_message",
        target="draft-42",
        recipient="alice@company.test",
        purpose="legitimate business communication",
        session_id="sess-99",
    )
    v1, r1 = manager.validate_and_consume(approval.approval_id, agent_b_action, session_id="sess-99")
    assert v1 is False
    assert r1 == "approval_scope_mismatch"

    # 2. Mutated recipient cannot be authorized
    mutated_recipient = request(
        agent_id="agent-sender",
        tool_name="mock_mail_tool",
        operation="send_message",
        target="draft-42",
        recipient="exfiltration@evil.test",
        purpose="legitimate business communication",
        session_id="sess-99",
    )
    v2, r2 = manager.validate_and_consume(approval.approval_id, mutated_recipient, session_id="sess-99")
    assert v2 is False
    assert r2 == "approval_scope_mismatch"

    # 3. Mutated operation cannot be authorized
    mutated_operation = request(
        agent_id="agent-sender",
        tool_name="mock_mail_tool",
        operation="delete_message",
        target="draft-42",
        recipient="alice@company.test",
        purpose="legitimate business communication",
        session_id="sess-99",
    )
    v3, r3 = manager.validate_and_consume(approval.approval_id, mutated_operation, session_id="sess-99")
    assert v3 is False
    assert r3 == "approval_scope_mismatch"

    # 4. Mutated target cannot be authorized
    mutated_target = request(
        agent_id="agent-sender",
        tool_name="mock_mail_tool",
        operation="send_message",
        target="different_draft_999",
        recipient="alice@company.test",
        purpose="legitimate business communication",
        session_id="sess-99",
    )
    v4, r4 = manager.validate_and_consume(approval.approval_id, mutated_target, session_id="sess-99")
    assert v4 is False
    assert r4 == "approval_scope_mismatch"

    # 5. Injection risk flag added dynamically cannot be authorized by previous benign approval
    mutated_risk = request(
        agent_id="agent-sender",
        tool_name="mock_mail_tool",
        operation="send_message",
        target="draft-42",
        recipient="alice@company.test",
        purpose="legitimate business communication",
        session_id="sess-99",
        risk_flags=("prompt_injection_pattern",),
    )
    v5, r5 = manager.validate_and_consume(approval.approval_id, mutated_risk, session_id="sess-99")
    assert v5 is False
    assert r5 == "approval_scope_mismatch"


def test_malformed_approval_requests_fail_safely():
    manager = ApprovalManager()
    action = request()

    # Empty approval_id
    v1, r1 = manager.validate_and_consume("", action)
    assert v1 is False
    assert r1 == "approval_not_found"

    # Whitespace approval_id
    v2, r2 = manager.validate_and_consume("   ", action)
    assert v2 is False
    assert r2 == "approval_not_found"

    # None request
    v3, r3 = manager.validate_and_consume("any-id", None)
    assert v3 is False
    assert r3 == "malformed_request"

    # Missing tool_name in request
    class MockNoTool:
        agent_id = "agent-a"
        tool_name = ""
        operation = "send_message"

    v4, r4 = manager.validate_and_consume("any-id", MockNoTool())
    assert v4 is False
    assert r4 == "malformed_request"


def test_expired_and_reused_approvals():
    manager = ApprovalManager()
    base_time = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    action = request()

    # 1. Expired approval
    app_exp = manager.grant(action, ttl_seconds=10, now=base_time)
    past_time = base_time + timedelta(seconds=11)
    v1, r1 = manager.validate_and_consume(app_exp.approval_id, action, now=past_time)
    assert v1 is False
    assert r1 == "approval_expired"

    # 2. Reused approval
    app_single = manager.grant(action, ttl_seconds=60, now=base_time)
    v2, r2 = manager.validate_and_consume(app_single.approval_id, action, now=base_time)
    assert v2 is True
    assert r2 == "approval_valid"
    # Re-use immediately rejected
    v3, r3 = manager.validate_and_consume(app_single.approval_id, action, now=base_time)
    assert v3 is False
    assert r3 == "approval_not_found"


def test_grant_rejects_missing_identity_or_tools():
    manager = ApprovalManager()
    with pytest.raises(ValueError, match="request must be provided"):
        manager.grant(None)

    class MockBadAgent:
        agent_id = "   "
        tool_name = "mail_tool"
        operation = "send_message"
        session_id = None

    with pytest.raises(ValueError, match="agent_id"):
        manager.grant(MockBadAgent())




